"""DeepRecall end-to-end pipeline.

    pipeline = DeepRecall()
    pipeline.ingest_file("docs/kubernetes-guide.md")
    answer = pipeline.query("How do I configure auto-scaling for the API gateway?")
    print(answer.render())
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .generation.generator import Generator
from .indexing.store import IndexStore
from .ingestion.chunker import Chunker
from .ingestion.enrichment import Enricher
from .ingestion.parser import parse_file, parse_markdown
from .models import Answer, Chunk
from .retrieval.engine import HybridRetriever, RetrievalResult


class DeepRecall:
    def __init__(self, config: Config | None = None, domain_entities: list[str] | None = None):
        self.config = config or Config()
        self.store = IndexStore(self.config)
        self.enricher = Enricher(domain_entities)
        self.chunker = Chunker()
        self.retriever = HybridRetriever(self.store, self.config)
        self.generator = Generator(self.config)

    # ---- ingestion -----------------------------------------------------
    def ingest_text(self, text: str, source: str = "inline") -> list[Chunk]:
        nodes = parse_markdown(text, source=source)
        enrichment = self.enricher.enrich(nodes)
        chunks = self.chunker.chunk(nodes, enrichment, source=source)
        self.store.add(chunks)
        return chunks

    def ingest_file(self, path: str | Path) -> list[Chunk]:
        nodes = parse_file(path)
        enrichment = self.enricher.enrich(nodes)
        chunks = self.chunker.chunk(nodes, enrichment, source=Path(path).name)
        self.store.add(chunks)
        return chunks

    def ingest_dir(self, directory: str | Path, pattern: str = "*.md") -> int:
        n = 0
        for p in sorted(Path(directory).glob(pattern)):
            n += len(self.ingest_file(p))
        return n

    # ---- retrieval / generation ---------------------------------------
    def retrieve(self, query: str) -> RetrievalResult:
        return self.retriever.retrieve(query)

    def query(self, query: str) -> Answer:
        result = self.retriever.retrieve(query)
        return self.generator.generate(query, result)

    # ---- introspection -------------------------------------------------
    def stats(self) -> dict:
        return {"chunks": self.store.size, "backends": self.store.backends}
