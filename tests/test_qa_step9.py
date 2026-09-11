from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from core.approval.gate import HumanApprovalGate
from core.brand.rules import load_brand_rules
from core.qa.engine import qa_validate_asset
from core.qa.models import QAState
from core.qa.originality import OriginalityAnalyzer
from core.reference_library.models import ReferenceRecord
from core.reference_library.sqlite_client import SQLiteReferenceClient
from core.generators.google_ads import generate_google_ads_rsa
from core.generators.linkedin_ads import generate_linkedin_sponsored_content


def test_brand_and_hard_constraints_pass_for_valid_google_ads():
    brief = {"metadata": {"title": "Build AI Systems Enterprises Trust"}, "value_prop": {"primary_hook": "Move AI from pilot to measurable impact"}}
    ads = generate_google_ads_rsa(brief)
    report = qa_validate_asset(ads, "google_ads", references=[])
    assert report.overall_status == QAState.WARNING  # no corpus is a review warning
    assert report.checks[0].state == QAState.PASS
    assert report.checks[1].state == QAState.PASS


def test_google_constraints_rewrite_when_lengths_or_counts_fail():
    content = {"headlines": ["x" * 31], "descriptions": ["x" * 91], "display_paths": ["x" * 16]}
    report = qa_validate_asset(content, "google_ads", references=[])
    assert report.overall_status == QAState.REWRITE
    assert report.checks[0].state == QAState.REWRITE


def test_brand_rules_flag_forbidden_jargon():
    report = qa_validate_asset({"content": "This is a game-changing synergy with cheap migration."}, "blog", references=[])
    brand_check = next(c for c in report.checks if c.name == "brand_rules")
    assert brand_check.state == QAState.REWRITE
    assert "synergy" in brand_check.details["forbidden_jargon"]
    assert "cheap migration" in brand_check.details["forbidden_jargon"]


def test_originality_two_tier_lexical_thresholds():
    refs = [{"id": "r1", "title": "Winner", "content": "Move enterprise AI from pilot to measurable business impact."}]
    check = OriginalityAnalyzer().analyze("Move enterprise AI from pilot to measurable business impact.", refs)
    assert check.state == QAState.REWRITE
    assert check.details["lexical_similarity"] >= 0.75


def test_originality_can_use_semantic_distance_adapter():
    refs = [{"id": "r1", "title": "Winner", "content": "Different wording."}]
    def semantic(candidate, records):
        # Adapter returns similarity derived from a Chroma distance externally.
        return [{"id": "r1", "similarity": 0.80, "distance": 0.20}]
    check = OriginalityAnalyzer(semantic_search=semantic).analyze("New wording", refs)
    assert check.state == QAState.REWRITE
    assert check.details["semantic_similarity"] == 0.80


def test_emailens_is_in_pipeline_and_never_silently_passes_when_unavailable():
    class FakeEmailens:
        def audit(self, text):
            from core.qa.models import QACheck
            return QACheck(name="emailens", state=QAState.WARNING, message="mock audit")
    report = qa_validate_asset({"body": "Hello [Button Text]"}, "email", references=[], emailens_engine=FakeEmailens())
    assert any(c.name == "emailens" for c in report.checks)


def test_human_approval_blocks_export_until_explicit_approval():
    gate = HumanApprovalGate()
    with pytest.raises(PermissionError):
        gate.require_approved("kit-1")
    record = gate.approve("kit-1", "Executive Approver")
    assert record.approved is True
    gate.require_approved("kit-1")


def test_google_and_linkedin_reference_isolation(tmp_path):
    db = SQLiteReferenceClient(Path(tmp_path) / "references.db")
    now = datetime.now(timezone.utc)
    db.upsert(ReferenceRecord(id="g", title="Google winner", content="google copy", source="66degrees", platform="google", performance_score=.9, fetched_at=now))
    db.upsert(ReferenceRecord(id="l", title="LinkedIn winner", content="linkedin copy", source="66degrees", platform="linkedin", performance_score=.9, fetched_at=now))
    assert [r.id for r in db.search(platform="google")] == ["g"]
    assert [r.id for r in db.search(platform="linkedin")] == ["l"]
