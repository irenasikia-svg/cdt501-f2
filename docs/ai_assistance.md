# AI assistance disclosure

Which AI agent/model produced what, and how the team verified it. Completed in P8.

| Artefact | Produced by (agent / model) | Human role | How verified |
|---|---|---|---|
| `docs/plan.md` | Claude Code (cloud session) | ced answered P0 questions, approved plan | review by ced |
| Repo scaffold (P1) | Claude Code (cloud session) | ced to review | `scripts/check.sh` output |
| Sandbox, tools, audit log (P2) | Claude Code (cloud session) | ced approved phase | unit + property tests |
| Agent loop, backends, C0/C1 (P3) | Claude Code (cloud session) | ced approved phase | unit tests, mock smoke script |
| Policy engine C2, A1/A2, detector D (P4) | Claude Code (cloud session) | ced to review | unit + Hypothesis tests; manual review `docs/security_review.md` |

## Held-out attack set
- The human team used **Codex** (OpenAI) to help draft held-out injection text (reported by ced on
  2026-11-04). Model as reported by ced: "6 luna" (exact model id TBD, team to confirm). Codex ran
  **inside this repository** (confirmed by ced on 2026-11-04), so it could read the policy code.
  The held-out set is therefore treated as **white-box (adaptive) attacks**: unseen by the policy
  designer, but written with knowledge of the defence. TBD by the team: the prompts used, and who
  reviewed and edited each case.

## Notes
- The trailofbits skills named in the kickoff prompt (`property-based-testing`,
  `insecure-defaults`, `sharp-edges`) were not available in the cloud environment used for
  development. The equivalent work (Hypothesis property tests, manual fail-open review) is done by
  hand in P4 and recorded in `docs/security_review.md`.
