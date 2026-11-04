from f2agent.eval.metrics import bootstrap_ci, percentile, summarize


def ep(cond, kind, *, case, benign=True, attack=False, blocked=0, wall=1.0, stop="final_answer",
       family=None, k=0):
    return {"condition": cond, "case_type": kind, "case_id": case, "benign_pass": benign,
            "attack_success": attack, "blocked": blocked, "wall_s": wall, "stopped_reason": stop,
            "prompt_tokens": 10, "completion_tokens": 5, "family": family, "k": k}


def test_rates_and_false_blocks():
    recs = [ep("C2", "benign", case="b1"), ep("C2", "benign", case="b2", benign=False, blocked=1),
            ep("C2", "benign", case="b3", benign=False, blocked=0, stop="max_steps"),
            ep("C2", "attack", case="a1", attack=True, benign=False, family="f"),
            ep("C2", "attack", case="a2", attack=False, benign=True, family="f")]
    s = summarize(recs)
    assert s["BU"] == 1 / 3 and s["ASR"] == 0.5 and s["UA"] == 0.5
    assert s["false_block_rate"] == 1 / 3
    assert s["blocked_per_benign"] == 1 / 3
    assert s["coverage"] == 2 / 3
    assert s["tokens_mean"] == 15


def test_repeats_are_averaged_per_case_before_bootstrap():
    recs = [ep("C1", "attack", case="a1", attack=a, k=i) for i, a in enumerate([1, 1, 0])]
    s = summarize(recs)
    assert abs(s["ASR"] - 2 / 3) < 1e-9 and s["n_attack_cases"] == 1


def test_bootstrap_is_deterministic_and_brackets_mean():
    vals = {f"c{i}": [float(i % 2)] for i in range(20)}
    lo, hi = bootstrap_ci(vals)
    assert bootstrap_ci(vals) == (lo, hi)
    assert lo <= 0.5 <= hi
    assert bootstrap_ci({"a": [1.0], "b": [1.0]}) == (1.0, 1.0)
    assert bootstrap_ci({}) == (None, None)


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([1.0], 90) == 1.0
