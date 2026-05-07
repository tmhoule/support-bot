from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from indexer.chunker import chunk_markdown, Chunk
from indexer.embedder import embed_chunks
from indexer.git_source import GitSource
from indexer.watermark import WatermarkStore
from app.retrieval.chroma_client import ChromaIndex


@dataclass
class RunSummary:
    docs_seen: int
    chunks_upserted: int
    deleted_paths: int
    sha: str


def _chunk_id(path: str, char_start: int) -> str:
    return f"github::{path}::{char_start}"


class IndexRun:
    SOURCE = "github"

    def __init__(self, *, git_source: GitSource, llm, index: ChromaIndex, watermarks: WatermarkStore):
        self.git = git_source
        self.llm = llm
        self.index = index
        self.wm = watermarks

    async def execute(self) -> RunSummary:
        try:
            md_paths = self.git.sync_and_list_md()
            workdir = Path(self.git.workdir)

            seen_paths: set[str] = set()
            all_chunks: list[Chunk] = []
            for p in md_paths:
                rel = p.relative_to(workdir).as_posix()
                seen_paths.add(rel)
                content = p.read_text(encoding="utf-8", errors="replace")
                all_chunks.extend(chunk_markdown(content, source_path=rel))

            embedded = await embed_chunks(all_chunks, llm=self.llm)
            ids = [_chunk_id(e.chunk.source_path, e.chunk.char_start) for e in embedded]
            docs = [e.chunk.text for e in embedded]
            metas = [
                {
                    "source": self.SOURCE,
                    "path": e.chunk.source_path,
                    "title_path": e.chunk.title_path,
                    "char_start": e.chunk.char_start,
                }
                for e in embedded
            ]
            self.index.upsert_batch(ids=ids, embeddings=[e.embedding for e in embedded], documents=docs, metadatas=metas)

            sha = self.git.head_sha()
            self.wm.set(self.SOURCE, datetime.now(UTC), sha=sha)
            return RunSummary(docs_seen=len(seen_paths), chunks_upserted=len(ids), deleted_paths=0, sha=sha)
        except Exception as exc:
            self.wm.record_failure(self.SOURCE, repr(exc))
            raise
