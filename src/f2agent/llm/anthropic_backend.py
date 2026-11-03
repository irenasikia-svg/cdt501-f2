"""Optional Anthropic backend (install with `uv sync --extra anthropic`)."""

from __future__ import annotations

import json
import os

from f2agent.llm.base import LLMResponse, ToolCall


def to_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert OpenAI-format messages to (system, Anthropic messages)."""
    system, out = "", []
    for m in messages:
        if m["role"] == "system":
            system += m["content"]
        elif m["role"] == "tool":
            block = {"type": "tool_result", "tool_use_id": m["tool_call_id"],
                     "content": m["content"]}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        elif m["role"] == "assistant" and m.get("tool_calls"):
            blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
            for tc in m["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except ValueError:
                    args = {"_raw": tc["function"]["arguments"]}
                blocks.append({"type": "tool_use", "id": tc["id"],
                               "name": tc["function"]["name"], "input": args})
            out.append({"role": "assistant", "content": blocks})
        else:
            out.append({"role": m["role"], "content": m.get("content") or ""})
    return system, out


class AnthropicBackend:
    name = "anthropic"

    def __init__(self, model_id: str, api_key: str, temperature: float = 0.0, client=None):
        self.model_id, self.temperature, self.seed = model_id, temperature, None
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        self.client = client

    @classmethod
    def from_env(cls) -> AnthropicBackend:
        return cls(os.environ["ANTHROPIC_MODEL"], os.environ["ANTHROPIC_API_KEY"],
                   float(os.environ.get("LLM_TEMPERATURE", "0")))

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        system, msgs = to_anthropic(messages)
        atools = [{"name": t["function"]["name"], "description": t["function"]["description"],
                   "input_schema": t["function"]["parameters"]} for t in tools]
        resp = self.client.messages.create(model=self.model_id, system=system, messages=msgs,
                                           tools=atools, temperature=self.temperature,
                                           max_tokens=2048)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, b.input) for b in resp.content if b.type == "tool_use"]
        return LLMResponse(text, calls, resp.usage.input_tokens, resp.usage.output_tokens)
