from typing import Any
from core.brand.rules import load_brand_rules, BrandRules
from .hard_constraints import _flatten_text
from .models import QACheck, QAState


def validate_brand(content: Any, *, brand_rules: BrandRules | None = None) -> QACheck:
    rules = brand_rules or load_brand_rules()
    result = rules.validate_text(_flatten_text(content))
    issues = result["forbidden_jargon"] + [f"{x['from']} required instead of {x['from']}" for x in result["terminology_issues"]]
    state = QAState.REWRITE if issues else QAState.PASS
    return QACheck(
        name="brand_rules",
        state=state,
        message="Brand rules passed." if not issues else "Brand rule violations detected.",
        details={
            "forbidden_jargon": result["forbidden_jargon"],
            "terminology_issues": result["terminology_issues"],
            "mandatory_terminology": list(rules.mandatory_terminology.keys()),
        },
    )
