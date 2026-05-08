"""Per-conversation file uploads (logs, text dumps).

Files land at `{DATA_DIR}/uploads/{conversation_id}/{ts}-{safe_name}`. The orchestrator
reads them on each turn and includes their contents in the prompt as a system block.
"""

import re
from datetime import datetime, UTC
from pathlib import Path
from app.config import get_settings


ALLOWED_EXT = {
    ".log", ".txt", ".csv", ".json", ".xml", ".yaml", ".yml",
    ".conf", ".cfg", ".ini", ".err", ".out", ".md", ".tsv",
}
MAX_FILE_BYTES = 1_000_000          # 1 MB per file
MAX_PROMPT_BYTES_PER_FILE = 60_000  # truncate any single file past this when feeding to LLM
MAX_TOTAL_PROMPT_BYTES = 100_000    # cap the combined upload block per turn


def _sanitize(name: str) -> str:
    """Strip path components and dangerous chars; keep something reasonable."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")[:100]
    return cleaned or "file"


def upload_dir(conversation_id: str) -> Path:
    return Path(get_settings().data_dir) / "uploads" / conversation_id


async def save_upload(conversation_id: str, filename: str, file_obj) -> dict:
    """Save an uploaded file. Returns metadata dict suitable for persisting as a message.

    Raises ValueError on disallowed extension or oversize content.
    """
    safe = _sanitize(filename or "upload")
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"file type {ext or '(none)'} not allowed")

    data = await file_obj.read()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"file too large ({len(data)} bytes; max {MAX_FILE_BYTES})")

    udir = upload_dir(conversation_id)
    udir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    target = udir / f"{ts}-{safe}"
    target.write_bytes(data)

    settings = get_settings()
    return {
        "filename": safe,
        "path": str(target.relative_to(settings.data_dir)),
        "size": len(data),
    }


def read_upload_text(path: Path, max_bytes: int = MAX_PROMPT_BYTES_PER_FILE) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        return raw[:max_bytes].decode("utf-8", errors="replace") + "\n... [truncated]"
    return raw.decode("utf-8", errors="replace")


def list_upload_files(conversation_id: str) -> list[dict]:
    """Return upload metadata for a conversation. Disk-scoped — never crosses into other conversations.

    Each entry: {"filename", "size", "uploaded_at", "_path": Path}.
    """
    udir = upload_dir(conversation_id)
    if not udir.exists():
        return []
    out: list[dict] = []
    for p in sorted(udir.iterdir()):
        if not p.is_file():
            continue
        ts, _, original = p.name.partition("-")
        out.append({
            "filename": original or p.name,
            "size": p.stat().st_size,
            "uploaded_at": ts if original else "",
            "_path": p,
        })
    return out


def read_upload_by_filename(conversation_id: str, filename: str, *, max_bytes: int = MAX_PROMPT_BYTES_PER_FILE) -> dict:
    """Read an upload by display filename, scoped to this conversation only.

    Returns either {"filename", "content", "size", "truncated"} on success
    or {"error", "available"} if the file isn't found in this conversation.
    The lookup matches against the directory listing of `{DATA_DIR}/uploads/{conversation_id}/`,
    so path-traversal arguments cannot escape the scope.
    """
    files = list_upload_files(conversation_id)
    for f in files:
        if f["filename"] == filename:
            content = read_upload_text(f["_path"], max_bytes=max_bytes)
            return {
                "filename": filename,
                "content": content,
                "size": f["size"],
                "truncated": f["size"] > max_bytes,
            }
    return {"error": f"file not found: {filename}", "available": [f["filename"] for f in files]}
