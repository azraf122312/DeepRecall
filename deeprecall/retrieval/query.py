"""Step 1: Query understanding.

Classifies query intent and pulls out entities so the engine can apply the
right structural boosts and seed the graph traversal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..ingestion.enrichment import Enricher
from ..models import Intent


@dataclass
class QueryPlan:
    raw: str
    intent: Intent
    entities: list[str] = field(default_factory=list)


_Q_INTENT = [
    (Intent.HOWTO, re.compile(r"\b(how (do|to)|configure|set up|install|enable|deploy)\b", re.I)),
    (Intent.TROUBLESHOOTING, re.compile(r"\b(error|fail|not working|fix|debug|why is|troubleshoot)\b", re.I)),
    (Intent.DECISION, re.compile(r"\b(should i|which|vs\.?|versus|better|compare|trade-?off)\b", re.I)),
    (Intent.CONCEPTUAL, re.compile(r"\b(what is|what are|explain|define|meaning of)\b", re.I)),
]


class QueryUnderstanding:
    def __init__(self, enricher: Enricher | None = None):
        self.enricher = enricher or Enricher()

    def plan(self, query: str) -> QueryPlan:
        intent = Intent.UNKNOWN
        for cand, pat in _Q_INTENT:
            if pat.search(query):
                intent = cand
                break
        return QueryPlan(raw=query, intent=intent,
                         entities=self.enricher.extract_entities(query))
