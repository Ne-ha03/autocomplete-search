"""
load_test.py — simple benchmark against a running instance of the API.

Usage:
    python tests/load_test.py --url http://localhost:5000 --requests 1000 --query ama
"""

import argparse
import statistics
import time
import urllib.request
import urllib.parse
import json


def run(url: str, query: str, n: int):
    endpoint = f"{url}/api/autocomplete?{urllib.parse.urlencode({'q': query})}"
    latencies = []

    overall_start = time.perf_counter()
    for _ in range(n):
        start = time.perf_counter()
        with urllib.request.urlopen(endpoint, timeout=5) as resp:
            json.loads(resp.read())
        latencies.append((time.perf_counter() - start) * 1000)
    overall_elapsed = time.perf_counter() - overall_start

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    p99 = latencies[int(len(latencies) * 0.99) - 1]

    print(f"Requests:        {n}")
    print(f"Total time:      {overall_elapsed:.2f}s")
    print(f"Throughput:      {n / overall_elapsed:.1f} req/s")
    print(f"Mean latency:    {statistics.mean(latencies):.2f}ms")
    print(f"p50 latency:     {p50:.2f}ms")
    print(f"p95 latency:     {p95:.2f}ms")
    print(f"p99 latency:     {p99:.2f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--query", default="ama")
    parser.add_argument("--requests", type=int, default=1000)
    args = parser.parse_args()

    run(args.url, args.query, args.requests)
