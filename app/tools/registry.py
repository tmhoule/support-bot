from dataclasses import dataclass
from typing import Awaitable, Callable, Any


@dataclass
class Tool:
    name: str
    description: str
    parameters_schema: dict
    handler: Callable[..., Awaitable[Any]]


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def __iter__(self):
        return iter(self._tools.values())

    def openai_tool_schemas(self) -> list[dict]:
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters_schema}}
            for t in self._tools.values()
        ]

    async def invoke(self, name: str, args: dict) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return await self._tools[name].handler(**args)
