"""Backend-neutral LLM types. Messages use the OpenAI chat format (list of dicts)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: object  # dict when parsed; raw string when the model emitted invalid JSON


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMBackend(Protocol):
    name: str
    model_id: str
    temperature: float
    seed: int | None

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


def parse_arguments(raw: object) -> object:
    """Parse tool-call arguments. Anything that is not a JSON object is kept raw (fails later)."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return raw
    return value if isinstance(value, dict) else raw
