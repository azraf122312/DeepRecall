"""DeepRecall — a structure-aware, hybrid-retrieval RAG engine.

Core insight: documents are not flat text. They have structure, hierarchy,
and implicit relationships — and so should the RAG that reads them.
"""

from .pipeline import DeepRecall
from .config import Config, RetrievalConfig, GenerationConfig
from .models import Answer, Chunk, ChunkType, Intent

__version__ = "0.1.0"
__all__ = [
    "DeepRecall", "Config", "RetrievalConfig", "GenerationConfig",
    "Answer", "Chunk", "ChunkType", "Intent",
]
