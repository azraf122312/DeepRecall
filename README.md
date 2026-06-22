# DeepRecall

**A structure-aware, hybrid-retrieval RAG engine.**

> Core insight: most RAG fails because it treats documents as flat text.
> Documents have structure, hierarchy, and implicit relationships. Your RAG
> should too.

DeepRecall is a *Document Cognition Layer*: it parses documents into a
structural tree, enriches them with entities and intent, chunks them by
**semantic unit** (not token count), indexes them across four complementary
indices, and retrieves with hybrid fusion + structural boosting + reranking
before generating a **grounded, cited, confidence-scored** answer.

It runs **end-to-end with zero heavy dependencies** — pure-Python fallbacks
for embeddings, BM25, the relationship graph, reranking, and generation.
Install optional backends to upgrade any stage to production quality without
changing a line of calling code.

---

## Quick start

```bash
cd DeepRecall
python examples/demo.py          # full pipeline on the sample corpus
python -m pytest -q              # tests
```

> On Windows, invoke Python via the `py` launcher and force UTF-8 output:
> `set PYTHONUTF8=1 && py examples/demo.py`. If a broken global pytest plugin
> breaks collection, run `set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 && py -m pytest -q`.

```python
from deeprecall import DeepRecall

rag = DeepRecall()
rag.ingest_dir("examples/sample_docs")

answer = rag.query("How do I configure auto-scaling for the API gateway during high traffic?")
print(answer.render())
```

---

## Architecture

### 1. Ingestion pipeline — `deeprecall/ingestion/`
| Step | Module | What it does |
|------|--------|--------------|
| Structural parsing | `parser.py` | Markdown/HTML → ordered tree of `DocNode` (Title → Section → Subsection → Paragraph → List → Table → Code), preserving parent-child + reading order. *PDF/Word extension point for LayoutLMv3.* |
| Semantic enrichment | `enrichment.py` | NER (gazetteer/model), crude coreference, per-node **intent** classification. |
| Multi-granular chunking | `chunker.py` | Chunks by **semantic unit**: definition / procedure / comparison / code+explanation / FAQ / warning. Each chunk carries type, section path, related IDs, entities. |

### 2. Multi-vector index — `deeprecall/indexing/`
| Index | Module | Production backend |
|-------|--------|--------------------|
| Dense (meaning) | `dense.py` | sentence-transformers → ChromaDB / Pinecone *(fallback: hashing embedder)* |
| Sparse (keywords) | `sparse.py` | BM25 / Elasticsearch *(pure-Python Okapi BM25 built in)* |
| Graph (relationships) | `graph.py` | Neo4j typed edges *(fallback: in-memory entity co-occurrence + 1-hop traversal)* |
| Structural (hierarchy) | `structural.py` | custom — parents, siblings, section summaries |

### 3. Hybrid retrieval engine — `deeprecall/retrieval/`
1. **Query understanding** (`query.py`) — intent + entities
2. **Multi-index retrieval** (`store.py`) — dense + sparse + graph
3. **Reciprocal Rank Fusion** (`fusion.py`) — `Σ 1/(k+rank)`, k=60
4. **Structural boost** (`engine.py`) — e.g. procedures +0.10 for *how-to*, warnings +0.20 for *troubleshooting*
5. **Cross-encoder rerank** (`rerank.py`) — MiniLM cross-encoder *(fallback: lexical overlap)*
6. **Context assembly** (`assembly.py`) — chunk + section summary + related, dedup, ordered, cited

### 4. Generation with verification — `deeprecall/generation/`
- Source grounding — every claim cites a source ref `[n]`
- Uncertainty quantification — confidence from retrieval signal
- **"I don't know" detection** — no relevant chunks → refuse
- LLM via the Anthropic API (`claude-opus-4-8` / `claude-sonnet-4-6`) *(fallback: extractive grounded answer)*

---

## Upgrading stages

Everything is feature-detected. To go production:

```bash
pip install sentence-transformers   # real dense embeddings + reranker
pip install anthropic               # LLM generation
export ANTHROPIC_API_KEY=sk-ant-... # then generation auto-upgrades
```

Then swap the in-memory stores for ChromaDB / Elasticsearch / Neo4j by
editing only the `add()`/`search()` bodies in `indexing/*.py` — the
interfaces and the rest of the pipeline stay identical.

---

## Layout

```
deeprecall/
  models.py            # Chunk, DocNode, ScoredChunk, Answer, enums
  config.py            # tunable knobs (RRF k, boosts, model id, ...)
  ingestion/           # parse → enrich → chunk
  indexing/            # dense + sparse + graph + structural + store
  retrieval/           # query → fusion → rerank → assembly → engine
  generation/          # grounded, cited, verified generation
  pipeline.py          # DeepRecall facade
examples/
  sample_docs/         # demo corpus
  demo.py              # runnable end-to-end demo
tests/                 # pytest smoke + behavior tests
```

MIT licensed. Built as a clean, extensible reference implementation.
