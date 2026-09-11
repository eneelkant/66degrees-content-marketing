from datetime import datetime, timezone
from core.reference_library.models import ReferenceRecord
from core.reference_library.sqlite_client import SQLiteReferenceClient
from core.reference_library.hybrid_retriever import HybridRetriever

def make_db(tmp_path): return SQLiteReferenceClient(tmp_path / "references.db")

def test_sqlite_seed_and_search(tmp_path):
    db = make_db(tmp_path)
    db.upsert(ReferenceRecord(id="1", title="Agentic Enterprise", content="production AI", source="66degrees", industry="Healthcare", performance_score=.8))
    assert db.count() == 1
    assert len(db.search(industry="Healthcare")) == 1

def test_hybrid_formula_and_ranking(tmp_path):
    db = make_db(tmp_path)
    for i, perf in [("a", .9), ("b", .6), ("c", .2)]:
        db.upsert(ReferenceRecord(id=i, title=i, content=i, source="x", performance_score=perf, semantic_similarity=.5))
    r = HybridRetriever(db)
    ranked = r.retrieve("query", top_k=3)
    assert [x.record.id for x in ranked] == ["a", "b", "c"]
    assert abs(ranked[0].score - (.4*.5 + .5*.9 + .1*.5)) < 1e-9

def test_competitor_context_is_guardrailed(tmp_path):
    db = make_db(tmp_path)
    db.upsert(ReferenceRecord(id="c", title="Competitor angle", content="competitor positioning", source="competitor", source_type="competitor", authority_level="inspiration"))
    text = HybridRetriever(db).competitor_context(db.search())
    assert text.startswith("<competitor_inspiration>")
    assert "Do not copy language" in text
    assert text.endswith("</competitor_inspiration>")
