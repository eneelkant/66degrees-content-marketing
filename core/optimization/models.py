from typing import Any
from pydantic import BaseModel, Field


class OptimizedAsset(BaseModel):
    title: str
    content_markdown: str
    changes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def mock_default(cls):
        return cls(
            title="Optimized 66degrees Content",
            content_markdown="# Optimized 66degrees Content\n\nBuild practical AI capabilities with measurable business impact.",
            changes=["Applied targeted QA feedback constraints."],
            metadata={"mock": True},
        )


class RepurposedAsset(BaseModel):
    source_asset_type: str
    target_asset_type: str
    title: str
    content_markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def mock_default(cls):
        return cls(
            source_asset_type="source",
            target_asset_type="target",
            title="Repurposed 66degrees Content",
            content_markdown="# Repurposed 66degrees Content\n\nTurning source insights into a channel-ready asset.",
            metadata={"mock": True},
        )
