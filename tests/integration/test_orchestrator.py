import json
import pytest
from app.orchestrator import ChatOrchestrator
from app.tools.registry import ToolRegistry, Tool
from app.llm.litellm_client import StreamDelta
from app.db.repository import ConversationRepository
from app.retrieval.chroma_client import RetrievedChunk


class FakeLLM:
    def __init__(self, scripts):
        self._scripts = list(scripts)
        self.embed_calls = []

    async def embed(self, inputs):
        self.embed_calls.append(list(inputs))
        return [[1.0, 0.0] for _ in inputs]

    async def stream_chat(self, *, messages, tools):
        for delta in self._scripts.pop(0):
            yield delta


class FakeIndex:
    async def retrieve(self, query: str, top_k: int = 8):
        return [RetrievedChunk(id="1", document="patching is weekly", metadata={"source": "github", "path": "security/patching.md", "title_path": "Patching Policy > Cadence"}, distance=0.1)]


@pytest.mark.asyncio
async def test_simple_text_response_persisted(db_session):
    repo = ConversationRepository(db_session)
    convo = repo.create_conversation(tech_name="Alice")

    scripts = [[StreamDelta(text="Tier-1 servers are patched weekly "), StreamDelta(text="[github:security/patching.md]."), StreamDelta(finish_reason="stop")]]
    llm = FakeLLM(scripts)
    tools = ToolRegistry()

    orch = ChatOrchestrator(repo=repo, llm=llm, retriever=FakeIndex(), tools=tools, expand_queries=False)
    out = []
    async for tok in orch.handle_message(convo.id, "What's the patching cadence?"):
        out.append(tok)
    full = "".join(out)
    assert "weekly" in full
    msgs = repo.list_messages(convo.id)
    roles = [m.role for m in msgs]
    assert "user" in roles and "assistant" in roles


@pytest.mark.asyncio
async def test_no_citation_factual_gets_banner(db_session):
    repo = ConversationRepository(db_session)
    convo = repo.create_conversation(tech_name="Bob")
    scripts = [[StreamDelta(text="RDP requires port 3389 to be open."), StreamDelta(finish_reason="stop")]]
    orch = ChatOrchestrator(repo=repo, llm=FakeLLM(scripts), retriever=FakeIndex(), tools=ToolRegistry(), expand_queries=False)
    out = []
    async for tok in orch.handle_message(convo.id, "Tell me about RDP"):
        out.append(tok)
    full = "".join(out)
    assert "verify" in full.lower() or "documentation" in full.lower()


@pytest.mark.asyncio
async def test_tool_call_loop(db_session):
    repo = ConversationRepository(db_session)
    convo = repo.create_conversation(tech_name="Cara")
    tool_registry = ToolRegistry()

    async def echo(query: str) -> dict:
        return {"results": [{"title": "T", "url": "https://learn.microsoft.com/x", "snippet": "snip"}]}

    tool_registry.register(Tool(name="web_search", description="d", parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, handler=echo))

    scripts = [
        [
            StreamDelta(tool_call={"id": "c1", "function": {"name": "web_search", "arguments": json.dumps({"query": "rdp"})}}),
            StreamDelta(finish_reason="tool_calls"),
        ],
        [
            StreamDelta(text="See [https://learn.microsoft.com/x] for details."),
            StreamDelta(finish_reason="stop"),
        ],
    ]
    orch = ChatOrchestrator(repo=repo, llm=FakeLLM(scripts), retriever=FakeIndex(), tools=tool_registry, expand_queries=False)
    full = "".join([t async for t in orch.handle_message(convo.id, "rdp question")])
    assert "learn.microsoft.com" in full
    msgs = repo.list_messages(convo.id)
    tool_msgs = [m for m in msgs if m.role == "tool"]
    assert tool_msgs and tool_msgs[0].content_json["name"] == "web_search"
