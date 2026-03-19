"""YouTube search and audio download via Piped API.

Piped is a privacy-friendly YouTube proxy. Using its API means we never
talk to YouTube directly, avoiding bot detection and 429 rate limits
on datacenter IPs.

Multiple Piped instances are tried as fallbacks for reliability.
"""

import os
import tempfile
import subprocess
import requests

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.in.projectsegfau.lt",
]

_TIMEOUT = 30  # seconds per HTTP request


def _find_ffmpeg() -> str:
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                 os.path.expanduser("~/.local/bin/ffmpeg")]:
        if os.path.isfile(path):
            return path
    return "ffmpeg"


def _piped_get(path: str, params: dict = None) -> dict:
    """Try each Piped instance until one responds."""
    last_err = None
    for base in PIPED_INSTANCES:
        try:
            r = requests.get(f"{base}{path}", params=params, timeout=_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All Piped instances failed. Last error: {last_err}")


def search_youtube(query: str) -> dict:
    """Search YouTube via Piped. Returns the top video result as {id, title, url}."""
    data = _piped_get("/search", {"q": query, "filter": "videos"})

    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"No YouTube results found for '{query}'")

    # Pick the first video result
    for item in items:
        if item.get("url") and item.get("duration", 0) > 0:
            video_id = item["url"].replace("/watch?v=", "")
            return {
                "id": video_id,
                "title": item.get("title", query),
                "url": f"https://youtube.com/watch?v={video_id}",
            }

    # Fallback to first item
    item = items[0]
    video_id = item["url"].replace("/watch?v=", "")
    return {
        "id": video_id,
        "title": item.get("title", query),
        "url": f"https://youtube.com/watch?v={video_id}",
    }


def get_audio_stream_url(video_id: str) -> str:
    """Get the best audio stream URL for a video via Piped."""
    data = _piped_get(f"/streams/{video_id}")

    streams = data.get("audioStreams", [])
    if not streams:
        raise RuntimeError(f"No audio streams found for video {video_id}")

    # Sort by bitrate descending, prefer m4a/mp4 (better ffmpeg compat)
    streams.sort(key=lambda s: s.get("bitrate", 0), reverse=True)

    for s in streams:
        if s.get("url"):
            return s["url"]

    raise RuntimeError(f"No usable audio stream URL for video {video_id}")


def download_audio(stream_url: str, output_path: str):
    """Download an audio stream URL and convert to mp3 via ffmpeg."""
    # Download the raw audio stream
    r = requests.get(stream_url, timeout=120, stream=True)
    r.raise_for_status()

    raw_path = output_path + ".raw"
    with open(raw_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)

    # Convert to mp3 with ffmpeg
    try:
        subprocess.run(
            [_find_ffmpeg(), "-i", raw_path, "-vn", "-acodec", "libmp3lame",
             "-ab", "192k", "-y", output_path],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        if os.path.isfile(raw_path):
            os.unlink(raw_path)


def search_and_download(song_name: str, artist: str) -> str:
    """Search YouTube for a song and download the audio as mp3.

    Returns path to a temporary mp3 file. Caller must clean up.
    """
    query = f"{song_name} {artist}"

    # Step 1: Search
    result = search_youtube(query)
    video_id = result["id"]

    # Step 2: Get audio stream URL
    stream_url = get_audio_stream_url(video_id)

    # Step 3: Download and convert
    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    download_audio(stream_url, mp3_path)

    if not os.path.isfile(mp3_path):
        raise RuntimeError(f"Download failed for '{query}'")
    return mp3_path


def download_from_url(url: str) -> str:
    """Download audio from a YouTube URL (extracts video ID, uses Piped)."""
    import re
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract video ID from URL: {url}")

    video_id = match.group(1)
    stream_url = get_audio_stream_url(video_id)

    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    download_audio(stream_url, mp3_path)

    if not os.path.isfile(mp3_path):
        raise RuntimeError(f"Download failed for '{url}'")
    return mp3_path
