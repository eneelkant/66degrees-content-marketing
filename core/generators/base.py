from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenerationContext(BaseModel):
    brand_rules: Dict[str, Any] = Field(default_factory=dict)
    internal_winning_references: List[Dict[str, Any]] = Field(default_factory=list)
    competitor_xml_references: str = ""


class GeneratedAssetOutput(BaseModel):
    asset_type: str
    title: str
    content_markdown: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    word_count: int = 0
    character_count: int = 0


class BaseContentStrategy(ABC):
    asset_type: str

    @abstractmethod
    def generate(
        self,
        brief_data: Dict[str, Any],
        context: Optional[GenerationContext] = None,
    ) -> GeneratedAssetOutput:
        raise NotImplementedError

    def calculate_metrics(self, text: str) -> Dict[str, int]:
        return {"word_count": len(text.split()), "character_count": len(text)}

    def _common_context(self, context: Optional[GenerationContext]) -> dict[str, Any]:
        if context is None:
            return {"brand_terms": [], "voice": [], "winning_references": []}
        rules = context.brand_rules or {}
        return {
            "brand_terms": rules.get("mandatory_terminology", []),
            "voice": rules.get("voice", []),
            "winning_references": context.internal_winning_references,
        }
