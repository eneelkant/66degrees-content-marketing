class ChromaReferenceClient:
    """Optional ChromaDB adapter using a local sentence-transformers embedding function."""
    def __init__(self, persist_directory: str, collection_name: str = "66degrees_references"):
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        except ImportError as exc:
            raise RuntimeError("ChromaDB integration requires 'chromadb' and 'sentence-transformers'.") from exc
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._embedding = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self._client.get_or_create_collection(collection_name, embedding_function=self._embedding)

    def upsert(self, records):
        self.collection.upsert(ids=[r.id for r in records], documents=[r.content for r in records], metadatas=[{"title": r.title, "source": r.source} for r in records])

    def query(self, text: str, n_results: int = 20):
        return self.collection.query(query_texts=[text], n_results=n_results)
