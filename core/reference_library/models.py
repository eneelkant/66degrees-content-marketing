from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class ReferenceRecord(BaseModel):
    id: str
    title: str
    content: str
    source: str
    source_type: str = "internal"
    authority_level: str = "authoritative"
    channel: str | None = None
    platform: str | None = None
    industry: str | None = None
    topic: str | None = None
    performance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    semantic_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
