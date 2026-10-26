"""66degrees writing guidelines: load, select, prompt, and compliance."""

from .compliance import evaluate_compliance, preserve_facts_on_rewrite
from .loader import (
    get_guideline_version,
    knowledge_root,
    load_guideline_text,
    load_guidelines,
)
from .models import ComplianceFinding, ComplianceResult
from .prompt import build_writing_prompt
from .skills import SKILL_IDS, select_skills

# Back-compat alias: call sites may treat this as the current version string.
GUIDELINE_VERSION = get_guideline_version

__all__ = [
    "GUIDELINE_VERSION",
    "SKILL_IDS",
    "ComplianceFinding",
    "ComplianceResult",
    "build_writing_prompt",
    "evaluate_compliance",
    "get_guideline_version",
    "knowledge_root",
    "load_guideline_text",
    "load_guidelines",
    "preserve_facts_on_rewrite",
    "select_skills",
]
