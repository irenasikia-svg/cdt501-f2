"""Append-only audit log of every proposed tool call (allowed or blocked)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from f2agent.sandbox.canary import redact


class AuditRecord(BaseModel):
    run_id: str
    condition: str
    task_id: str
    step: int
    tool: str
    args: dict | str
    decision: Literal["allow", "block"]
    rule_id: str
    reason: str
    latency_ms: float
    ts: str


class AuditLogger:
    def __init__(self, path: Path, run_id: str, condition: str, task_id: str):
        self.path, self.records = Path(path), []
        self.ctx = {"run_id": run_id, "condition": condition, "task_id": task_id}
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, *, tool: str, args: object, decision: str, rule_id: str, reason: str,
            latency_ms: float) -> AuditRecord:
        """Record one proposed call. Canaries in args are redacted before writing."""
        safe_args = redact(args) if isinstance(args, dict | str) else repr(args)
        rec = AuditRecord(**self.ctx, step=len(self.records), tool=tool, args=safe_args,
                          decision=decision, rule_id=rule_id, reason=redact(reason),
                          latency_ms=latency_ms, ts=datetime.now(UTC).isoformat())
        with self.path.open("a", encoding="utf-8") as f:
            f.write(rec.model_dump_json() + "\n")
        self.records.append(rec)
        return rec
