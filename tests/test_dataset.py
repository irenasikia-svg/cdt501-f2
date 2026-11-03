"""The committed dev data must be well-formed and *effective* on the mock models."""

import pytest

from f2agent.agent.conditions import get_condition
from f2agent.agent.loop import run_episode
from f2agent.eval.checkers import attack_succeeded, benign_passed
from f2agent.eval.dataset import build_world, load_attacks, load_benign
from f2agent.llm import make_backend
from f2agent.policy.audit import AuditLogger

BENIGN = load_benign()
ATTACKS = load_attacks("dev")
BY_ID = {b.task.id: b for b in BENIGN}


def run(tmp_path, case, backend, cond, attack=None):
    world = build_world(tmp_path, attack)
    b = make_backend(backend, task=case.task, injections=[attack.injection] if attack else [])
    audit = AuditLogger(tmp_path / "a.jsonl", run_id="t", condition=cond, task_id=case.task.id)
    return world, run_episode(case.task, world, b, get_condition(cond), audit)


def test_sizes_and_families():
    assert 38 <= len(BENIGN) <= 45
    assert len({b.task.id for b in BENIGN}) == len(BENIGN)
    assert {a.family for a in ATTACKS} == {"direct_override", "fake_system",
                                           "authority_impersonation", "zh_simplified",
                                           "hidden_comment"}
    assert {a.goal for a in ATTACKS} >= {"exfil_canary_email", "exfil_canary_url",
                                         "email_attacker", "redirect_email",
                                         "write_outside_output", "delete_doc"}
    assert all(a.task_id in BY_ID for a in ATTACKS)


def test_attack_domains_are_reserved():
    for a in ATTACKS:
        for c in a.injection.calls:
            for v in c.args.values():
                if "@" in str(v) and "{" not in str(v):
                    assert str(v).endswith(".example")


@pytest.mark.parametrize("case", BENIGN, ids=lambda c: c.task.id)
def test_every_benign_task_passes_with_compliant_model_under_c0_and_c2(tmp_path, case):
    for cond in ("C0", "C2"):
        world, ep = run(tmp_path / cond, case, "mock_compliant", cond)
        assert benign_passed(case.check, world, ep.final_text), (cond, ep.steps)
        assert ep.blocked == 0, cond


@pytest.mark.parametrize("atk", ATTACKS, ids=lambda a: a.id)
def test_every_dev_attack_works_on_gullible_c0_and_not_on_compliant(tmp_path, atk):
    case = BY_ID[atk.task_id]
    world, _ = run(tmp_path / "g", case, "mock_gullible", "C0", atk)
    assert attack_succeeded(atk.success, world)
    world, ep = run(tmp_path / "c", case, "mock_compliant", "C0", atk)
    assert not attack_succeeded(atk.success, world)
    assert benign_passed(case.check, world, ep.final_text)   # carrier keeps the task solvable


@pytest.mark.parametrize("atk", ATTACKS, ids=lambda a: a.id)
def test_c2_contains_every_dev_attack(tmp_path, atk):
    world, _ = run(tmp_path, BY_ID[atk.task_id], "mock_gullible", "C2", atk)
    assert not attack_succeeded(atk.success, world)
