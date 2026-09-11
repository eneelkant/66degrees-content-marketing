from datetime import datetime, timezone
from .models import ApprovalRecord


class HumanApprovalGate:
    def __init__(self):
        self._records: dict[str, ApprovalRecord] = {}

    def approve(self, asset_or_kit_id: str, approved_by: str, notes: str | None = None) -> ApprovalRecord:
        if not approved_by.strip():
            raise ValueError("approved_by is required for human approval")
        record = ApprovalRecord(
            asset_or_kit_id=asset_or_kit_id,
            approved=True,
            approved_by=approved_by,
            approved_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        self._records[asset_or_kit_id] = record
        return record

    def is_approved(self, asset_or_kit_id: str) -> bool:
        return self._records.get(asset_or_kit_id, ApprovalRecord(asset_or_kit_id=asset_or_kit_id)).approved

    def require_approved(self, asset_or_kit_id: str) -> None:
        if not self.is_approved(asset_or_kit_id):
            raise PermissionError(f"Export blocked: '{asset_or_kit_id}' has not received explicit human approval.")
