import asyncio
import json
from fastapi import APIRouter, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from app.db.session import session_scope
from app.db.repository import ConversationRepository

router = APIRouter()
templates = Jinja2Templates(directory="templates")
_stream_queues: dict[str, asyncio.Queue] = {}
_pending_messages: dict[str, str] = {}


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
async def post_message(conversation_id: str, text: str = Form(...)):
    _pending_messages[conversation_id] = text
    return HTMLResponse(f'<div class="msg msg-user"><div class="role">user</div><div class="content">{text}</div></div>')


@router.get("/chat/{conversation_id}/stream")
async def stream(conversation_id: str, request: Request):
    text = _pending_messages.pop(conversation_id, None)
    if text is None:
        async def empty():
            yield {"event": "token", "data": ""}
        return EventSourceResponse(empty())

    from app.main import build_orchestrator
    orch = build_orchestrator()

    async def gen():
        try:
            async for tok in orch.handle_message(conversation_id, text):
                yield {"event": "token", "data": tok}
        finally:
            yield {"event": "done", "data": ""}

    return EventSourceResponse(gen())
