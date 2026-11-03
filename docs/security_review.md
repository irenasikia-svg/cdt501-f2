# Security review of the policy engine (P4)

**Scope:** `src/f2agent/policy/`, `src/f2agent/tools/`, `src/f2agent/sandbox/world.py`,
`src/f2agent/agent/loop.py`, `src/f2agent/agent/conditions.py` at the P4 commit.
**Method:** manual review aimed at fail-open paths, insecure defaults and sharp edges, plus
Hypothesis property tests (`tests/test_policy_properties.py`) and a scratch probe of transformed
secrets. The trailofbits `insecure-defaults` / `sharp-edges` skills were **not available** in the
development environment, so this review was done by hand following the same questions. A team
member with those skills installed should re-run them and append findings below.
**Author:** Claude Code (cloud session). Status: DRAFT – team to verify.

## Invariants checked by property tests
| Invariant | Test |
|---|---|
| Any argument containing a canary is blocked at every outbound sink (C2 and A2) | `test_canary_in_any_argument_blocks_every_outbound_sink` |
| Any tool not in the task manifest is blocked (all ablations) | `test_any_tool_not_in_manifest_is_blocked` |
| Unknown tool names / non-object arguments are blocked; `check` never raises | `test_check_never_raises_and_unknown_or_malformed_is_blocked` |
| An allowed write path always normalises inside `output/` | `test_allowed_write_paths_normalise_inside_output` |
| Resolved sandbox paths never leave the world root or touch `_state/` | `test_resolved_paths_stay_inside_root_and_outside_state` |

## Findings

| id | Severity | Finding | Status |
|---|---|---|---|
| SR-1 | High | **Bare canary body bypassed the taint rule.** The secret check only matched `CANARY-xxxxxxxx`. A model that dropped the prefix (`b9cb7f5f`), changed case or inserted separators (`b9 cb 7f 5f`) passed. Evidence: `test_bare_canary_body_from_read_secret_is_blocked` failed on 4 cases before the fix. | **Fixed**: canary bodies the agent has read are matched after removing non-hex characters (`taint.has_canary_body`). Test now passes. |
| SR-2 | Medium | **Transformed secrets to an allowed recipient are not detected.** Splitting a canary across messages, reversing it or spelling it out reaches `prof.chan@uni.example` when the task allows emailing (scratch probe: `split half`, `reversed`, `spelled` → allow). | **Residual risk.** Mitigated because the recipient/URL checks still stop any attacker-controlled destination. Report as a limitation; an attacker-goal "send the secret to the legitimate recipient" is out of our threat model. |
| SR-3 | Medium | **Untrusted-content taint is substring-based.** A paraphrase of document text is not recognised as document-derived, so `taint.untrusted` can miss it. | Residual risk. The destination checks (`arg.*`) are the primary barrier; `taint.untrusted` is defence in depth. |
| SR-4 | Low | `untrusted_to_sink` is one flag for all outbound sinks. With argument checks disabled (A2 only), document text can reach `fetch_url` with an attacker URL (probe: `A2 untrusted url to fetch` → allow). | Accepted: only reachable in ablation A2, which is meant to show this. C2 blocks it (`arg.url`). |
| SR-5 | Low | Reverse-substring rule (`s in untrusted content`, len ≥ 12) can **false-block** a legitimate subject line that happens to appear in a document. | Measured, not fixed: shows up in the false-block rate (P6). |
| SR-6 | Low | `read_file` may read `secrets/` in every condition ("read-only by default" allows reads). Containment of secrets relies entirely on the taint rule at sinks, so A1 (no taint) is expected to leak to allowed recipients. | By design, so that ablation A1 isolates the taint rule. |
| SR-7 | Low | Audit-log redaction only masks the literal canary pattern; an encoded canary in a blocked argument is written to `logs/` as is. | Accepted: logs are local and git-ignored. |
| SR-8 | Info | Policy and dispatcher validate the same raw arguments with the same pydantic model (`parse_args`), so there is no parse-differential between the check and the execution. | OK |
| SR-9 | Info | Every exception inside the engine becomes `block / internal_error` (`test_internal_error_fails_closed`). Blocked calls return a neutral message and never reach the sandbox. | OK |
| SR-10 | Info | The manifest is built only from `Task.capabilities`, which is written by humans with the task; model output and document text never reach `Manifest.from_capabilities`. Write grants outside `output/` are rejected at manifest build time. | OK |
