"""Step 5: Context assembly (not just concatenation).

  - Include: chunk + parent-section summary + related chunks
  - Order: most relevant first, but preserve logical flow within a source
  - Deduplicate: drop near-duplicate / fully-contained chunks
  - Cite: every block keeps its source id for grounded generation
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..indexing.structural import StructuralIndex
from ..models import ScoredChunk


@dataclass
class AssembledContext:
    blocks: list[dict] = field(default_factory=list)   # {ref, text, type, score}
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)

    def as_prompt(self, max_chars: int) -> str:
        out, used = [], 0
        for b in self.blocks:
            piece = f"[{b['ref']}] ({b['type']})\n{b['text']}\n"
            if used + len(piece) > max_chars:
                break
            out.append(piece)
            used += len(piece)
        return "\n".join(out)


def _is_dup(a: str, b: str) -> bool:
    a, b = a.strip(), b.strip()
    return a in b or b in a


class ContextAssembler:
    def __init__(self, structural: StructuralIndex):
        self.structural = structural

    def assemble(self, scored: list[ScoredChunk], final_k: int) -> AssembledContext:
        top = scored[:final_k]
        ctx = AssembledContext()
        seen_text: list[str] = []
        related: list[str] = []

        for i, sc in enumerate(top):
            c = sc.chunk
            if any(_is_dup(c.text, s) for s in seen_text):
                continue
            seen_text.append(c.text)

            ref = f"{i + 1}"
            ctx.blocks.append({
                "ref": f"{c.source} {c.section_path}".strip(),
                "text": c.text,
                "type": c.chunk_type.value,
                "score": round(sc.score, 4),
            })
            ctx.sources.append(c.citation())

            # surface sibling/related chunk titles as "related" pointers
            for rel in self.structural.siblings(c.id):
                label = (rel.section_path or rel.text[:50]).strip()
                if label and label not in related:
                    related.append(label)

        ctx.related = related[:4]
        return ctx
