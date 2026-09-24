"""Campaign lifecycle models and status enums."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    QA_PENDING = "QA_PENDING"
    QA_PASSED = "QA_PASSED"
    QA_FAILED = "QA_FAILED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPORTED = "EXPORTED"
    ERROR = "ERROR"


class CampaignStage(str, Enum):
    STRATEGY = "strategy"
    EVENT_INTELLIGENCE = "event_intelligence"
    CONTENT = "content"
    REPURPOSING = "repurposing"
    SOCIAL = "social"
    BRAND = "brand"
    QA = "qa"
    OPTIMIZATION = "optimization"
    APPROVAL = "approval"
    EXPORT = "export"


STAGE_ORDER: tuple[CampaignStage, ...] = (
    CampaignStage.STRATEGY,
    CampaignStage.EVENT_INTELLIGENCE,
    CampaignStage.CONTENT,
    CampaignStage.REPURPOSING,
    CampaignStage.SOCIAL,
    CampaignStage.BRAND,
    CampaignStage.QA,
    CampaignStage.OPTIMIZATION,
    CampaignStage.APPROVAL,
    CampaignStage.EXPORT,
)


class StageRecord(BaseModel):
    stage: CampaignStage
    status: str = "pending"  # pending | complete | failed | skipped
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CampaignBrief(BaseModel):
    campaign_name: str
    campaign_type: str = "content"
    audience: str | dict[str, Any] = "Enterprise technology leaders"
    objective: str
    offer: str | None = None
    key_messages: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=lambda: ["email", "linkedin", "landing_page"])
    deadline: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CampaignState(BaseModel):
    campaign_id: str
    status: CampaignStatus = CampaignStatus.DRAFT
    current_stage: CampaignStage = CampaignStage.STRATEGY
    brief: dict[str, Any] = Field(default_factory=dict)
    kit_id: str | None = None
    strategy: dict[str, Any] | None = None
    event_brief: dict[str, Any] | None = None
    assets: dict[str, Any] = Field(default_factory=dict)
    social_assets: list[dict[str, Any]] = Field(default_factory=list)
    repurposed_assets: list[dict[str, Any]] = Field(default_factory=list)
    brand_results: dict[str, Any] = Field(default_factory=dict)
    qa_results: dict[str, Any] = Field(default_factory=dict)
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    approval: dict[str, Any] = Field(default_factory=dict)
    export: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def summary(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "kit_id": self.kit_id,
            "completed_stages": [
                name for name, rec in self.stages.items() if rec.status == "complete"
            ],
            "failed_stages": [
                name for name, rec in self.stages.items() if rec.status == "failed"
            ],
            "qa_status": (self.qa_results or {}).get("overall_status"),
            "approval_status": self.approval.get("status") or (
                "approved" if self.status == CampaignStatus.APPROVED else "pending"
                if self.status == CampaignStatus.APPROVAL_PENDING
                else self.status.value
            ),
            "export_status": self.export.get("status") or (
                "exported" if self.status == CampaignStatus.EXPORTED else "blocked"
            ),
            "asset_keys": list(self.assets.keys()),
            "social_count": len(self.social_assets),
        }
