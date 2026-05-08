import pytest
from pathlib import Path
from app.uploads import (
    save_upload,
    read_upload_text,
    list_upload_files,
    read_upload_by_filename,
    MAX_FILE_BYTES,
)


class FakeUploadFile:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self):
        return self._content


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


def test_list_upload_files_returns_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    udir = tmp_path / "uploads" / "c1"
    udir.mkdir(parents=True)
    (udir / "20260508T000000-a.log").write_text("AAA")
    (udir / "20260508T000010-b.log").write_text("BBBBB")
    files = list_upload_files("c1")
    by_name = {f["filename"]: f for f in files}
    assert by_name["a.log"]["size"] == 3
    assert by_name["b.log"]["size"] == 5
    assert by_name["a.log"]["uploaded_at"] == "20260508T000000"


def test_list_upload_files_returns_empty_for_unknown_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert list_upload_files("never-existed") == []


def test_read_upload_by_filename_returns_content(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    udir = tmp_path / "uploads" / "c1"
    udir.mkdir(parents=True)
    (udir / "20260508T000000-app.log").write_text("ERROR: connect refused")
    out = read_upload_by_filename("c1", "app.log")
    assert out["filename"] == "app.log"
    assert "ERROR" in out["content"]
    assert out["truncated"] is False


def test_read_upload_by_filename_returns_error_with_available(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    udir = tmp_path / "uploads" / "c1"
    udir.mkdir(parents=True)
    (udir / "20260508T000000-real.log").write_text("x")
    out = read_upload_by_filename("c1", "fake.log")
    assert "error" in out
    assert "real.log" in out["available"]


def test_read_upload_is_scoped_to_conversation(tmp_path, monkeypatch):
    """A read in conversation B must NOT return a file uploaded to conversation A."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    a_dir = tmp_path / "uploads" / "convo-A"
    a_dir.mkdir(parents=True)
    (a_dir / "20260508T000000-secret.log").write_text("PRIVATE_TO_A")
    out = read_upload_by_filename("convo-B", "secret.log")
    assert "error" in out
    assert "PRIVATE_TO_A" not in str(out)


def test_read_upload_path_traversal_attempt_is_ignored(tmp_path, monkeypatch):
    """Even if the model invents a path-traversal filename, it can't escape the conversation dir."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    a_dir = tmp_path / "uploads" / "convo-A"
    a_dir.mkdir(parents=True)
    (a_dir / "20260508T000000-real.log").write_text("data")
    # Caller from convo-B tries traversal-style filenames
    out1 = read_upload_by_filename("convo-B", "../convo-A/20260508T000000-real.log")
    out2 = read_upload_by_filename("convo-B", "../../etc/passwd")
    assert "error" in out1 and "error" in out2
