from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EventSource(BaseModel):
    type: Literal["google_cloud", "66degrees"]
    url: str | None = None


class EventMetadata(BaseModel):
    title: str
    date: str | None = None
    event_format: str | None = None
    location: str | None = None


class EventAudience(BaseModel):
    primary_persona: str | None = None
    industry_verticals: list[str] = Field(default_factory=list)


class EventValueProp(BaseModel):
    primary_hook: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)


class EventBrief(BaseModel):
    metadata: EventMetadata
    audience: EventAudience
    value_prop: EventValueProp
    cta_primary: str = "Register"
    agenda: list[Any] = Field(default_factory=list)
    speakers: list[Any] = Field(default_factory=list)
    source: EventSource | None = None


class EventBriefResult(BaseModel):
    status: Literal["READY_FOR_GENERATION", "NEEDS_CLARIFICATION"]
    missing_fields: list[str] = Field(default_factory=list)
    brief: dict[str, Any]
    questions: list[str] = Field(default_factory=list)
