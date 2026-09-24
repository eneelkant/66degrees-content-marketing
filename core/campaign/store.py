"""Filesystem campaign state store (JSON under data/campaigns/)."""
from __future__ import annotations

import json
from pathlib import Path

from config.settings import get_settings

from .models import CampaignState


class CampaignStore:
    def __init__(self, root: Path | None = None):
        settings = get_settings()
        base = Path(root) if root is not None else Path(settings.data_dir) / "campaigns"
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, campaign_id: str) -> Path:
        safe = "".join(c for c in campaign_id if c.isalnum() or c in ("-", "_"))
        if not safe:
            raise ValueError("campaign_id is empty or invalid")
        return self.root / f"{safe}.json"

    def save(self, state: CampaignState) -> Path:
        state.touch()
        path = self._path(state.campaign_id)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, campaign_id: str) -> CampaignState:
        path = self._path(campaign_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Unknown campaign_id '{campaign_id}'. "
                "Create a campaign with create_campaign first, or check the ID."
            )
        return CampaignState.model_validate_json(path.read_text(encoding="utf-8"))

    def find_by_kit_id(self, kit_id: str) -> CampaignState | None:
        for path in self.root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("kit_id") == kit_id:
                return CampaignState.model_validate(data)
        return None

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))


def default_store() -> CampaignStore:
    return CampaignStore()
