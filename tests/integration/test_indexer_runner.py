import pytest
from pathlib import Path
from indexer.runner import IndexRun
from indexer.git_source import GitSource
from app.retrieval.chroma_client import ChromaIndex
from indexer.watermark import WatermarkStore


class FakeLLM:
    async def embed(self, inputs):
        return [[float(i), 0.0] for i, _ in enumerate(inputs)]


class StaticGitSource(GitSource):
    def __init__(self, fixture_dir: Path):
        self._fixture = fixture_dir
        self.workdir = fixture_dir

    def sync_and_list_md(self):
        return sorted(p for p in self._fixture.rglob("*.md"))

    def head_sha(self):
        return "fake-sha"


@pytest.mark.asyncio
async def test_full_run_indexes_fixture(tmp_path):
    fixture = Path("tests/fixtures/sample_repo")
    chroma = ChromaIndex(persist_dir=str(tmp_path / "chroma"))
    wm = WatermarkStore(tmp_path / "wm.json")
    src = StaticGitSource(fixture)
    run = IndexRun(git_source=src, llm=FakeLLM(), index=chroma, watermarks=wm)
    summary = await run.execute()
    assert summary.docs_seen == 2
    assert summary.chunks_upserted >= 2
    assert chroma.count() >= 2
    assert wm.get("github") is not None
