"""Campaign status transition guards.

Illegal transitions raise PermissionError with actionable messages.
"""
from __future__ import annotations

from .models import CampaignStatus


# Allowed directed edges. Failure/terminal states are explicit.
_ALLOWED: dict[CampaignStatus, frozenset[CampaignStatus]] = {
    CampaignStatus.DRAFT: frozenset(
        {
            CampaignStatus.GENERATED,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.GENERATED: frozenset(
        {
            CampaignStatus.QA_PENDING,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.QA_PENDING: frozenset(
        {
            CampaignStatus.QA_PASSED,
            CampaignStatus.QA_FAILED,
            CampaignStatus.REVISION_REQUIRED,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.QA_PASSED: frozenset(
        {
            CampaignStatus.APPROVAL_PENDING,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.QA_FAILED: frozenset(
        {
            CampaignStatus.REVISION_REQUIRED,
            CampaignStatus.QA_PENDING,
            CampaignStatus.ERROR,
            CampaignStatus.REJECTED,
        }
    ),
    CampaignStatus.REVISION_REQUIRED: frozenset(
        {
            CampaignStatus.GENERATED,
            CampaignStatus.QA_PENDING,
            CampaignStatus.ERROR,
            CampaignStatus.REJECTED,
        }
    ),
    CampaignStatus.APPROVAL_PENDING: frozenset(
        {
            CampaignStatus.APPROVED,
            CampaignStatus.REJECTED,
            CampaignStatus.REVISION_REQUIRED,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.APPROVED: frozenset(
        {
            CampaignStatus.EXPORTED,
            CampaignStatus.ERROR,
        }
    ),
    CampaignStatus.REJECTED: frozenset({CampaignStatus.ERROR}),
    CampaignStatus.EXPORTED: frozenset(),
    CampaignStatus.ERROR: frozenset(
        {
            CampaignStatus.DRAFT,
            CampaignStatus.GENERATED,
            CampaignStatus.QA_PENDING,
            CampaignStatus.REVISION_REQUIRED,
        }
    ),
}


def can_transition(current: CampaignStatus, target: CampaignStatus) -> bool:
    if current == target:
        return True
    return target in _ALLOWED.get(current, frozenset())


def transition(current: CampaignStatus, target: CampaignStatus) -> CampaignStatus:
    """Return target status or raise PermissionError for illegal moves."""
    if can_transition(current, target):
        return target

    # High-signal forbidden paths called out in product requirements.
    if current == CampaignStatus.QA_FAILED and target == CampaignStatus.APPROVED:
        raise PermissionError(
            "Illegal transition: QA_FAILED → APPROVED. "
            "Re-run QA until QA_PASSED, then move to APPROVAL_PENDING before approval."
        )
    if current == CampaignStatus.APPROVAL_PENDING and target == CampaignStatus.EXPORTED:
        raise PermissionError(
            "Illegal transition: APPROVAL_PENDING → EXPORTED. "
            "A human must approve the campaign before export."
        )
    if current != CampaignStatus.APPROVED and target == CampaignStatus.EXPORTED:
        raise PermissionError(
            f"Export blocked from status {current.value}. "
            "Campaign must be APPROVED before EXPORTED."
        )
    if target == CampaignStatus.APPROVED and current not in {
        CampaignStatus.APPROVAL_PENDING,
        CampaignStatus.APPROVED,
    }:
        raise PermissionError(
            f"Cannot approve from status {current.value}. "
            "Campaign must be APPROVAL_PENDING (after QA_PASSED)."
        )

    raise PermissionError(
        f"Illegal campaign status transition: {current.value} → {target.value}."
    )


def assert_exportable(status: CampaignStatus) -> None:
    if status != CampaignStatus.APPROVED and status != CampaignStatus.EXPORTED:
        raise PermissionError(
            f"Export blocked: campaign status is {status.value}, not APPROVED."
        )
