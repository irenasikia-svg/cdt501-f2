# CDT501 · F2 — Permission-enforced document agents

Research prototype for the question: **can a document agent contain malicious instructions hidden
in documents and still finish legitimate work?**

> Status: under construction (phase-by-phase, see `docs/plan.md`). All results are `TBD` until
> produced by a committed command into `results/`.

## Quick start
```bash
git clone https://github.com/irenasikia-svg/cdt501-f2
cd cdt501-f2
uv sync
bash scripts/check.sh
```
Real-LLM runs need a `.env` (copy `.env.example`). Development and `check.sh` use deterministic
mock models only and need no key.

## Method (summary)
A trusted user task is turned into a **capability manifest**. Every tool call the agent proposes is
checked in Python by a **policy engine** (tool allowlist, typed argument checks, information-flow
rule, read-only by default) before it reaches a simulated sink. All decisions go to an audit log.
Details: `docs/architecture.md` (TBD, P8).

## Results
TBD (P6).

## Reproduction
TBD (P8).

## Repository layout
See `AGENTS.md`.
