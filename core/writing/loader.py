"""Load curated writing guidelines from content_knowledge/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_ROOT = _REPO_ROOT / "content_knowledge"
_GUIDELINES_DIR = _KNOWLEDGE_ROOT / "writing_guidelines"
_VERSION_FILE = _KNOWLEDGE_ROOT / "VERSION"

# Document id → filename under writing_guidelines/
GUIDELINE_FILES: dict[str, str] = {
    "company_facts": "company_facts.md",
    "messaging": "messaging_and_terminology.md",
    "brand_voice": "brand_voice.md",
    "audience": "audience_and_positioning.md",
    "grammar": "grammar_and_style.md",
    "structure": "content_structure.md",
    "social_email": "social_and_email.md",
    "specs": "specs_and_guardrails.md",
    "prohibited": "prohibited_claims.md",
    "proof": "proof_and_evidence.md",
    "reader_journey": "reader_journey.md",
    "ceo_voice": "ceo_voice.md",
    "craft": "craft_mechanisms.md",
    "checklist": "content_quality_checklist.md",
}

FALLBACK_VERSION = "unavailable"


def knowledge_root() -> Path:
    return _KNOWLEDGE_ROOT


def guidelines_dir() -> Path:
    return _GUIDELINES_DIR


@lru_cache(maxsize=1)
def get_guideline_version() -> str:
    if not _VERSION_FILE.is_file():
        return FALLBACK_VERSION
    text = _VERSION_FILE.read_text(encoding="utf-8").strip()
    return text or FALLBACK_VERSION


def load_guideline_text(doc_id: str) -> str:
    """Load one guideline document by id. Raises FileNotFoundError if missing."""
    filename = GUIDELINE_FILES.get(doc_id)
    if not filename:
        raise KeyError(f"Unknown guideline document id: {doc_id}")
    path = _GUIDELINES_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Writing guideline missing: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_guidelines() -> dict[str, str]:
    """Load all guideline documents. Empty dict if knowledge root is missing."""
    if not _GUIDELINES_DIR.is_dir():
        return {}
    loaded: dict[str, str] = {}
    for doc_id, filename in GUIDELINE_FILES.items():
        path = _GUIDELINES_DIR / filename
        if path.is_file():
            loaded[doc_id] = path.read_text(encoding="utf-8")
    return loaded


def clear_guideline_cache() -> None:
    load_guidelines.cache_clear()
    get_guideline_version.cache_clear()


def expected_source_archive_files() -> tuple[str, ...]:
    """Archive filenames accounted for in source_manifest (for tests)."""
    return (
        "00_README.md",
        "01_COMPANY_FACTS.md",
        "02_MESSAGING_V17.md",
        "03_WRITING_RULES.md",
        "04_FORMAT_RULES.md",
        "05_READER_JOURNEY.md",
        "06_PROOF_INDEX.md",
        "07_CEO_VOICE_BEN_KESSLER.md",
        "08_CRAFT_CIALDINI.md",
        "08_CRAFT_EMAIL_MECHANISMS.md",
        "08_CRAFT_HALBERT_BORON.md",
        "08_CRAFT_PERSUASIVE_COPYWRITING.md",
        "08_CRAFT_SUGARMAN.md",
        "09_SPECS_AND_GUARDRAILS.md",
    )
