"""Sparse keyword index (BM25).

Pure-Python BM25 (Okapi). In production this would be Elasticsearch, but
the scoring is identical in spirit and needs no external service.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ..models import Chunk

_WORD = re.compile(r"[a-z0-9][a-z0-9\-]*")
_STOP = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "is",
         "are", "be", "with", "this", "that", "it", "as", "by", "at"}


def _tokenize(text: str) -> list[str]:
    return [t for t in _WORD.findall(text.lower()) if t not in _STOP]


class SparseIndex:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._docs: dict[str, list[str]] = {}
        self._chunks: dict[str, Chunk] = {}
        self._df: Counter = Counter()
        self._avg_len: float = 0.0

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            toks = _tokenize(f"{c.section_path} {c.text}")
            self._docs[c.id] = toks
            self._chunks[c.id] = c
            for term in set(toks):
                self._df[term] += 1
        if self._docs:
            self._avg_len = sum(len(d) for d in self._docs.values()) / len(self._docs)

    def _idf(self, term: str) -> float:
        n = len(self._docs)
        df = self._df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        q_terms = _tokenize(query)
        scored: list[tuple[Chunk, float]] = []
        for cid, toks in self._docs.items():
            tf = Counter(toks)
            dl = len(toks) or 1
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = self._idf(term)
                num = tf[term] * (self.k1 + 1)
                den = tf[term] + self.k1 * (1 - self.b + self.b * dl / (self._avg_len or 1))
                score += idf * num / den
            if score > 0:
                scored.append((self._chunks[cid], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
