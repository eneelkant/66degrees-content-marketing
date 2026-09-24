"""Brand rules loader and deterministic text validation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).with_name("brand_rules.json")

_PLACEHOLDER_RE = re.compile(
    r"(?i)\b(tbd|todo|lorem ipsum|xxxx|\[insert[^\]]*\]|\{[^}]+\})\b"
)
_UNSUPPORTED_CLAIM_RE = re.compile(
    r"(?i)\b("
    r"guaranteed\s+roi|100%\s+success|never\s+fails|"
    r"#1\s+in\s+the\s+world|fastest\s+growing\s+partner"
    r")\b"
)


class BrandRules:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.mandatory_terminology = data.get("mandatory_terminology", {})
        self.forbidden_jargon = [x.lower() for x in data.get("forbidden_jargon", [])]
        self.voice = data.get("voice", [])
        self.personality = data.get("personality", [])
        self.strategic_pillars = data.get("strategic_pillars", [])
        self.company_names = [x.lower() for x in data.get("company_names", ["66degrees"])]
        self.prohibited_placeholders = data.get(
            "prohibited_placeholders",
            ["tbd", "todo", "lorem ipsum", "[insert"],
        )

    def validate_text(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        forbidden = [term for term in self.forbidden_jargon if term in lowered]
        replacements = []
        for approved, disallowed in self.mandatory_terminology.items():
            for bad in disallowed:
                if bad.lower() in lowered:
                    replacements.append({"from": bad, "to": approved})

        placeholders = sorted(set(_PLACEHOLDER_RE.findall(text)))
        unsupported_claims = sorted({m.group(0) for m in _UNSUPPORTED_CLAIM_RE.finditer(text)})

        return {
            "valid": not forbidden and not replacements and not placeholders and not unsupported_claims,
            "forbidden_jargon": forbidden,
            "terminology_issues": replacements,
            "placeholders": placeholders,
            "unsupported_claims": unsupported_claims,
            "company_names_expected": self.company_names,
        }


def load_brand_rules(path: str | Path = DEFAULT_PATH) -> BrandRules:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Brand rules must be a JSON object")
    return BrandRules(data)
