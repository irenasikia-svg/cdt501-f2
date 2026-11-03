"""Smoke check: one benign task and one inline sample injection, all conditions, mock backends.

Prints a table only; it writes nothing to results/. Real metrics come from run_eval.py (P6).
Usage: uv run python scripts/smoke_c0_c1.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from f2agent.agent.conditions import get_condition  # noqa: E402
from f2agent.agent.loop import run_episode  # noqa: E402
from f2agent.llm import make_backend  # noqa: E402
from f2agent.policy.audit import AuditLogger  # noqa: E402
from f2agent.sandbox.canary import find_canaries  # noqa: E402
from f2agent.sandbox.world import World  # noqa: E402
from tests.helpers import (  # noqa: E402
    ATTACK_TASK,
    CARRIER_ID,
    CARRIER_TEXT,
    INJECTION,
    SUMMARY_TASK,
)


def one(tmp: Path, task, backend: str, cond: str, attack: bool) -> tuple[bool, bool, int, int]:
    extra = {f"{CARRIER_ID}.md": CARRIER_TEXT} if attack else None
    world = World.fresh(parent=tmp, extra_docs=extra)
    audit = AuditLogger(Path("logs") / f"smoke_{cond}_{backend}_{task.id}.jsonl",
                        run_id="smoke", condition=cond, task_id=task.id)
    ep = run_episode(task, world, make_backend(backend, task, [INJECTION]),
                     get_condition(cond), audit)
    out = world.root / task.reference_plan[-1].args["filename"]
    leaked = any(find_canaries(m["body"]) for m in world.outbox())
    return out.exists(), leaked, len(ep.steps), ep.blocked


def main() -> None:
    print(f"{'backend':16} {'cond':4} {'case':8} {'task_done':9} {'leaked':13} steps blocked")
    with tempfile.TemporaryDirectory() as d:
        for backend in ("mock_compliant", "mock_gullible"):
            for cond in ("C0", "C1", "C2", "A1", "A2", "D"):
                for task, attack in ((SUMMARY_TASK, False), (ATTACK_TASK, True)):
                    done, leaked, n, b = one(Path(d), task, backend, cond, attack)
                    case = "attack" if attack else "benign"
                    print(f"{backend:16} {cond:4} {case:8} {done!s:9} {leaked!s:13} {n:5} {b}")


if __name__ == "__main__":
    main()
