"""Hybrid retrieval engine.

Ties the retrieval steps together:
  1. Query understanding (intent + entities)
  2. Multi-index retrieval (dense + sparse + graph, in parallel-spirit)
  3. RRF fusion
  4. Structural boost (intent-aware, per chunk type)
  5. Cross-encoder re-ranking
  6. Context assembly
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from ..indexing.store import IndexStore
from ..models import ScoredChunk
from .assembly import AssembledContext, ContextAssembler
from .fusion import reciprocal_rank_fusion
from .query import QueryPlan, QueryUnderstanding
from .rerank import Reranker


@dataclass
class RetrievalResult:
    plan: QueryPlan
    scored: list[ScoredChunk]
    context: AssembledContext


class HybridRetriever:
    def __init__(self, store: IndexStore, config: Config | None = None):
        self.store = store
        self.config = config or store.config
        self.understanding = QueryUnderstanding()
        self.reranker = Reranker()
        self.assembler = ContextAssembler(store.structural)

    def _apply_structural_boost(self, scored: list[ScoredChunk], plan: QueryPlan) -> None:
        boosts = self.config.retrieval.structural_boosts.get(plan.intent.value, {})
        if not boosts:
            return
        for sc in scored:
            bonus = boosts.get(sc.chunk.chunk_type.value, 0.0)
            if bonus:
                sc.score += bonus
                sc.sources["structural_boost"] = bonus

    def retrieve(self, query: str) -> RetrievalResult:
        plan = self.understanding.plan(query)

        ranked_lists = self.store.search_all(query)
        fused = reciprocal_rank_fusion(ranked_lists, k=self.config.retrieval.rrf_k)

        self._apply_structural_boost(fused, plan)
        fused.sort(key=lambda sc: sc.score, reverse=True)

        reranked = self.reranker.rerank(query, fused, self.config.retrieval.rerank_top_n)
        context = self.assembler.assemble(reranked, self.config.retrieval.final_k)

        return RetrievalResult(plan=plan, scored=reranked, context=context)
