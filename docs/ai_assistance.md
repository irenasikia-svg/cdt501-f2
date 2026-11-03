# AI assistance disclosure

Which AI agent/model produced what, and how the team verified it. Completed in P8.

| Artefact | Produced by (agent / model) | Human role | How verified |
|---|---|---|---|
| `docs/plan.md` | Claude Code (cloud session) | ced answered P0 questions, approved plan | review by ced |
| Repo scaffold (P1) | Claude Code (cloud session) | ced to review | `scripts/check.sh` output |

## Notes
- The trailofbits skills named in the kickoff prompt (`property-based-testing`,
  `insecure-defaults`, `sharp-edges`) were not available in the cloud environment used for
  development. The equivalent work (Hypothesis property tests, manual fail-open review) is done by
  hand in P4 and recorded in `docs/security_review.md`.
