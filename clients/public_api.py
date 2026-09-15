"""Stable 11-tool public API used by all client adapters."""
from __future__ import annotations

from typing import Any
import uuid

from core.mcp_legacy import tools as _tools

from clients.surface import PUBLIC_TOOL_NAMES
from core.event_brief.questions import find_missing_fields, build_questions
from core.security.input import sanitize_payload
from config.logging import configure_logging, tool_timer
logger=configure_logging("INFO")
from core.security.input import sanitize_payload
from config.logging import configure_logging, tool_timer

logger = configure_logging("INFO")


_KITS: dict[str, dict[str, Any]] = {}
_ASSETS: dict[str, dict[str, Any]] = {}


def generate_content_strategy(goals_json: dict[str, Any]) -> dict[str, Any]:
    goals = goals_json or {}
    return {
        "status": "READY",
        "strategy": {
            "objective": goals.get("objective") or goals.get("goal") or "Define measurable content marketing outcomes.",
            "audience": goals.get("audience", {}),
            "channels": goals.get("channels", ["website", "blog", "linkedin", "email"]),
            "content_pillars": ["Modernize", "Build", "Manage & Scale"],
            "measurement": goals.get("measurement", ["engagement", "qualified leads", "pipeline influence"]),
        },
    }


def process_event_brief(brief_data: dict[str, Any]) -> dict[str, Any]:
    brief = sanitize_payload(brief_data or {})
    missing = find_missing_fields(brief)
    return {
        "status": "NEEDS_CLARIFICATION" if missing else "READY_FOR_GENERATION",
        "missing_fields": missing,
        "brief": brief,
        "questions": build_questions(missing),
    }


def generate_campaign_kit(brief_data: dict[str, Any]) -> dict[str, Any]:
    done = tool_timer(logger, "generate_campaign_kit")
    result = _tools.generate_campaign_kit(sanitize_payload(brief_data))
    done(qa_status=result.get("qa_status"))
    kit = result.get("campaign_kit", {})
    kit_id = kit.get("campaign_metadata", {}).get("campaign_id") or f"kit_{uuid.uuid4().hex[:12]}"
    kit.setdefault("campaign_metadata", {})["campaign_id"] = kit_id
    _KITS[kit_id] = kit
    return {**result, "kit_id": kit_id}


def generate_content_asset(asset_type: str, brief_data: dict[str, Any]) -> dict[str, Any]:
    done = tool_timer(logger, "generate_content_asset")
    result = _tools.generate_content_asset(sanitize_payload(asset_type), sanitize_payload(brief_data))
    done(qa_status=result.get("qa_status"))
    if result.get("asset"):
        asset_id = result["asset"].get("metadata", {}).get("asset_id") or f"asset_{uuid.uuid4().hex[:12]}"
        result["asset"]["metadata"]["asset_id"] = asset_id
        _ASSETS[asset_id] = result["asset"]
        result["asset_id"] = asset_id
    return result


def refine_content_asset(asset_id: str, feedback_instructions: str) -> dict[str, Any]:
    if asset_id not in _ASSETS:
        raise ValueError(f"Unknown asset_id '{asset_id}'")
    result = _tools.optimize_content_asset(_ASSETS[asset_id], {"feedback": feedback_instructions})
    asset = result.get("asset")
    if asset:
        asset.setdefault("metadata", {})["asset_id"] = asset_id
        _ASSETS[asset_id] = asset
    return {**result, "asset_id": asset_id}


def generate_social_posts(source_asset_json: dict[str, Any], platforms: list[str]) -> dict[str, Any]:
    if not platforms:
        raise ValueError("platforms is required")
    assets = []
    for platform in platforms:
        target = "linkedin_post" if platform.lower() == "linkedin" else f"{platform.lower()}_post"
        assets.append(_tools.repurpose_content_asset(source_asset_json, target)["asset"])
    return {"status": "GENERATED", "platforms": platforms, "assets": assets}


def repurpose_content_asset(source_asset_json: dict[str, Any], target_formats: list[str]) -> dict[str, Any]:
    return _tools.repurpose_content_asset(source_asset_json, target_formats)


def optimize_content_asset(asset_json: dict[str, Any], qa_feedback: Any) -> dict[str, Any]:
    return _tools.optimize_content_asset(asset_json, qa_feedback)


def qa_validate_asset(content_json: dict[str, Any], asset_type: str) -> dict[str, Any]:
    done = tool_timer(logger, "qa_validate_asset")
    result = _tools.qa_validate_asset(sanitize_payload(content_json), sanitize_payload(asset_type))
    done(qa_status=result.get("overall_status"))
    return result


def approve_campaign_kit(kit_id: str) -> dict[str, Any]:
    if kit_id not in _KITS:
        raise ValueError(f"Unknown kit_id '{kit_id}'")
    approver = "human"
    result = _tools.approve_campaign_kit(sanitize_payload(kit_id), approver, notes="Explicit human approval trigger invoked through MCP.")
    return result


def export_campaign_kit(kit_id: str, export_format: str) -> dict[str, Any]:
    if kit_id not in _KITS:
        raise ValueError(f"Unknown kit_id '{kit_id}'")
    return _tools.export_campaign_kit(kit_id, _KITS[kit_id], export_format)
