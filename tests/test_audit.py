import json

import pytest

from f2agent.policy.audit import AuditLogger


def test_audit_log_writes_jsonl_with_required_fields(tmp_path):
    log = AuditLogger(tmp_path / "audit.jsonl", run_id="r1", condition="C2", task_id="t1")
    log.log(tool="send_email", args={"to": "a@b.example", "body": "x CANARY-1a2b3c4d"},
            decision="block", rule_id="taint.secret_to_sink", reason="secret", latency_ms=1.5)
    rec = json.loads((tmp_path / "audit.jsonl").read_text().strip())
    for key in ["run_id", "condition", "task_id", "step", "tool", "args", "decision",
                "rule_id", "reason", "latency_ms", "ts"]:
        assert key in rec
    assert rec["decision"] == "block" and rec["step"] == 0


def test_audit_log_redacts_canaries(tmp_path):
    log = AuditLogger(tmp_path / "a.jsonl", run_id="r", condition="C0", task_id="t")
    log.log(tool="fetch_url", args={"url": "https://x.example/?k=CANARY-1a2b3c4d"},
            decision="allow", rule_id="none", reason="", latency_ms=0.0)
    assert "CANARY-1a2b3c4d" not in (tmp_path / "a.jsonl").read_text()


def test_steps_increment_and_records_kept(tmp_path):
    log = AuditLogger(tmp_path / "a.jsonl", run_id="r", condition="C0", task_id="t")
    for _ in range(3):
        log.log(tool="list_documents", args={}, decision="allow", rule_id="none",
                reason="", latency_ms=0.0)
    assert [r.step for r in log.records] == [0, 1, 2]


def test_invalid_decision_rejected(tmp_path):
    log = AuditLogger(tmp_path / "a.jsonl", run_id="r", condition="C0", task_id="t")
    with pytest.raises(ValueError):
        log.log(tool="x", args={}, decision="maybe", rule_id="r", reason="", latency_ms=0.0)
