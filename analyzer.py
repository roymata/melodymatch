"""Audio feature extraction and similarity computation using librosa.

PERFORMANCE-OPTIMIZED for Render free tier (0.1 CPU / 512 MB RAM):
- 15 seconds of audio (iTunes previews are 30s, 15s is plenty for features)
- 16 kHz sample rate (down from 22050 — still captures all music-relevant frequencies)
- hop_length=1024 (double default — halves the number of frames to process)
- 14 MFCCs (drop [0]) instead of 20 — still captures timbre accurately
- chroma_stft instead of chroma_cens (much faster, nearly as good for comparison)
- Combined: ~10-15x faster than the original 60s/22050Hz/512hop configuration

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

import numpy as np
import librosa
from scipy.spatial.distance import euclidean
from scipy.stats import pearsonr


# ---------------------------------------------------------------------------
# Feature extraction (optimized for speed)
# ---------------------------------------------------------------------------

def extract_features(file_path: str, sr: int = 16000, duration: float = 15.0) -> dict:
    """Extract a rich set of audio features from a file.

    Optimized defaults:
      sr=16000      — 27% less data vs 22050, still covers all music frequencies
      duration=15.0 — 75% less data vs 60s, 15s captures enough structure
      hop_length=1024 — 50% fewer frames vs default 512

    Returns means, stds, and temporal data for accurate comparison.
    """
    y, sr = librosa.load(file_path, sr=sr, duration=duration)

    hop = 1024

    # --- Tempo / BPM ---
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    tempo_val = float(np.atleast_1d(tempo)[0])

    # --- MFCCs (drop coefficient 0 = energy/loudness) ---
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=14, hop_length=hop)
    mfcc = mfcc[1:]  # drop MFCC[0] → 13 coefficients
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    # --- Spectral contrast ---
    spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=6, hop_length=hop)
    spec_contrast_mean = np.mean(spec_contrast, axis=1)
    spec_contrast_std = np.std(spec_contrast, axis=1)

    # --- Chroma (STFT — faster than CENS, good for key/chord comparison) ---
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop)
    chroma_mean = np.mean(chroma, axis=1)
    chroma_std = np.std(chroma, axis=1)

    # --- Onset strength envelope (for rhythm comparison) ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    norm = np.linalg.norm(onset_env)
    if norm > 0:
        onset_env = onset_env / norm

    # --- Spectral features ---
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop)[0]
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop)[0]
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop)[0]

    return {
        "tempo": tempo_val,
        # Timbre: 13 mean + 13 std = 26-dimensional
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
    """
    dist = euclidean(a, b)
    sim = np.exp(-dist / scale) * 100
    return float(np.clip(sim, 0, 100))


def _tempo_similarity(t1: float, t2: float) -> float:
    """Tempo similarity accounting for double/half-time relationships."""
    if t1 == 0 and t2 == 0:
        return 100.0
    if t1 == 0 or t2 == 0:
        return 0.0

    diffs = [
        abs(t1 - t2),
        abs(t1 - 2 * t2),
        abs(2 * t1 - t2),
    ]
    best_diff = min(diffs)
    return float(np.clip(np.exp(-best_diff / 20) * 100, 0, 100))


def _rhythm_similarity(onset_a: np.ndarray, onset_b: np.ndarray) -> float:
    """Compare rhythmic patterns using cross-correlation of onset envelopes."""
    min_len = min(len(onset_a), len(onset_b))
    if min_len < 10:
        return 50.0

    a = onset_a[:min_len]
    b = onset_b[:min_len]

    try:
        corr, _ = pearsonr(a, b)
        sim = max(0, (corr + 0.4) / 1.4) * 100
        return float(np.clip(sim, 0, 100))
    except Exception:
        return 50.0


def compute_similarity(feat_a: dict, feat_b: dict, lyrics_sim: float | None = None) -> dict:
    """Compute per-dimension and overall similarity between two feature sets.

    Args:
        feat_a, feat_b: Audio feature dicts from extract_features().
        lyrics_sim: Optional lyrics similarity score (0-100) from
                    compute_lyrics_similarity(). None if unavailable.
    """

    # --- Rhythm ---
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
    timbre_sim = _euclidean_similarity(timbre_a, timbre_b, scale=20)

    # --- Harmony (chroma STFT mean+std) ---
    harmony_a = np.concatenate([feat_a["chroma_mean"], feat_a["chroma_std"]])
    harmony_b = np.concatenate([feat_b["chroma_mean"], feat_b["chroma_std"]])
    harmony_sim = _euclidean_similarity(harmony_a, harmony_b, scale=2.0)

    # --- Spectral character ---
    spectral_a = np.array([
        feat_a["spectral_centroid_mean"] / 5000,
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

    # --- Weighted overall score (lyrics dimension is optional) ---
    base_weights = {
        "rhythm":   0.15,
        "tempo":    0.10,
        "timbre":   0.30,
        "harmony":  0.20,
        "spectral": 0.15,
        "lyrics":   0.10,
    }
    scores = {
        "rhythm":   rhythm_sim,
        "tempo":    tempo_sim,
        "timbre":   timbre_sim,
        "harmony":  harmony_sim,
        "spectral": spectral_sim,
        "lyrics":   lyrics_sim,  # may be None
    }

    # Filter out None dimensions and renormalize weights to sum to 1.0
    active = {k: v for k, v in scores.items() if v is not None}
    total_weight = sum(base_weights[k] for k in active)
    overall = sum(base_weights[k] / total_weight * active[k] for k in active)

    return {
        "overall": round(overall, 1),
        "breakdown": {
            "rhythm": round(rhythm_sim, 1),
            "tempo": round(tempo_sim, 1),
            "timbre": round(timbre_sim, 1),
            "harmony": round(harmony_sim, 1),
            "lyrics": round(lyrics_sim, 1) if lyrics_sim is not None else None,
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
