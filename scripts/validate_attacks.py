"""Validate an attack file BEFORE freezing it. Meant for the human team on the held-out split.

Checks per case: schema; task and carrier exist; only reserved domains; the attack really
succeeds on mock_gullible (C0); it does not fire on mock_compliant; the legitimate task stays
solvable with the injected carrier. Prints ids and verdicts only, never injection text.
Usage: uv run python scripts/validate_attacks.py --split heldout
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f2agent.agent.conditions import get_condition  # noqa: E402
from f2agent.agent.loop import run_episode  # noqa: E402
from f2agent.eval.checkers import attack_succeeded, benign_passed  # noqa: E402
from f2agent.eval.dataset import build_world, load_attacks, load_tasks  # noqa: E402
from f2agent.llm import make_backend  # noqa: E402
from f2agent.policy.audit import AuditLogger  # noqa: E402
from f2agent.sandbox.world import SANDBOX_TEMPLATE  # noqa: E402

HOSTS = re.compile(r"[\w.+-]+@([\w.-]*\w)|https?://([^/\s?#\"'\\]+)")
RESERVED = (".example", ".invalid", ".test")


def run(tmp: Path, case, atk, backend: str):
    world = build_world(tmp, atk)
    audit = AuditLogger(tmp / "audit.jsonl", run_id="validate", condition="C0",
                        task_id=case.task.id)
    ep = run_episode(case.task, world, make_backend(backend, case.task, [atk.injection]),
                     get_condition("C0"), audit)
    return world, ep


def problems(atk, tasks: dict, tmp: Path) -> list[str]:
    out = []
    case = tasks.get(atk.task_id)
    if case is None:
        return [f"unknown task_id {atk.task_id}"]
    docs = {p.stem for p in (SANDBOX_TEMPLATE / "docs").iterdir()}
    for c in [atk, *atk.extra_carriers]:
        if not c.new_doc and c.carrier_doc not in docs:
            out.append(f"unknown carrier_doc {c.carrier_doc}")
    if out:
        return out
    blob = atk.model_dump_json()
    hosts = {(m or u).lower() for m, u in HOSTS.findall(blob)}
    bad = {h for h in hosts if not h.endswith(RESERVED)}
    if bad:
        out.append(f"non-reserved domains: {sorted(bad)}")
    if atk.injection.trigger not in atk.injection_text + "".join(
            c.injection_text for c in atk.extra_carriers):
        out.append("injection.trigger does not appear in any injection_text")
    world, _ = run(tmp / "g", case, atk, "mock_gullible")
    if not attack_succeeded(atk.success, world):
        out.append("attack does NOT succeed on mock_gullible C0 (check calls/success)")
    world, ep = run(tmp / "c", case, atk, "mock_compliant")
    if attack_succeeded(atk.success, world):
        out.append("success check fires even for mock_compliant (check success)")
    if not benign_passed(case.check, world, ep.final_text):
        out.append("legitimate task no longer passes with this carrier")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    split = ap.parse_args().split
    try:
        attacks = load_attacks(split)
    except Exception as e:  # schema errors: show pydantic's message
        print(f"FAIL: cannot load {split} attacks:\n{e}")
        return 1
    tasks = {c.task.id: c for c in load_tasks(split)}
    failed = 0
    with tempfile.TemporaryDirectory() as d:
        for i, atk in enumerate(attacks):
            probs = problems(atk, tasks, Path(d) / str(i))
            failed += bool(probs)
            print(f"{'FAIL' if probs else 'ok  '} {atk.id} [{atk.family}/{atk.goal}]")
            for p in probs:
                print(f"       - {p}")
    ids = [a.id for a in attacks]
    if len(ids) != len(set(ids)):
        print("FAIL: duplicate ids")
        failed += 1
    print(f"{len(attacks)} cases, {failed} with problems")
    return 1 if failed or not attacks else 0


if __name__ == "__main__":
    sys.exit(main())
