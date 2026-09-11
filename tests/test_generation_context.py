from datetime import datetime, timezone
from pathlib import Path

from core.brand.rules import load_brand_rules
from core.generators.base import GenerationContext, GeneratedAssetOutput
from core.generators.context_builder import build_generation_context
from core.generators.factory import content_factory
from core.reference_library.models import ReferenceRecord
from core.reference_library.sqlite_client import SQLiteReferenceClient


class FakeRetriever:
    def __init__(self, records):
        self.records = records

    def retrieve(self, query, *, industry=None, channel=None, top_k=3):
        return self.records[:top_k]

    @staticmethod
    def competitor_context(records):
        return "<competitor_inspiration></competitor_inspiration>"


def brief():
    return {
        "metadata": {"title": "Agentic AI for Healthcare", "event_format": "webinar"},
        "audience": {"primary_persona": "CIO", "industry_verticals": ["Healthcare"]},
        "value_prop": {"primary_hook": "Move AI into measurable healthcare workflows", "key_takeaways": ["Secure architecture"]},
        "cta_primary": "Register",
    }


def test_all_eight_strategies_resolve_and_return_schema():
    for asset_type in content_factory.supported_types():
        strategy = content_factory.get_strategy(asset_type)
        result = strategy.generate(brief(), GenerationContext())
        assert isinstance(result, GeneratedAssetOutput)
        assert result.asset_type == asset_type
        assert result.word_count > 0


def test_context_builder_injects_brand_and_references(tmp_path):
    db = SQLiteReferenceClient(Path(tmp_path) / "references.db")
    record = ReferenceRecord(
        id="winner-1", title="Healthcare AI winner", content="Secure AI workflows",
        source="66degrees", source_type="internal", industry="Healthcare",
        performance_score=0.9, fetched_at=datetime.now(timezone.utc),
        metadata={"campaign_angle": "Secure AI workflows"},
    )
    db.upsert(record)
    retriever = FakeRetriever([])
    # Use the actual DB-backed record as the fake retrieval result.
    class DBRetriever(FakeRetriever):
        def retrieve(self, query, *, industry=None, channel=None, top_k=3):
            from types import SimpleNamespace
            return [SimpleNamespace(record=r, score=0.95) for r in db.search(industry=industry, limit=3)]
    context = build_generation_context(brief(), brand_engine=load_brand_rules(), hybrid_retriever=DBRetriever([]))
    assert context.internal_winning_references
    assert context.internal_winning_references[0]["id"] == "winner-1"
    assert context.brand_rules
