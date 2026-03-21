"""BPM lookup from songbpm.com — authoritative tempo source.

Instead of detecting BPM from a 30-second audio preview (unreliable),
we fetch the professionally-curated BPM from songbpm.com.

Falls back to None if the song isn't found, so the caller can use
audio-based detection as a last resort.
"""
from __future__ import annotations

import re
import requests

_TIMEOUT = 8


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug matching songbpm.com's format."""
    text = text.lower().strip()
    # Remove common prefixes/suffixes that songbpm.com strips
    text = re.sub(r'^\.\.\.\s*', '', text)       # "...Baby" → "Baby"
    text = re.sub(r'\s*\(.*?\)\s*$', '', text)   # "(Remastered)" etc.
    text = re.sub(r'\s*\[.*?\]\s*$', '', text)   # "[Deluxe]" etc.
    text = re.sub(r"['']+", '', text)             # apostrophes
    text = re.sub(r'[^\w\s-]', '', text)          # remove non-alphanumeric
    text = re.sub(r'[\s_]+', '-', text)           # spaces → hyphens
    text = re.sub(r'-+', '-', text)               # collapse hyphens
    return text.strip('-')


def fetch_bpm(song_name: str, artist: str) -> float | None:
    """Fetch BPM from songbpm.com for the given song.

    Returns the BPM as a float, or None if not found.
    URL pattern: https://songbpm.com/@{artist-slug}/{song-slug}
    """
    if not song_name or not artist:
        return None

    artist_slug = _slugify(artist)
    song_slug = _slugify(song_name)

    if not artist_slug or not song_slug:
        return None

    url = f"https://songbpm.com/@{artist_slug}/{song_slug}"

    try:
        r = requests.get(
            url,
            timeout=_TIMEOUT,
            headers={"User-Agent": "MelodyMatch/1.0 (song comparison tool)"},
        )
        if r.status_code != 200:
            return None

        # songbpm.com has the BPM in an <h1>96 BPM</h1> tag
        # and also in text like "tempo of 96 BPM" and "Tempo (BPM): 96"
        # Use the most specific pattern first
        match = re.search(r'<h1>\s*(\d+)\s*BPM\s*</h1>', r.text, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Fallback: any "NUMBER BPM" pattern
        match = re.search(r'(\d{2,3})\s*BPM', r.text)
        if match:
            bpm = float(match.group(1))
            if 30 <= bpm <= 250:
                return bpm

    except Exception:
        pass

    return None
