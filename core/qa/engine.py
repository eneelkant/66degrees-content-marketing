from typing import Any
from core.brand.rules import load_brand_rules
from core.reference_library.hybrid_retriever import HybridRetriever
from core.reference_library.sqlite_client import SQLiteReferenceClient
from pathlib import Path
from .brand import validate_brand
from .emailens import EmailensAuditEngine
from .hard_constraints import validate_hard_constraints, _flatten_text
from .models import QAReport, QAState
from .originality import OriginalityAnalyzer

DB_PATH = Path(__file__).resolve().parents[2] / "references" / "references.db"


def _status(checks):
    states = [c.state for c in checks]
    if QAState.REWRITE in states:
        return QAState.REWRITE
    if QAState.WARNING in states:
        return QAState.WARNING
    return QAState.PASS


def qa_validate_asset(content_json: dict[str, Any], asset_type: str, *, references=None, semantic_search=None, emailens_engine=None) -> QAReport:
    checks = [validate_hard_constraints(content_json, asset_type), validate_brand(content_json, brand_rules=load_brand_rules())]
    if references is None:
        sqlite = SQLiteReferenceClient(DB_PATH)
        refs = [r.model_dump(mode="json") for r in sqlite.search(limit=20)]
    else:
        refs = references
    checks.append(OriginalityAnalyzer(semantic_search=semantic_search).analyze(content_json, refs))

    if asset_type == "email":
        emailens = emailens_engine or EmailensAuditEngine()
        checks.append(emailens.audit(_flatten_text(content_json)))

    status = _status(checks)
    return QAReport(asset_type=asset_type, overall_status=status, checks=checks, approval_required=True, approval_status="LOCKED")
