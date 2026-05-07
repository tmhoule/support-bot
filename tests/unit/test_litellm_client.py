import pytest
from app.llm.litellm_client import LiteLLMClient


@pytest.mark.asyncio
async def test_embed_returns_vectors(httpx_mock):
    httpx_mock.add_response(
        url="https://litellm.test/embeddings",
        json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]},
    )
    client = LiteLLMClient(base_url="https://litellm.test", api_key="k", chat_model="c", embedding_model="e")
    out = await client.embed(["hello", "world"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_chat_streams_deltas(httpx_mock):
    sse_body = (
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        b'data: [DONE]\n\n'
    )
    httpx_mock.add_response(url="https://litellm.test/chat/completions", content=sse_body, headers={"content-type": "text/event-stream"})
    client = LiteLLMClient(base_url="https://litellm.test", api_key="k", chat_model="c", embedding_model="e")
    chunks = []
    async for delta in client.stream_chat(messages=[{"role": "user", "content": "hi"}], tools=[]):
        chunks.append(delta)
    assert "".join(c.text for c in chunks if c.text) == "Hello"
