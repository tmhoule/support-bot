import pytest
from app.llm.litellm_client import StreamDelta
from app.retrieval.query_expansion import expand_query


class FakeLLM:
    def __init__(self, body: str):
        self._body = body

    async def stream_chat(self, *, messages, tools):
        yield StreamDelta(text=self._body)
        yield StreamDelta(finish_reason="stop")


@pytest.mark.asyncio
async def test_expansion_parses_json_array():
    llm = FakeLLM('["proxy server configuration", "PAC file", "outbound network policy"]')
    out = await expand_query("internet doesn't work", llm)
    assert out[0] == "internet doesn't work"
    assert "proxy server configuration" in out
    assert len(out) == 4


@pytest.mark.asyncio
async def test_expansion_strips_code_fences():
    llm = FakeLLM('```json\n["a", "b", "c"]\n```')
    out = await expand_query("q", llm)
    assert out == ["q", "a", "b", "c"]


@pytest.mark.asyncio
async def test_expansion_falls_back_on_bad_json():
    llm = FakeLLM("not json at all")
    out = await expand_query("q", llm)
    assert out == ["q"]


@pytest.mark.asyncio
async def test_expansion_caps_extras():
    llm = FakeLLM('["1", "2", "3", "4", "5"]')
    out = await expand_query("q", llm, max_extras=2)
    assert out == ["q", "1", "2"]
