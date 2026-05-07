import re
from dataclasses import dataclass
from html import escape as _html_escape


BANNER = "⚠️ This answer is not backed by your documentation — verify before acting."

_GITHUB_CITE = re.compile(r"\[github:([^\]\s]+)\]")
_URL_CITE = re.compile(r"\[(https?://[^\]\s]+)\]")
_KB_CITE = re.compile(r"\[(KB\d{5,})\]", re.IGNORECASE)
_QUESTION_OR_GREETING = re.compile(r"\b(hi|hello|hey|how can i help|what (is|are)|could you|please)\b", re.IGNORECASE)
_FACTUAL_HINT = re.compile(r"\b(use|requires?|set|enable|disable|run|check|edit|configure|port|service|policy|GPO|registry)\b", re.IGNORECASE)


@dataclass
class Citation:
    kind: str
    ref: str


def extract_citations(text: str) -> list[Citation]:
    cites: list[Citation] = []
    for m in _GITHUB_CITE.finditer(text):
        cites.append(Citation(kind="github", ref=m.group(1)))
    for m in _URL_CITE.finditer(text):
        cites.append(Citation(kind="url", ref=m.group(1)))
    for m in _KB_CITE.finditer(text):
        cites.append(Citation(kind="kb", ref=m.group(1).upper()))
    return cites


def needs_warning_banner(text: str) -> bool:
    if extract_citations(text):
        return False
    if _QUESTION_OR_GREETING.search(text) and not _FACTUAL_HINT.search(text):
        return False
    return bool(_FACTUAL_HINT.search(text))


def _normalize_repo_url(repo_url: str) -> str:
    base = repo_url.strip()
    if base.endswith(".git"):
        base = base[:-4]
    return base.rstrip("/")


def render_inline_citations_html(escaped_text: str, *, github_repo_url: str, branch: str = "main") -> str:
    """Replace [github:...], [https://...], [KB...] markers with anchor tags.

    Input must already be HTML-escaped — this function only inserts our own anchor markup.
    """
    base = _normalize_repo_url(github_repo_url)

    def gh(m):
        path = m.group(1)
        return f'<a href="{base}/blob/{branch}/{path}" target="_blank" rel="noopener">github:{path}</a>'

    def url(m):
        href = m.group(1)
        return f'<a href="{href}" target="_blank" rel="noopener">{href}</a>'

    def kb(m):
        ref = m.group(1).upper()
        return f'<span class="cite-kb">{ref}</span>'

    s = _GITHUB_CITE.sub(gh, escaped_text)
    s = _URL_CITE.sub(url, s)
    s = _KB_CITE.sub(kb, s)
    return s


class CitationStreamRewriter:
    """Buffers raw model tokens, holds back unclosed '[' until the matching ']' arrives,
    then emits HTML-escaped text with citation links rendered."""

    def __init__(self, *, github_repo_url: str, branch: str = "main"):
        self.github_repo_url = github_repo_url
        self.branch = branch
        self._buffer = ""

    def feed(self, raw: str) -> str:
        self._buffer += raw
        last_open = self._buffer.rfind("[")
        last_close = self._buffer.rfind("]")
        if last_open > last_close:
            safe_raw = self._buffer[:last_open]
            self._buffer = self._buffer[last_open:]
        else:
            safe_raw = self._buffer
            self._buffer = ""
        return self._render(safe_raw)

    def flush(self) -> str:
        out = self._render(self._buffer)
        self._buffer = ""
        return out

    def _render(self, raw: str) -> str:
        if not raw:
            return ""
        escaped = _html_escape(raw).replace("\n", "<br>")
        return render_inline_citations_html(escaped, github_repo_url=self.github_repo_url, branch=self.branch)
