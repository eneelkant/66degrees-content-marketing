from pathlib import Path
from typing import Any, Dict
from core.reference_library.sqlite_client import SQLiteReferenceClient
from core.reference_library.sync import ReferenceSync
from core.reference_library.source_fetcher import ApprovedSourceFetcher
from core.generators.context_builder import build_generation_context
from core.generators.factory import content_factory
from core.quality.pipeline import validate_content_quality

DB_PATH = Path(__file__).resolve().parents[2] / "references" / "references.db"
_db = SQLiteReferenceClient(DB_PATH)
_sync = ReferenceSync(_db)


def refresh_reference_library(force: bool = False):
    if not force and not _sync.is_stale():
        return {
            "status": "CURRENT",
            "record_count": _db.count(),
            "last_refresh": _sync.last_refresh.isoformat()
            if _sync.last_refresh else None,
        }

    records = ApprovedSourceFetcher().fetch_all()
    return _sync.sync(records)


def reference_status():
    return {"database": str(DB_PATH), "record_count": _db.count(), "last_refresh": _sync.last_refresh.isoformat() if _sync.last_refresh else None, "refresh_interval_days": 2}


def generate_content_asset(asset_type: str, brief_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from core.writing.compliance import evaluate_compliance

        context = build_generation_context(
            brief_data, content_type=asset_type, writing_mode="generate"
        )
        strategy = content_factory.get_strategy(asset_type)
        generated = strategy.generate(brief_data, context=context)
        asset = generated.model_dump(mode="json")
        asset["metadata"]["status"] = "DRAFT"
        metadata = asset.get("metadata") or {}
        quality = validate_content_quality(
            {
                "title": asset.get("title") or "",
                "meta_description": metadata.get("meta_description") or "",
                "body": asset.get("content_markdown") or "",
                "content_markdown": asset.get("content_markdown") or "",
                "cta": metadata.get("cta") or "",
                "word_count_form": metadata.get("word_count_form") or "short_form",
            },
            content_type=asset_type,
            context=context.content_context,
        )
        compliance = evaluate_compliance(
            {
                "title": asset.get("title") or "",
                "content_markdown": asset.get("content_markdown") or "",
                "cta": metadata.get("cta") or "",
            },
            asset_type,
            brief_data=brief_data,
            mode="qa",
            skills=list(context.applicable_skills) or None,
        )
        writing_compliance = compliance.to_public_dict()
        asset["metadata"]["quality"] = quality
        asset["metadata"]["writing_compliance"] = writing_compliance
        asset["metadata"]["guideline_version"] = context.guideline_version
        asset["metadata"]["applicable_skills"] = list(context.applicable_skills)
        return {
            "qa_status": "GENERATED_DRAFT",
            "context_injected": True,
            "references_retrieved": len(context.internal_winning_references),
            "source_context": context.content_context,
            "quality": quality,
            "writing_compliance": writing_compliance,
            "guideline_version": context.guideline_version,
            "applicable_skills": list(context.applicable_skills),
            "asset": asset,
        }
    except ValueError as err:
        return {"qa_status": "FAILED", "error": str(err)}

from core.generators.campaign_kit import campaign_kit_orchestrator

def generate_campaign_kit(brief_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the deterministic four-channel Master Campaign Kit."""
    try:
        return {"qa_status":"DRAFT_PENDING_QA", "campaign_kit": campaign_kit_orchestrator.create_kit(brief_data)}
    except (ValueError, TypeError) as err:
        return {"qa_status":"FAILED", "error":str(err)}

from core.qa.engine import qa_validate_asset as _qa_validate_asset
from core.approval.gate import HumanApprovalGate
import json
from pathlib import Path as _Path
from core.optimization.optimizer import optimize_content_asset as _optimize_content_asset
from core.optimization.repurposer import repurpose_content_asset as _repurpose_content_asset
from exporters.campaign import export_approved_campaign

_approval_gate = HumanApprovalGate()


def qa_validate_asset(
    content_json: Dict[str, Any],
    asset_type: str,
    brief_data: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report = _qa_validate_asset(content_json, asset_type, brief_data=brief_data)
    return report.model_dump(mode="json")


def approve_campaign_kit(kit_id: str, approved_by: str, notes: str | None = None) -> Dict[str, Any]:
    return _approval_gate.approve(kit_id, approved_by, notes).model_dump(mode="json")


def optimize_content_asset(asset_json: Dict[str, Any], qa_feedback: Any, provider: str | None = None) -> Dict[str, Any]:
    asset_type = (asset_json or {}).get("asset_type")
    context = build_generation_context(
        asset_json, content_type=asset_type, writing_mode="optimize"
    )
    result = _optimize_content_asset(
        asset_json,
        qa_feedback,
        context=context,
        provider=provider,
    )
    asset = result.get("asset") or {}
    metadata = asset.setdefault("metadata", {})
    metadata["guideline_version"] = context.guideline_version
    metadata["applicable_skills"] = list(context.applicable_skills)
    result["guideline_version"] = context.guideline_version
    result["applicable_skills"] = list(context.applicable_skills)
    return result


def repurpose_content_asset(source_asset_json: Dict[str, Any], target_formats: str | list[str], provider: str | None = None) -> Dict[str, Any]:
    targets = [target_formats] if isinstance(target_formats, str) else target_formats
    if not targets:
        raise ValueError("target_formats is required")
    context = build_generation_context(
        source_asset_json, writing_mode="repurpose"
    )
    return {"status": "REPURPOSED", "assets": [
        _repurpose_content_asset(source_asset_json, target, context=context, provider=provider)["asset"]
        for target in targets
    ]}


def export_campaign_kit(kit_id: str, kit: Dict[str, Any], export_format: str = "json") -> Dict[str, Any]:
    output_dir = _Path(__file__).resolve().parents[1] / "exports"
    return export_approved_campaign(kit_id, kit, export_format, _approval_gate, output_dir)
