import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).with_name("brand_rules.json")

class BrandRules:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.mandatory_terminology = data.get("mandatory_terminology", {})
        self.forbidden_jargon = [x.lower() for x in data.get("forbidden_jargon", [])]
        self.voice = data.get("voice", [])
        self.personality = data.get("personality", [])
        self.strategic_pillars = data.get("strategic_pillars", [])

    def validate_text(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        forbidden = [term for term in self.forbidden_jargon if term in lowered]
        replacements = []
        for approved, disallowed in self.mandatory_terminology.items():
            for bad in disallowed:
                if bad.lower() in lowered:
                    replacements.append({"from": bad, "to": approved})
        return {
            "valid": not forbidden and not replacements,
            "forbidden_jargon": forbidden,
            "terminology_issues": replacements,
        }

def load_brand_rules(path: str | Path = DEFAULT_PATH) -> BrandRules:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Brand rules must be a JSON object")
    return BrandRules(data)
