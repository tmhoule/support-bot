from dataclasses import dataclass
from pathlib import Path
import chromadb


@dataclass
class RetrievedChunk:
    id: str
    document: str
    metadata: dict
    distance: float


class ChromaIndex:
    COLLECTION = "docs"

    def __init__(self, persist_dir: str):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._coll = self._client.get_or_create_collection(self.COLLECTION)

    def upsert_batch(self, *, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        self._coll.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def delete_by_path(self, path: str) -> None:
        self._coll.delete(where={"path": path})

    def delete_ids(self, ids: list[str]) -> None:
        if ids:
            self._coll.delete(ids=ids)

    def count(self) -> int:
        return self._coll.count()

    def search(self, *, query_embedding: list[float], top_k: int = 8, source_filter: str | None = None) -> list[RetrievedChunk]:
        where = {"source": source_filter} if source_filter else None
        res = self._coll.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
        ids = res.get("ids", [[]])[0]
        if not ids:
            return []
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        return [RetrievedChunk(id=i, document=d, metadata=m, distance=dist) for i, d, m, dist in zip(ids, docs, metas, dists)]


class ChromaRetriever:
    """Adapter that does query-time embedding then vector search."""

    def __init__(self, index: "ChromaIndex", llm):
        self.index = index
        self.llm = llm

    async def retrieve(self, query: str, top_k: int = 8) -> list[RetrievedChunk]:
        [vec] = await self.llm.embed([query])
        return self.index.search(query_embedding=vec, top_k=top_k)
