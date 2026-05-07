import re
from dataclasses import dataclass


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
