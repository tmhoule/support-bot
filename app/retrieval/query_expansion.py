"""Generate alternate phrasings of a user question to improve retrieval recall.

Symptom-style questions ("can't get to the internet, internal pages work") share
little vocabulary with system docs ("proxy configuration", "PAC file"). Embedding
similarity misses those links. Asking the LLM to rewrite the question into
documentation-style queries dramatically improves recall on troubleshooting asks.
"""

import json
from typing import Protocol


class _Chatter(Protocol):
    def stream_chat(self, *, messages: list[dict], tools: list[dict]): ...


_SYSTEM = (
    "You generate alternate documentation-search queries. "
    "Return ONLY a JSON array of strings — no prose, no code fences."
)

_USER_TEMPLATE = (
    'A support technician asked: "{question}"\n\n'
    "Generate 3 alternate ways to phrase this question that would help find relevant "
    "documentation about the underlying system or root cause. Focus on technical "
    "vocabulary the docs would use (system names, configuration topics, infrastructure "
    "components, error categories).\n\n"
    "Return ONLY a JSON array of 3 strings. Example:\n"
    '["proxy server configuration", "PAC file settings", "outbound network policy"]'
)


async def expand_query(question: str, llm: _Chatter, *, max_extras: int = 3) -> list[str]:
    """Return [question, ...up to max_extras expansions]. Falls back to [question] on any error."""
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _USER_TEMPLATE.format(question=question)},
    ]
    full = ""
    try:
        async for delta in llm.stream_chat(messages=messages, tools=[]):
            if delta.text:
                full += delta.text
        text = full.strip()
        if text.startswith("```"):
            text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("```"))
        arr = json.loads(text)
        if isinstance(arr, list):
            extras = [str(s).strip() for s in arr if isinstance(s, str) and str(s).strip()]
            return [question, *extras[:max_extras]]
    except Exception:
        pass
    return [question]
