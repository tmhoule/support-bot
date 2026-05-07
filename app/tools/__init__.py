import json
from app.config import Settings
from app.tools.registry import Tool, ToolRegistry
from app.web_search.base import WebSearchClient
from app.web_search.noop import NoopClient
from app.web_search.searxng import SearxNGClient


def build_web_search(settings: Settings) -> WebSearchClient:
    if settings.web_search_backend == "searxng":
        import os
        return SearxNGClient(base_url=os.environ["SEARXNG_BASE_URL"], allowed_domains=settings.web_search_allowed_domains)
    return NoopClient(allowed_domains=settings.web_search_allowed_domains)


def build_default_registry(settings: Settings) -> ToolRegistry:
    reg = ToolRegistry()
    web = build_web_search(settings)

    async def web_search(query: str, max_results: int = 5) -> dict:
        results = await web.query(query, max_results=max_results)
        return {"results": [r.__dict__ for r in results]}

    reg.register(Tool(
        name="web_search",
        description="Search vetted external documentation. Returns title/url/snippet for top results.",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}},
            "required": ["query"],
        },
        handler=web_search,
    ))
    return reg
