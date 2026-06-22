"""Generation with verification.

Standard RAG: "Here's what I found..."
DeepRecall:   "Based on [3 sources], the recommended approach is X, with
               caveat Y from [warning block]."

Features:
  - Source grounding: every answer carries its source IDs
  - Uncertainty quantification: confidence derived from retrieval signal
  - "I don't know" detection: no relevant chunks -> refuse
  - Optional LLM generation via the Anthropic API (claude-opus-4-8 /
    claude-sonnet-4-6), with a deterministic extractive fallback so the
    pipeline answers even with no API key.
"""

from __future__ import annotations

from ..config import Config
from ..models import Answer
from ..retrieval.engine import RetrievalResult

_SYSTEM = (
    "You are DeepRecall, a structure-aware retrieval assistant. Answer ONLY "
    "from the provided context blocks. Cite the bracketed source ref after "
    "each claim, e.g. [1]. If the context does not contain the answer, say so "
    "plainly. Surface any warning/caveat blocks explicitly."
)


class Generator:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._client = self._maybe_client()

    def _maybe_client(self):
        if not (self.config.generation.use_llm and self.config.anthropic_api_key):
            return None
        try:  # pragma: no cover - only when sdk + key present
            import anthropic
            return anthropic.Anthropic(api_key=self.config.anthropic_api_key)
        except Exception:
            return None

    @staticmethod
    def _confidence(result: RetrievalResult) -> float:
        """Confidence from retrieval *consensus*, not from the #1/#2 gap.

        The precise indices (BM25 + entity graph) only fire on genuine
        keyword/entity matches, so their presence on the top chunk is the
        strongest signal that the corpus actually covers the query. The
        cross-encoder (or lexical-overlap fallback) confirms relevance. The
        dense fallback matches everything weakly, so it is intentionally not
        a confidence driver on its own.
        """
        if not result.scored:
            return 0.0
        top = result.scored[0]
        precise = sum(1 for k in ("sparse", "graph") if k in top.sources)
        ce = top.sources.get("cross_encoder", 0.0)
        conf = (0.45 * (precise / 2)
                + 0.40 * min(ce * 1.5, 1.0)
                + 0.15 * min(top.score * 3, 1.0))
        return max(0.0, min(1.0, conf))

    def generate(self, query: str, result: RetrievalResult) -> Answer:
        gen = self.config.generation
        confidence = self._confidence(result)

        if not result.context.blocks or confidence < gen.min_confidence_to_answer:
            return Answer(
                text=("I don't have enough grounded information to answer that "
                      "confidently. No sufficiently relevant sources were found."),
                confidence=confidence, refused=True,
            )

        prompt_ctx = result.context.as_prompt(gen.max_context_chars)

        if self._client is not None:  # pragma: no cover
            text = self._generate_llm(query, prompt_ctx)
        else:
            text = self._generate_extractive(query, result)

        return Answer(
            text=text,
            sources=result.context.sources,
            related=result.context.related,
            confidence=confidence,
        )

    def _generate_llm(self, query: str, context: str) -> str:  # pragma: no cover
        msg = self._client.messages.create(
            model=self.config.generation.model,
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Context blocks:\n\n{context}\n\nQuestion: {query}",
            }],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    def _generate_extractive(self, query: str, result: RetrievalResult) -> str:
        """No-LLM grounded answer: stitch the top blocks with inline citations."""
        lines: list[str] = []
        warnings: list[str] = []
        for i, b in enumerate(result.context.blocks, start=1):
            snippet = b["text"].strip().split("\n\n")[0].strip()
            if len(snippet) > 320:
                snippet = snippet[:320].rsplit(" ", 1)[0] + "…"
            if b["type"] == "warning":
                warnings.append(f"{snippet} [{i}]")
            else:
                lines.append(f"{snippet} [{i}]")

        intent = result.plan.intent.value
        head = f"Based on {len(result.context.blocks)} source(s), here is what applies to your {intent} query:"
        body = "\n\n".join(lines) if lines else "(see sources)"
        out = f"{head}\n\n{body}"
        if warnings:
            out += "\n\n⚠ Caveats:\n" + "\n".join(f"- {w}" for w in warnings)
        return out
