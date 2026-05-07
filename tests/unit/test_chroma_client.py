import pytest
from app.retrieval.chroma_client import ChromaIndex, RetrievedChunk


def test_upsert_and_search(tmp_path):
    idx = ChromaIndex(persist_dir=str(tmp_path / "chroma"))
    idx.upsert_batch(
        ids=["a", "b"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["alpha doc", "beta doc"],
        metadatas=[
            {"source": "github", "path": "a.md", "title_path": "A"},
            {"source": "github", "path": "b.md", "title_path": "B"},
        ],
    )
    hits = idx.search(query_embedding=[1.0, 0.0], top_k=2)
    assert isinstance(hits[0], RetrievedChunk)
    assert hits[0].id == "a"
    assert hits[0].metadata["path"] == "a.md"


def test_delete_removes_ids(tmp_path):
    idx = ChromaIndex(persist_dir=str(tmp_path / "chroma"))
    idx.upsert_batch(ids=["x"], embeddings=[[1.0, 0.0]], documents=["x doc"], metadatas=[{"source": "github", "path": "x.md", "title_path": "X"}])
    idx.delete_by_path("x.md")
    assert idx.search(query_embedding=[1.0, 0.0], top_k=1) == []


def test_count(tmp_path):
    idx = ChromaIndex(persist_dir=str(tmp_path / "chroma"))
    assert idx.count() == 0
    idx.upsert_batch(ids=["x"], embeddings=[[1.0]], documents=["x"], metadatas=[{"source": "github", "path": "x.md", "title_path": "X"}])
    assert idx.count() == 1
