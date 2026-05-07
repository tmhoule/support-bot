import httpx
from app.web_search.base import WebSearchClient, SearchResult


class SearxNGClient(WebSearchClient):
    def __init__(self, *, base_url: str, allowed_domains: list[str], timeout: float = 10.0):
        super().__init__(allowed_domains=allowed_domains)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _query_backend(self, text: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(f"{self.base_url}/search", params={"q": text, "format": "json"})
            r.raise_for_status()
            data = r.json()
        return [SearchResult(title=d.get("title", ""), url=d.get("url", ""), snippet=d.get("content", "")) for d in data.get("results", [])]
