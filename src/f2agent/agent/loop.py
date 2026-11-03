"""Standard tool-calling loop: every proposed call is checked by the guard and audited."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from f2agent.agent.conditions import Condition
from f2agent.agent.task import Task
from f2agent.llm.base import LLMBackend, ToolCall
from f2agent.policy.audit import AuditLogger
from f2agent.prompts import wrap_untrusted
from f2agent.sandbox.world import World
from f2agent.tools.registry import execute, openai_tool_schemas
from f2agent.tools.schemas import Provenance, ToolResult

BLOCKED_MSG = "ERROR: this action is not permitted for the current task. Continue with the task."


@dataclass
class Step:
    tool: str
    args: object
    allowed: bool
    rule_id: str
    ok: bool
    provenance: str


@dataclass
class Episode:
    task_id: str
    condition: str
    final_text: str = ""
    steps: list[Step] = field(default_factory=list)
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_s: float = 0.0
    stopped_reason: str = ""

    @property
    def blocked(self) -> int:
        return sum(not s.allowed for s in self.steps)


def _assistant_msg(content: str, calls: list[ToolCall]) -> dict:
    msg = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = [{"id": c.id, "type": "function", "function": {
            "name": c.name, "arguments": c.arguments if isinstance(c.arguments, str)
            else json.dumps(c.arguments, ensure_ascii=False)}} for c in calls]
    return msg


def _tool_text(result: ToolResult, cond: Condition) -> str:
    if not result.ok:
        return f"ERROR: {result.error}"
    if cond.wrap_untrusted and result.provenance != Provenance.TRUSTED_USER:
        return wrap_untrusted(result.content, result.provenance.value)
    return result.content


def _handle_call(call: ToolCall, world, guard, cond, audit, history, ep) -> str:
    """Check one proposed call, audit it, then execute it or return a neutral error."""
    t0 = time.perf_counter()
    decision = guard.check(call.name, call.arguments, history)
    audit.log(tool=call.name, args=call.arguments, decision="allow" if decision.allow else
              "block", rule_id=decision.rule_id, reason=decision.reason,
              latency_ms=(time.perf_counter() - t0) * 1000)
    result = execute(world, call.name, call.arguments) if decision.allow else None
    if result is not None:
        history.append(result)
    ep.steps.append(Step(call.name, call.arguments, decision.allow, decision.rule_id,
                         bool(result and result.ok), result.provenance if result else ""))
    return _tool_text(result, cond) if result else BLOCKED_MSG


def run_episode(task: Task, world: World, backend: LLMBackend, cond: Condition,
                audit: AuditLogger, max_steps: int = 12) -> Episode:
    ep, guard, history = Episode(task.id, cond.id), cond.make_guard(task), []
    messages = [{"role": "system", "content": cond.system_prompt},
                {"role": "user", "content": task.instruction}]
    tools, start = openai_tool_schemas(), time.perf_counter()
    while True:
        if len(ep.steps) >= max_steps:
            ep.stopped_reason = "max_steps"
            break
        resp = backend.complete(messages, tools)
        ep.llm_calls += 1
        ep.prompt_tokens += resp.prompt_tokens
        ep.completion_tokens += resp.completion_tokens
        messages.append(_assistant_msg(resp.content, resp.tool_calls))
        if not resp.tool_calls:
            ep.final_text, ep.stopped_reason = resp.content, "final_answer"
            break
        for call in resp.tool_calls:
            text = _handle_call(call, world, guard, cond, audit, history, ep)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
    ep.wall_s = time.perf_counter() - start
    return ep
