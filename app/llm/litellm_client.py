import json
from dataclasses import dataclass
from typing import AsyncIterator
import httpx


@dataclass
class StreamDelta:
    text: str | None = None
    tool_call: dict | None = None
    finish_reason: str | None = None


class LiteLLMClient:
    def __init__(self, *, base_url: str, api_key: str, chat_model: str, embedding_model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.timeout = timeout

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def embed(self, inputs: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(f"{self.base_url}/embeddings", json={"model": self.embedding_model, "input": inputs}, headers=self._headers())
            r.raise_for_status()
            return [d["embedding"] for d in r.json()["data"]]

    async def stream_chat(self, *, messages: list[dict], tools: list[dict]) -> AsyncIterator[StreamDelta]:
        payload = {"model": self.chat_model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            async with c.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers()) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        return
                    obj = json.loads(data)
                    choice = obj.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    finish = choice.get("finish_reason")
                    if "tool_calls" in delta:
                        for tc in delta["tool_calls"]:
                            yield StreamDelta(tool_call=tc)
                    if "content" in delta and delta["content"]:
                        yield StreamDelta(text=delta["content"])
                    if finish:
                        yield StreamDelta(finish_reason=finish)
