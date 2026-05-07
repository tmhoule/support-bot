from app.web_search.base import WebSearchClient, SearchResult


class NoopClient(WebSearchClient):
    async def _query_backend(self, text: str, max_results: int) -> list[SearchResult]:
        return []
