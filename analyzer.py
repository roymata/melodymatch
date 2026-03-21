"""Audio feature extraction and similarity — ZERO librosa dependency.

Uses only numpy + scipy + soundfile for fast analysis on weak CPUs.
librosa pulls in numba/llvmlite/JIT which is far too heavy for Render free tier.

Accuracy improvements over naive FFT approach:
- Chroma uses a dedicated 4096-point FFT for fine pitch resolution (~2.7 Hz/bin)
  with Gaussian weighting across pitch classes (not hard bin assignment)
- Tempo uses mel-band onset strength (not raw spectral flux) with parabolic
  interpolation for sub-lag BPM accuracy
- All spectral features computed from properly-sized STFTs
"""
from __future__ import annotations

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


def _load_audio(file_path: str, sr: int = 11025, duration: float = 30.0):
    """Load audio file as mono float32 at target sample rate."""
    try:
        y, file_sr = sf.read(file_path, dtype="float32")
        if y.ndim > 1:
            y = y.mean(axis=1)
        if file_sr == sr:
            return y[: int(duration * sr)], sr
    except Exception:
        pass

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

def _stft(y: np.ndarray, n_fft: int, hop: int) -> np.ndarray:
    """Compute magnitude STFT using stride tricks (no Python loops)."""
    # Pad signal so we don't lose the tail
    pad_len = n_fft - (len(y) % hop) if len(y) % hop else 0
    if pad_len > 0:
        y = np.concatenate([y, np.zeros(pad_len, dtype=y.dtype)])

    window = np.hanning(n_fft).astype(np.float32)
    n_frames = max(1, 1 + (len(y) - n_fft) // hop)

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


def _chroma_filterbank(sr: int, n_fft: int, n_chroma: int = 12) -> np.ndarray:
    """Map FFT bins to 12 pitch classes with Gaussian weighting.

    Uses Gaussian spread so each bin contributes to nearby pitch classes
    proportionally, instead of hard-assigning to a single class.
    This produces meaningful chroma even with moderate frequency resolution.
    """
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    n_bins = len(freqs)
    fb = np.zeros((n_chroma, n_bins), dtype=np.float64)

    for i in range(n_bins):
        f = freqs[i]
        if f < 65:  # below C2, ignore
            continue
        # Fractional pitch class (0-12 continuous)
        midi = 12 * np.log2(f / 440.0) + 69
        chroma_pos = midi % 12  # 0.0 to 11.999...

        # Gaussian contribution to each pitch class
        for c in range(n_chroma):
            # Circular distance in semitones
            dist = abs(chroma_pos - c)
            dist = min(dist, 12 - dist)
            # Gaussian with sigma=0.5 semitones — tight enough to separate keys
            if dist < 2.0:
                fb[c, i] += np.exp(-0.5 * (dist / 0.5) ** 2)

    # Normalize each pitch class row
    row_sum = fb.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1
    fb = fb / row_sum

    return fb.astype(np.float32)


# ── Filterbank caches ────────────────────────────────────────────────────
_cache = {}


def _get_fb(key: str, builder, *args):
    if key not in _cache:
        _cache[key] = builder(*args)
    return _cache[key]


# ---------------------------------------------------------------------------
# Tempo estimation
# ---------------------------------------------------------------------------

def _parabolic_interp(ac: np.ndarray, idx: int) -> float:
    """Parabolic interpolation around an autocorrelation peak for sub-lag precision."""
    if idx <= 0 or idx >= len(ac) - 1:
        return float(idx)
    alpha = float(ac[idx - 1])
    beta = float(ac[idx])
    gamma = float(ac[idx + 1])
    denom = alpha - 2 * beta + gamma
    if abs(denom) > 1e-10:
        return idx + 0.5 * (alpha - gamma) / denom
    return float(idx)


def _estimate_tempo(onset_env: np.ndarray, sr: int, hop: int) -> float:
    """Estimate BPM using autocorrelation with aggressive octave-error correction.

    The #1 failure mode in tempo detection is octave errors: the algorithm
    finds 70 BPM when the real tempo is 140 BPM (or vice versa). This happens
    because the autocorrelation at 2× the period is always strong (every other
    beat matches perfectly).

    Fix: find the strongest peak, then ALWAYS check the double-tempo candidate
    (half lag). If the double-tempo has any autocorrelation support AND falls
    in the common 70-180 BPM range, prefer it — because humans almost always
    perceive the faster pulse as "the tempo".
    """
    if len(onset_env) < 40:
        return 120.0

    # Smooth the onset envelope to reduce noise
    kernel_size = 5
    kernel = np.ones(kernel_size) / kernel_size
    env = np.convolve(onset_env, kernel, mode="same")

    # Normalize
    env = env - np.mean(env)
    norm = np.linalg.norm(env)
    if norm < 1e-8:
        return 120.0
    env = env / norm

    # Autocorrelation via FFT (much faster for long signals)
    n = len(env)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2
    fft_env = np.fft.rfft(env, fft_size)
    ac = np.fft.irfft(fft_env * np.conj(fft_env))[:n]
    if ac[0] > 0:
        ac = ac / ac[0]

    fps = sr / hop
    min_lag = max(2, int(60 * fps / 220))   # 220 BPM
    max_lag = min(int(60 * fps / 40), len(ac) - 2)  # 40 BPM

    if max_lag <= min_lag + 2:
        return 120.0

    ac_range = ac[min_lag: max_lag + 1]

    # Weight autocorrelation to suppress very slow tempos (<60 BPM)
    # which are almost always octave errors (4× or 8× the real period).
    # Keep 60-200 BPM roughly neutral to not bias the initial pick.
    weights = np.ones(len(ac_range), dtype=np.float64)
    for i in range(len(ac_range)):
        lag = i + min_lag
        bpm = 60.0 * fps / lag
        if bpm < 55:
            weights[i] = 0.2   # heavily suppress: almost never real
        elif bpm > 200:
            weights[i] = 0.3   # suppress very fast tempos

    weighted = ac_range * weights
    best_offset = int(np.argmax(weighted))
    best_lag = best_offset + min_lag

    refined_lag = _parabolic_interp(ac, best_lag)
    best_bpm = 60.0 * fps / refined_lag if refined_lag > 0 else 120.0

    # ── Octave-error fix: check if the true tempo is DOUBLE ──────────────
    # For a 170 BPM signal, autocorrelation often picks 85 BPM (half tempo)
    # because every-other-beat alignment is just as strong. To detect this:
    # check if there are real onset peaks BETWEEN the detected beats.
    # If the midpoints have strong onsets, the true tempo is double.
    if best_bpm < 100 and best_bpm * 2 <= 200:
        single_period = fps / (best_bpm / 60)  # frames per detected beat
        n_checks = min(30, int(len(onset_env) / single_period) - 1)

        if n_checks >= 4:
            beat_strengths = []
            mid_strengths = []
            for i in range(n_checks):
                beat_pos = int(i * single_period)
                mid_pos = int((i + 0.5) * single_period)
                if beat_pos < len(onset_env):
                    lo = max(0, beat_pos - 2)
                    hi = min(len(onset_env), beat_pos + 3)
                    beat_strengths.append(float(np.max(onset_env[lo:hi])))
                if mid_pos < len(onset_env):
                    lo = max(0, mid_pos - 2)
                    hi = min(len(onset_env), mid_pos + 3)
                    mid_strengths.append(float(np.max(onset_env[lo:hi])))

            if beat_strengths and mid_strengths:
                beat_avg = np.mean(beat_strengths)
                mid_avg = np.mean(mid_strengths)
                # If midpoints have >= 40% the strength of on-beats,
                # there are real beats there → true tempo is double
                if beat_avg > 0 and mid_avg > beat_avg * 0.4:
                    best_bpm *= 2

    # Also check tripling for very slow detections (handles 3× period errors)
    if best_bpm < 70 and best_bpm * 3 <= 200:
        triple_period = fps / (best_bpm * 3 / 60)
        n_checks = min(30, int(len(onset_env) / triple_period) - 1)
        if n_checks >= 4:
            strengths = []
            for i in range(n_checks):
                pos = int(i * triple_period)
                if pos < len(onset_env):
                    lo = max(0, pos - 2)
                    hi = min(len(onset_env), pos + 3)
                    strengths.append(float(np.max(onset_env[lo:hi])))
            if strengths and np.mean(strengths) > 0.1 * np.max(onset_env):
                best_bpm *= 3

    # Safety: if somehow > 200, halve
    if best_bpm > 200:
        half_bpm = best_bpm / 2
        if 60 <= half_bpm <= 160:
            best_bpm = half_bpm

    # Sanity bounds
    if best_bpm < 40 or best_bpm > 220:
        return 120.0

    return round(best_bpm, 1)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(file_path: str, sr: int = 11025, duration: float = 30.0) -> dict:
    """Extract audio features using numpy/scipy only (no librosa).

    Uses the FULL iTunes preview (~30 seconds) for maximum accuracy.
    At sr=11025 with numpy FFT, even 30 seconds processes in <0.2s.

    Key accuracy decisions:
    - Full 30s for tempo estimation (60+ beats at 120 BPM vs 16 before)
    - Full 30s for chroma — captures key changes and full harmonic picture
    - Dedicated high-res STFT (4096-pt) for chroma — ~2.7 Hz/bin resolution
    - Mel-based onset strength with smoothing for rhythm/tempo
    - Octave-error correction for BPM (checks half/double candidates)
    """
    y, sr = _load_audio(file_path, sr, duration)

    # ── Main STFT for spectral features ──────────────────────────────────
    n_fft = 1024
    hop = 512
    S = _stft(y, n_fft, hop)
    S_pow = S ** 2

    # ── MFCCs from mel spectrogram ───────────────────────────────────────
    mel_fb = _get_fb(f"mel_{sr}_{n_fft}_40", _mel_filterbank, sr, n_fft, 40)
    mel_spec = mel_fb @ S_pow
    log_mel = np.log(mel_spec + 1e-10)
    mfcc_all = dct(log_mel, type=2, axis=0, norm="ortho")[:14]
    mfcc = mfcc_all[1:]  # drop MFCC[0] → 13 coefficients
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)

    # ── Chroma from HIGH-RES STFT (4096-pt → 2.7 Hz/bin) ────────────────
    chroma_nfft = 4096
    chroma_hop = 1024
    S_chroma = _stft(y, chroma_nfft, chroma_hop)
    chroma_fb = _get_fb(f"chroma_{sr}_{chroma_nfft}", _chroma_filterbank, sr, chroma_nfft)
    chroma = chroma_fb @ (S_chroma ** 2)
    chroma_norm = chroma.sum(axis=0, keepdims=True) + 1e-10
    chroma = chroma / chroma_norm
    chroma_mean = np.mean(chroma, axis=1)
    chroma_std = np.std(chroma, axis=1)

    # ── Spectral contrast (4 bands, safe for Nyquist) ────────────────────
    band_edges = 200.0 * (2.0 ** np.arange(5))  # [200,400,800,1600,3200]
    freq_axis = np.linspace(0, sr / 2, S.shape[0])
    contrasts = []
    for b in range(4):
        lo = np.searchsorted(freq_axis, band_edges[b])
        hi = np.searchsorted(freq_axis, band_edges[b + 1])
        hi = max(hi, lo + 1)
        band = S[lo:hi, :]
        contrasts.append(np.percentile(band, 98, axis=0) - np.percentile(band, 2, axis=0))
    lo = np.searchsorted(freq_axis, band_edges[-1])
    band = S[lo:, :] if lo < S.shape[0] else S[-1:, :]
    contrasts.append(np.percentile(band, 98, axis=0) - np.percentile(band, 2, axis=0))
    spec_contrast = np.array(contrasts)
    spec_contrast_mean = np.mean(spec_contrast, axis=1)
    spec_contrast_std = np.std(spec_contrast, axis=1)

    # ── Onset envelope from mel-band energy flux ─────────────────────────
    # Much more accurate than raw spectral flux — standard in MIR systems
    mel_diff = np.maximum(0, np.diff(log_mel, axis=1))
    onset_env = np.mean(mel_diff, axis=0)
    onset_env = np.concatenate([[0], onset_env])
    onset_norm = np.linalg.norm(onset_env)
    onset_env_normalized = onset_env / onset_norm if onset_norm > 0 else onset_env

    # ── Tempo via autocorrelation with interpolation ─────────────────────
    # Use a finer-resolution onset envelope for better BPM precision
    fine_hop = 256
    S_fine = _stft(y, n_fft, fine_hop)
    mel_fine = mel_fb @ (S_fine ** 2)
    log_mel_fine = np.log(mel_fine + 1e-10)
    mel_diff_fine = np.maximum(0, np.diff(log_mel_fine, axis=1))
    onset_fine = np.mean(mel_diff_fine, axis=0)
    onset_fine = np.concatenate([[0], onset_fine])
    tempo = _estimate_tempo(onset_fine, sr, fine_hop)

    # ── Spectral summary features ────────────────────────────────────────
    freqs_col = np.fft.rfftfreq(n_fft, 1.0 / sr).reshape(-1, 1)
    s_sum = S.sum(axis=0, keepdims=True) + 1e-10

    centroid = (freqs_col * S).sum(axis=0) / s_sum.squeeze()
    cumsum = np.cumsum(S, axis=0)
    total = cumsum[-1:, :] + 1e-10
    rolloff_idx = np.argmax(cumsum >= 0.85 * total, axis=0)
    rolloff = rolloff_idx.astype(float) * sr / n_fft

    # Per-frame ZCR (vectorized)
    n_frames = S.shape[1]
    zcr_frames = np.zeros(n_frames)
    for i in range(n_frames):
        frame = y[i * hop: i * hop + n_fft]
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
        "onset_env": onset_env_normalized.tolist(),
        "spectral_centroid_mean": float(np.mean(centroid)),
        "spectral_centroid_std": float(np.std(centroid)),
        "spectral_rolloff_mean": float(np.mean(rolloff)),
        "zcr_mean": float(np.mean(zcr_frames)),
        "zcr_std": float(np.std(zcr_frames)),
    }


# ---------------------------------------------------------------------------
# Similarity computation
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
    # scale=1.0 (tighter than before) — with accurate chroma, different keys
    # should produce clearly different vectors
    harmony_sim = _euclidean_similarity(harmony_a, harmony_b, scale=1.0)

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
