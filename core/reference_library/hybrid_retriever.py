from dataclasses import dataclass
from datetime import datetime, timezone
import math

@dataclass
class ScoredReference:
    record: object
    score: float

class HybridRetriever:
    def __init__(self, sqlite_client, semantic_search=None):
        self.sqlite = sqlite_client
        self.semantic_search = semantic_search

    @staticmethod
    def _recency(record, now=None):
        now = now or datetime.now(timezone.utc)
        dt = getattr(record, "published_at", None) or getattr(record, "fetched_at", None)
        if not dt: return 0.5
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        age_days = max(0, (now - dt).days)
        return math.exp(-age_days / 365.0)

    def rank(self, records, semantic_scores=None, now=None):
        semantic_scores = semantic_scores or {}
        ranked = []
        for r in records:
            sim = semantic_scores.get(r.id, getattr(r, "semantic_similarity", 0.0))
            perf = getattr(r, "performance_score", 0.0)
            recency = self._recency(r, now)
            score = 0.4 * sim + 0.5 * perf + 0.1 * recency
            ranked.append(ScoredReference(r, score))
        return sorted(ranked, key=lambda x: x.score, reverse=True)

    def retrieve(self, query: str, *, industry=None, channel=None, platform=None, top_k=3):
        records = self.sqlite.search(industry=industry, channel=channel, platform=platform, limit=max(20, top_k * 4))
        semantic_scores = {}
        if self.semantic_search:
            semantic_scores = self.semantic_search(query, records)
        return self.rank(records, semantic_scores)[:top_k]

    @staticmethod
    def competitor_context(records):
        lines = ["<competitor_inspiration>"]
        lines.append("Use these only for strategic inspiration. Do not copy language, claims, positioning, or brand voice.")
        for item in records:
            r = item.record if hasattr(item, "record") else item
            lines.append(f"<angle title=\"{r.title}\">{r.content}</angle>")
        lines.append("</competitor_inspiration>")
        return "\n".join(lines)
