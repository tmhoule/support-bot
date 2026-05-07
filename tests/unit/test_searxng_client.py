import pytest
from app.web_search.searxng import SearxNGClient


@pytest.mark.asyncio
async def test_parses_searxng_response(httpx_mock):
    httpx_mock.add_response(
        url="https://searx.test/search?q=hello&format=json",
        json={"results": [
            {"title": "T1", "url": "https://learn.microsoft.com/a", "content": "snip1"},
            {"title": "T2", "url": "https://learn.microsoft.com/b", "content": "snip2"},
        ]},
    )
    c = SearxNGClient(base_url="https://searx.test", allowed_domains=["learn.microsoft.com"])
    out = await c.query("hello", max_results=2)
    assert [r.title for r in out] == ["T1", "T2"]
    assert out[0].snippet == "snip1"
