import json
import subprocess
from pathlib import Path
from typing import Any
from .models import QACheck, QAState


class EmailensAuditEngine:
    """Programmatic bridge to the repo-local @emailens/engine Node package."""

    def __init__(self, project_dir: str | Path | None = None):
        self.project_dir = Path(project_dir or Path(__file__).resolve().parents[2])
        self.runner = self.project_dir / "engines" / "emailens" / "audit_email.mjs"

    def audit(self, html_or_text: str) -> QACheck:
        if not self.runner.exists():
            return QACheck(name="emailens", state=QAState.WARNING, message="Emailens runner is not configured.", details={"configured": False})
        try:
            proc = subprocess.run(
                ["node", str(self.runner)],
                input=json.dumps({"email": html_or_text}),
                text=True,
                capture_output=True,
                cwd=self.project_dir,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return QACheck(name="emailens", state=QAState.WARNING, message=f"Emailens execution unavailable: {exc}", details={"configured": False})
        if proc.returncode != 0:
            return QACheck(name="emailens", state=QAState.WARNING, message="Emailens execution failed; no silent PASS was issued.", details={"stderr": proc.stderr[-2000:]})
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return QACheck(name="emailens", state=QAState.WARNING, message="Emailens returned non-JSON output.", details={"raw": proc.stdout[-2000:]})
        spam = result.get("spam", {}) if isinstance(result, dict) else {}
        score = spam.get("score", result.get("spam_score")) if isinstance(spam, dict) else result.get("spam_score")
        findings = spam.get("findings", []) if isinstance(spam, dict) else []
        # Emailens' local engine provides spam scoring. Domain-level SPF/DKIM/DMARC
        # deliverability requires its server/DNS entry point, so we do not fabricate it here.
        risk = "high" if isinstance(score, (int, float)) and float(score) < 60 else "low"
        state = QAState.REWRITE if risk == "high" else QAState.PASS
        return QACheck(name="emailens", state=state, message="Emailens audit completed.", details={
            **result,
            "spam_score": score,
            "spam_risk": risk,
            "spam_findings": findings,
            "deliverability_score": result.get("deliverability_score"),
            "deliverability_scope": "local_content_audit_only",
        })
