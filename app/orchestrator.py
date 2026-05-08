import json
from dataclasses import dataclass
from typing import AsyncIterator, Protocol
from app.citations import needs_warning_banner, BANNER, extract_citations
from app.db.repository import ConversationRepository
from app.tools.registry import Tool, ToolRegistry
from app.retrieval.chroma_client import RetrievedChunk
from app.retrieval.query_expansion import expand_query
from app.uploads import list_upload_files, read_upload_by_filename


SYSTEM_PROMPT = """You are a tier-1 IT support assistant. Answer ONLY using:
1. The retrieved documentation chunks provided in the context.
2. Tool results returned during this conversation.

Available tools:
- web_search(query): vetted external documentation search.
- list_uploads(): list any log/config files the technician attached in THIS conversation.
- read_upload(filename): read the contents of one of those uploaded files.

When the technician describes a specific error, slowness, or misconfiguration, call list_uploads() first to see if they've shared a relevant log, then read_upload() to inspect it before answering.

Rules:
- Cite every factual claim with the doc path or URL it came from, in square brackets, e.g. [github:security/patching.md] or [https://learn.microsoft.com/...].
- If the documentation does not cover the question, say "I don't have documentation on that — here's where to look:" and suggest concrete next steps (logs, tools, escalation).
- Prefer "I don't know" over guessing.
- Be concise; technicians are time-pressed.
"""


class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int = 8) -> list[RetrievedChunk]: ...


class LLM(Protocol):
    async def embed(self, inputs: list[str]) -> list[list[float]]: ...
    def stream_chat(self, *, messages: list[dict], tools: list[dict]): ...


@dataclass
class _ToolCallAccum:
    id: str = ""
    name: str = ""
    args: str = ""


class ChatOrchestrator:
    MAX_TOOL_ROUNDS = 5
    TOP_K_PER_QUERY = 15
    FINAL_CHUNK_CAP = 20

    def __init__(self, *, repo: ConversationRepository, llm: LLM, retriever: Retriever, tools: ToolRegistry, expand_queries: bool = True):
        self.repo = repo
        self.llm = llm
        self.retriever = retriever
        self.tools = tools
        self.expand_queries = expand_queries

    async def _retrieve_for(self, user_text: str) -> list[RetrievedChunk]:
        queries = await expand_query(user_text, self.llm) if self.expand_queries else [user_text]
        best_by_id: dict[str, RetrievedChunk] = {}
        for q in queries:
            for chunk in await self.retriever.retrieve(q, top_k=self.TOP_K_PER_QUERY):
                existing = best_by_id.get(chunk.id)
                if existing is None or chunk.distance < existing.distance:
                    best_by_id[chunk.id] = chunk
        return sorted(best_by_id.values(), key=lambda c: c.distance)[: self.FINAL_CHUNK_CAP]

    def _build_request_tools(self, conversation_id: str) -> ToolRegistry:
        """Build a per-request ToolRegistry that adds upload tools scoped to THIS conversation.

        The upload tool handlers close over `conversation_id`, so they can only see
        files in `{DATA_DIR}/uploads/{conversation_id}/`. Cross-conversation reads
        are impossible regardless of what arguments the model passes.
        """
        reg = ToolRegistry()
        for t in self.tools:
            reg.register(t)

        async def list_uploads_handler() -> dict:
            files = list_upload_files(conversation_id)
            return {"files": [{"filename": f["filename"], "size": f["size"], "uploaded_at": f["uploaded_at"]} for f in files]}

        async def read_upload_handler(filename: str, max_bytes: int = 60_000) -> dict:
            return read_upload_by_filename(conversation_id, filename, max_bytes=max_bytes)

        reg.register(Tool(
            name="list_uploads",
            description="List files the technician uploaded in this conversation. Returns {files: [{filename, size, uploaded_at}, ...]}. Call this before answering any question that might involve a log or config file.",
            parameters_schema={"type": "object", "properties": {}, "required": []},
            handler=list_uploads_handler,
        ))
        reg.register(Tool(
            name="read_upload",
            description="Read the contents of an uploaded file in this conversation. Use list_uploads first to see filenames. Returns {filename, content, size, truncated} or {error, available}.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Exact filename from list_uploads"},
                    "max_bytes": {"type": "integer", "default": 60000, "description": "Max bytes to return; content is truncated past this."},
                },
                "required": ["filename"],
            },
            handler=read_upload_handler,
        ))
        return reg

    async def handle_message(self, conversation_id: str, user_text: str) -> AsyncIterator[str]:
        self.repo.add_message(conversation_id, role="user", content={"type": "text", "text": user_text})

        chunks = await self._retrieve_for(user_text)
        context_block = self._render_context(chunks)
        prior = self.repo.list_messages(conversation_id)
        messages = self._build_messages(prior, context_block, user_text)
        request_tools = self._build_request_tools(conversation_id)

        full_text_parts: list[str] = []
        rounds = 0
        while rounds < self.MAX_TOOL_ROUNDS:
            rounds += 1
            tool_calls: list[_ToolCallAccum] = []
            assistant_text = ""
            finish_reason = None
            async for delta in self.llm.stream_chat(messages=messages, tools=request_tools.openai_tool_schemas()):
                if delta.text:
                    assistant_text += delta.text
                    full_text_parts.append(delta.text)
                    yield delta.text
                if delta.tool_call:
                    self._accum_tool_call(tool_calls, delta.tool_call)
                if delta.finish_reason:
                    finish_reason = delta.finish_reason
            if tool_calls:
                messages.append({"role": "assistant", "content": assistant_text or None, "tool_calls": [self._tool_call_msg(tc) for tc in tool_calls]})
                for tc in tool_calls:
                    args = json.loads(tc.args or "{}")
                    try:
                        result = await request_tools.invoke(tc.name, args)
                    except Exception as exc:
                        result = {"error": repr(exc)}
                    self.repo.add_message(conversation_id, role="tool", content={"type": "tool_call", "name": tc.name, "args": args, "result": result})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
                continue
            break

        full_text = "".join(full_text_parts)
        if needs_warning_banner(full_text):
            yield "\n\n" + BANNER
            full_text = full_text + "\n\n" + BANNER

        cites = extract_citations(full_text)
        self.repo.add_message(conversation_id, role="assistant", content={"type": "model_response", "text": full_text, "citations": [c.__dict__ for c in cites]})

    @staticmethod
    def _accum_tool_call(buf: list[_ToolCallAccum], delta_tc: dict) -> None:
        idx = delta_tc.get("index", 0)
        while len(buf) <= idx:
            buf.append(_ToolCallAccum())
        slot = buf[idx]
        if delta_tc.get("id"):
            slot.id = delta_tc["id"]
        fn = delta_tc.get("function", {})
        if fn.get("name"):
            slot.name = fn["name"]
        if fn.get("arguments") is not None:
            slot.args += fn["arguments"]

    @staticmethod
    def _tool_call_msg(tc: _ToolCallAccum) -> dict:
        return {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.args}}

    @staticmethod
    def _render_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "(no relevant documentation chunks retrieved)"
        lines = []
        for c in chunks:
            cite = f"github:{c.metadata['path']}" if c.metadata.get("source") == "github" else c.metadata.get("path", c.id)
            lines.append(f"[{cite}] ({c.metadata.get('title_path', '')})\n{c.document}\n")
        return "\n---\n".join(lines)

    @staticmethod
    def _build_messages(prior, context_block: str, user_text: str) -> list[dict]:
        # `prior` already contains the just-saved user message at the end (added before this call),
        # so the loop carries the full transcript including the current turn — no extra append.
        msgs: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Retrieved context:\n{context_block}"},
        ]
        for m in prior:
            if m.role == "user":
                msgs.append({"role": "user", "content": m.content_json.get("text", "")})
            elif m.role == "assistant" and m.content_json.get("type") == "model_response":
                msgs.append({"role": "assistant", "content": m.content_json.get("text", "")})
        return msgs
