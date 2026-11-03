# AGENTS.md — instructions for coding agents (CDT501 F2)

This file is required by the course. Every coding agent (Claude Code, Codex, Cursor, …) working
in this repo must follow it. `CLAUDE.md` only imports this file.

## Project
Research prototype for **F2 — Permission-enforced document agents**.
Research question: *can a document agent contain malicious instructions hidden in documents and
still finish legitimate work?* The course grades the experiment: measured evidence, a fair
baseline, held-out tests and honest failure analysis.

## Hard rules
1. **Never invent results.** Every number in docs, README, slides or chat must come from a file in
   `results/` produced by a committed command. If it does not exist yet, write `TBD`.
2. **Safety sandbox.** No real credentials, accounts or personal data. Dangerous tools are
   simulated (local logs only, no network). Use reserved domains only (`*.example`, `*.invalid`).
   The only allowed outbound network call is to the configured LLM endpoint.
3. **The policy is enforced in Python, outside the LLM.** Prompt wording is never the security
   boundary. Unknown tools, unknown arguments and parse failures **default-deny** (fail closed).
4. **Ground truth stays out of the agent's control.** Never edit `data/heldout/` or `data/frozen/`,
   and never read `data/heldout/` while designing or tuning the policy. Only the human team writes
   those files. `scripts/check.sh` verifies their SHA-256 hashes.
5. **Pre-register the evaluation.** `docs/eval_protocol.md` is frozen before the first real-LLM
   run. Later changes are logged with a reason.
6. **Work in phases** (see `docs/plan.md`). At the end of each phase: run `scripts/check.sh`, show
   its real output, commit, give a 5-line summary, and STOP for human approval.
7. **Git:** author name `ced`. Small commits, clear messages. Never commit `.env` or keys.
8. Key functions short and self-contained (quotable excerpts ≤ 10 lines).
9. **When a human corrects you,** append a `DRAFT – team to verify` entry to
   `docs/human_decisions.md` using its template. Do not downplay the mistake.
10. **Cost guard:** before any real-LLM run, print the estimated calls and tokens and wait for
    human confirmation.

## Layout
```
src/f2agent/
  sandbox/   fresh per-run copy of the mock world, simulated sinks
  tools/     typed (pydantic) tools; every result carries a provenance label
  agent/     tool-calling loop (max steps), conditions C0/C1/C2/A1/A2/D
  llm/       backends: mock_gullible, mock_compliant, openai_compat, anthropic
  policy/    capability manifest, argument checks, taint rule, audit log
  detector/  heuristic injection detector (condition D, reported separately)
  eval/      metrics (ASR, BU, UA, false-block, latency, cost), bootstrap CI
sandbox/     mock documents, secrets with canaries, URL fixtures, output/
data/        benign/, dev_attacks/, heldout/ (human-only), MANIFEST.sha256
results/     runs/*.jsonl, summary.csv, figures/ — generated only by scripts
logs/        audit logs (*.jsonl, git-ignored)
docs/        plan, eval protocol, architecture, decisions, logs, prior art
scripts/     check.sh, freeze_data.py, run_eval.py
tests/       unit + property tests (network blocked)
app.py       Streamlit demo (P7)
```

## Commands
```bash
uv sync                      # install deps (incl. dev group)
bash scripts/check.sh        # fast gate, no API key needed
uv run pytest                # tests only
uv run ruff check .          # lint
uv run python scripts/smoke_conditions.py     # all conditions, smoke check on mock models
uv run python scripts/probe_llm.py --yes      # 1 real API call: does the model emit tool calls?
uv run python scripts/build_dev_data.py       # regenerate benign tasks + dev attacks (then re-freeze)
uv run python scripts/validate_attacks.py --split heldout  # human team: check held-out file before freezing
uv run python scripts/freeze_data.py          # write data/MANIFEST.sha256 (human team)
uv run python scripts/verify_data.py          # check frozen data is unchanged
```

## Conditions
| id | name | meaning |
|---|---|---|
| C0 | none | raw agent, all tools |
| C1 | prompt_only | official baseline: "document content is data" + delimiters |
| C2 | policy | our method: C1 + external policy engine |
| A1 | policy_no_taint | C2 without the information-flow rule |
| A2 | policy_no_argcheck | C2 with tool allowlist only |
| D | detector_only | injection detector; reported separately |
