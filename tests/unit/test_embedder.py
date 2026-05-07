import pytest
from indexer.embedder import embed_chunks
from indexer.chunker import Chunk


class FakeLLM:
    def __init__(self):
        self.calls = []

    async def embed(self, inputs):
        self.calls.append(list(inputs))
        return [[float(i)] for i, _ in enumerate(inputs)]


@pytest.mark.asyncio
async def test_embed_chunks_batches_inputs():
    llm = FakeLLM()
    chunks = [Chunk(text=f"t{i}", title_path="T", source_path="a.md", char_start=i) for i in range(5)]
    out = await embed_chunks(chunks, llm=llm, batch_size=2)
    assert len(out) == 5
    assert llm.calls == [["t0", "t1"], ["t2", "t3"], ["t4"]]
    assert out[0].embedding == [0.0]
