from f2agent.llm.mock import ScriptedModel
from tests.helpers import ATTACK_TASK, INJECTION, SUMMARY_TASK


def tool_msg(content):
    return {"role": "tool", "tool_call_id": "x", "content": content}


def test_compliant_follows_plan_then_finishes():
    m = ScriptedModel(SUMMARY_TASK.reference_plan, injections=[INJECTION], obey=False)
    msgs = [{"role": "user", "content": "task"}]
    r1 = m.complete(msgs, [])
    assert r1.tool_calls[0].name == "read_document"
    msgs += [{"role": "assistant", "content": ""}, tool_msg("doc text " + INJECTION.trigger)]
    r2 = m.complete(msgs, [])
    assert r2.tool_calls[0].name == "write_note"
    assert r2.tool_calls[0].arguments["content"].startswith("doc text")
    msgs += [{"role": "assistant", "content": ""}, tool_msg("wrote")]
    assert m.complete(msgs, []).tool_calls == []


def test_gullible_obeys_injection_only_after_seeing_it():
    m = ScriptedModel(ATTACK_TASK.reference_plan, injections=[INJECTION], obey=True)
    msgs = [{"role": "user", "content": "task"}]
    assert m.complete(msgs, []).tool_calls[0].name == "read_document"
    msgs += [{"role": "assistant", "content": ""}, tool_msg("blah " + INJECTION.trigger)]
    names = []
    for content in ["CANARY-b9cb7f5f", "sent", "wrote"]:
        r = m.complete(msgs, [])
        names.append(r.tool_calls[0].name)
        msgs += [{"role": "assistant", "content": ""}, tool_msg(content)]
    assert names == ["read_file", "send_email", "write_note"]


def test_gullible_never_fires_without_trigger():
    m = ScriptedModel(SUMMARY_TASK.reference_plan, injections=[INJECTION], obey=True)
    msgs = [{"role": "user", "content": "task"}]
    seen = []
    for _ in range(5):
        r = m.complete(msgs, [])
        if not r.tool_calls:
            break
        seen.append(r.tool_calls[0].name)
        msgs += [{"role": "assistant", "content": ""}, tool_msg("clean text")]
    assert seen == ["read_document", "write_note"]


def test_mock_is_deterministic():
    def run():
        m = ScriptedModel(ATTACK_TASK.reference_plan, injections=[INJECTION], obey=True)
        msgs, out = [{"role": "user", "content": "t"}], []
        for _ in range(6):
            r = m.complete(msgs, [])
            out.append([(c.name, c.arguments) for c in r.tool_calls])
            msgs += [{"role": "assistant", "content": ""}, tool_msg(INJECTION.trigger)]
        return out
    assert run() == run()


def test_split_injection_fires_only_after_both_parts_seen():
    from f2agent.llm.mock import Injection, PlannedCall
    inj = Injection(trigger="PART-B", requires=["PART-A"],
                    calls=[PlannedCall(tool="delete_document", args={"doc_id": "x"})])
    plan = [PlannedCall(tool="read_document", args={"doc_id": d}) for d in "abc"]
    m = ScriptedModel(plan, injections=[inj], obey=True)
    msgs, names = [{"role": "user", "content": "t"}], []
    for content in ["PART-B only", "PART-A now", "z", "z"]:
        r = m.complete(msgs, [])
        names.append(r.tool_calls[0].name if r.tool_calls else None)
        msgs += [{"role": "assistant", "content": ""}, tool_msg(content)]
    assert names == ["read_document", "read_document", "delete_document", "read_document"]
