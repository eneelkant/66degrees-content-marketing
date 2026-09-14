import sqlite3
from pathlib import Path
from .models import ReferenceRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS reference_records (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL,
 source_type TEXT NOT NULL, authority_level TEXT NOT NULL, channel TEXT, industry TEXT, topic TEXT,
 platform TEXT, performance_score REAL NOT NULL, semantic_similarity REAL NOT NULL, published_at TEXT,
 fetched_at TEXT, version TEXT, metadata_json TEXT NOT NULL
);
"""

class SQLiteReferenceClient:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(reference_records)")}
        if "platform" not in columns:
            self.conn.execute("ALTER TABLE reference_records ADD COLUMN platform TEXT")
        self.conn.commit()

    def upsert(self, record: ReferenceRecord) -> None:
        self.conn.execute("""INSERT OR REPLACE INTO reference_records (
                id, title, content, source, source_type, authority_level,
                channel, industry, topic, performance_score,
                semantic_similarity, published_at, fetched_at, version,
                metadata_json, platform
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            record.id, record.title, record.content, record.source, record.source_type,
            record.authority_level, record.channel, record.industry, record.topic,
            record.performance_score, record.semantic_similarity,
            record.published_at.isoformat() if record.published_at else None,
            record.fetched_at.isoformat() if record.fetched_at else None,
            record.version, __import__('json').dumps(record.metadata), record.platform
        ))
        self.conn.commit()

    def search(self, *, industry: str | None = None, channel: str | None = None, platform: str | None = None, limit: int = 20):
        clauses, params = [], []
        if industry: clauses.append("(industry = ? OR industry IS NULL)"); params.append(industry)
        if channel: clauses.append("(channel = ? OR channel IS NULL)"); params.append(channel)
        if platform: clauses.append("(platform = ? OR platform IS NULL)"); params.append(platform)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.conn.execute(f"SELECT * FROM reference_records {where} ORDER BY performance_score DESC LIMIT ?", [*params, limit]).fetchall()
        return [self._row(r) for r in rows]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM reference_records").fetchone()[0])

    @staticmethod
    def _row(r):
        import json
        d = dict(r); d["metadata"] = json.loads(d.pop("metadata_json")); return ReferenceRecord(**d)

    def close(self): self.conn.close()
