"""
main.py — Flask REST API for the autocomplete search engine.

Endpoints
---------
GET  /                       -> serves the demo web UI
GET  /api/autocomplete?q=... -> top-N suggestions for a prefix
GET  /api/stats              -> health + dataset stats
POST /api/insert             -> add/boost a word at runtime  {"word": "...", "frequency": 1}

Run directly:
    python main.py
or via gunicorn / Docker (see Dockerfile).
"""

from __future__ import annotations
import os
import time
import logging

from flask import Flask, request, jsonify, send_from_directory

from trie import Trie
from utils import load_words_into_trie, timer_ms

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("autocomplete")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "words.txt")
WEB_DIR = os.path.join(BASE_DIR, "web")

app = Flask(__name__, static_folder=None)

# ---------------------------------------------------------------------- #
# Optional Redis cache. The app works fine without Redis — it just skips
# caching if the connection isn't available (e.g. running `python main.py`
# without `docker-compose up`).
# ---------------------------------------------------------------------- #
_redis_client = None
try:
    import redis  # type: ignore

    _redis_host = os.environ.get("REDIS_HOST", "localhost")
    _redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    _candidate = redis.Redis(host=_redis_host, port=_redis_port, socket_connect_timeout=0.2)
    _candidate.ping()
    _redis_client = _candidate
    log.info("Connected to Redis at %s:%s — caching enabled", _redis_host, _redis_port)
except Exception:
    log.info("Redis not available — running without caching (this is fine)")
    _redis_client = None

CACHE_TTL_SECONDS = 60

# ---------------------------------------------------------------------- #
# Load the trie once at startup
# ---------------------------------------------------------------------- #
trie = Trie()
_load_start = time.perf_counter()
_word_count = load_words_into_trie(trie, DATA_PATH)
_load_ms = (time.perf_counter() - _load_start) * 1000
log.info("Loaded %d words into trie in %.2fms", _word_count, _load_ms)


# ---------------------------------------------------------------------- #
# Routes
# ---------------------------------------------------------------------- #
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/api/autocomplete", methods=["GET"])
def autocomplete():
    prefix = request.args.get("q", "").strip().lower()
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    if not prefix:
        return jsonify({"query": "", "suggestions": [], "response_time_ms": 0.0, "cached": False})

    cache_key = f"ac:{prefix}:{limit}"
    if _redis_client is not None:
        try:
            cached = _redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached is not None:
            import json

            return jsonify(
                {
                    "query": prefix,
                    "suggestions": json.loads(cached),
                    "response_time_ms": 0.0,
                    "cached": True,
                }
            )

    with timer_ms() as t:
        suggestions = trie.search_suggestions(prefix, limit=limit)

    if _redis_client is not None:
        try:
            import json

            _redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(suggestions))
        except Exception:
            pass

    return jsonify(
        {
            "query": prefix,
            "suggestions": suggestions,
            "response_time_ms": round(t["elapsed_ms"], 3),
            "cached": False,
        }
    )


@app.route("/api/insert", methods=["POST"])
def insert_word():
    payload = request.get_json(silent=True) or {}
    word = str(payload.get("word", "")).strip().lower()
    frequency = int(payload.get("frequency", 1))

    if not word or not word.isalpha():
        return jsonify({"error": "word must be a non-empty alphabetic string"}), 400

    trie.insert(word, frequency)
    return jsonify({"status": "ok", "word": word, "frequency": frequency})


@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(
        {
            "status": "healthy",
            "words_loaded": trie.word_count(),
            "load_time_ms": round(_load_ms, 2),
            "cache_enabled": _redis_client is not None,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
