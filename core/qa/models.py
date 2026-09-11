from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class QAState(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    REWRITE = "REWRITE"


class QACheck(BaseModel):
    name: str
    state: QAState
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class QAReport(BaseModel):
    asset_type: str
    overall_status: QAState
    checks: list[QACheck] = Field(default_factory=list)
    approval_required: bool = True
    approval_status: str = "LOCKED"

    @property
    def rewrite_required(self) -> bool:
        return self.overall_status == QAState.REWRITE


class ApprovalRecord(BaseModel):
    asset_or_kit_id: str
    approved: bool = False
    approved_by: str | None = None
    approved_at: str | None = None
    notes: str | None = None
