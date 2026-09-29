from datetime import datetime, timedelta, timezone
import json
import os
import tempfile
from pathlib import Path

REFRESH_DAYS = 2


class ReferenceSync:
    def __init__(self, sqlite_client, chroma_client=None, metadata_path=None):
        self.sqlite = sqlite_client
        self.chroma = chroma_client
        self.metadata_path = (
            Path(metadata_path)
            if metadata_path
            else Path(sqlite_client.db_path).with_suffix(".refresh.json")
        )
        self.last_refresh = self._load_last_refresh()

    def _load_last_refresh(self):
        try:
            value = json.loads(self.metadata_path.read_text(encoding="utf-8")).get("last_refresh")
            return datetime.fromisoformat(value) if value else None
        except (FileNotFoundError, ValueError, json.JSONDecodeError, AttributeError, OSError):
            return None

    def is_stale(self, now=None):
        now = now or datetime.now(timezone.utc)
        return self.last_refresh is None or now - self.last_refresh >= timedelta(days=REFRESH_DAYS)

    def sync(self, records):
        if not records:
            raise ValueError("Refusing to sync an empty reference record list.")
        for r in records:
            self.sqlite.upsert(r)
        if self.chroma:
            self.chroma.upsert(records)
        self.last_refresh = datetime.now(timezone.utc)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_refresh": self.last_refresh.isoformat(),
            "refresh_interval_days": REFRESH_DAYS,
            "record_count": self.sqlite.count(),
        }
        self._atomic_write_json(self.metadata_path, payload)
        return {
            "status": "REFRESHED",
            "record_count": self.sqlite.count(),
            "last_refresh": self.last_refresh.isoformat(),
        }

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
