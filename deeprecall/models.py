"""Core data structures for DeepRecall.

These are the shared currency between every stage of the pipeline. The key
idea behind DeepRecall is that documents are *not* flat text: they have
structure, hierarchy, and implicit relationships. Every chunk therefore
carries its structural position and typed metadata, not just a string.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(str, Enum):
    """Structural role of a node in a parsed document tree."""

    DOCUMENT = "document"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    CODE = "code"


class ChunkType(str, Enum):
    """Semantic unit type. Chunking is by meaning, not token count."""

    DEFINITION = "definition"          # term + explanation
    PROCEDURE = "procedure"            # numbered steps / how-to
    COMPARISON = "comparison"          # comparison table
    CODE_EXAMPLE = "code_example"      # code + explanation pair
    FAQ = "faq"                        # question + answer
    WARNING = "warning"                # caution / gotcha
    REFERENCE = "reference"            # plain reference prose
    NARRATIVE = "narrative"            # general prose fallback


class Intent(str, Enum):
    """Per-section / per-query intent. Drives structural retrieval boosts."""

    HOWTO = "how-to"
    REFERENCE = "reference"
    TROUBLESHOOTING = "troubleshooting"
    DECISION = "decision"
    WARNING = "warning"
    CONCEPTUAL = "conceptual"
    UNKNOWN = "unknown"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class DocNode:
    """A node in the structural tree produced by the parser."""

    node_type: NodeType
    text: str
    level: int = 0                                  # heading depth
    title: str = ""                                 # nearest heading title
    parent_id: Optional[str] = None
    order: int = 0                                  # reading order
    id: str = field(default_factory=lambda: _new_id("node"))
    children: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    """A retrievable, semantically-coherent unit."""

    text: str
    chunk_type: ChunkType = ChunkType.NARRATIVE
    intent: Intent = Intent.UNKNOWN
    source: str = ""                                # e.g. "kubernetes-guide.md"
    section_path: str = ""                          # e.g. "§4.2 HPA Configuration"
    parent_id: Optional[str] = None
    related_ids: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("chunk"))

    def citation(self) -> str:
        sec = f" {self.section_path}" if self.section_path else ""
        return f"{self.source}{sec}".strip()


@dataclass
class ScoredChunk:
    """A chunk with a retrieval score and provenance of where it came from."""

    chunk: Chunk
    score: float
    sources: dict[str, float] = field(default_factory=dict)   # index_name -> raw score

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"ScoredChunk({self.chunk.id}, score={self.score:.3f}, type={self.chunk.chunk_type.value})"


@dataclass
class Answer:
    """Final generated answer with grounding metadata."""

    text: str
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    confidence: float = 0.0
    refused: bool = False

    def render(self) -> str:
        if self.refused:
            return self.text
        out = ["Answer", "─" * 60, self.text, ""]
        if self.sources:
            out.append("Sources:")
            out += [f"  [{i + 1}] {s}" for i, s in enumerate(self.sources)]
            out.append("")
        if self.related:
            out.append("Related:")
            out += [f"  → {r}" for r in self.related]
        out.append("")
        out.append(f"(confidence: {self.confidence:.0%})")
        return "\n".join(out)
