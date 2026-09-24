"""Campaign status machine transition guards."""
import pytest

from core.campaign.models import CampaignStatus
from core.campaign.state_machine import assert_exportable, can_transition, transition


def test_qa_failed_cannot_become_approved():
    with pytest.raises(PermissionError, match="QA_FAILED"):
        transition(CampaignStatus.QA_FAILED, CampaignStatus.APPROVED)


def test_approval_pending_cannot_export_directly():
    with pytest.raises(PermissionError, match="APPROVAL_PENDING"):
        transition(CampaignStatus.APPROVAL_PENDING, CampaignStatus.EXPORTED)


def test_approved_can_export():
    assert transition(CampaignStatus.APPROVED, CampaignStatus.EXPORTED) == CampaignStatus.EXPORTED


def test_happy_path_transitions():
    status = CampaignStatus.DRAFT
    status = transition(status, CampaignStatus.GENERATED)
    status = transition(status, CampaignStatus.QA_PENDING)
    status = transition(status, CampaignStatus.QA_PASSED)
    status = transition(status, CampaignStatus.APPROVAL_PENDING)
    status = transition(status, CampaignStatus.APPROVED)
    status = transition(status, CampaignStatus.EXPORTED)
    assert status == CampaignStatus.EXPORTED


def test_assert_exportable_blocks_pending():
    with pytest.raises(PermissionError, match="Export blocked"):
        assert_exportable(CampaignStatus.APPROVAL_PENDING)
    assert_exportable(CampaignStatus.APPROVED)


def test_can_transition_helper():
    assert can_transition(CampaignStatus.APPROVAL_PENDING, CampaignStatus.APPROVED)
    assert not can_transition(CampaignStatus.QA_FAILED, CampaignStatus.APPROVED)
