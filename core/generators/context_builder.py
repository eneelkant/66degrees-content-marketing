from typing import Any, Dict
from core.brand.rules import load_brand_rules
from core.generators.base import GenerationContext
from core.reference_library.hybrid_retriever import HybridRetriever
from core.reference_library.sqlite_client import SQLiteReferenceClient
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "references" / "references.db"


def build_generation_context(
    brief_data: Dict[str, Any],
    *,
    brand_engine=None,
    hybrid_retriever=None,
) -> GenerationContext:
    """Build a client/LLM-neutral context bundle from brand rules and references."""
    brand_engine = brand_engine or load_brand_rules()
    if hybrid_retriever is None:
        sqlite = SQLiteReferenceClient(DB_PATH)
        hybrid_retriever = HybridRetriever(sqlite)

    value_prop = brief_data.get("value_prop", {}) or {}
    metadata = brief_data.get("metadata", {}) or {}
    audience = brief_data.get("audience", {}) or {}
    query_text = value_prop.get("primary_hook") or metadata.get("title") or "66degrees enterprise AI"
    industries = audience.get("industry_verticals") or []
    industry = industries[0] if industries else None

    retrieval = hybrid_retriever.retrieve(query_text, industry=industry, top_k=3)
    if isinstance(retrieval, dict):
        internal = retrieval.get("internal_winners", [])
        competitor = retrieval.get("competitor_xml_block", "")
    else:
        internal = []
        for item in retrieval:
            record = getattr(item, "record", item)
            if getattr(record, "source_type", "internal") == "internal":
                data = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
                data["hybrid_score"] = getattr(item, "score", data.get("performance_score", 0.0))
                internal.append(data)
        competitor_records = [item for item in retrieval if getattr(getattr(item, "record", item), "source_type", "internal") == "competitor"]
        competitor = hybrid_retriever.competitor_context(competitor_records)

    return GenerationContext(
        brand_rules=brand_engine.data,
        internal_winning_references=internal[:3],
        competitor_xml_references=competitor,
    )
