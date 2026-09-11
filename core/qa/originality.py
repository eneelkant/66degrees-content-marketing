from typing import Any, Iterable
from .hard_constraints import _flatten_text
from .models import QACheck, QAState

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - dependency is installed in normal QA environments
    fuzz = None


class OriginalityAnalyzer:
    """Two-tier corpus similarity: RapidFuzz lexical matching, then optional Chroma semantic distance."""

    def __init__(self, semantic_search=None, *, warning_threshold: float = 0.55, rewrite_threshold: float = 0.75):
        self.semantic_search = semantic_search
        self.warning_threshold = warning_threshold
        self.rewrite_threshold = rewrite_threshold

    @staticmethod
    def _lexical_similarity(candidate: str, reference: str) -> float:
        if fuzz is None:
            # Conservative fallback for environments that have not installed the QA extra.
            a = set(candidate.lower().split())
            b = set(reference.lower().split())
            return len(a & b) / max(1, len(a | b))
        return fuzz.token_set_ratio(candidate, reference) / 100.0

    def analyze(self, content: Any, references: Iterable[dict[str, Any]] = ()) -> QACheck:
        candidate = _flatten_text(content).strip()
        refs = list(references)
        if not refs:
            return QACheck(
                name="originality",
                state=QAState.WARNING,
                message="No internal reference corpus was available for originality comparison.",
                details={"lexical_similarity": 0.0, "semantic_similarity": None, "references_checked": 0},
            )

        lexical_matches = []
        for ref in refs:
            ref_text = str(ref.get("content", ""))
            score = self._lexical_similarity(candidate, ref_text)
            lexical_matches.append({"id": ref.get("id"), "title": ref.get("title"), "score": score})
        lexical_matches.sort(key=lambda x: x["score"], reverse=True)
        best_lexical = lexical_matches[0]["score"]

        semantic_similarity = None
        semantic_match = None
        if self.semantic_search:
            result = self.semantic_search(candidate, refs)
            if result:
                semantic_match = max(result, key=lambda x: x.get("similarity", 0.0))
                semantic_similarity = semantic_match.get("similarity")

        combined = best_lexical if semantic_similarity is None else max(best_lexical, float(semantic_similarity))
        if combined >= self.rewrite_threshold:
            state = QAState.REWRITE
        elif combined >= self.warning_threshold:
            state = QAState.WARNING
        else:
            state = QAState.PASS

        return QACheck(
            name="originality",
            state=state,
            message={QAState.PASS: "No material similarity risk detected.", QAState.WARNING: "Similarity warrants human review.", QAState.REWRITE: "Similarity is high; rewrite before approval."}[state],
            details={
                "lexical_similarity": best_lexical,
                "semantic_similarity": semantic_similarity,
                "combined_similarity": combined,
                "top_lexical_matches": lexical_matches[:3],
                "semantic_match": semantic_match,
                "references_checked": len(refs),
            },
        )
