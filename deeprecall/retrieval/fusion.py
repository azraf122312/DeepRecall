"""Step 3: Reciprocal Rank Fusion (RRF).

score_RRF(d) = Σ_i 1 / (k + rank_i(d))   over each index i that ranked d.
k = 60 is the standard constant. RRF is rank-based, so it fuses indices
with wildly different score scales (cosine vs BM25 vs graph counts) without
needing to normalize them.
"""

from __future__ import annotations

from ..models import Chunk, ScoredChunk


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[tuple[Chunk, float]]],
    k: int = 60,
) -> list[ScoredChunk]:
    fused: dict[str, ScoredChunk] = {}
    for index_name, results in ranked_lists.items():
        for rank, (chunk, raw) in enumerate(results, start=1):
            contribution = 1.0 / (k + rank)
            if chunk.id not in fused:
                fused[chunk.id] = ScoredChunk(chunk=chunk, score=0.0, sources={})
            fused[chunk.id].score += contribution
            fused[chunk.id].sources[index_name] = raw

    out = list(fused.values())
    out.sort(key=lambda sc: sc.score, reverse=True)
    return out
