"""utils.py — small helpers for loading data and timing requests."""

from __future__ import annotations
import os
import time
from contextlib import contextmanager
from typing import Iterator

from trie import Trie


def load_words_into_trie(trie: Trie, path: str) -> int:
    """Load a `word<TAB>frequency` file into the given trie.

    Falls back to treating each line as a bare word (frequency=1) if no
    tab-separated frequency is present, so plain word lists work too.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Word list not found: {path}")

    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "\t" in line:
                word, freq_str = line.split("\t", 1)
                try:
                    freq = int(freq_str)
                except ValueError:
                    freq = 1
            else:
                word, freq = line, 1
            trie.insert(word.lower(), freq)
            count += 1
    return count


@contextmanager
def timer_ms() -> Iterator[dict]:
    """Context manager yielding a dict that gets populated with
    `elapsed_ms` once the block exits. Usage:

        with timer_ms() as t:
            do_work()
        print(t["elapsed_ms"])
    """
    result: dict = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed_ms"] = (time.perf_counter() - start) * 1000
