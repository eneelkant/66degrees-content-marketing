from typing import Any, Dict
from pydantic import BaseModel, Field, field_validator
from core.reference_library.hybrid_retriever import HybridRetriever
from core.reference_library.sqlite_client import SQLiteReferenceClient
from pathlib import Path

class LinkedInSponsoredContent(BaseModel):
    primary_text: str = Field(min_length=1)
    headline: str = Field(min_length=1, max_length=200)
    cta: str
    reference_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cta")
    @classmethod
    def valid_cta(cls, value):
        allowed = {"Register", "Sign Up", "Learn More"}
        if value not in allowed: raise ValueError(f"CTA must be one of {sorted(allowed)}")
        return value

def _refs(brief_data: Dict[str, Any]):
    db = SQLiteReferenceClient(Path(__file__).resolve().parents[2] / "references" / "references.db")
    try:
        hook = brief_data.get("value_prop", {}).get("primary_hook", "")
        return HybridRetriever(db).retrieve(hook, platform="linkedin", top_k=3)
    finally: db.close()

def generate_linkedin_sponsored_content(brief_data: Dict[str, Any]) -> dict:
    title = brief_data.get("metadata", {}).get("title", "Enterprise AI Event")
    hook = brief_data.get("value_prop", {}).get("primary_hook", "Build practical AI capabilities")
    refs = _refs(brief_data)
    text = f"Walk in with a business challenge. Walk out with practical ideas for {hook.lower()}. Join 66degrees for {title}."[:600]
    return LinkedInSponsoredContent(primary_text=text, headline=title[:200], cta="Register", reference_metadata={"platform":"linkedin","references_retrieved":len(refs),"reference_ids":[r.record.id for r in refs]}).model_dump(mode="json")
