"""YouTube search and audio download via Piped + Invidious APIs.

Uses multiple YouTube proxy services as fallbacks so we never talk to
YouTube directly — avoiding bot detection and 429 rate limits on
datacenter IPs.

Fallback chain:
  1. Piped API instances (search + stream)
  2. Invidious API instances (search + stream)
"""

import os
import re
import tempfile
import subprocess
import requests

# Current working Piped API instances (updated March 2026)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi-libre.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.leptons.xyz",
    "https://api.piped.yt",
    "https://pipedapi.drgns.space",
    "https://piped-api.privacy.com.de",
    "https://pipedapi.nosebs.ru",
    "https://pipedapi.darkness.services",
    "https://pipedapi.ducks.party",
]

# Invidious API instances as secondary fallback
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://yewtu.be",
    "https://invidious.nerdvpn.de",
]

_TIMEOUT = 20  # seconds per HTTP request to each instance


def _find_ffmpeg() -> str:
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                 os.path.expanduser("~/.local/bin/ffmpeg")]:
        if os.path.isfile(path):
            return path
    return "ffmpeg"


# ---------------------------------------------------------------------------
# Piped API helpers
# ---------------------------------------------------------------------------

def _piped_get(path: str, params: dict = None) -> dict | None:
    """Try each Piped instance; return JSON or None if all fail."""
    for base in PIPED_INSTANCES:
        try:
            r = requests.get(f"{base}{path}", params=params, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return data
        except Exception:
            continue
    return None


def _piped_search(query: str) -> str | None:
    """Search via Piped, return video ID or None."""
    data = _piped_get("/search", {"q": query, "filter": "videos"})
    if not data:
        return None

    for item in data.get("items", []):
        url = item.get("url", "")
        if url and item.get("duration", 0) > 0:
            return url.replace("/watch?v=", "")
    return None


def _piped_audio_url(video_id: str) -> str | None:
    """Get proxied audio stream URL via Piped, or None."""
    data = _piped_get(f"/streams/{video_id}")
    if not data:
        return None

    streams = data.get("audioStreams", [])
    if not streams:
        return None

    # Sort by bitrate descending
    streams.sort(key=lambda s: s.get("bitrate", 0), reverse=True)
    for s in streams:
        if s.get("url"):
            return s["url"]
    return None


# ---------------------------------------------------------------------------
# Invidious API helpers (fallback)
# ---------------------------------------------------------------------------

def _invidious_get(path: str, params: dict = None) -> dict | list | None:
    """Try each Invidious instance; return JSON or None."""
    for base in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(f"{base}/api/v1{path}", params=params, timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return data
        except Exception:
            continue
    return None


def _invidious_search(query: str) -> str | None:
    """Search via Invidious, return video ID or None."""
    data = _invidious_get("/search", {"q": query, "type": "video"})
    if not data or not isinstance(data, list):
        return None

    for item in data:
        vid = item.get("videoId")
        if vid and item.get("lengthSeconds", 0) > 0:
            return vid
    return None


def _invidious_audio_url(video_id: str) -> str | None:
    """Get audio stream URL via Invidious, or None."""
    data = _invidious_get(f"/videos/{video_id}")
    if not data:
        return None

    # Invidious provides adaptiveFormats with audio
    for fmt in data.get("adaptiveFormats", []):
        if fmt.get("type", "").startswith("audio/") and fmt.get("url"):
            return fmt["url"]
    return None


# ---------------------------------------------------------------------------
# Unified search and download
# ---------------------------------------------------------------------------

def search_video(query: str) -> str:
    """Search YouTube for a query, return video ID. Tries Piped then Invidious."""
    vid = _piped_search(query)
    if vid:
        return vid

    vid = _invidious_search(query)
    if vid:
        return vid

    raise RuntimeError(
        f"Could not find '{query}' on YouTube. "
        "All proxy instances are currently unavailable. Please try again later "
        "or paste a direct YouTube URL instead."
    )


def get_audio_url(video_id: str) -> str:
    """Get a downloadable audio URL for a video ID. Tries Piped then Invidious."""
    url = _piped_audio_url(video_id)
    if url:
        return url

    url = _invidious_audio_url(video_id)
    if url:
        return url

    raise RuntimeError(
        f"Could not get audio for video {video_id}. "
        "All proxy instances failed. Please try again later."
    )


def download_audio(stream_url: str, output_path: str):
    """Download an audio stream URL and convert to mp3 via ffmpeg."""
    r = requests.get(stream_url, timeout=120, stream=True,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    raw_path = output_path + ".raw"
    with open(raw_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)

    try:
        subprocess.run(
            [_find_ffmpeg(), "-i", raw_path, "-vn", "-acodec", "libmp3lame",
             "-ab", "192k", "-y", "-loglevel", "error", output_path],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        if os.path.isfile(raw_path):
            os.unlink(raw_path)

    if not os.path.isfile(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError("Audio conversion failed — output file is empty")


def search_and_download(song_name: str, artist: str) -> str:
    """Search YouTube for a song and download audio as mp3.

    Returns path to a temporary mp3 file. Caller must clean up the parent dir.
    """
    query = f"{song_name} {artist}"
    video_id = search_video(query)
    stream_url = get_audio_url(video_id)

    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    download_audio(stream_url, mp3_path)
    return mp3_path


def download_from_url(url: str) -> str:
    """Download audio from a YouTube URL via Piped/Invidious proxies."""
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract video ID from URL: {url}")

    video_id = match.group(1)
    stream_url = get_audio_url(video_id)

    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    download_audio(stream_url, mp3_path)
    return mp3_path
