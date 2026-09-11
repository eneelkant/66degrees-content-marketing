from pydantic import BaseModel

class ApprovalRecord(BaseModel):
    asset_or_kit_id: str
    approved: bool = False
    approved_by: str | None = None
    approved_at: str | None = None
    notes: str | None = None
