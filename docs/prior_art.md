# Prior art

Rule: never write a patent number or citation that has not been verified by the team.
The report needs ≥ 3 patents; the team adds them after checking Google Patents.

## Seeded by the course
| Reference | Layer | Relation to F2 |
|---|---|---|
| AgentDojo (Debenedetti et al., 2024) | benchmark | Environment + attack suite for prompt injection against tool-using agents; our ASR/BU/UA metrics follow the same spirit. |
| WO2025216701A1 | detection | Prompt-injection **detection** patent: a different layer from our **permission enforcement**. Compare with condition D. |
| CaMeL, "Defeating Prompt Injections by Design" (arXiv 2503.18813) | enforcement by design | Closest design: capabilities + information-flow control outside the LLM. |

## Patents added by the team (verified)
| Number | Title | Verified by / date | Relevance |
|---|---|---|---|
| | | | |

## Suggested search queries (for the team to run on Google Patents)
- `"prompt injection" AND (permission OR capability) AND agent`
- `"large language model" AND "tool call" AND (policy OR authorization) AND "information flow"`
- `LLM agent "taint tracking" OR "data provenance" exfiltration`
- `"indirect prompt injection" AND document AND (sandbox OR allowlist)`
