"""Guard interface: decides whether a proposed tool call may run. Policies arrive in P4."""

from __future__ import annotations

from typing import NamedTuple, Protocol

from f2agent.tools.schemas import ToolResult


class Decision(NamedTuple):
    allow: bool
    rule_id: str
    reason: str


class Guard(Protocol):
    def check(self, tool: str, args: object, history: list[ToolResult]) -> Decision: ...


class AllowAll:
    """No enforcement (conditions C0 and C1)."""

    def check(self, tool: str, args: object, history: list[ToolResult]) -> Decision:
        return Decision(True, "none", "no policy in this condition")
