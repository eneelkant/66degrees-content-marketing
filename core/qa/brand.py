from typing import Any
from core.brand.rules import load_brand_rules, BrandRules
from .hard_constraints import _flatten_text
from .models import QACheck, QAState


def validate_brand(content: Any, *, brand_rules: BrandRules | None = None) -> QACheck:
    rules = brand_rules or load_brand_rules()
    result = rules.validate_text(_flatten_text(content))
    issues: list[str] = list(result["forbidden_jargon"])
    issues.extend(
        f"{item['from']} → use {item['to']}" for item in result["terminology_issues"]
    )
    issues.extend(f"placeholder:{p}" for p in result.get("placeholders", []))
    issues.extend(f"unsupported_claim:{c}" for c in result.get("unsupported_claims", []))
    state = QAState.REWRITE if issues else QAState.PASS
    return QACheck(
        name="brand_rules",
        state=state,
        message="Brand rules passed." if not issues else "Brand rule violations detected.",
        details={
            "forbidden_jargon": result["forbidden_jargon"],
            "terminology_issues": result["terminology_issues"],
            "placeholders": result.get("placeholders", []),
            "unsupported_claims": result.get("unsupported_claims", []),
            "mandatory_terminology": list(rules.mandatory_terminology.keys()),
            "issues": issues,
        },
    )
