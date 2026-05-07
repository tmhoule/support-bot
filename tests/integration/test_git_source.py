import subprocess
from pathlib import Path
from indexer.git_source import GitSource


def _make_remote_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    (work / "README.md").write_text("# Hello\n")
    (work / "guide.md").write_text("# Guide\n## A\nbody\n")
    (work / "image.png").write_bytes(b"\x89PNG\r\n")
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(["git", "-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "clone", "--bare", "-q", str(work), str(remote)], check=True)
    return remote


def test_first_clone_then_pull(tmp_path):
    remote = _make_remote_repo(tmp_path)
    workdir = tmp_path / "checkout"
    src = GitSource(repo_url=str(remote), workdir=workdir, token=None)
    md_files = src.sync_and_list_md()
    paths = sorted(p.relative_to(workdir).as_posix() for p in md_files)
    assert paths == ["README.md", "guide.md"]


def test_skips_non_md(tmp_path):
    remote = _make_remote_repo(tmp_path)
    workdir = tmp_path / "checkout"
    files = GitSource(repo_url=str(remote), workdir=workdir, token=None).sync_and_list_md()
    assert all(p.suffix == ".md" for p in files)
