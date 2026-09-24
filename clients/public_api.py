"""Stable public API used by all client adapters."""
from __future__ import annotations

import uuid
from typing import Any

from clients.surface import PUBLIC_TOOL_NAMES
from config.logging import configure_logging, tool_timer
from core.campaign.models import CampaignStatus
from core.campaign.orchestrator import get_orchestrator
from core.campaign.state_machine import assert_exportable
from core.event_brief.intake import process_event_brief as _process_event_brief
from core.mcp_legacy import tools as _tools
from core.security.input import sanitize_payload

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
    return _process_event_brief(sanitize_payload(brief_data or {}))


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
        raise ValueError("platforms is required — pass at least one platform such as 'linkedin'.")
    assets = []
    for platform in platforms:
        target = "linkedin_post" if platform.lower() == "linkedin" else f"{platform.lower()}_post"
        result = _tools.repurpose_content_asset(source_asset_json, target)
        if "asset" in result:
            assets.append(result["asset"])
        elif result.get("assets"):
            assets.append(result["assets"][0])
        else:
            raise ValueError(
                f"Repurposing to '{target}' did not return an asset. "
                "Check the source asset JSON and target platform."
            )
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
        raise ValueError(
            f"Unknown kit_id '{kit_id}'. Generate a campaign kit first with "
            "generate_campaign_kit, then pass the returned kit_id to approve_campaign_kit."
        )
    approver = "human"
    result = _tools.approve_campaign_kit(
        sanitize_payload(kit_id),
        approver,
        notes="Explicit human approval trigger invoked through MCP.",
    )
    get_orchestrator().sync_kit_approved(kit_id)
    return result


def export_campaign_kit(kit_id: str, export_format: str) -> dict[str, Any]:
    if kit_id not in _KITS:
        raise ValueError(
            f"Unknown kit_id '{kit_id}'. Generate and approve a campaign kit before export."
        )
    result = _tools.export_campaign_kit(kit_id, _KITS[kit_id], export_format)
    get_orchestrator().sync_kit_exported(kit_id, result)
    return result


def create_campaign(brief_data: dict[str, Any]) -> dict[str, Any]:
    """Run the governed campaign pipeline and stop at the human approval gate."""
    done = tool_timer(logger, "create_campaign")
    result = get_orchestrator().create_campaign(sanitize_payload(brief_data or {}))
    done(qa_status=result.get("qa_status"), approval_state=result.get("status"))
    return result


def get_campaign_status(campaign_id: str) -> dict[str, Any]:
    return get_orchestrator().get_status(sanitize_payload(campaign_id))


def resume_campaign(campaign_id: str) -> dict[str, Any]:
    done = tool_timer(logger, "resume_campaign")
    result = get_orchestrator().resume_campaign(sanitize_payload(campaign_id))
    done(approval_state=result.get("status"))
    return result


def approve_campaign(campaign_id: str) -> dict[str, Any]:
    """Explicit human approval for an orchestrated campaign (requires APPROVAL_PENDING)."""
    return get_orchestrator().mark_approved(sanitize_payload(campaign_id))


def export_campaign(campaign_id: str, export_format: str = "json") -> dict[str, Any]:
    """Export an approved orchestrated campaign. Fails if not APPROVED."""
    orch = get_orchestrator()
    state = orch.store.load(sanitize_payload(campaign_id))
    assert_exportable(state.status)
    if not state.kit_id:
        raise ValueError(f"Campaign '{campaign_id}' has no kit_id to export.")
    if state.kit_id not in _KITS:
        _KITS[state.kit_id] = {
            "campaign_metadata": {"campaign_id": state.kit_id},
            **state.assets,
        }
    if state.status == CampaignStatus.APPROVED and not _tools._approval_gate.is_approved(
        state.kit_id
    ):
        _tools.approve_campaign_kit(state.kit_id, "human", "Synced before export.")
    exported = export_campaign_kit(state.kit_id, export_format)
    # sync_kit_exported already ran inside export_campaign_kit; ensure campaign status.
    if orch.store.load(campaign_id).status != CampaignStatus.EXPORTED:
        orch.mark_exported(campaign_id, exported)
    return {**exported, "campaign_id": campaign_id}
