"""Step 2: Semantic enrichment.

Adds meaning on top of structure:
  - Named entity recognition (domain-tunable)
  - Lightweight coreference hint ("the system" -> last named entity)
  - Intent classification per node (how-to / reference / troubleshooting / ...)

Production DeepRecall would use a domain-trained NER model + a coref model
(e.g. spaCy + fastcoref) and a fine-tuned intent classifier. This module
provides a rule-based implementation that is good enough to drive retrieval
boosts and is trivially replaceable.
"""

from __future__ import annotations

import re

from ..models import DocNode, Intent, NodeType

# Seed gazetteer — extend per domain, or swap for a trained NER model.
_DEFAULT_ENTITIES = [
    "Kubernetes", "HPA", "Horizontal Pod Autoscaler", "API Gateway",
    "metrics-server", "Load Balancer", "Ingress", "Pod", "Deployment",
    "ChromaDB", "Pinecone", "Elasticsearch", "Neo4j", "ColBERT", "BM25",
]

_INTENT_PATTERNS = [
    (Intent.TROUBLESHOOTING, re.compile(r"\b(error|fail|troubleshoot|debug|fix|broken|not working|issue)\b", re.I)),
    (Intent.WARNING, re.compile(r"\b(warning|caution|danger|never|do not|avoid|must not)\b", re.I)),
    (Intent.HOWTO, re.compile(r"\b(how to|step \d|configure|install|set up|enable|deploy|run)\b", re.I)),
    (Intent.DECISION, re.compile(r"\b(vs\.?|versus|compared to|trade-?off|choose between|pros and cons)\b", re.I)),
    (Intent.CONCEPTUAL, re.compile(r"\b(is a|refers to|means|defined as|concept|overview)\b", re.I)),
]


class Enricher:
    def __init__(self, entities: list[str] | None = None):
        terms = entities or _DEFAULT_ENTITIES
        # longest-first so "Horizontal Pod Autoscaler" wins over "Pod"
        self._patterns = [
            (t, re.compile(rf"\b{re.escape(t)}\b", re.I))
            for t in sorted(terms, key=len, reverse=True)
        ]

    def extract_entities(self, text: str) -> list[str]:
        found: list[str] = []
        for canonical, pat in self._patterns:
            if pat.search(text) and canonical not in found:
                found.append(canonical)
        return found

    def classify_intent(self, text: str, node_type: NodeType) -> Intent:
        if node_type == NodeType.CODE:
            return Intent.HOWTO
        if node_type == NodeType.TABLE:
            return Intent.DECISION
        for intent, pat in _INTENT_PATTERNS:
            if pat.search(text):
                return intent
        return Intent.REFERENCE

    def enrich(self, nodes: list[DocNode]) -> dict[str, dict]:
        """Return {node_id: {"entities": [...], "intent": Intent}}."""
        result: dict[str, dict] = {}
        last_entity: str | None = None
        for n in nodes:
            ents = self.extract_entities(f"{n.title}\n{n.text}")
            # crude coreference: if the text leans on "the system/it" and we
            # have a recent entity, attach it so retrieval can still match.
            if not ents and last_entity and re.search(r"\b(the system|it|this)\b", n.text, re.I):
                ents = [last_entity]
            if ents:
                last_entity = ents[0]
            result[n.id] = {
                "entities": ents,
                "intent": self.classify_intent(f"{n.title}\n{n.text}", n.node_type),
            }
        return result
