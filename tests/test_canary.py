from f2agent.sandbox.canary import find_canaries, redact


def test_find_canaries_extracts_all():
    text = "a CANARY-1a2b3c4d b CANARY-deadbeef"
    assert find_canaries(text) == {"CANARY-1a2b3c4d", "CANARY-deadbeef"}


def test_find_canaries_ignores_lookalikes():
    assert find_canaries("CANARY-XYZ CANARY-1234 canary-1a2b3c4d") == set()


def test_redact_nested_values():
    data = {"body": "key CANARY-1a2b3c4d", "to": ["x@y.example", "CANARY-deadbeef"], "n": 3}
    out = redact(data)
    assert "CANARY-1a2b3c4d" not in str(out)
    assert "CANARY-deadbeef" not in str(out)
    assert out["n"] == 3 and out["to"][0] == "x@y.example"
