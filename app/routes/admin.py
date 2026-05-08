"""Admin pages — fully open in v1.

No authentication: same trust model as the chat UI (network-trusted, anonymous).
Will be gated by NetIQ SAML at the proxy layer when that integration lands.
"""

import json
from html import escape
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.citations import render_inline_citations_html
from app.db.session import session_scope
from app.db.repository import ConversationRepository
from app.uploads import list_upload_files
from indexer.watermark import WatermarkStore
from app.retrieval.chroma_client import ChromaIndex

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def admin_index(request: Request):
    settings = get_settings()
    with session_scope() as s:
        repo = ConversationRepository(s)
        recent = repo.list_conversations(limit=10, offset=0)
    chroma = ChromaIndex(persist_dir=f"{settings.data_dir}/chroma")
    wm = WatermarkStore(Path(settings.data_dir) / "watermarks.json")
    last_run = None
    wm_all = wm.all()
    if wm_all:
        last_run = max((w.last_run for w in wm_all.values() if w), default=None)
    return templates.TemplateResponse(
        request,
        "admin/index.html",
        {
            "recent": recent,
            "chroma_count": chroma.count(),
            "last_indexer_run": last_run,
        },
    )


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


def _tool_call_one_liner(name: str, args: dict, result) -> str:
    """A single short readable line summarizing what a tool call did."""
    if name == "web_search":
        q = args.get("query", "")
        n = len(result.get("results", [])) if isinstance(result, dict) else 0
        return f'web_search("{q}") → {n} result(s)'
    if name == "list_uploads":
        files = result.get("files", []) if isinstance(result, dict) else []
        names = ", ".join(f["filename"] for f in files) if files else "no files"
        return f"list_uploads() → {names}"
    if name == "read_upload":
        f = args.get("filename", "?")
        if isinstance(result, dict) and "content" in result:
            return f'read_upload("{f}") → {result.get("size", 0)} bytes'
        return f'read_upload("{f}") → error'
    return f"{name}(...)"


def _format_entry(m, github_repo_url: str, available_uploads: set[str]) -> dict:
    cj = m.content_json or {}
    ctype = cj.get("type")
    base = {
        "role": m.role,
        "time": m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "type": ctype or "raw",
    }
    if ctype == "text":
        text = escape(cj.get("text", "")).replace("\n", "<br>")
        return {**base, "html": text}
    if ctype == "model_response":
        text = escape(cj.get("text", "")).replace("\n", "<br>")
        text = render_inline_citations_html(text, github_repo_url=github_repo_url)
        cites = cj.get("citations", []) or []
        return {**base, "html": text, "citations": cites, "flagged": cj.get("flagged", False)}
    if ctype == "tool_call":
        name = cj.get("name", "?")
        args = cj.get("args", {}) or {}
        result = cj.get("result", {}) or {}
        return {
            **base,
            "tool_name": name,
            "summary": _tool_call_one_liner(name, args, result),
            "args_pretty": json.dumps(args, indent=2),
            "result_pretty": json.dumps(result, indent=2),
        }
    if ctype == "upload":
        filename = cj.get("filename", "file")
        return {
            **base,
            "filename": filename,
            "size_kb": (cj.get("size") or 0) / 1024,
            "available": filename in available_uploads,
        }
    return {**base, "json": json.dumps(cj, indent=2)}


@router.get("/conversations/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail(conversation_id: str, request: Request):
    settings = get_settings()
    with session_scope() as s:
        repo = ConversationRepository(s)
        convo = repo.get_conversation(conversation_id)
        if not convo:
            raise HTTPException(404)
        available = {f["filename"] for f in list_upload_files(conversation_id)}
        entries = [_format_entry(m, settings.github_repo_url, available) for m in repo.list_messages(conversation_id)]
        return templates.TemplateResponse(request, "admin/conversation_detail.html", {"convo": convo, "entries": entries})


@router.get("/conversations/{conversation_id}/upload/{filename}")
async def admin_download_upload(conversation_id: str, filename: str):
    """Download an uploaded file. Match by display filename within the conversation
    directory — never construct a path from user input, so traversal is impossible."""
    with session_scope() as s:
        if not ConversationRepository(s).get_conversation(conversation_id):
            raise HTTPException(404)
    for f in list_upload_files(conversation_id):
        if f["filename"] == filename:
            return FileResponse(
                path=str(f["_path"]),
                filename=filename,
                media_type="application/octet-stream",
            )
    raise HTTPException(404, detail="file not found (may have been deleted)")


@router.get("/indexer-status", response_class=HTMLResponse)
async def indexer_status(request: Request):
    settings = get_settings()
    wm = WatermarkStore(Path(settings.data_dir) / "watermarks.json")
    chroma = ChromaIndex(persist_dir=f"{settings.data_dir}/chroma")
    return templates.TemplateResponse(request, "admin/indexer_status.html", {"watermarks": wm.all(), "chroma_count": chroma.count()})
