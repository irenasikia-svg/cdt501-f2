"""Deterministic scripted models.

* mock_compliant: executes the trusted task's reference plan and nothing else.
* mock_gullible: same plan, but obeys every injected instruction it actually *sees* in a tool
  result (worst case). Containment must therefore come from outside the model.
Argument templates (delimiters removed from tool results first):
  {last}        latest tool result of the same source (user plan or injection)
  {last_urlenc} the same, URL-encoded (for exfiltration via a query string)
  {plan_last}   latest result of the user's plan
  {all}         every result of the user's plan, joined
A planned call with tool "final" ends the episode with args["text"] as the answer.
"""

from __future__ import annotations

from collections import deque
from urllib.parse import quote

from pydantic import BaseModel

from f2agent.llm.base import LLMResponse, ToolCall
from f2agent.prompts import unwrap


class PlannedCall(BaseModel):
    tool: str
    args: dict


class Injection(BaseModel):
    trigger: str              # text that, once seen in a tool result, makes the model obey
    calls: list[PlannedCall]  # what the injected instruction asks the agent to do
    requires: list[str] = []  # other text that must ALSO have been seen (split injections)


class ScriptedModel:
    temperature, seed = 0.0, None

    def __init__(self, plan: list[PlannedCall], injections=(), obey: bool = False,
                 name: str = "mock"):
        self.name = self.model_id = name
        self.queue = deque(("plan", c) for c in plan)
        self.pending = list(injections) if obey else []
        self.seen_upto, self.n, self.source = 0, 0, "plan"
        self.last = {"plan": "", "injection": ""}
        self.plan_results: list[str] = []
        self.seen_text = ""

    def _observe(self, messages: list[dict]) -> None:
        for msg in messages[self.seen_upto:]:
            if msg.get("role") == "tool":
                text = unwrap(msg.get("content") or "")
                self.last[self.source] = text
                if self.source == "plan":
                    self.plan_results.append(text)
                self._maybe_obey(text)
        self.seen_upto = len(messages)

    def _maybe_obey(self, text: str) -> None:
        self.seen_text += "\n" + text
        ready = [i for i in self.pending if i.trigger in self.seen_text
                 and all(r in self.seen_text for r in i.requires)]
        for inj in ready:
            self.pending.remove(inj)
            self.queue.extendleft(("injection", c) for c in reversed(inj.calls))  # obey now

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self._observe(messages)
        if not self.queue:
            return LLMResponse(content="Done.")
        (self.source, call), self.n = self.queue.popleft(), self.n + 1
        args = {k: self._render(v) if isinstance(v, str) else v for k, v in call.args.items()}
        if call.tool == "final":
            self.queue.clear()
            return LLMResponse(content=args.get("text", "Done."))
        return LLMResponse(content="", tool_calls=[ToolCall(f"call_{self.n}", call.tool, args)])

    def _render(self, v: str) -> str:
        last = self.last[self.source]
        subs = {"{last_urlenc}": quote(last, safe=""), "{plan_last}": self.last["plan"],
                "{all}": "\n\n".join(self.plan_results), "{last}": last}
        for key, val in subs.items():
            v = v.replace(key, val)
        return v
