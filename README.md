# ⚡ Autocomplete Search System

A Trie-backed prefix search engine with a Flask REST API and a small web UI,
plus optional Redis caching. Built to demonstrate a classic data structure
(Trie) applied to a real product feature (search-as-you-type).

## Features
- Trie data structure for O(prefix length + matches) lookups
- Frequency-based ranking (most common word wins ties, then alphabetical)
- REST API (`/api/autocomplete`, `/api/stats`, `/api/insert`)
- Runtime word insertion endpoint
- Optional Redis response caching (app runs fine without Redis too)
- Web UI with debounced input and live response-time display
- Unit tests (11 cases) + a load-test script for real benchmarking
- Dockerized, with `docker-compose` wiring in Redis

## Project Structure
```
autocomplete-search/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── main.py      # Flask app + routes
│   ├── trie.py       # Trie data structure (the core algorithm)
│   └── utils.py       # word-loading + timing helpers
├── data/
│   └── words.txt       # ~10,000 English words with frequency rank
├── tests/
│   ├── test_trie.py     # unit tests (pytest)
│   └── load_test.py      # simple benchmark script
└── web/
    └── index.html         # demo UI
```

## Quick Start

### Option A — Docker (recommended, includes Redis caching)
```bash
docker-compose up --build
# visit http://localhost:5000
```

### Option B — Local Python (no Redis, still fully functional)
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd app
python main.py
# visit http://localhost:5000
```

### Run the tests
```bash
pip install -r requirements.txt
pytest tests/test_trie.py -v
```

### Run the benchmark (against a running instance)
```bash
python tests/load_test.py --url http://localhost:5000 --query ama --requests 1000
```

## API

### `GET /api/autocomplete?q=<prefix>&limit=<n>`
```bash
curl "http://localhost:5000/api/autocomplete?q=amaz"
```
```json
{
  "query": "amaz",
  "suggestions": ["amazon", "amazing"],
  "response_time_ms": 0.03,
  "cached": false
}
```

### `GET /api/stats`
```json
{
  "status": "healthy",
  "words_loaded": 9989,
  "load_time_ms": 45.38,
  "cache_enabled": false
}
```

### `POST /api/insert`
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"word":"amazonprime","frequency":500}' \
  http://localhost:5000/api/insert
```

## How It Works

A Trie stores each word one character per node, so words sharing a prefix
share the same path from the root. To answer `q=amaz`, the engine walks 4
nodes deep (one per character of the prefix) and then does a depth-first
search of just the subtree under that node — it never looks at words that
don't start with "amaz".

```
      root
      /  \
     a    g
     |    |
     m    o
     |    |
     a    o
     |    |
     z    g
    / \    \
   o   i    l
   |   |    |
   n   n    e
  (amazon) (amazing) (google)
```

**Complexity**
- Insert: `O(L)` where `L` = word length
- Search: `O(L + K log K)` where `L` = prefix length, `K` = number of
  matches under that prefix (the `log K` comes from ranking the matches)
- Space: proportional to the number of *unique* character paths, not the
  number of words — shared prefixes are stored once

## Measured Performance

These numbers came from actually running the benchmark script in this repo
against the local dev server (single Flask process, no Redis, ~10K words),
not simulated:

| Metric | Result |
|---|---|
| Dataset | 9,989 unique words, frequency-ranked |
| Trie build time | ~45ms at startup |
| Per-query latency (server-side) | 0.02–0.05ms |
| End-to-end p50 latency (client, incl. HTTP overhead) | ~1.1ms |
| End-to-end p99 latency | ~1.7ms |
| Sequential throughput (single dev-server process) | ~800 req/s |

Two things worth calling out honestly if this comes up in an interview:
- The **server-side** search itself is sub-millisecond — the ~1ms
  end-to-end number is mostly HTTP/loopback overhead, not the algorithm.
- The ~800 req/s figure is from a **single-threaded dev server answering
  requests sequentially** from one client. Running behind gunicorn with
  multiple workers (as the Dockerfile does) and testing with concurrent
  clients would show meaningfully higher throughput — if you want that
  number, run `tests/load_test.py` with a concurrent client against the
  Docker build and report what you actually measure, rather than quoting
  a number nobody ran.
- The bundled `data/words.txt` has ~10K words for a fast, realistic demo.
  The Trie itself has no problem scaling to a much larger dictionary; if
  you want a "1M+ words" talking point, swap in a larger word list (e.g.
  a full English dictionary or product-title corpus) and rerun the
  benchmark — don't just claim the number.

## Interview Talking Points

**Why a Trie instead of a HashMap or a database query?**
A HashMap gives O(1) lookup for an *exact* key, but prefix search needs
"all keys starting with X" — that means scanning every key, which is
O(n). A Trie turns that into a direct walk to the prefix node followed by
a search of only the matching subtree. A database `LIKE 'prefix%'` query
also works, but pays network and query-planning overhead on every
keystroke, which a Trie held in memory avoids entirely.

**How would you scale this to a much larger dataset or more traffic?**
1. Cache popular prefixes (already wired up here via Redis)
2. Shard the Trie by first character (or first N characters) across nodes
3. Serve read replicas behind a load balancer; the Trie is read-heavy
4. Rebuild/refresh the Trie periodically from a source-of-truth store
   rather than mutating it under live traffic
5. Add typo-tolerance (edit-distance / fuzzy matching) as a separate,
   slower fallback path when exact-prefix search returns nothing

**What's the space complexity?**
Worst case `O(ALPHABET_SIZE × N × M)` (N words, average length M), but in
practice much lower because words sharing a prefix share nodes — the
Trie only pays for the number of *distinct* character paths, not the raw
character count across all words.

## Possible Extensions
- Typo correction via edit distance for zero-result queries
- Personalized ranking (per-user frequency boosts)
- Sharded/distributed Trie for datasets too large for one process
- Analytics on query patterns to inform ranking weights
