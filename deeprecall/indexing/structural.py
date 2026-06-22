"""Structural position index.

Tracks the hierarchy (which section a chunk belongs to, which chunks are
its parents/siblings) so context assembly can pull in a parent-section
summary and logical neighbours, and so retrieval can apply intent-aware
boosts based on chunk *type*.
"""

from __future__ import annotations

from ..models import Chunk


class StructuralIndex:
    def __init__(self):
        self._chunks: dict[str, Chunk] = {}
        self._by_parent: dict[str, list[str]] = {}

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.id] = c
            self._by_parent.setdefault(c.parent_id or "", []).append(c.id)

    def get(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    def siblings(self, chunk_id: str) -> list[Chunk]:
        c = self._chunks.get(chunk_id)
        if not c:
            return []
        ids = self._by_parent.get(c.parent_id or "", [])
        return [self._chunks[i] for i in ids if i != chunk_id and i in self._chunks]

    def section_summary(self, chunk_id: str, max_chars: int = 280) -> str:
        """Cheap extractive 'summary' of the containing section."""
        c = self._chunks.get(chunk_id)
        if not c:
            return ""
        ids = self._by_parent.get(c.parent_id or "", [])
        text = " ".join(self._chunks[i].text for i in ids if i in self._chunks)
        return text[:max_chars].rsplit(" ", 1)[0] + ("…" if len(text) > max_chars else "")
