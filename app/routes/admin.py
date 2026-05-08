"""Admin pages — fully open in v1.

No authentication: same trust model as the chat UI (network-trusted, anonymous).
Will be gated by NetIQ SAML at the proxy layer when that integration lands.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.db.session import session_scope
from app.db.repository import ConversationRepository
from indexer.watermark import WatermarkStore
from app.retrieval.chroma_client import ChromaIndex

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("/conversations", response_class=HTMLResponse)
async def conversations(request: Request, name: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    with session_scope() as s:
        repo = ConversationRepository(s)
        rows = repo.list_conversations(limit=limit, offset=offset, name_filter=name)
        return templates.TemplateResponse(
            request,
            "admin/conversations.html",
            {"rows": rows, "name": name or "", "limit": limit, "offset": offset},
        )


@router.get("/conversations/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail(conversation_id: str, request: Request):
    with session_scope() as s:
        repo = ConversationRepository(s)
        convo = repo.get_conversation(conversation_id)
        if not convo:
            raise HTTPException(404)
        msgs = []
        for m in repo.list_messages(conversation_id):
            msgs.append({"role": m.role, "created_at": m.created_at.isoformat(), "body": json.dumps(m.content_json, indent=2)})
        return templates.TemplateResponse(request, "admin/conversation_detail.html", {"convo": convo, "msgs": msgs})


@router.get("/indexer-status", response_class=HTMLResponse)
async def indexer_status(request: Request):
    settings = get_settings()
    wm = WatermarkStore(Path(settings.data_dir) / "watermarks.json")
    chroma = ChromaIndex(persist_dir=f"{settings.data_dir}/chroma")
    return templates.TemplateResponse(request, "admin/indexer_status.html", {"watermarks": wm.all(), "chroma_count": chroma.count()})
