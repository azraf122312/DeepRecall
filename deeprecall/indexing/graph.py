"""Relationship graph index.

Models the implicit relationships between chunks via the entities they
mention. In production this is Neo4j with typed edges (X "depends on" Y,
"prerequisite of", etc.). Here we build an in-memory entity co-occurrence
graph: chunks sharing entities are linked, and a query can traverse from
matched entities to related chunks the keyword/vector search would miss.
"""

from __future__ import annotations

import re

from ..models import Chunk

_WORD = re.compile(r"[a-z0-9][a-z0-9\-]*")


class GraphIndex:
    def __init__(self):
        # entity (lower) -> set of chunk ids
        self._entity_chunks: dict[str, set[str]] = {}
        self._chunks: dict[str, Chunk] = {}
        # adjacency: chunk id -> {neighbour id: weight}
        self._adj: dict[str, dict[str, float]] = {}

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.id] = c
            self._adj.setdefault(c.id, {})
            for ent in c.entities:
                self._entity_chunks.setdefault(ent.lower(), set()).add(c.id)

        # build edges between chunks that share an entity
        for ids in self._entity_chunks.values():
            ids = list(ids)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    self._adj[a][b] = self._adj[a].get(b, 0.0) + 1.0
                    self._adj[b][a] = self._adj[b].get(a, 0.0) + 1.0

    def _query_entities(self, query: str, known: list[str]) -> list[str]:
        ql = query.lower()
        return [e for e in known if e.lower() in ql]

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Find chunks directly mentioning query entities, then 1-hop neighbours."""
        known = list(self._entity_chunks.keys())
        hits = self._query_entities(query, [c for c in known])
        if not hits:
            return []

        scores: dict[str, float] = {}
        for ent in hits:
            for cid in self._entity_chunks.get(ent, ()):
                scores[cid] = scores.get(cid, 0.0) + 1.0
                # 1-hop traversal: related-to neighbours get a discounted boost
                for nbr, w in self._adj.get(cid, {}).items():
                    scores[nbr] = scores.get(nbr, 0.0) + 0.4 * w / (w + 1)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self._chunks[cid], s) for cid, s in ranked]
