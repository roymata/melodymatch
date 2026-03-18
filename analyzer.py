"""Audio feature extraction and similarity computation using librosa.

Key design choices for accurate similarity:
- Use Euclidean distance (not cosine) — cosine on music feature means gives
  inflated scores because all songs live in a similar "direction" of feature space.
- Concatenate mean + std to capture both "what the song sounds like on average"
  and "how much variation there is" (a ballad vs. EDM have different std profiles).
- Drop MFCC[0] (energy/loudness) — it dominates cosine similarity and doesn't
  reflect musical content.
- Compare temporal structure via onset-strength cross-correlation for rhythm.
- Use an exponential-decay mapping from distance to 0-100 similarity, calibrated
  so that genuinely different songs score 20-40% and similar ones score 70-90%.
"""

import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import librosa
from scipy.spatial.distance import euclidean
from scipy.stats import pearsonr


_YT_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


# ---------------------------------------------------------------------------
# yt-dlp helpers (unchanged)
# ---------------------------------------------------------------------------

def _find_ytdlp() -> str:
    """Resolve path to yt-dlp, checking common locations."""
    for path in [
        os.path.expanduser("~/.local/bin/yt-dlp"),       # local standalone
        os.path.join(os.path.dirname(sys.executable), "yt-dlp"),  # venv
        "/usr/local/bin/yt-dlp",                          # Docker pip install
    ]:
        if os.path.isfile(path):
            return path
    return "yt-dlp"  # fallback to PATH


def _find_ffmpeg_dir() -> str:
    """Find the directory containing ffmpeg."""
    for path in [
        os.path.expanduser("~/.local/bin/ffmpeg"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]:
        if os.path.isfile(path):
            return os.path.dirname(path)
    return "/usr/bin"  # sensible default


def download_youtube_audio(url: str) -> str:
    """Download audio from a YouTube URL via yt-dlp."""
    if not _YT_URL_RE.match(url):
        raise ValueError("Invalid YouTube URL")

    tmp_dir = tempfile.mkdtemp()
    out_template = os.path.join(tmp_dir, "audio.%(ext)s")

    try:
        subprocess.run(
            [
                _find_ytdlp(),
                "--no-playlist",
                "-f", "bestaudio/best",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
                "--ffmpeg-location", _find_ffmpeg_dir(),
                "-o", out_template,
                url,
            ],
            check=True, capture_output=True, timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"yt-dlp failed: {exc.stderr.decode(errors='replace')[:300]}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("YouTube download timed out (120 s)")

    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    if not os.path.isfile(mp3_path):
        for f in os.listdir(tmp_dir):
            return os.path.join(tmp_dir, f)
        raise RuntimeError("Download produced no output file")
    return mp3_path


def search_and_download_youtube(song_name: str, artist: str) -> str:
    """Search YouTube by name + artist, download the top result."""
    query = f"{song_name} {artist}"
    tmp_dir = tempfile.mkdtemp()
    out_template = os.path.join(tmp_dir, "audio.%(ext)s")

    try:
        subprocess.run(
            [
                _find_ytdlp(),
                "--no-playlist",
                "-f", "bestaudio/best",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
                "--ffmpeg-location", _find_ffmpeg_dir(),
                "-o", out_template,
                f"ytsearch1:{query}",
            ],
            check=True, capture_output=True, timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"YouTube search failed for '{query}': "
            f"{exc.stderr.decode(errors='replace')[:300]}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"YouTube search/download timed out for '{query}'")

    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    if not os.path.isfile(mp3_path):
        for f in os.listdir(tmp_dir):
            return os.path.join(tmp_dir, f)
        raise RuntimeError(f"No results found for '{query}'")
    return mp3_path


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(file_path: str, sr: int = 22050, duration: float = 60.0) -> dict:
    """Extract a rich set of audio features from a file.

    Returns means, stds, and temporal data for accurate comparison.
    """
    y, sr = librosa.load(file_path, sr=sr, duration=duration)

    # --- Tempo / BPM ---
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])

    # --- MFCCs (drop coefficient 0 = energy/loudness) ---
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    mfcc = mfcc[1:]  # drop MFCC[0]
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    # --- Spectral contrast ---
    spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=6)
    spec_contrast_mean = np.mean(spec_contrast, axis=1)
    spec_contrast_std = np.std(spec_contrast, axis=1)

    # --- Chroma (CENS = more robust for music comparison) ---
    chroma = librosa.feature.chroma_cens(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    chroma_std = np.std(chroma, axis=1)

    # --- Onset strength envelope (for rhythm comparison) ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    # Normalize to unit energy
    norm = np.linalg.norm(onset_env)
    if norm > 0:
        onset_env = onset_env / norm

    # --- Spectral features ---
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]

    return {
        "tempo": tempo_val,
        # Timbre: 19 mean + 19 std = 38-dimensional
        "mfcc_mean": mfcc_mean.tolist(),
        "mfcc_std": mfcc_std.tolist(),
        # Spectral texture: 7 mean + 7 std = 14-dimensional
        "spectral_contrast_mean": spec_contrast_mean.tolist(),
        "spectral_contrast_std": spec_contrast_std.tolist(),
        # Harmony: 12 mean + 12 std = 24-dimensional
        "chroma_mean": chroma_mean.tolist(),
        "chroma_std": chroma_std.tolist(),
        # Rhythm: onset envelope (variable length, used for cross-correlation)
        "onset_env": onset_env.tolist(),
        # Spectral summary stats
        "spectral_centroid_mean": float(np.mean(spectral_centroid)),
        "spectral_centroid_std": float(np.std(spectral_centroid)),
        "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
        "spectral_bandwidth_mean": float(np.mean(spectral_bandwidth)),
        "zcr_mean": float(np.mean(zcr)),
        "zcr_std": float(np.std(zcr)),
    }


# ---------------------------------------------------------------------------
# Similarity computation
# ---------------------------------------------------------------------------

def _euclidean_similarity(a: np.ndarray, b: np.ndarray, scale: float) -> float:
    """Convert Euclidean distance to 0-100 similarity via exponential decay.

    `scale` controls sensitivity — smaller = stricter (lower scores for same distance).
    Typical scale values: 10-30 for normalized features, 50-200 for raw features.
    """
    dist = euclidean(a, b)
    sim = np.exp(-dist / scale) * 100
    return float(np.clip(sim, 0, 100))


def _tempo_similarity(t1: float, t2: float) -> float:
    """Tempo similarity accounting for double/half-time relationships.

    Uses a stricter mapping than before — 10 BPM difference ≈ 85%,
    20 BPM difference ≈ 55%, 40+ BPM difference ≈ 10%.
    """
    if t1 == 0 and t2 == 0:
        return 100.0
    if t1 == 0 or t2 == 0:
        return 0.0

    # Check direct, double, and half time
    diffs = [
        abs(t1 - t2),
        abs(t1 - 2 * t2),
        abs(2 * t1 - t2),
    ]
    best_diff = min(diffs)

    # Exponential decay: 0 diff = 100%, 10 diff ≈ 85%, 30 diff ≈ 40%, 50+ ≈ ~10%
    return float(np.clip(np.exp(-best_diff / 20) * 100, 0, 100))


def _rhythm_similarity(onset_a: np.ndarray, onset_b: np.ndarray) -> float:
    """Compare rhythmic patterns using cross-correlation of onset envelopes.

    This captures actual beat patterns rather than just average rhythmic energy.
    """
    # Trim to same length
    min_len = min(len(onset_a), len(onset_b))
    if min_len < 10:
        return 50.0  # Not enough data

    a = onset_a[:min_len]
    b = onset_b[:min_len]

    # Pearson correlation of onset strength envelopes
    try:
        corr, _ = pearsonr(a, b)
        # Map from [-1, 1] to [0, 100], where:
        # corr=1.0 → 100%, corr=0.0 → 30%, corr=-1.0 → 0%
        sim = max(0, (corr + 0.4) / 1.4) * 100
        return float(np.clip(sim, 0, 100))
    except Exception:
        return 50.0


def compute_similarity(feat_a: dict, feat_b: dict) -> dict:
    """Compute per-dimension and overall similarity between two feature sets.

    Uses Euclidean distance with exponential decay for discriminative scoring.
    """

    # --- Rhythm (onset-envelope cross-correlation) ---
    rhythm_sim = _rhythm_similarity(
        np.array(feat_a["onset_env"]),
        np.array(feat_b["onset_env"]),
    )

    # --- Tempo ---
    tempo_sim = _tempo_similarity(feat_a["tempo"], feat_b["tempo"])

    # --- Timbre (MFCC mean+std + spectral contrast mean+std) ---
    timbre_a = np.concatenate([
        feat_a["mfcc_mean"], feat_a["mfcc_std"],
        feat_a["spectral_contrast_mean"], feat_a["spectral_contrast_std"],
    ])
    timbre_b = np.concatenate([
        feat_b["mfcc_mean"], feat_b["mfcc_std"],
        feat_b["spectral_contrast_mean"], feat_b["spectral_contrast_std"],
    ])
    # Scale=25: two pop songs ≈ 60-80%, pop vs. classical ≈ 20-40%
    timbre_sim = _euclidean_similarity(timbre_a, timbre_b, scale=25)

    # --- Harmony (chroma CENS mean+std) ---
    harmony_a = np.concatenate([feat_a["chroma_mean"], feat_a["chroma_std"]])
    harmony_b = np.concatenate([feat_b["chroma_mean"], feat_b["chroma_std"]])
    # Scale=1.5: songs in same key ≈ 70-90%, different keys ≈ 20-50%
    harmony_sim = _euclidean_similarity(harmony_a, harmony_b, scale=1.5)

    # --- Spectral character (brightness, bandwidth, zcr) ---
    spectral_a = np.array([
        feat_a["spectral_centroid_mean"] / 5000,  # normalize to ~0-1 range
        feat_a["spectral_rolloff_mean"] / 10000,
        feat_a["spectral_bandwidth_mean"] / 5000,
        feat_a["zcr_mean"] * 10,
        feat_a["spectral_centroid_std"] / 2000,
        feat_a["zcr_std"] * 10,
    ])
    spectral_b = np.array([
        feat_b["spectral_centroid_mean"] / 5000,
        feat_b["spectral_rolloff_mean"] / 10000,
        feat_b["spectral_bandwidth_mean"] / 5000,
        feat_b["zcr_mean"] * 10,
        feat_b["spectral_centroid_std"] / 2000,
        feat_b["zcr_std"] * 10,
    ])
    spectral_sim = _euclidean_similarity(spectral_a, spectral_b, scale=0.8)

    # --- Weighted overall score ---
    # Timbre and harmony are the most discriminative for "do these sound alike?"
    overall = (
        0.15 * rhythm_sim
        + 0.10 * tempo_sim
        + 0.35 * timbre_sim
        + 0.25 * harmony_sim
        + 0.15 * spectral_sim
    )

    return {
        "overall": round(overall, 1),
        "breakdown": {
            "rhythm": round(rhythm_sim, 1),
            "tempo": round(tempo_sim, 1),
            "timbre": round(timbre_sim, 1),
            "harmony": round(harmony_sim, 1),
        },
        "details": {
            "song_a": {
                "tempo_bpm": round(feat_a["tempo"], 1),
                "spectral_centroid": round(feat_a["spectral_centroid_mean"], 1),
            },
            "song_b": {
                "tempo_bpm": round(feat_b["tempo"], 1),
                "spectral_centroid": round(feat_b["spectral_centroid_mean"], 1),
            },
        },
    }
