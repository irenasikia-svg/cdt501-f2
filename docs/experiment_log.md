# Experiment log

One entry per run that produces files in `results/`. Never edit past entries; append corrections.

## Template

```
### EXP-<nn> · <date>
- Command:
- Git commit:
- Conditions / backend / model id / temperature / seed:
- Dataset manifest hash:
- Output files:
- Notes (anomalies, aborted runs, cost):
```

## Entries

### EXP-01 · 2026-11-04 · full mock evaluation, dev + white-box held-out
- Command: `uv run python scripts/run_eval.py --backend mock_gullible --split both` and the same
  with `--backend mock_compliant`
- Git commit: d944b5d (clean)
- Conditions / backend / model id / temperature / seed: C0 C1 C2 A1 A2 D · mock_gullible,
  mock_compliant · deterministic, k = 1
- Dataset manifest hash: e15f4a9c021e (includes the frozen held-out set)
- Output files: `results/runs/mock_*_both.jsonl`, `results/summary.csv`,
  `results/family_breakdown.csv`, `results/figures/*`, `results/failures_C2.md`
- Notes: first run touching held-out data. The policy was frozen before this run (last policy
  change: P4). Held-out has no separate benign tasks, so held-out reports ASR and UA only.
