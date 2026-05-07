from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchClient(ABC):
    def __init__(self, *, allowed_domains: list[str]):
        self.allowed_domains = [d.lower().lstrip(".") for d in allowed_domains]

    async def query(self, text: str, max_results: int = 5) -> list[SearchResult]:
        raw = await self._query_backend(text, max_results)
        return [r for r in raw if self._is_allowed(r.url)][:max_results]

    def _is_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        if not host or not self.allowed_domains:
            return False
        return any(host == d or host.endswith("." + d) for d in self.allowed_domains)

    @abstractmethod
    async def _query_backend(self, text: str, max_results: int) -> list[SearchResult]: ...
