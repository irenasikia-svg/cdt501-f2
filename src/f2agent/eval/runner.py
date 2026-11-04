"""Run episodes and turn each into one self-describing result record."""

from __future__ import annotations

import hashlib
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from f2agent.agent.conditions import get_condition
from f2agent.agent.loop import run_episode
from f2agent.eval.checkers import attack_succeeded, benign_passed
from f2agent.eval.dataset import DATA, AttackCase, BenignCase, build_world
from f2agent.llm import make_backend
from f2agent.policy.audit import AuditLogger
from f2agent.sandbox.canary import redact
from f2agent.sandbox.world import REPO_ROOT

META_KEYS = ["run_id", "split", "condition", "backend", "model_id", "temperature", "seed", "k",
             "git_commit", "prompt_hash", "manifest_hash", "timestamp"]


def git_commit() -> str:
    def git(*a):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True,  # noqa: S603,S607
                              text=True).stdout.strip()
    dirty = git("status", "--porcelain", "--", "src", "scripts", "data", "sandbox")
    return (git("rev-parse", "--short", "HEAD") or "unknown") + ("-dirty" if dirty else "")


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def manifest_hash() -> str:
    p = DATA / "MANIFEST.sha256"
    return sha12(p.read_text()) if p.exists() else "none"


def run_case(*, run_id: str, split: str, cond_id: str, backend_name: str, k: int,
             case: BenignCase, attack: AttackCase | None, work: Path, logs: Path,
             commit: str, mhash: str) -> dict:
    cond = get_condition(cond_id)
    case_id = attack.id if attack else case.task.id
    world = build_world(work / f"{cond_id}_{case_id}_{k}", attack)
    backend = make_backend(backend_name, task=case.task,
                           injections=[attack.injection] if attack else [])
    audit = AuditLogger(logs / f"{cond_id}_{case_id}_{k}.jsonl", run_id=run_id,
                        condition=cond_id, task_id=case.task.id)
    t0, error, ep = time.perf_counter(), "", None
    try:
        ep = run_episode(case.task, world, backend, cond, audit)
    except Exception as e:  # backend/network failure: recorded, counted as task failure
        error = f"{type(e).__name__}: {e}"[:300]
    final = ep.final_text if ep else ""
    return {
        "run_id": run_id, "split": split, "condition": cond_id, "backend": backend_name,
        "model_id": backend.model_id, "served_model": getattr(backend, "served_model", None),
        "temperature": backend.temperature, "seed": backend.seed, "k": k,
        "case_type": "attack" if attack else "benign", "case_id": case_id,
        "task_id": case.task.id, "family": attack.family if attack else None,
        "goal": attack.goal if attack else None,
        "benign_pass": bool(ep) and benign_passed(case.check, world, final),
        "attack_success": bool(attack) and attack_succeeded(attack.success, world),
        "blocked": ep.blocked if ep else 0, "steps": len(ep.steps) if ep else 0,
        "llm_calls": ep.llm_calls if ep else 0,
        "prompt_tokens": ep.prompt_tokens if ep else 0,
        "completion_tokens": ep.completion_tokens if ep else 0,
        "wall_s": round(time.perf_counter() - t0, 4),
        "stopped_reason": ep.stopped_reason if ep else "error", "error": error,
        "final_text": redact(final)[:500],
        "audit": [r.model_dump(exclude={"run_id", "condition", "task_id"}) for r in audit.records],
        "git_commit": commit, "prompt_hash": sha12(cond.system_prompt), "manifest_hash": mhash,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
    }
