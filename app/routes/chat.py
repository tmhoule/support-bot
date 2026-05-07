import json
import uuid
from html import escape
from fastapi import APIRouter, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from app.db.session import session_scope
from app.db.repository import ConversationRepository
from app.rate_limit import InMemoryRateLimiter
from app.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")
_pending_messages: dict[str, tuple[str, str]] = {}  # turn_id -> (conversation_id, text)
_limiter: InMemoryRateLimiter | None = None


def _get_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = InMemoryRateLimiter(limit_per_min=get_settings().rate_limit_per_min)
    return _limiter


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "name_prompt.html")


@router.post("/chat/start")
async def start_chat(tech_name: str = Form(...)):
    with session_scope() as s:
        repo = ConversationRepository(s)
        convo = repo.create_conversation(tech_name=tech_name.strip()[:80] or "anonymous")
    return RedirectResponse(url=f"/chat/{convo.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/chat/{conversation_id}", response_class=HTMLResponse)
async def chat_page(conversation_id: str, request: Request):
    with session_scope() as s:
        repo = ConversationRepository(s)
        convo = repo.get_conversation(conversation_id)
        if not convo:
            raise HTTPException(404)
        messages = []
        for m in repo.list_messages(conversation_id):
            text = m.content_json.get("text") if m.content_json.get("type") in ("text", "model_response") else json.dumps(m.content_json)
            messages.append({"role": m.role, "text": text})
        return templates.TemplateResponse(
            request,
            "chat.html",
            {"tech_name": convo.tech_name, "conversation_id": conversation_id, "messages": messages},
        )


@router.post("/chat/{conversation_id}/message", response_class=HTMLResponse)
async def post_message(conversation_id: str, request: Request, text: str = Form(...)):
    key = f"{request.client.host}:{conversation_id}"
    if not _get_limiter().check(key):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    turn_id = uuid.uuid4().hex
    _pending_messages[turn_id] = (conversation_id, text)
    safe_text = escape(text).replace("\n", "<br>")
    stream_url = f"/chat/{conversation_id}/stream/{turn_id}"
    return HTMLResponse(
        f'<div class="msg msg-user"><div class="role">user</div>'
        f'<div class="content">{safe_text}</div></div>'
        f'<div class="msg msg-assistant">'
        f'<div class="role">assistant</div>'
        f'<div class="content"'
        f' hx-ext="sse"'
        f' sse-connect="{stream_url}"'
        f' sse-swap="token"'
        f' hx-swap="beforeend"'
        f' sse-close="done"></div></div>'
    )


@router.get("/chat/{conversation_id}/stream/{turn_id}")
async def stream(conversation_id: str, turn_id: str, request: Request):
    pending = _pending_messages.pop(turn_id, None)
    if pending is None:
        async def empty():
            yield {"event": "done", "data": ""}
        return EventSourceResponse(empty())

    _, text = pending
    from app.main import build_orchestrator
    orch = build_orchestrator()

    async def gen():
        try:
            async for tok in orch.handle_message(conversation_id, text):
                yield {"event": "token", "data": escape(tok).replace("\n", "<br>")}
        finally:
            yield {"event": "done", "data": ""}

    return EventSourceResponse(gen())
