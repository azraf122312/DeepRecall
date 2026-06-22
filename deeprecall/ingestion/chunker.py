"""Step 3: Multi-granular, semantic chunking.

We do NOT chunk by token count. We chunk by semantic unit:
  - Definition block (term + explanation)
  - Procedure (numbered steps)
  - Comparison table
  - Code example + explanation pair
  - FAQ (question + answer)
  - Warning block

Each chunk carries its type, parent section path, and (later) related IDs.
"""

from __future__ import annotations

import re

from ..models import Chunk, ChunkType, DocNode, Intent, NodeType

_NUMBERED = re.compile(r"^\s*\d+[.)]\s+", re.M)
_QUESTION = re.compile(r".+\?\s*$")
_DEFINITION = re.compile(r"^\s*[\w\s-]{2,40}\s*(:|—|-|is|are)\s+", re.I)


def _section_path(node: DocNode, by_id: dict[str, DocNode]) -> str:
    """Walk parents to build a human-readable section path."""
    parts: list[str] = []
    cur: DocNode | None = node
    seen = set()
    while cur and cur.id not in seen:
        seen.add(cur.id)
        if cur.node_type in (NodeType.SECTION, NodeType.SUBSECTION) and cur.title:
            parts.append(cur.title)
        cur = by_id.get(cur.parent_id) if cur.parent_id else None
    return " › ".join(reversed(parts))


def _classify_chunk(node: DocNode, intent: Intent) -> ChunkType:
    text = node.text
    if node.node_type == NodeType.CODE:
        return ChunkType.CODE_EXAMPLE
    if node.node_type == NodeType.TABLE:
        return ChunkType.COMPARISON
    if intent == Intent.WARNING:
        return ChunkType.WARNING
    if len(_NUMBERED.findall(text)) >= 2 or intent == Intent.HOWTO:
        return ChunkType.PROCEDURE
    if _QUESTION.match(node.title or "") or _QUESTION.match(text.splitlines()[0] if text else ""):
        return ChunkType.FAQ
    if _DEFINITION.match(text):
        return ChunkType.DEFINITION
    if intent == Intent.REFERENCE:
        return ChunkType.REFERENCE
    return ChunkType.NARRATIVE


class Chunker:
    def __init__(self, min_chars: int = 40, merge_short_into_section: bool = True):
        self.min_chars = min_chars
        self.merge = merge_short_into_section

    def chunk(self, nodes: list[DocNode], enrichment: dict[str, dict],
              source: str = "") -> list[Chunk]:
        by_id = {n.id: n for n in nodes}
        chunks: list[Chunk] = []

        for n in nodes:
            if n.node_type in (NodeType.DOCUMENT, NodeType.SECTION, NodeType.SUBSECTION):
                continue  # headings become section_path context, not chunks
            body = n.text.strip()
            if len(body) < self.min_chars and n.node_type == NodeType.PARAGRAPH:
                continue  # skip trivial fragments

            meta = enrichment.get(n.id, {})
            intent: Intent = meta.get("intent", Intent.UNKNOWN)
            ctype = _classify_chunk(n, intent)

            # Pair a code block with the preceding explanatory paragraph.
            text = body
            if ctype == ChunkType.CODE_EXAMPLE:
                prev = self._previous_paragraph(n, nodes, by_id)
                if prev:
                    text = f"{prev}\n\n{body}"

            chunks.append(Chunk(
                text=text,
                chunk_type=ctype,
                intent=intent,
                source=source,
                section_path=_section_path(n, by_id),
                parent_id=n.parent_id,
                entities=meta.get("entities", []),
            ))

        self._link_siblings(chunks)
        return chunks

    @staticmethod
    def _previous_paragraph(node: DocNode, nodes: list[DocNode],
                            by_id: dict[str, DocNode]) -> str | None:
        prev = [n for n in nodes if n.order < node.order
                and n.node_type == NodeType.PARAGRAPH
                and n.parent_id == node.parent_id]
        return prev[-1].text.strip() if prev else None

    @staticmethod
    def _link_siblings(chunks: list[Chunk]) -> None:
        """Chunks under the same parent section are 'related'."""
        by_parent: dict[str, list[Chunk]] = {}
        for c in chunks:
            by_parent.setdefault(c.parent_id or "", []).append(c)
        for group in by_parent.values():
            ids = [c.id for c in group]
            for c in group:
                c.related_ids = [i for i in ids if i != c.id]
