import pytest
from app.tools.registry import ToolRegistry, Tool


@pytest.mark.asyncio
async def test_register_and_invoke():
    reg = ToolRegistry()

    async def handler(query: str) -> dict:
        return {"echo": query}

    reg.register(Tool(name="echo", description="echo back", parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, handler=handler))
    schemas = reg.openai_tool_schemas()
    assert schemas[0]["function"]["name"] == "echo"
    out = await reg.invoke("echo", {"query": "hi"})
    assert out == {"echo": "hi"}


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        await reg.invoke("missing", {})
