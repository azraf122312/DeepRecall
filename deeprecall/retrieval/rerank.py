"""Step 4: Cross-encoder re-ranking.

A cross-encoder (e.g. MiniLM cross-encoder) jointly scores (query, chunk)
pairs for far better precision than bi-encoder similarity. Used when the
library is installed; otherwise we fall back to a lexical-overlap proxy so
the stage still runs and reorders sensibly.
"""

from __future__ import annotations

import re

from ..models import ScoredChunk

_WORD = re.compile(r"[a-z0-9]+")


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:  # pragma: no cover - only when lib present
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self.backend = f"cross-encoder:{model_name}"
        except Exception:
            self.model = None
            self.backend = "lexical-overlap-fallback"

    def rerank(self, query: str, candidates: list[ScoredChunk],
               top_n: int) -> list[ScoredChunk]:
        pool = candidates[:top_n]
        if not pool:
            return candidates

        if self.model is not None:  # pragma: no cover
            pairs = [(query, sc.chunk.text) for sc in pool]
            scores = self.model.predict(pairs)
            for sc, s in zip(pool, scores):
                sc.sources["cross_encoder"] = float(s)
                sc.score = float(s)
        else:
            q_terms = set(_WORD.findall(query.lower()))
            for sc in pool:
                terms = set(_WORD.findall(sc.chunk.text.lower()))
                overlap = len(q_terms & terms) / (len(q_terms) or 1)
                sc.sources["cross_encoder"] = overlap
                # blend lexical signal with the fused rank score
                sc.score = 0.5 * sc.score + 0.5 * overlap

        pool.sort(key=lambda sc: sc.score, reverse=True)
        return pool + candidates[top_n:]
