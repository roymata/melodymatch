"""Audio feature extraction and similarity — ZERO librosa dependency.

Uses only numpy + scipy + soundfile for 10-50x faster analysis on weak CPUs.
librosa pulls in numba/llvmlite/JIT which is far too heavy for Render free tier.

All spectral features are computed from a single STFT pass using numpy.fft.
Audio loading uses soundfile (native C, instant for WAV) with ffmpeg fallback.
"""

import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy.fft import dct
from scipy.spatial.distance import euclidean
from scipy.stats import pearsonr


# ---------------------------------------------------------------------------
# Audio loading
# ---------------------------------------------------------------------------

def _find_ffmpeg() -> str:
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(path):
            return path
    return "ffmpeg"


def _load_audio(file_path: str, sr: int = 11025, duration: float = 8.0):
    """Load audio file as mono float32 at target sample rate.

    Uses soundfile for WAV (instant), falls back to ffmpeg for other formats.
    """
    try:
        y, file_sr = sf.read(file_path, dtype="float32")
        if y.ndim > 1:
            y = y.mean(axis=1)
        if file_sr == sr:
            return y[: int(duration * sr)], sr
    except Exception:
        pass

    # Fallback: convert via ffmpeg (handles mp3, m4a, ogg, etc.)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            [_find_ffmpeg(), "-i", file_path, "-vn", "-ac", "1",
             "-ar", str(sr), "-t", str(duration),
             "-y", "-loglevel", "error", tmp.name],
            check=True, capture_output=True, timeout=30,
        )
        y, _ = sf.read(tmp.name, dtype="float32")
        return y, sr
    finally:
        if os.path.isfile(tmp.name):
            os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Spectrogram helpers (numpy-only, vectorized)
# ---------------------------------------------------------------------------

def _stft(y: np.ndarray, n_fft: int = 1024, hop: int = 512) -> np.ndarray:
    """Compute magnitude STFT using stride tricks (no Python loops)."""
    window = np.hanning(n_fft).astype(np.float32)
    n_frames = max(1, 1 + (len(y) - n_fft) // hop)

    # Create overlapping frames via stride tricks — fully vectorized
    shape = (n_frames, n_fft)
    strides = (y.strides[0] * hop, y.strides[0])
    frames = np.lib.stride_tricks.as_strided(y, shape=shape, strides=strides)

    windowed = frames * window
    return np.abs(np.fft.rfft(windowed, axis=1)).T  # (n_fft//2+1, n_frames)


def _mel_filterbank(sr: int, n_fft: int, n_mels: int = 40) -> np.ndarray:
    """Build mel-scale triangular filterbank matrix."""
    fmax = sr / 2.0
    mel_lo = 2595 * np.log10(1 + 0 / 700)
    mel_hi = 2595 * np.log10(1 + fmax / 700)
    mels = np.linspace(mel_lo, mel_hi, n_mels + 2)
    hz = 700 * (10 ** (mels / 2595) - 1)
    bins = np.floor((n_fft + 1) * hz / sr).astype(int)

    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(n_mels):
        lo, mid, hi = bins[m], bins[m + 1], bins[m + 2]
        if mid > lo:
            fb[m, lo:mid] = np.linspace(0, 1, mid - lo, endpoint=False)
        if hi > mid:
            fb[m, mid:hi] = np.linspace(1, 0, hi - mid, endpoint=False)
    return fb


# Module-level cache (sr and n_fft never change between calls)
_cached_mel_fb = None
_cached_mel_key = None
_cached_chroma_fb = None
_cached_chroma_key = None


def _get_mel_fb(sr: int, n_fft: int, n_mels: int = 40) -> np.ndarray:
    global _cached_mel_fb, _cached_mel_key
    key = (sr, n_fft, n_mels)
    if _cached_mel_key != key:
        _cached_mel_fb = _mel_filterbank(sr, n_fft, n_mels)
        _cached_mel_key = key
    return _cached_mel_fb


def _chroma_filterbank(sr: int, n_fft: int, n_chroma: int = 12) -> np.ndarray:
    """Map FFT bins to 12 pitch classes."""
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    fb = np.zeros((n_chroma, len(freqs)), dtype=np.float32)
    for i, f in enumerate(freqs):
        if f >= 65:  # ignore below C2
            pitch = 12 * np.log2(f / 440 + 1e-10) + 69
            fb[int(round(pitch)) % 12, i] += 1
    return fb


def _get_chroma_fb(sr: int, n_fft: int) -> np.ndarray:
    global _cached_chroma_fb, _cached_chroma_key
    key = (sr, n_fft)
    if _cached_chroma_key != key:
        _cached_chroma_fb = _chroma_filterbank(sr, n_fft)
        _cached_chroma_key = key
    return _cached_chroma_fb


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(file_path: str, sr: int = 11025, duration: float = 8.0) -> dict:
    """Extract audio features using numpy/scipy only (no librosa).

    ~10-50x faster than librosa on Render free tier because:
    - No numba/llvmlite JIT overhead
    - Single STFT pass (vectorized via stride tricks)
    - Cached filterbanks (mel, chroma)
    - soundfile reads WAV natively (no audioread fallback)
    """
    y, sr = _load_audio(file_path, sr, duration)

    n_fft = 1024
    hop = 512

    # ── Single STFT pass ─────────────────────────────────────────────────
    S = _stft(y, n_fft, hop)
    S_pow = S ** 2

    # ── MFCCs from mel spectrogram ───────────────────────────────────────
    mel_fb = _get_mel_fb(sr, n_fft, n_mels=40)
    mel_spec = mel_fb @ S_pow
    log_mel = np.log(mel_spec + 1e-10)
    mfcc_all = dct(log_mel, type=2, axis=0, norm="ortho")[:14]
    mfcc = mfcc_all[1:]  # drop MFCC[0] → 13 coefficients
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    # ── Chroma (12 pitch classes) ────────────────────────────────────────
    chroma_fb = _get_chroma_fb(sr, n_fft)
    chroma = chroma_fb @ S_pow
    chroma_norm = chroma.sum(axis=0, keepdims=True) + 1e-10
    chroma = chroma / chroma_norm
    chroma_mean = np.mean(chroma, axis=1)
    chroma_std = np.std(chroma, axis=1)

    # ── Spectral contrast (4 bands, safe for 11025 Hz Nyquist) ──────────
    band_edges = 200.0 * (2.0 ** np.arange(5))  # [200, 400, 800, 1600, 3200]
    freq_axis = np.linspace(0, sr / 2, S.shape[0])
    contrasts = []
    for b in range(4):
        lo = np.searchsorted(freq_axis, band_edges[b])
        hi = np.searchsorted(freq_axis, band_edges[b + 1])
        hi = max(hi, lo + 1)
        band = S[lo:hi, :]
        contrasts.append(np.percentile(band, 98, axis=0) - np.percentile(band, 2, axis=0))
    # Last sub-band: above 3200 Hz to Nyquist
    lo = np.searchsorted(freq_axis, band_edges[-1])
    band = S[lo:, :] if lo < S.shape[0] else S[-1:, :]
    contrasts.append(np.percentile(band, 98, axis=0) - np.percentile(band, 2, axis=0))
    spec_contrast = np.array(contrasts)
    spec_contrast_mean = np.mean(spec_contrast, axis=1)
    spec_contrast_std = np.std(spec_contrast, axis=1)

    # ── Onset envelope (spectral flux) ───────────────────────────────────
    flux = np.sum(np.maximum(0, np.diff(S_pow, axis=1)), axis=0)
    flux = np.concatenate([[0], flux])
    norm = np.linalg.norm(flux)
    onset_env = flux / norm if norm > 0 else flux

    # ── Tempo via autocorrelation ────────────────────────────────────────
    if len(onset_env) > 10:
        ac = np.correlate(onset_env, onset_env, mode="full")
        ac = ac[len(ac) // 2 :]
        min_lag = max(1, int(60 * sr / hop / 200))   # 200 BPM
        max_lag = min(int(60 * sr / hop / 60), len(ac) - 1)  # 60 BPM
        if max_lag > min_lag:
            best_lag = np.argmax(ac[min_lag : max_lag + 1]) + min_lag
            tempo = 60.0 * sr / hop / best_lag
        else:
            tempo = 120.0
    else:
        tempo = 120.0

    # ── Spectral summary features ────────────────────────────────────────
    freqs_col = np.fft.rfftfreq(n_fft, 1.0 / sr).reshape(-1, 1)
    s_sum = S.sum(axis=0, keepdims=True) + 1e-10

    centroid = ((freqs_col * S).sum(axis=0) / s_sum.squeeze())
    cumsum = np.cumsum(S, axis=0)
    total = cumsum[-1:, :] + 1e-10
    rolloff_idx = np.argmax(cumsum >= 0.85 * total, axis=0)
    rolloff = rolloff_idx.astype(float) * sr / n_fft

    # Per-frame ZCR
    n_frames = S.shape[1]
    zcr_frames = np.zeros(n_frames)
    for i in range(n_frames):
        frame = y[i * hop : i * hop + n_fft]
        if len(frame) > 1:
            zcr_frames[i] = np.mean(np.abs(np.diff(np.sign(frame))) > 0)

    return {
        "tempo": float(tempo),
        "mfcc_mean": mfcc_mean.tolist(),
        "mfcc_std": mfcc_std.tolist(),
        "spectral_contrast_mean": spec_contrast_mean.tolist(),
        "spectral_contrast_std": spec_contrast_std.tolist(),
        "chroma_mean": chroma_mean.tolist(),
        "chroma_std": chroma_std.tolist(),
        "onset_env": onset_env.tolist(),
        "spectral_centroid_mean": float(np.mean(centroid)),
        "spectral_centroid_std": float(np.std(centroid)),
        "spectral_rolloff_mean": float(np.mean(rolloff)),
        "zcr_mean": float(np.mean(zcr_frames)),
        "zcr_std": float(np.std(zcr_frames)),
    }


# ---------------------------------------------------------------------------
# Similarity computation (unchanged — same math as before)
# ---------------------------------------------------------------------------

def _euclidean_similarity(a: np.ndarray, b: np.ndarray, scale: float) -> float:
    dist = euclidean(a, b)
    sim = np.exp(-dist / scale) * 100
    return float(np.clip(sim, 0, 100))


def _tempo_similarity(t1: float, t2: float) -> float:
    if t1 == 0 and t2 == 0:
        return 100.0
    if t1 == 0 or t2 == 0:
        return 0.0
    diffs = [abs(t1 - t2), abs(t1 - 2 * t2), abs(2 * t1 - t2)]
    return float(np.clip(np.exp(-min(diffs) / 20) * 100, 0, 100))


def _rhythm_similarity(onset_a: np.ndarray, onset_b: np.ndarray) -> float:
    min_len = min(len(onset_a), len(onset_b))
    if min_len < 10:
        return 50.0
    try:
        corr, _ = pearsonr(onset_a[:min_len], onset_b[:min_len])
        return float(np.clip(max(0, (corr + 0.4) / 1.4) * 100, 0, 100))
    except Exception:
        return 50.0


def compute_similarity(feat_a: dict, feat_b: dict, lyrics_sim: float | None = None) -> dict:
    rhythm_sim = _rhythm_similarity(
        np.array(feat_a["onset_env"]), np.array(feat_b["onset_env"]),
    )
    tempo_sim = _tempo_similarity(feat_a["tempo"], feat_b["tempo"])

    timbre_a = np.concatenate([
        feat_a["mfcc_mean"], feat_a["mfcc_std"],
        feat_a["spectral_contrast_mean"], feat_a["spectral_contrast_std"],
    ])
    timbre_b = np.concatenate([
        feat_b["mfcc_mean"], feat_b["mfcc_std"],
        feat_b["spectral_contrast_mean"], feat_b["spectral_contrast_std"],
    ])
    timbre_sim = _euclidean_similarity(timbre_a, timbre_b, scale=20)

    harmony_a = np.concatenate([feat_a["chroma_mean"], feat_a["chroma_std"]])
    harmony_b = np.concatenate([feat_b["chroma_mean"], feat_b["chroma_std"]])
    harmony_sim = _euclidean_similarity(harmony_a, harmony_b, scale=2.0)

    spectral_a = np.array([
        feat_a["spectral_centroid_mean"] / 5000,
        feat_a["spectral_rolloff_mean"] / 10000,
        feat_a["zcr_mean"] * 10,
        feat_a["spectral_centroid_std"] / 2000,
        feat_a["zcr_std"] * 10,
    ])
    spectral_b = np.array([
        feat_b["spectral_centroid_mean"] / 5000,
        feat_b["spectral_rolloff_mean"] / 10000,
        feat_b["zcr_mean"] * 10,
        feat_b["spectral_centroid_std"] / 2000,
        feat_b["zcr_std"] * 10,
    ])
    spectral_sim = _euclidean_similarity(spectral_a, spectral_b, scale=0.8)

    base_weights = {
        "rhythm": 0.15, "tempo": 0.10, "timbre": 0.30,
        "harmony": 0.20, "spectral": 0.15, "lyrics": 0.10,
    }
    scores = {
        "rhythm": rhythm_sim, "tempo": tempo_sim, "timbre": timbre_sim,
        "harmony": harmony_sim, "spectral": spectral_sim, "lyrics": lyrics_sim,
    }
    active = {k: v for k, v in scores.items() if v is not None}
    total_weight = sum(base_weights[k] for k in active)
    overall = sum(base_weights[k] / total_weight * active[k] for k in active)

    return {
        "overall": round(overall, 1),
        "breakdown": {
            "rhythm": round(rhythm_sim, 1), "tempo": round(tempo_sim, 1),
            "timbre": round(timbre_sim, 1), "harmony": round(harmony_sim, 1),
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
