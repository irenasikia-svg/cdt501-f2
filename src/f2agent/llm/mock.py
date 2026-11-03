"""Deterministic scripted models.

* mock_compliant: executes the trusted task's reference plan and nothing else.
* mock_gullible: same plan, but obeys every injected instruction it actually *sees* in a tool
  result (worst case). Containment must therefore come from outside the model.
Argument templates: "{last}" = latest tool result of the same source (the user's plan or the
injection), delimiters removed, so obeying an injection does not corrupt the legitimate output.
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
        self.queue = deque(("plan", c) for c in plan)
        self.pending = list(injections) if obey else []
        self.seen_upto, self.n, self.source = 0, 0, "plan"
        self.last = {"plan": "", "injection": ""}

    def _observe(self, messages: list[dict]) -> None:
        for msg in messages[self.seen_upto:]:
            if msg.get("role") == "tool":
                text = unwrap(msg.get("content") or "")
                self.last[self.source] = text
                self._maybe_obey(text)
        self.seen_upto = len(messages)

    def _maybe_obey(self, text: str) -> None:
        for inj in [i for i in self.pending if i.trigger in text]:
            self.pending.remove(inj)
            self.queue.extendleft(("injection", c) for c in reversed(inj.calls))  # obey now

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self._observe(messages)
        if not self.queue:
            return LLMResponse(content="Done.")
        (self.source, call), self.n = self.queue.popleft(), self.n + 1
        last = self.last[self.source]
        args = {k: v.replace("{last}", last) if isinstance(v, str) else v
                for k, v in call.args.items()}
        return LLMResponse(content="", tool_calls=[ToolCall(f"call_{self.n}", call.tool, args)])
