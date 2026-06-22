"""Multi-vector index orchestrator.

Owns the four indices (dense, sparse, graph, structural) and exposes a
single add()/search() surface. Each search() returns per-index ranked lists,
which the retrieval engine fuses with RRF.
"""

from __future__ import annotations

from ..config import Config
from ..models import Chunk
from .dense import DenseIndex
from .sparse import SparseIndex
from .graph import GraphIndex
from .structural import StructuralIndex


class IndexStore:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.dense = DenseIndex(self.config.embedding_model, self.config.embedding_dim)
        self.sparse = SparseIndex()
        self.graph = GraphIndex()
        self.structural = StructuralIndex()
        self._all: dict[str, Chunk] = {}

    def add(self, chunks: list[Chunk]) -> None:
        self.dense.add(chunks)
        self.sparse.add(chunks)
        self.graph.add(chunks)
        self.structural.add(chunks)
        for c in chunks:
            self._all[c.id] = c

    def get(self, chunk_id: str) -> Chunk | None:
        return self._all.get(chunk_id)

    def search_all(self, query: str) -> dict[str, list[tuple[Chunk, float]]]:
        k = self.config.retrieval.top_k_per_index
        return {
            "dense": self.dense.search(query, k),
            "sparse": self.sparse.search(query, k),
            "graph": self.graph.search(query, k),
        }

    @property
    def size(self) -> int:
        return len(self._all)

    @property
    def backends(self) -> dict[str, str]:
        return {"dense": self.dense.backend, "sparse": "bm25", "graph": "in-memory-entity"}
