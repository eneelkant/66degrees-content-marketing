from typing import Any


class ChromaSemanticDistanceAdapter:
    """Adapter for an existing Chroma collection configured with the repo's embedding function."""

    def __init__(self, collection):
        self.collection = collection

    def __call__(self, candidate: str, references: list[dict[str, Any]]):
        if not references:
            return []
        ids = [str(r["id"]) for r in references if r.get("id") is not None]
        result = self.collection.query(query_texts=[candidate], n_results=min(len(ids), 10), include=["distances", "metadatas"])
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        matches = []
        for distance, metadata in zip(distances, metadatas):
            metadata = metadata or {}
            # Chroma returns distance, so convert it to a bounded similarity for QA thresholds.
            similarity = 1.0 / (1.0 + float(distance))
            matches.append({"id": metadata.get("id"), "distance": float(distance), "similarity": similarity})
        return matches
