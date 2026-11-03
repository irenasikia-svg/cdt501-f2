"""Policy engine (condition C2 and ablations). Enforced in Python; every failure blocks."""

from __future__ import annotations

import posixpath

from pydantic import BaseModel

from f2agent.agent.guard import Decision
from f2agent.policy.manifest import Manifest
from f2agent.policy.taint import (
    derived_from,
    fragments,
    has_canary,
    has_canary_body,
    seen_canary_bodies,
)
from f2agent.tools.registry import TOOLS, parse_args
from f2agent.tools.schemas import Provenance, ToolResult

ALLOW = Decision(True, "allow", "permitted by task manifest")


def block(rule: str, reason: str) -> Decision:
    return Decision(False, rule, reason)


class PolicyEngine:
    def __init__(self, manifest: Manifest, use_taint: bool = True, use_argcheck: bool = True):
        self.m, self.use_taint, self.use_argcheck = manifest, use_taint, use_argcheck

    def check(self, tool: str, raw_args: object, history: list[ToolResult]) -> Decision:
        try:
            return self._check(tool, raw_args, history)
        except Exception as e:  # fail closed on any bug
            return block("internal_error", f"{type(e).__name__}")

    def _check(self, tool, raw_args, history) -> Decision:
        if tool not in TOOLS:
            return block("tool.unknown", f"unknown tool {tool!r}")
        try:
            args = parse_args(tool, raw_args)
        except Exception as e:
            return block("args.invalid", type(e).__name__)
        if tool not in self.m.allowed_tools:
            return block("tool.not_in_manifest", f"{tool} not granted for this task")
        if self.use_argcheck and (d := self._argcheck(tool, args)):
            return d
        if self.use_taint and TOOLS[tool].outbound and (d := self._taint(args, history)):
            return d
        return ALLOW

    def _argcheck(self, tool: str, a: BaseModel) -> Decision | None:
        if tool == "write_note" and not _under(a.filename, self.m.write_prefixes):
            return block("arg.path", "write path outside the task's output folder")
        if tool == "send_email" and a.to.lower() not in self.m.recipients:
            return block("arg.recipient", "recipient not in task manifest")
        if tool == "fetch_url" and a.url not in self.m.urls:
            return block("arg.url", "URL not in task allowlist")
        if tool == "delete_document" and a.doc_id not in self.m.deletable:
            return block("arg.delete", "document not deletable for this task")
        return None

    def _taint(self, a: BaseModel, history: list[ToolResult]) -> Decision | None:
        """No secret may reach an outbound sink; untrusted text only if the task allows it."""
        values = [v for v in a.model_dump().values() if isinstance(v, str)]
        S, U = Provenance.SECRET, Provenance.UNTRUSTED_DOC
        secret, bodies = fragments(history, S), seen_canary_bodies(history)
        if any(has_canary(v) or has_canary_body(v, bodies) or derived_from(v, secret, history, S)
               for v in values):
            return block("taint.secret", "secret-derived data to outbound sink")
        if not self.m.untrusted_to_sink:
            untrusted, trusted = fragments(history, U), self.m.trusted_values()
            if any(v not in trusted and derived_from(v, untrusted, history, U) for v in values):
                return block("taint.untrusted", "document-derived data to outbound sink")
        return None


def _under(path: str, prefixes: tuple[str, ...]) -> bool:
    norm = posixpath.normpath(path)
    if path.startswith("/") or ".." in norm.split("/"):
        return False
    return any(norm.startswith(p) and norm != p.rstrip("/") for p in prefixes)
