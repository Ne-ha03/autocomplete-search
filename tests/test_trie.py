"""
test_trie.py — unit tests for the Trie implementation.

Run with:
    pytest tests/
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from trie import Trie  # noqa: E402


def make_trie():
    t = Trie()
    t.insert("amazon", 100)
    t.insert("amazon prime", 80)
    t.insert("amazonian", 5)
    t.insert("amaze", 20)
    t.insert("amazing", 60)
    t.insert("apple", 90)
    t.insert("app", 70)
    t.insert("application", 40)
    return t


def test_empty_prefix_matches_are_scoped_correctly():
    t = make_trie()
    assert t.search_suggestions("xyz") == []


def test_basic_prefix_match():
    t = make_trie()
    results = t.search_suggestions("ama")
    assert set(results) == {"amazon", "amazon prime", "amazonian", "amaze", "amazing"}


def test_ranking_by_frequency_descending():
    t = make_trie()
    results = t.search_suggestions("ama", limit=3)
    # amazon(100) > amazon prime(80) > amazing(60)
    assert results == ["amazon", "amazon prime", "amazing"]


def test_limit_is_respected():
    t = make_trie()
    results = t.search_suggestions("a", limit=2)
    assert len(results) == 2


def test_exact_word_prefix_included():
    t = make_trie()
    results = t.search_suggestions("app")
    assert "app" in results
    assert "apple" in results
    assert "application" in results


def test_case_insensitivity():
    t = make_trie()
    assert t.search_suggestions("AMA") == t.search_suggestions("ama")


def test_insert_accumulates_frequency():
    t = Trie()
    t.insert("test", 1)
    t.insert("test", 1)
    t.insert("test", 1)
    scored = t.search_suggestions_with_scores("test")
    assert scored == [("test", 3)]


def test_delete_removes_word():
    t = make_trie()
    assert "app" in t.search_suggestions("app")
    assert t.delete("app") is True
    assert "app" not in t.search_suggestions("app")
    # siblings sharing the prefix path must survive
    assert "apple" in t.search_suggestions("app")


def test_delete_nonexistent_word_returns_false():
    t = make_trie()
    assert t.delete("doesnotexist") is False


def test_alphabetical_tiebreak():
    t = Trie()
    t.insert("bat", 5)
    t.insert("ant", 5)
    t.insert("cat", 5)
    # equal frequency -> alphabetical order
    assert t.search_suggestions("") == ["ant", "bat", "cat"]


def test_word_count_tracks_unique_words():
    t = Trie()
    t.insert("dog")
    t.insert("dog")  # duplicate, should not double-count
    t.insert("doge")
    assert t.word_count() == 2


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
