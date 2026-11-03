"""Deterministic scripted models.

* mock_compliant: executes the trusted task's reference plan and nothing else.
* mock_gullible: same plan, but obeys every injected instruction it actually *sees* in a tool
  result (worst case). Containment must therefore come from outside the model.
Argument templates: "{last}" = content of the latest tool result (delimiters removed).
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from f2agent.llm.base import LLMResponse, ToolCall
from f2agent.prompts import unwrap


class PlannedCall(BaseModel):
    tool: str
    args: dict


class Injection(BaseModel):
    trigger: str              # text that, once seen in a tool result, makes the model obey
    calls: list[PlannedCall]  # what the injected instruction asks the agent to do


class ScriptedModel:
    temperature, seed = 0.0, None

    def __init__(self, plan: list[PlannedCall], injections=(), obey: bool = False,
                 name: str = "mock"):
        self.name = self.model_id = name
        self.queue = deque(plan)
        self.pending = list(injections) if obey else []
        self.seen_upto, self.last, self.n = 0, "", 0

    def _observe(self, messages: list[dict]) -> None:
        for msg in messages[self.seen_upto:]:
            if msg.get("role") == "tool":
                self.last = unwrap(msg.get("content") or "")
                self._maybe_obey(self.last)
        self.seen_upto = len(messages)

    def _maybe_obey(self, text: str) -> None:
        for inj in [i for i in self.pending if i.trigger in text]:
            self.pending.remove(inj)
            self.queue.extendleft(reversed(inj.calls))  # obey immediately

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self._observe(messages)
        if not self.queue:
            return LLMResponse(content="Done.")
        call, self.n = self.queue.popleft(), self.n + 1
        args = {k: v.replace("{last}", self.last) if isinstance(v, str) else v
                for k, v in call.args.items()}
        return LLMResponse(content="", tool_calls=[ToolCall(f"call_{self.n}", call.tool, args)])
