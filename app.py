"""MelodyMatch — single-service Flask app.

Serves the React frontend as static files AND exposes the audio comparison API.
"""

import os
import shutil
import tempfile
import threading

import requests as http_requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from analyzer import extract_features, compute_similarity
from youtube import search_and_download, download_from_url

# Serve built React app from /static (built during Docker build)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
CORS(app)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}

# ── Comparison counter (in-memory, seeded for social proof) ────────────────
_counter_lock = threading.Lock()
_comparison_count = 1247  # seed


def _increment_counter():
    global _comparison_count
    with _counter_lock:
        _comparison_count += 1


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def _resolve_song(song: dict) -> str:
    """Download audio for a song entry (search or URL). Returns temp file path."""
    stype = song.get("type", "search")
    if stype == "url":
        url = (song.get("url") or "").strip()
        if not url:
            raise ValueError("URL is required when type is 'url'")
        return download_from_url(url)
    name = (song.get("name") or "").strip()
    artist = (song.get("artist") or "").strip()
    if not name:
        raise ValueError("Song name is required for search")
    # If artist is empty, use name as the full query
    return search_and_download(name, artist or name)


def _cleanup_paths(paths: list):
    for p in paths:
        if p:
            parent = os.path.dirname(p)
            if parent and parent != "/tmp" and parent != tempfile.gettempdir():
                shutil.rmtree(parent, ignore_errors=True)


# ── API routes ──────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def stats():
    """Return comparison counter for the frontend."""
    return jsonify({"comparisons": _comparison_count})


@app.route("/api/compare", methods=["POST"])
def compare():
    """Compare two uploaded audio files."""
    if "file_a" not in request.files or "file_b" not in request.files:
        return jsonify({"error": "Two files required (file_a, file_b)"}), 400

    file_a = request.files["file_a"]
    file_b = request.files["file_b"]

    for f, label in [(file_a, "file_a"), (file_b, "file_b")]:
        if not f.filename or not _allowed_file(f.filename):
            return jsonify({"error": f"Unsupported file type for {label}"}), 400

    tmp_a = tmp_b = None
    try:
        ext_a = os.path.splitext(file_a.filename)[1].lower()
        ext_b = os.path.splitext(file_b.filename)[1].lower()
        tmp_a = tempfile.NamedTemporaryFile(delete=False, suffix=ext_a)
        tmp_b = tempfile.NamedTemporaryFile(delete=False, suffix=ext_b)
        file_a.save(tmp_a.name)
        file_b.save(tmp_b.name)

        features_a = extract_features(tmp_a.name)
        features_b = extract_features(tmp_b.name)
        result = compute_similarity(features_a, features_b)
        _increment_counter()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Comparison failed: {str(e)}"}), 500
    finally:
        for p in [tmp_a, tmp_b]:
            if p:
                try:
                    os.unlink(p.name)
                except OSError:
                    pass


@app.route("/api/compare-mixed", methods=["POST"])
def compare_mixed():
    """Compare two songs — each can be a search query or a YouTube URL."""
    data = request.get_json(silent=True)
    if not data or "song_a" not in data or "song_b" not in data:
        return jsonify({"error": "song_a and song_b are required"}), 400

    path_a = path_b = None
    try:
        path_a = _resolve_song(data["song_a"])
        path_b = _resolve_song(data["song_b"])

        features_a = extract_features(path_a)
        features_b = extract_features(path_b)
        result = compute_similarity(features_a, features_b)
        _increment_counter()
        return jsonify(result)
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Comparison failed: {str(e)}"}), 500
    finally:
        _cleanup_paths([path_a, path_b])


# ── iTunes search proxy (CORS workaround) ──────────────────────────────────

@app.route("/api/search")
def itunes_search():
    """Proxy iTunes Search API to avoid browser CORS restrictions."""
    term = request.args.get("term", "").strip()
    if not term or len(term) < 2:
        return jsonify({"results": []})

    try:
        r = http_requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "media": "music", "entity": "song", "limit": "6"},
            timeout=10,
        )
        return jsonify(r.json())
    except Exception:
        return jsonify({"results": []})


# ── Serve React SPA ────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    """Serve React frontend — any non-API route falls through to index.html."""
    file_path = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "false").lower() == "true")
