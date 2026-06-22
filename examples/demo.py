"""End-to-end DeepRecall demo.

Run from the project root:

    python examples/demo.py

Works with zero extra dependencies (pure-Python fallbacks). If you install
sentence-transformers and set ANTHROPIC_API_KEY, the same code automatically
upgrades to real embeddings + LLM generation.
"""

from pathlib import Path
import sys

# Ensure Unicode (─ → ⚠ ›) prints on Windows consoles (cp1252) too.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deeprecall import DeepRecall  # noqa: E402

DOCS = Path(__file__).parent / "sample_docs"

QUERIES = [
    "How do I configure auto-scaling for the API gateway during high traffic?",
    "What happens if I forget the metrics-server?",
    "Should I use rate limiting or auto-scaling?",
    "How do I bake a sourdough loaf?",   # should refuse — out of corpus
]


def main() -> None:
    rag = DeepRecall(domain_entities=None)
    n = rag.ingest_dir(DOCS)
    print(f"Ingested {n} chunks from {DOCS}")
    print(f"Backends: {rag.stats()['backends']}\n")

    for q in QUERIES:
        print("=" * 72)
        print(f"Q: {q}\n")
        result = rag.retrieve(q)
        print(f"[plan] intent={result.plan.intent.value} entities={result.plan.entities}")
        for sc in result.scored[:3]:
            print(f"   - {sc.chunk.chunk_type.value:12} {sc.score:.3f} "
                  f"{sc.chunk.section_path}  {dict((k, round(v,2)) for k,v in sc.sources.items())}")
        print()
        answer = rag.query(q)
        print(answer.render())
        print()


if __name__ == "__main__":
    main()
