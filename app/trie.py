"""
trie.py — Core Trie data structure for the autocomplete engine.

A Trie (prefix tree) stores words character-by-character so that all words
sharing a common prefix share the same path from the root. This makes
prefix lookups very fast: instead of scanning every word in the dataset,
we walk directly to the node representing the prefix and only explore the
subtree beneath it.

Complexity
----------
insert(word):            O(L)              L = length of the word
search_suggestions(p):   O(L + K log K)     L = len(prefix), K = matches
                                             under that prefix (log K is
                                             from sorting the matches)
space:                   O(ALPHABET_SIZE * N * M) worst case
                                             N = number of words,
                                             M = average word length
                                             (much better in practice due
                                             to shared prefixes)
"""

from __future__ import annotations
import heapq
from typing import Dict, List, Tuple, Optional


class TrieNode:
    __slots__ = ("children", "is_word", "frequency", "word")

    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.is_word: bool = False
        self.frequency: int = 0
        # Cached full word at terminal nodes avoids rebuilding strings
        # during traversal.
        self.word: Optional[str] = None


class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()
        self._word_count = 0

    # ------------------------------------------------------------------ #
    # Mutation
    # ------------------------------------------------------------------ #
    def insert(self, word: str, frequency: int = 1) -> None:
        """Insert a word into the trie, accumulating frequency if it
        already exists (so re-inserting the same word boosts its rank)."""
        if not word:
            return

        node = self.root
        for char in word:
            child = node.children.get(char)
            if child is None:
                child = TrieNode()
                node.children[char] = child
            node = child

        if not node.is_word:
            self._word_count += 1
            node.word = word
        node.is_word = True
        node.frequency += frequency

    def delete(self, word: str) -> bool:
        """Remove a word from the trie. Returns True if it existed."""
        node = self.root
        path = [node]
        for char in word:
            node = node.children.get(char)
            if node is None:
                return False
            path.append(node)

        if not node.is_word:
            return False

        node.is_word = False
        node.frequency = 0
        node.word = None
        self._word_count -= 1

        # Prune now-dead branches (nodes with no children and not a word)
        for parent, char in zip(reversed(path[:-1]), reversed(word)):
            child = parent.children[char]
            if child.children or child.is_word:
                break
            del parent.children[char]

        return True

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #
    def search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Return up to `limit` suggestions for `prefix`, ranked by
        frequency (descending) then alphabetically."""
        results = self.search_suggestions_with_scores(prefix, limit)
        return [word for word, _freq in results]

    def search_suggestions_with_scores(
        self, prefix: str, limit: int = 10
    ) -> List[Tuple[str, int]]:
        prefix = prefix.lower()
        node = self._walk(prefix)
        if node is None:
            return []

        # If the prefix itself is a complete, valid word, make sure it is
        # included in the candidate set even though DFS below already
        # covers it (kept explicit for clarity/readability).
        candidates: List[Tuple[str, int]] = []
        self._dfs(node, prefix, candidates)

        # Top-K selection via heap: O(K log limit), cheaper than a full
        # sort when the candidate set under a short/common prefix is large.
        top = heapq.nsmallest(limit, candidates, key=lambda item: (-item[1], item[0]))
        return top

    def is_prefix(self, prefix: str) -> bool:
        return self._walk(prefix.lower()) is not None

    def word_count(self) -> int:
        return self._word_count

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _walk(self, prefix: str) -> Optional[TrieNode]:
        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return None
        return node

    def _dfs(
        self,
        node: TrieNode,
        current_word: str,
        out: List[Tuple[str, int]],
    ) -> None:
        """Iterative DFS (avoids Python recursion-limit issues on very
        deep/large tries) collecting (word, frequency) pairs."""
        stack = [(node, current_word)]
        while stack:
            n, word = stack.pop()
            if n.is_word:
                out.append((word, n.frequency))
            for char, child in n.children.items():
                stack.append((child, word + char))
