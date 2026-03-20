"""Lyrics fetching and text similarity for MelodyMatch.

Fetches lyrics from free APIs (no API key required):
  1. lrclib.net (primary) — fast, has instrumental detection
  2. lyrics.ovh (fallback) — simple REST API

Computes text similarity using cosine distance on word-frequency vectors
(lightweight, no ML models, uses only scipy + stdlib).
"""

import re
from collections import Counter

import numpy as np
import requests
from scipy.spatial.distance import cosine as cosine_distance

_TIMEOUT = 10  # seconds per API call

# Minimal English stop words (common words that don't carry meaning)
_STOP_WORDS = frozenset({
    "a", "about", "all", "am", "an", "and", "are", "as", "at", "be", "been",
    "but", "by", "can", "could", "da", "de", "did", "do", "does", "for",
    "from", "got", "had", "has", "have", "he", "her", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "just", "la", "le", "like",
    "may", "me", "might", "my", "na", "no", "not", "now", "of", "oh", "on",
    "or", "our", "out", "so", "some", "than", "that", "the", "them", "then",
    "there", "they", "this", "to", "too", "up", "us", "was", "we", "were",
    "what", "when", "which", "who", "will", "with", "would", "ya", "yeah",
    "you", "your",
})


# ---------------------------------------------------------------------------
# Lyrics fetching
# ---------------------------------------------------------------------------

def _fetch_from_lrclib(song_name: str, artist: str) -> str | None:
    """Try lrclib.net — returns plainLyrics or None."""
    try:
        r = requests.get(
            "https://lrclib.net/api/get",
            params={"artist_name": artist, "track_name": song_name},
            headers={"User-Agent": "MelodyMatch/1.0"},
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # lrclib returns instrumental flag
        if data.get("instrumental"):
            return ""  # empty string = instrumental (distinct from None = not found)
        lyrics = data.get("plainLyrics") or data.get("syncedLyrics") or ""
        return lyrics.strip() if lyrics.strip() else None
    except Exception:
        return None


def _fetch_from_lyrics_ovh(song_name: str, artist: str) -> str | None:
    """Fallback to lyrics.ovh."""
    try:
        # lyrics.ovh uses URL path: /v1/{artist}/{title}
        r = requests.get(
            f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(song_name)}",
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        lyrics = data.get("lyrics", "")
        return lyrics.strip() if lyrics.strip() else None
    except Exception:
        return None


def fetch_lyrics(song_name: str, artist: str) -> str | None:
    """Fetch lyrics for a song. Returns:
      - lyrics text (str) if found
      - empty string if instrumental
      - None if unavailable

    Tries lrclib.net first, then lyrics.ovh as fallback.
    """
    if not song_name or not artist:
        return None

    # Try lrclib first (better API, has instrumental detection)
    result = _fetch_from_lrclib(song_name, artist)
    if result is not None:
        return result

    # Fallback to lyrics.ovh
    result = _fetch_from_lyrics_ovh(song_name, artist)
    if result is not None:
        return result

    return None


# ---------------------------------------------------------------------------
# Text similarity (lightweight, no ML)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words, remove stop words."""
    # Remove everything except letters, numbers, whitespace
    cleaned = re.sub(r"[^a-z0-9\s]", "", text.lower())
    tokens = cleaned.split()
    # Filter stop words and very short tokens
    return [t for t in tokens if t not in _STOP_WORDS and len(t) >= 2]


def compute_lyrics_similarity(lyrics_a: str | None, lyrics_b: str | None) -> float | None:
    """Compare two sets of lyrics using cosine similarity on word frequency vectors.

    Returns:
      - float (0-100) if both lyrics are available and have enough words
      - None if either is None, empty, or too short (<5 meaningful tokens)
    """
    if lyrics_a is None or lyrics_b is None:
        return None
    if not lyrics_a.strip() or not lyrics_b.strip():
        return None

    tokens_a = _tokenize(lyrics_a)
    tokens_b = _tokenize(lyrics_b)

    # Need minimum tokens for a meaningful comparison
    if len(tokens_a) < 5 or len(tokens_b) < 5:
        return None

    freq_a = Counter(tokens_a)
    freq_b = Counter(tokens_b)

    # Build aligned vectors from the union of all vocabulary
    all_words = sorted(set(freq_a) | set(freq_b))
    vec_a = np.array([freq_a.get(w, 0) for w in all_words], dtype=float)
    vec_b = np.array([freq_b.get(w, 0) for w in all_words], dtype=float)

    # scipy cosine returns distance (0=identical, 2=opposite), convert to similarity
    try:
        dist = cosine_distance(vec_a, vec_b)
        similarity = (1 - dist) * 100
        return float(np.clip(similarity, 0, 100))
    except Exception:
        return None
