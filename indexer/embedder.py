from dataclasses import dataclass
from typing import Protocol
from indexer.chunker import Chunk


class Embedder(Protocol):
    async def embed(self, inputs: list[str]) -> list[list[float]]: ...


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float]


async def embed_chunks(chunks: list[Chunk], *, llm: Embedder, batch_size: int = 32) -> list[EmbeddedChunk]:
    out: list[EmbeddedChunk] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vecs = await llm.embed([c.text for c in batch])
        out.extend(EmbeddedChunk(chunk=c, embedding=v) for c, v in zip(batch, vecs))
    return out
