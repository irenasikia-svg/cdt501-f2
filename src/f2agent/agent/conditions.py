"""Experimental conditions. Same agent, tasks and budget; only the defence differs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from f2agent.agent.guard import AllowAll, Guard
from f2agent.agent.task import Task
from f2agent.prompts import BASE_PROMPT, PROMPT_ONLY_DEFENCE


@dataclass(frozen=True)
class Condition:
    id: str
    name: str
    system_prompt: str
    wrap_untrusted: bool
    make_guard: Callable[[Task], Guard]


CONDITIONS: dict[str, Condition] = {
    "C0": Condition("C0", "none", BASE_PROMPT, False, lambda task: AllowAll()),
    "C1": Condition("C1", "prompt_only", BASE_PROMPT + PROMPT_ONLY_DEFENCE, True,
                    lambda task: AllowAll()),
}


def get_condition(cid: str) -> Condition:
    if cid not in CONDITIONS:
        raise KeyError(f"condition {cid!r} not implemented yet")
    return CONDITIONS[cid]
