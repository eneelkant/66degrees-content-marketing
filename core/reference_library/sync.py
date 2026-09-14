from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

REFRESH_DAYS = 2

class ReferenceSync:
    def __init__(self, sqlite_client, chroma_client=None, metadata_path=None):
        self.sqlite = sqlite_client
        self.chroma = chroma_client
        self.metadata_path = Path(metadata_path) if metadata_path else Path(sqlite_client.db_path).with_suffix(".refresh.json")
        self.last_refresh = self._load_last_refresh()

    def _load_last_refresh(self):
        try:
            value = json.loads(self.metadata_path.read_text(encoding="utf-8")).get("last_refresh")
            return datetime.fromisoformat(value) if value else None
        except (FileNotFoundError, ValueError, json.JSONDecodeError, AttributeError):
            return None

    def is_stale(self, now=None):
        now = now or datetime.now(timezone.utc)
        return self.last_refresh is None or now - self.last_refresh >= timedelta(days=REFRESH_DAYS)

    def sync(self, records):
        for r in records:
            self.sqlite.upsert(r)
        if self.chroma:
            self.chroma.upsert(records)
        self.last_refresh = datetime.now(timezone.utc)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps({"last_refresh": self.last_refresh.isoformat(), "refresh_interval_days": REFRESH_DAYS}, indent=2), encoding="utf-8")
        return {"status": "REFRESHED", "record_count": self.sqlite.count(), "last_refresh": self.last_refresh.isoformat()}
