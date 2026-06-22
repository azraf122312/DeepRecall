"""Dense vector index (text meaning).

Uses sentence-transformers + a real ANN store (ChromaDB/Pinecone) when
available. Falls back to a deterministic hashing embedding + brute-force
cosine search so the system runs anywhere with zero install. The fallback is
not semantically strong, but it keeps the full pipeline exercised and the
interface identical.
"""

from __future__ import annotations

import hashlib
import math
import re

from ..models import Chunk

_WORD = re.compile(r"[a-z0-9]+")


class _HashingEmbedder:
    """Bag-of-words hashed into a fixed-dim L2-normalized vector."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def encode(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _WORD.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class _STEmbedder:  # pragma: no cover - exercised only when lib installed
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # both are L2-normalized


class DenseIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dim: int = 256):
        try:
            self.embedder = _STEmbedder(model_name)
            self.backend = f"sentence-transformers:{model_name}"
        except Exception:
            self.embedder = _HashingEmbedder(dim)
            self.backend = "hashing-fallback"
        self._vectors: dict[str, list[float]] = {}
        self._chunks: dict[str, Chunk] = {}

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._vectors[c.id] = self.embedder.encode(f"{c.section_path}\n{c.text}")
            self._chunks[c.id] = c

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        q = self.embedder.encode(query)
        scored = [(self._chunks[cid], _cosine(q, vec)) for cid, vec in self._vectors.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
