from pathlib import Path
from urllib.parse import urlparse, urlunparse
import git


class GitSource:
    def __init__(self, *, repo_url: str, workdir: Path, token: str | None):
        self.repo_url = self._inject_token(repo_url, token) if token else repo_url
        self.workdir = Path(workdir)

    @staticmethod
    def _inject_token(url: str, token: str) -> str:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return url
        netloc = f"x-access-token:{token}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))

    def sync_and_list_md(self) -> list[Path]:
        if not (self.workdir / ".git").exists():
            self.workdir.parent.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(self.repo_url, self.workdir)
        else:
            repo = git.Repo(self.workdir)
            repo.remotes.origin.pull()
        return sorted(p for p in self.workdir.rglob("*.md") if ".git" not in p.parts)

    def head_sha(self) -> str:
        return git.Repo(self.workdir).head.commit.hexsha
