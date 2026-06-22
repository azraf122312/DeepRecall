"""Smoke + behavior tests for DeepRecall. Run: python -m pytest -q"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deeprecall import DeepRecall, ChunkType, Intent
from deeprecall.ingestion.parser import parse_markdown
from deeprecall.ingestion.chunker import Chunker
from deeprecall.ingestion.enrichment import Enricher
from deeprecall.retrieval.fusion import reciprocal_rank_fusion
from deeprecall.models import Chunk

DOCS = Path(__file__).resolve().parents[1] / "examples" / "sample_docs"


def _rag():
    rag = DeepRecall()
    rag.ingest_dir(DOCS)
    return rag


def test_parser_builds_tree():
    nodes = parse_markdown("# Title\n\n## Sec\n\nbody text here that is long enough.\n", "t.md")
    assert any(n.node_type.value == "section" for n in nodes)
    assert any("body text" in n.text for n in nodes)


def test_chunker_detects_types():
    text = ("## Steps\n\n1. do a\n2. do b\n3. do c\n\n"
            "## Warn\n\nWarning: never delete the prod database.\n")
    nodes = parse_markdown(text, "t.md")
    enr = Enricher().enrich(nodes)
    chunks = Chunker().chunk(nodes, enr, "t.md")
    types = {c.chunk_type for c in chunks}
    assert ChunkType.PROCEDURE in types
    assert ChunkType.WARNING in types


def test_rrf_fuses_and_ranks():
    c1, c2 = Chunk(text="a"), Chunk(text="b")
    fused = reciprocal_rank_fusion({
        "dense": [(c1, 0.9), (c2, 0.1)],
        "sparse": [(c2, 5.0), (c1, 1.0)],
    }, k=60)
    assert len(fused) == 2
    assert {sc.chunk.id for sc in fused} == {c1.id, c2.id}
    # c1 is rank1+rank2, c2 is rank2+rank1 -> equal here; just check structure
    assert all(set(sc.sources) == {"dense", "sparse"} for sc in fused)


def test_howto_query_prefers_procedure():
    rag = _rag()
    result = rag.retrieve("How do I configure auto-scaling for the API gateway?")
    assert result.plan.intent == Intent.HOWTO
    top_types = [sc.chunk.chunk_type for sc in result.scored[:3]]
    assert ChunkType.PROCEDURE in top_types or ChunkType.CODE_EXAMPLE in top_types


def test_out_of_corpus_refuses():
    rag = _rag()
    ans = rag.query("How do I bake a sourdough loaf?")
    assert ans.refused is True


def test_grounded_answer_has_sources():
    rag = _rag()
    ans = rag.query("What happens if I forget the metrics-server?")
    assert not ans.refused
    assert ans.sources
