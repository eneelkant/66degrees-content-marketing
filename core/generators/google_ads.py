from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator
from core.reference_library.hybrid_retriever import HybridRetriever
from core.reference_library.sqlite_client import SQLiteReferenceClient
from pathlib import Path

MAX_HEADLINE = 30
MAX_DESCRIPTION = 90
MAX_PATH = 15

class GoogleAdsRSA(BaseModel):
    headlines: list[str] = Field(min_length=15, max_length=15)
    descriptions: list[str] = Field(min_length=4, max_length=4)
    display_path_1: str = "event"
    display_path_2: str = "register"
    reference_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("headlines")
    @classmethod
    def headline_limits(cls, values):
        if any(len(v) > MAX_HEADLINE for v in values): raise ValueError("Google Ads headlines must be <= 30 characters")
        return values
    @field_validator("descriptions")
    @classmethod
    def description_limits(cls, values):
        if any(len(v) > MAX_DESCRIPTION for v in values): raise ValueError("Google Ads descriptions must be <= 90 characters")
        return values
    @field_validator("display_path_1", "display_path_2")
    @classmethod
    def path_limits(cls, value):
        if len(value) > MAX_PATH: raise ValueError("Google Ads display paths must be <= 15 characters")
        return value

def _refs(brief_data: Dict[str, Any]):
    db = SQLiteReferenceClient(Path(__file__).resolve().parents[2] / "references" / "references.db")
    try:
        hook = brief_data.get("value_prop", {}).get("primary_hook", "")
        return HybridRetriever(db).retrieve(hook, platform="google", top_k=3)
    finally: db.close()

def generate_google_ads_rsa(brief_data: Dict[str, Any]) -> dict:
    title = brief_data.get("metadata", {}).get("title", "Enterprise AI Event")
    hook = brief_data.get("value_prop", {}).get("primary_hook", "Build practical AI capabilities")
    audience = brief_data.get("audience", {}).get("primary_persona", "Enterprise leaders")
    refs = _refs(brief_data)
    headlines = [title, hook, "Put AI to Work", "Build AI That Delivers", "Enterprise AI Strategy", "From AI Pilot to Scale", "Modernize with AI", "Build with Confidence", "Practical AI for Leaders", "AI That Drives Outcomes", "Transform Data Into Action", "Make AI Enterprise-Ready", "Move AI Into Production", "66degrees AI Expertise", "Reserve Your Seat"]
    headlines = [h[:MAX_HEADLINE] for h in headlines]
    descriptions = [
        f"Join {audience} peers to explore {hook.lower()}."[:MAX_DESCRIPTION],
        "Learn practical approaches to modernize, build and scale AI."[:MAX_DESCRIPTION],
        "Get actionable guidance for moving enterprise AI from pilot to impact."[:MAX_DESCRIPTION],
        "Explore proven strategies and reserve your seat."[:MAX_DESCRIPTION],
    ]
    return GoogleAdsRSA(headlines=headlines, descriptions=descriptions, reference_metadata={"platform":"google","references_retrieved":len(refs),"reference_ids":[r.record.id for r in refs]}).model_dump(mode="json")
