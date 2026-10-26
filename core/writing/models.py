"""Writing compliance result models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ComplianceStatus = Literal["pass", "needs_revision", "unavailable"]


class ComplianceFinding(BaseModel):
    severity: Literal["hard_failure", "warning"]
    rule: str
    message: str
    source: str = ""
    section: str | None = None
    suggested_fix: str = ""


class ComplianceResult(BaseModel):
    status: ComplianceStatus
    guideline_version: str
    applicable_skills: list[str] = Field(default_factory=list)
    hard_failures: list[ComplianceFinding] = Field(default_factory=list)
    warnings: list[ComplianceFinding] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    loaded: bool = True
    details: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "guideline_version": self.guideline_version,
            "applicable_skills": list(self.applicable_skills),
            "hard_failures": [f.model_dump(mode="json") for f in self.hard_failures],
            "warnings": [f.model_dump(mode="json") for f in self.warnings],
            "suggested_fixes": list(self.suggested_fixes),
            "loaded": self.loaded,
        }
