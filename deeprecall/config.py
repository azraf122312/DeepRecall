"""Configuration for DeepRecall.

Defaults are chosen so the system runs end-to-end with *zero* heavy
dependencies. Optional backends (sentence-transformers, cross-encoder,
Anthropic API, Neo4j) are auto-detected and used when available, otherwise
DeepRecall falls back to deterministic pure-Python implementations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class RetrievalConfig:
    top_k_per_index: int = 10        # candidates pulled from each index
    rrf_k: int = 60                  # reciprocal-rank-fusion constant (standard)
    final_k: int = 5                 # chunks handed to the generator
    rerank_top_n: int = 20           # how many to cross-encode
    # Structural boosts: intent -> {chunk_type: bonus}
    structural_boosts: dict = field(default_factory=lambda: {
        "how-to": {"procedure": 0.10, "code_example": 0.05},
        "troubleshooting": {"warning": 0.20, "faq": 0.10},
        "decision": {"comparison": 0.15},
        "conceptual": {"definition": 0.10},
    })


@dataclass
class GenerationConfig:
    use_llm: bool = True             # use Anthropic API if key present
    model: str = "claude-opus-4-8"   # see config note below
    self_consistency_samples: int = 1
    min_confidence_to_answer: float = 0.15
    max_context_chars: int = 8000


@dataclass
class Config:
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 256         # used by the hashing fallback
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)

    @property
    def anthropic_api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")
