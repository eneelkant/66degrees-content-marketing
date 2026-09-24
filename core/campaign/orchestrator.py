"""Modular campaign orchestrator — runs stages, persists state, stops at human approval."""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from core.brand.rules import load_brand_rules
from core.mcp_legacy import tools as _tools

from .brief import brief_to_event_shape, validate_marketing_brief
from .models import (
    STAGE_ORDER,
    CampaignStage,
    CampaignState,
    CampaignStatus,
    StageRecord,
)
from .state_machine import assert_exportable, transition
from .store import CampaignStore, default_store

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)


def _annotate_asset(
    asset: Any,
    *,
    campaign_id: str,
    content_type: str,
    status: str,
) -> Any:
    if not isinstance(asset, dict):
        return {
            "content": asset,
            "metadata": {
                "campaign_id": campaign_id,
                "content_type": content_type,
                "status": status,
                "updated_at": _now(),
            },
        }
    meta = dict(asset.get("metadata") or {})
    meta.update(
        {
            "campaign_id": campaign_id,
            "content_type": content_type,
            "status": status,
            "updated_at": _now(),
        }
    )
    return {**asset, "metadata": meta}


class CampaignOrchestrator:
    """Execute the governed campaign pipeline and stop at human approval."""

    def __init__(
        self,
        store: CampaignStore | None = None,
        *,
        api: Any | None = None,
        max_optimize_loops: int = 1,
    ):
        self.store = store or default_store()
        self._api = api
        self.max_optimize_loops = max_optimize_loops

    @property
    def api(self) -> Any:
        if self._api is None:
            # Deferred to avoid import cycle with clients.public_api.
            import clients.public_api as public_api  # noqa: PLC0415

            self._api = public_api
        return self._api

    def create_campaign(self, brief_data: dict[str, Any]) -> dict[str, Any]:
        raw = dict(brief_data or {})
        idempotency_key = (
            str(raw.get("idempotency_key") or "").strip()
            or str((raw.get("extra") or {}).get("idempotency_key") or "").strip()
            or None
        )
        if idempotency_key:
            existing = self.store.find_by_idempotency_key(idempotency_key)
            if existing:
                self._log(existing, "create_campaign", "idempotent_hit")
                if existing.status in {
                    CampaignStatus.APPROVAL_PENDING,
                    CampaignStatus.APPROVED,
                    CampaignStatus.EXPORTED,
                    CampaignStatus.REVISION_REQUIRED,
                    CampaignStatus.QA_FAILED,
                    CampaignStatus.ERROR,
                }:
                    return {
                        **existing.summary(),
                        "message": "Idempotent create: returning existing campaign.",
                        "idempotent": True,
                    }
                return {
                    **self.run_until_approval(existing.campaign_id),
                    "idempotent": True,
                }

        brief = validate_marketing_brief(raw)
        campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
        state = CampaignState(
            campaign_id=campaign_id,
            idempotency_key=idempotency_key,
            status=CampaignStatus.DRAFT,
            current_stage=CampaignStage.STRATEGY,
            brief=brief.model_dump(mode="json"),
            stages={stage.value: StageRecord(stage=stage) for stage in STAGE_ORDER},
            provider=os.getenv("LLM_PROVIDER", "mock"),
        )
        self.store.save(state)
        self._log(state, "create_campaign", "started")
        return self.run_until_approval(campaign_id)

    def get_status(self, campaign_id: str) -> dict[str, Any]:
        state = self.store.load(campaign_id)
        return {
            **state.summary(),
            "brand_results": state.brand_results,
            "qa_results": {
                "overall_status": (state.qa_results or {}).get("overall_status"),
                "approval_required": (state.qa_results or {}).get("approval_required", True),
            },
            "errors": state.errors,
        }

    def resume_campaign(self, campaign_id: str) -> dict[str, Any]:
        state = self.store.load(campaign_id)
        if state.status == CampaignStatus.APPROVAL_PENDING:
            return {
                **state.summary(),
                "message": (
                    "Campaign is waiting for human approval. "
                    f"Call approve_campaign with campaign_id '{campaign_id}' "
                    f"(or approve_campaign_kit with kit_id '{state.kit_id}') before export."
                ),
            }
        if state.status == CampaignStatus.APPROVED:
            return {
                **state.summary(),
                "message": (
                    "Campaign is approved. Call export_campaign / export_campaign_kit to export."
                ),
            }
        if state.status == CampaignStatus.EXPORTED:
            return {
                **state.summary(),
                "message": "Campaign already exported.",
                "idempotent": True,
            }
        if state.status in {CampaignStatus.REVISION_REQUIRED, CampaignStatus.QA_FAILED}:
            self._reset_stages_from(state, CampaignStage.QA)
            # Re-enter the QA path from a content-ready state.
            state.status = CampaignStatus.GENERATED
            self.store.save(state)
        if state.status == CampaignStatus.ERROR:
            # Retry from the first failed stage.
            for stage in STAGE_ORDER:
                rec = state.stages.get(stage.value)
                if rec and rec.status == "failed":
                    rec.status = "pending"
                    rec.error = None
                    break
            state.status = CampaignStatus.DRAFT if not state.kit_id else CampaignStatus.GENERATED
            self.store.save(state)
        return self.run_until_approval(campaign_id)

    def run_until_approval(
        self,
        campaign_id: str,
        *,
        stop_after: CampaignStage | None = None,
    ) -> dict[str, Any]:
        state = self.store.load(campaign_id)
        runners: list[tuple[CampaignStage, Callable[[CampaignState], None]]] = [
            (CampaignStage.STRATEGY, self._stage_strategy),
            (CampaignStage.EVENT_INTELLIGENCE, self._stage_event),
            (CampaignStage.CONTENT, self._stage_content),
            (CampaignStage.REPURPOSING, self._stage_repurpose),
            (CampaignStage.SOCIAL, self._stage_social),
            (CampaignStage.BRAND, self._stage_brand),
            (CampaignStage.QA, self._stage_qa),
            (CampaignStage.OPTIMIZATION, self._stage_optimize),
            (CampaignStage.APPROVAL, self._stage_await_approval),
        ]
        try:
            for stage, runner in runners:
                rec = state.stages.get(stage.value)
                if rec and rec.status == "complete":
                    continue
                if state.status in {
                    CampaignStatus.APPROVAL_PENDING,
                    CampaignStatus.APPROVED,
                    CampaignStatus.EXPORTED,
                    CampaignStatus.REJECTED,
                    CampaignStatus.REVISION_REQUIRED,
                    CampaignStatus.QA_FAILED,
                }:
                    break
                self._run_stage(state, stage, runner)
                self.store.save(state)
                if stop_after is not None and stage == stop_after:
                    self._log(state, "orchestrator", "stopped_after", stage=stage.value)
                    break
                if state.status in {
                    CampaignStatus.ERROR,
                    CampaignStatus.QA_FAILED,
                    CampaignStatus.REVISION_REQUIRED,
                    CampaignStatus.REJECTED,
                }:
                    break
        except Exception as exc:
            if state.status != CampaignStatus.ERROR:
                try:
                    state.status = transition(state.status, CampaignStatus.ERROR)
                except PermissionError:
                    state.status = CampaignStatus.ERROR
            state.errors.append(str(exc))
            self.store.save(state)
            self._log(state, "orchestrator", "error", error_type=type(exc).__name__)
            raise

        self.store.save(state)
        message = f"Campaign ended in status {state.status.value}."
        if state.status == CampaignStatus.APPROVAL_PENDING:
            message = "Stopped at human approval gate. Review assets, then approve before export."
        elif state.status == CampaignStatus.REVISION_REQUIRED:
            message = (
                "QA requires revision. Update content / call resume_campaign after fixes. "
                "Export remains blocked."
            )
        elif stop_after is not None and state.status not in {
            CampaignStatus.APPROVAL_PENDING,
            CampaignStatus.REVISION_REQUIRED,
        }:
            message = f"Stopped after stage '{stop_after.value}' for interrupt/resume testing."
        return {
            **state.summary(),
            "generated_assets": {
                "kit_id": state.kit_id,
                "assets": list(state.assets.keys()),
                "social_count": len(state.social_assets),
                "repurposed_count": len(state.repurposed_assets),
            },
            "qa_status": (state.qa_results or {}).get("overall_status"),
            "approval_status": state.approval.get("status", "pending"),
            "message": message,
        }

    def mark_approved(
        self,
        campaign_id: str,
        approved_by: str = "human",
        notes: str | None = None,
    ) -> dict[str, Any]:
        state = self.store.load(campaign_id)
        if state.status == CampaignStatus.APPROVED:
            return {**state.summary(), "idempotent": True, "message": "Already approved."}
        if state.status == CampaignStatus.EXPORTED:
            return {**state.summary(), "idempotent": True, "message": "Already exported."}
        state.status = transition(state.status, CampaignStatus.APPROVED)
        state.current_stage = CampaignStage.APPROVAL
        state.approval = {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": _now(),
            "notes": notes,
        }
        stage = state.stages[CampaignStage.APPROVAL.value]
        stage.status = "complete"
        stage.finished_at = _now()
        if state.kit_id:
            if state.kit_id not in self.api._KITS:
                self.api._KITS[state.kit_id] = {
                    "campaign_metadata": {"campaign_id": state.kit_id},
                    **state.assets,
                }
            _tools.approve_campaign_kit(
                state.kit_id,
                approved_by,
                notes or "Approved via campaign orchestrator.",
            )
        self.store.save(state)
        self._log(state, "approve_campaign", "approved")
        return state.summary()

    def mark_exported(self, campaign_id: str, export_result: dict[str, Any]) -> dict[str, Any]:
        state = self.store.load(campaign_id)
        if state.status == CampaignStatus.EXPORTED:
            return {
                **state.summary(),
                "idempotent": True,
                "export": state.export,
                "message": "Already exported; returning prior export metadata.",
            }
        assert_exportable(state.status)
        state.status = transition(state.status, CampaignStatus.EXPORTED)
        state.current_stage = CampaignStage.EXPORT
        state.export = {"status": "exported", **export_result, "exported_at": _now()}
        stage = state.stages[CampaignStage.EXPORT.value]
        stage.status = "complete"
        stage.finished_at = _now()
        self.store.save(state)
        self._log(state, "export_campaign", "exported")
        return state.summary()

    def sync_kit_approved(self, kit_id: str) -> None:
        state = self.store.find_by_kit_id(kit_id)
        if not state:
            return
        if state.status == CampaignStatus.APPROVAL_PENDING:
            state.status = transition(state.status, CampaignStatus.APPROVED)
            state.approval = {
                "status": "approved",
                "approved_by": "human",
                "approved_at": _now(),
                "notes": "Synced from approve_campaign_kit",
            }
            state.stages[CampaignStage.APPROVAL.value].status = "complete"
            self.store.save(state)

    def sync_kit_exported(self, kit_id: str, export_result: dict[str, Any]) -> None:
        state = self.store.find_by_kit_id(kit_id)
        if not state:
            return
        if state.status == CampaignStatus.APPROVED:
            state.status = transition(state.status, CampaignStatus.EXPORTED)
            state.export = {"status": "exported", **export_result, "exported_at": _now()}
            state.stages[CampaignStage.EXPORT.value].status = "complete"
            self.store.save(state)

    def _reset_stages_from(self, state: CampaignState, start: CampaignStage) -> None:
        started = False
        for stage in STAGE_ORDER:
            if stage == start:
                started = True
            if not started:
                continue
            rec = state.stages.setdefault(stage.value, StageRecord(stage=stage))
            rec.status = "pending"
            rec.error = None
            rec.started_at = None
            rec.finished_at = None

    # --- stages -----------------------------------------------------------------

    def _run_stage(
        self,
        state: CampaignState,
        stage: CampaignStage,
        runner: Callable[[CampaignState], None],
    ) -> None:
        record = state.stages.setdefault(stage.value, StageRecord(stage=stage))
        record.status = "running"
        record.started_at = _now()
        state.previous_stage = state.current_stage
        state.current_stage = stage
        started = time.perf_counter()
        try:
            runner(state)
            if record.status == "running":
                record.status = "complete"
            record.finished_at = _now()
            ms = round((time.perf_counter() - started) * 1000, 2)
            self._log(state, stage.value, record.status, duration_ms=ms)
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            record.finished_at = _now()
            try:
                state.status = transition(state.status, CampaignStatus.ERROR)
            except PermissionError:
                state.status = CampaignStatus.ERROR
            state.errors.append(f"{stage.value}: {exc}")
            self._log(
                state,
                stage.value,
                "failed",
                error_type=type(exc).__name__,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            raise

    def _stage_strategy(self, state: CampaignState) -> None:
        brief = validate_marketing_brief(state.brief)
        result = self.api.generate_content_strategy(
            {
                "objective": brief.objective,
                "audience": brief.audience,
                "channels": brief.channels,
            }
        )
        state.strategy = result
        state.stages[CampaignStage.STRATEGY.value].details = {"status": result.get("status")}

    def _stage_event(self, state: CampaignState) -> None:
        brief = validate_marketing_brief(state.brief)
        event_shape = brief_to_event_shape(brief)
        result = self.api.process_event_brief(event_shape)
        state.event_brief = result
        state.stages[CampaignStage.EVENT_INTELLIGENCE.value].details = {
            "status": result.get("status"),
            "missing_fields": result.get("missing_fields", []),
        }

    def _stage_content(self, state: CampaignState) -> None:
        brief = validate_marketing_brief(state.brief)
        event_shape = brief_to_event_shape(brief)
        if state.event_brief and isinstance(state.event_brief.get("brief"), dict):
            event_shape = {**event_shape, **state.event_brief["brief"]}
        result = self.api.generate_campaign_kit(event_shape)
        if result.get("qa_status") == "FAILED":
            raise RuntimeError(result.get("error") or "Campaign kit generation failed")
        state.kit_id = result.get("kit_id")
        kit = result.get("campaign_kit") or {}
        state.assets = {}
        for key in ("landing_page", "google_ads", "linkedin_ads", "email_campaign"):
            if key in kit:
                state.assets[key] = _annotate_asset(
                    kit[key],
                    campaign_id=state.campaign_id,
                    content_type=key,
                    status="GENERATED",
                )
        state.status = transition(state.status, CampaignStatus.GENERATED)
        state.stages[CampaignStage.CONTENT.value].details = {"kit_id": state.kit_id}

    def _stage_repurpose(self, state: CampaignState) -> None:
        source = state.assets.get("landing_page") or next(iter(state.assets.values()), None)
        if not source:
            state.stages[CampaignStage.REPURPOSING.value].status = "skipped"
            return
        result = self.api.repurpose_content_asset(source, ["linkedin_post"])
        assets = result.get("assets") or []
        state.repurposed_assets = [
            _annotate_asset(
                asset,
                campaign_id=state.campaign_id,
                content_type="linkedin_post",
                status="REPURPOSED",
            )
            for asset in assets
        ]
        state.stages[CampaignStage.REPURPOSING.value].details = {
            "count": len(state.repurposed_assets)
        }

    def _stage_social(self, state: CampaignState) -> None:
        source = state.assets.get("landing_page") or next(iter(state.assets.values()), None)
        if not source:
            state.stages[CampaignStage.SOCIAL.value].status = "skipped"
            return
        platforms: list[str] = []
        for channel in (state.brief or {}).get("channels") or []:
            name = str(channel).lower()
            if "linkedin" in name:
                platforms.append("linkedin")
            elif name in {"x", "twitter"}:
                platforms.append("x")
        if not platforms:
            platforms = ["linkedin"]
        result = self.api.generate_social_posts(source, platforms)
        assets = result.get("assets") or []
        state.social_assets = [
            _annotate_asset(
                asset,
                campaign_id=state.campaign_id,
                content_type="social_post",
                status="GENERATED",
            )
            for asset in assets
        ]
        state.stages[CampaignStage.SOCIAL.value].details = {
            "platforms": platforms,
            "count": len(state.social_assets),
        }

    def _stage_brand(self, state: CampaignState) -> None:
        rules = load_brand_rules()
        results: dict[str, Any] = {}
        for name, asset in state.assets.items():
            results[name] = rules.validate_text(_flatten_text(asset))
        state.brand_results = results
        failures = [k for k, v in results.items() if not v.get("valid", True)]
        state.stages[CampaignStage.BRAND.value].details = {
            "failed_assets": failures,
            "checked": list(results.keys()),
        }

    def _stage_qa(self, state: CampaignState) -> None:
        if state.status == CampaignStatus.GENERATED:
            state.status = transition(state.status, CampaignStatus.QA_PENDING)
        elif state.status not in {CampaignStatus.QA_PENDING, CampaignStatus.REVISION_REQUIRED}:
            # Allow resume paths that already sit in QA_PENDING.
            try:
                state.status = transition(state.status, CampaignStatus.QA_PENDING)
            except PermissionError:
                state.status = CampaignStatus.QA_PENDING
        asset = state.assets.get("landing_page") or next(iter(state.assets.values()), {})
        report = self.api.qa_validate_asset(asset, "landing_page")
        state.qa_results = report
        overall = report.get("overall_status")
        if overall == "REWRITE":
            state.status = transition(state.status, CampaignStatus.REVISION_REQUIRED)
        elif overall in {"PASS", "WARNING"}:
            state.status = transition(state.status, CampaignStatus.QA_PASSED)
        else:
            state.status = transition(state.status, CampaignStatus.QA_FAILED)
        state.stages[CampaignStage.QA.value].details = {"overall_status": overall}

    def _stage_optimize(self, state: CampaignState) -> None:
        overall = (state.qa_results or {}).get("overall_status")
        if overall not in {"REWRITE", "WARNING"}:
            state.stages[CampaignStage.OPTIMIZATION.value].status = "skipped"
            return

        asset_key = "landing_page" if "landing_page" in state.assets else next(iter(state.assets))
        asset = state.assets[asset_key]
        for _ in range(self.max_optimize_loops):
            optimized = self.api.optimize_content_asset(
                asset,
                {"state": overall, "violations": ["Improve clarity and brand alignment"]},
            )
            asset = optimized.get("asset") or asset
            state.assets[asset_key] = _annotate_asset(
                asset,
                campaign_id=state.campaign_id,
                content_type=asset_key,
                status="OPTIMIZED",
            )
            report = self.api.qa_validate_asset(state.assets[asset_key], "landing_page")
            state.qa_results = report
            overall = report.get("overall_status")
            if overall in {"PASS", "WARNING"}:
                if state.status == CampaignStatus.REVISION_REQUIRED:
                    state.status = transition(state.status, CampaignStatus.QA_PENDING)
                if state.status == CampaignStatus.QA_PENDING:
                    state.status = transition(state.status, CampaignStatus.QA_PASSED)
                break

        # Production rule: do NOT auto-promote REWRITE to approval.
        if overall == "REWRITE":
            state.status = CampaignStatus.REVISION_REQUIRED
        state.stages[CampaignStage.OPTIMIZATION.value].details = {
            "final_qa": (state.qa_results or {}).get("overall_status")
        }

    def _stage_await_approval(self, state: CampaignState) -> None:
        if state.status in {CampaignStatus.QA_FAILED, CampaignStatus.REVISION_REQUIRED}:
            raise PermissionError(
                f"Cannot enter approval while {state.status.value}. "
                "Fix content and call resume_campaign after QA passes."
            )
        if state.status != CampaignStatus.QA_PASSED:
            raise PermissionError(
                f"Cannot enter approval from {state.status.value}; QA_PASSED is required."
            )
        state.status = transition(state.status, CampaignStatus.APPROVAL_PENDING)
        state.approval = {"status": "pending", "gate": "human"}
        state.stages[CampaignStage.APPROVAL.value].status = "complete"
        state.stages[CampaignStage.APPROVAL.value].details = {
            "message": "Awaiting explicit human approval before export."
        }
        state.stages[CampaignStage.EXPORT.value].status = "pending"
        state.stages[CampaignStage.EXPORT.value].details = {"blocked": True}

    def _log(self, state: CampaignState, agent: str, status: str, **fields: Any) -> None:
        logger.info(
            "campaign_event",
            extra={
                "campaign_id": state.campaign_id,
                "stage": state.current_stage.value if state.current_stage else None,
                "previous_stage": state.previous_stage.value if state.previous_stage else None,
                "agent": agent,
                "tool": agent,
                "status": status,
                "approval_state": state.status.value,
                "provider": state.provider or os.getenv("LLM_PROVIDER", "mock"),
                **fields,
            },
        )


_orchestrator: CampaignOrchestrator | None = None


def get_orchestrator(store: CampaignStore | None = None) -> CampaignOrchestrator:
    global _orchestrator
    if store is not None:
        return CampaignOrchestrator(store=store)
    if _orchestrator is None:
        _orchestrator = CampaignOrchestrator()
    return _orchestrator
