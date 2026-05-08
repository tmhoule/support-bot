import pytest
from pathlib import Path
from app.uploads import (
    save_upload,
    read_upload_text,
    render_uploads_for_prompt,
    MAX_FILE_BYTES,
)


class FakeUploadFile:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self):
        return self._content


class FakeMsg:
    def __init__(self, role: str, content_json: dict):
        self.role = role
        self.content_json = content_json


@pytest.mark.asyncio
async def test_save_upload_writes_file_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    info = await save_upload("convo123", "app.log", FakeUploadFile(b"hello world"))
    assert info["filename"] == "app.log"
    assert info["size"] == 11
    full = tmp_path / info["path"]
    assert full.exists()
    assert full.read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_upload_rejects_unknown_extension(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="not allowed"):
        await save_upload("c1", "binary.exe", FakeUploadFile(b"\x00" * 10))


@pytest.mark.asyncio
async def test_save_upload_rejects_oversize(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    big = b"x" * (MAX_FILE_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        await save_upload("c1", "huge.log", FakeUploadFile(big))


@pytest.mark.asyncio
async def test_save_upload_sanitizes_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    info = await save_upload("c1", "../../etc/passwd.log", FakeUploadFile(b"x"))
    assert "/" not in info["filename"]
    assert ".." not in info["filename"]
    assert info["filename"].endswith(".log")


def test_read_upload_text_truncates(tmp_path):
    p = tmp_path / "big.log"
    p.write_bytes(b"a" * 1000)
    out = read_upload_text(p, max_bytes=100)
    assert "[truncated]" in out


def test_render_uploads_concatenates_and_caps(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    udir = tmp_path / "uploads" / "c1"
    udir.mkdir(parents=True)
    (udir / "20260508T000000-a.log").write_text("AAA")
    (udir / "20260508T000001-b.log").write_text("BBB")
    msgs = [
        FakeMsg("user", {"text": "hi"}),
        FakeMsg("upload", {"filename": "a.log", "path": "uploads/c1/20260508T000000-a.log", "size": 3}),
        FakeMsg("upload", {"filename": "b.log", "path": "uploads/c1/20260508T000001-b.log", "size": 3}),
    ]
    out = render_uploads_for_prompt(msgs)
    assert "a.log" in out and "AAA" in out
    assert "b.log" in out and "BBB" in out


def test_render_uploads_skips_missing_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    msgs = [
        FakeMsg("upload", {"filename": "ghost.log", "path": "uploads/c1/missing.log", "size": 0}),
    ]
    assert render_uploads_for_prompt(msgs) == ""
