"""Song search and audio download via iTunes Search API + YouTube proxy fallback.

Primary: iTunes/Apple Music Search API
  - Free, no API key, no auth, no rate limiting issues
  - Returns 30-second AAC preview URLs (Apple CDN — always fast and reliable)
  - 30 seconds is enough for accurate librosa audio analysis

Fallback: Piped/Invidious YouTube proxies (if iTunes has no preview)
"""

import os
import re
import tempfile
import subprocess
import requests

_TIMEOUT = 20

# Piped + Invidious as fallback for YouTube URL downloads
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi-libre.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.leptons.xyz",
    "https://api.piped.yt",
    "https://pipedapi.drgns.space",
    "https://piped-api.privacy.com.de",
]

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://yewtu.be",
    "https://invidious.nerdvpn.de",
]


def _find_ffmpeg() -> str:
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                 os.path.expanduser("~/.local/bin/ffmpeg")]:
        if os.path.isfile(path):
            return path
    return "ffmpeg"


# ---------------------------------------------------------------------------
# iTunes Search API (primary — reliable, free, no auth)
# ---------------------------------------------------------------------------

def _itunes_search(query: str, limit: int = 5) -> list[dict]:
    """Search iTunes for songs. Returns list of track results."""
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": query, "media": "music", "entity": "song", "limit": limit},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("results", [])
    except Exception:
        pass
    return []


def _itunes_download_preview(preview_url: str, output_path: str):
    """Download an iTunes preview URL and convert to WAV at analysis sample rate.

    Outputs mono 11025 Hz WAV — this means librosa.load can skip resampling
    entirely and soundfile reads it natively (no audioread fallback).
    """
    r = requests.get(preview_url, timeout=60, stream=True)
    r.raise_for_status()

    # iTunes previews are m4a — download then convert to WAV
    raw_path = output_path + ".m4a"
    with open(raw_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)

    try:
        subprocess.run(
            [_find_ffmpeg(), "-i", raw_path, "-vn", "-ac", "1",
             "-ar", "11025", "-y", "-loglevel", "error", output_path],
            check=True, capture_output=True, timeout=30,
        )
    finally:
        if os.path.isfile(raw_path):
            os.unlink(raw_path)

    if not os.path.isfile(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError("Audio conversion failed")


# ---------------------------------------------------------------------------
# YouTube proxy fallback (for direct URL downloads)
# ---------------------------------------------------------------------------

def _proxy_get(path: str, instances: list, prefix: str = "", params: dict = None):
    """Try instances until one returns valid JSON."""
    for base in instances:
        try:
            r = requests.get(f"{base}{prefix}{path}", params=params, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return data
        except Exception:
            continue
    return None


def _youtube_audio_url(video_id: str) -> str | None:
    """Try to get audio stream URL from Piped then Invidious."""
    # Try Piped
    data = _proxy_get(f"/streams/{video_id}", PIPED_INSTANCES)
    if data:
        streams = sorted(data.get("audioStreams", []),
                         key=lambda s: s.get("bitrate", 0), reverse=True)
        for s in streams:
            if s.get("url"):
                return s["url"]

    # Try Invidious
    data = _proxy_get(f"/videos/{video_id}", INVIDIOUS_INSTANCES, prefix="/api/v1")
    if data:
        for fmt in data.get("adaptiveFormats", []):
            if fmt.get("type", "").startswith("audio/") and fmt.get("url"):
                return fmt["url"]

    return None


def _download_stream(stream_url: str, output_path: str):
    """Download a stream URL and convert to WAV at analysis sample rate."""
    r = requests.get(stream_url, timeout=120, stream=True,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    raw_path = output_path + ".raw"
    with open(raw_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)

    try:
        subprocess.run(
            [_find_ffmpeg(), "-i", raw_path, "-vn", "-ac", "1",
             "-ar", "11025", "-y", "-loglevel", "error", output_path],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        if os.path.isfile(raw_path):
            os.unlink(raw_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_and_download(song_name: str, artist: str) -> str:
    """Search for a song and download audio as mp3.

    Uses iTunes as primary source (30-sec previews, always reliable).
    Returns path to a temporary mp3 file. Caller must clean up the parent dir.
    """
    query = f"{song_name} {artist}"

    # Try iTunes first — reliable and fast
    results = _itunes_search(query)
    for track in results:
        preview_url = track.get("previewUrl")
        if preview_url:
            tmp_dir = tempfile.mkdtemp()
            mp3_path = os.path.join(tmp_dir, "audio.wav")
            try:
                _itunes_download_preview(preview_url, mp3_path)
                return mp3_path
            except Exception:
                continue

    raise RuntimeError(
        f"Could not find a playable preview for '{song_name}' by {artist}. "
        "Try a different spelling, or use the YouTube URL fallback option."
    )


def download_from_url(url: str) -> str:
    """Download audio from a YouTube URL via proxy services."""
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract video ID from URL: {url}")

    video_id = match.group(1)
    stream_url = _youtube_audio_url(video_id)

    if not stream_url:
        raise RuntimeError(
            "Could not get audio from YouTube — all proxy services are unavailable. "
            "Please try again later."
        )

    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "audio.wav")
    _download_stream(stream_url, mp3_path)

    if not os.path.isfile(mp3_path) or os.path.getsize(mp3_path) < 1000:
        raise RuntimeError(f"Download failed for '{url}'")
    return mp3_path
