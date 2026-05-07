import pytest
from app.web_search.base import SearchResult, WebSearchClient


class FakeBackend(WebSearchClient):
    def __init__(self, allowed_domains, results):
        super().__init__(allowed_domains=allowed_domains)
        self._results = results

    async def _query_backend(self, text, max_results):
        return self._results


@pytest.mark.asyncio
async def test_allowlist_filters_results():
    raw = [
        SearchResult(title="Good", url="https://learn.microsoft.com/x", snippet=""),
        SearchResult(title="Bad", url="https://random-blog.example.com/y", snippet=""),
    ]
    client = FakeBackend(allowed_domains=["learn.microsoft.com"], results=raw)
    out = await client.query("anything")
    assert [r.url for r in out] == ["https://learn.microsoft.com/x"]


@pytest.mark.asyncio
async def test_empty_allowlist_returns_nothing():
    client = FakeBackend(allowed_domains=[], results=[SearchResult(title="x", url="https://x.com/", snippet="")])
    assert await client.query("q") == []
