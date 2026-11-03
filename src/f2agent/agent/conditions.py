"""Experimental conditions. Same agent, tasks and budget; only the defence differs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from f2agent.agent.guard import AllowAll, Guard
from f2agent.agent.task import Task
from f2agent.detector.heuristic import flag_injection
from f2agent.prompts import BASE_PROMPT, PROMPT_ONLY_DEFENCE
from f2agent.tools.schemas import Provenance, ToolResult

DETECTOR_STUB = "[document removed by injection detector]"


@dataclass(frozen=True)
class Condition:
    id: str
    name: str
    system_prompt: str
    wrap_untrusted: bool
    make_guard: Callable[[Task], Guard]
    result_filter: Callable[[ToolResult], ToolResult] | None = None


def _policy(use_taint: bool = True, use_argcheck: bool = True) -> Callable[[Task], Guard]:
    from f2agent.policy.engine import PolicyEngine
    from f2agent.policy.manifest import Manifest

    def make(task: Task) -> Guard:
        manifest = Manifest.from_capabilities(task.id, task.capabilities)
        return PolicyEngine(manifest, use_taint=use_taint, use_argcheck=use_argcheck)
    return make


def drop_flagged(r: ToolResult) -> ToolResult:
    """Condition D: replace untrusted results that the detector flags."""
    if r.ok and r.provenance != Provenance.TRUSTED_USER and flag_injection(r.content):
        return r.model_copy(update={"content": DETECTOR_STUB})
    return r


C1_PROMPT = BASE_PROMPT + PROMPT_ONLY_DEFENCE

CONDITIONS: dict[str, Condition] = {
    "C0": Condition("C0", "none", BASE_PROMPT, False, lambda task: AllowAll()),
    "C1": Condition("C1", "prompt_only", C1_PROMPT, True, lambda task: AllowAll()),
    "C2": Condition("C2", "policy", C1_PROMPT, True, _policy()),
    "A1": Condition("A1", "policy_no_taint", C1_PROMPT, True, _policy(use_taint=False)),
    "A2": Condition("A2", "policy_no_argcheck", C1_PROMPT, True, _policy(use_argcheck=False)),
    "D": Condition("D", "detector_only", C1_PROMPT, True, lambda task: AllowAll(),
                   result_filter=drop_flagged),
}


def get_condition(cid: str) -> Condition:
    if cid not in CONDITIONS:
        raise KeyError(f"condition {cid!r} not implemented yet")
    return CONDITIONS[cid]
