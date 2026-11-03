"""OpenAI-compatible chat backend (OpenRouter, DeepSeek, Ollama, ...)."""

from __future__ import annotations

import os
import time

from f2agent.llm.base import LLMResponse, ToolCall, parse_arguments


class OpenAICompatBackend:
    name = "openai_compat"

    def __init__(self, model_id: str, base_url: str, api_key: str, temperature: float = 0.0,
                 seed: int | None = 42, client=None, max_retries: int = 4):
        self.model_id, self.temperature, self.seed = model_id, temperature, seed
        self.max_retries = max_retries
        if client is None:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
        self.client = client
        self.served_model: str | None = None

    @classmethod
    def from_env(cls) -> OpenAICompatBackend:
        return cls(model_id=os.environ["OPENAI_COMPAT_MODEL"],
                   base_url=os.environ["OPENAI_COMPAT_BASE_URL"],
                   api_key=os.environ["OPENAI_COMPAT_API_KEY"],
                   temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
                   seed=int(os.environ.get("LLM_SEED", "42")))

    def _create(self, **kwargs):
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:  # rate limits / transient errors on free tiers
                if attempt == self.max_retries or not _is_transient(e):
                    raise
                time.sleep(2 ** (attempt + 1))

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self._create(model=self.model_id, messages=messages, tools=tools,
                            temperature=self.temperature, seed=self.seed)
        self.served_model = getattr(resp, "model", None)
        msg = resp.choices[0].message
        calls = [ToolCall(tc.id, tc.function.name, parse_arguments(tc.function.arguments))
                 for tc in (msg.tool_calls or [])]
        usage = getattr(resp, "usage", None)
        return LLMResponse(content=msg.content or "", tool_calls=calls,
                           prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                           completion_tokens=getattr(usage, "completion_tokens", 0) or 0)


def _is_transient(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    return status in (408, 429, 500, 502, 503, 504) or type(e).__name__ in (
        "APIConnectionError", "APITimeoutError", "RateLimitError")
