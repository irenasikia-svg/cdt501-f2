#!/usr/bin/env bash
# Fast quality gate. No API key, no network. Prints a PASS/FAIL summary.
set -uo pipefail
cd "$(dirname "$0")/.."

declare -a NAMES=() STATUS=()
record() { NAMES+=("$1"); STATUS+=("$2"); }

run_step() {  # run_step <name> <command...>
  local name="$1"; shift
  echo "== $name"
  if "$@"; then record "$name" PASS; else record "$name" FAIL; fi
}

run_step "ruff check" uv run ruff check .
run_step "pytest (unit + property, network blocked)" uv run pytest

run_step "data manifest (frozen files unchanged)" uv run python scripts/verify_data.py

echo "== end-to-end mock run (dev set)"
echo "not implemented yet (P4-P6)"; record "e2e mock: C0/C1 attacked, C2 ASR=0, C2 BU>=threshold" SKIP

echo "== results metadata"
if [[ -f scripts/check_results_metadata.py ]]; then
  run_step "results metadata" uv run python scripts/check_results_metadata.py
else
  echo "no results checker yet (P6)"; record "results metadata" SKIP
fi

echo; echo "================ SUMMARY ================"
fail=0
for i in "${!NAMES[@]}"; do
  printf '%-55s %s\n' "${NAMES[$i]}" "${STATUS[$i]}"
  [[ "${STATUS[$i]}" == FAIL ]] && fail=1
done
if [[ $fail -eq 0 ]]; then echo "OVERALL: PASS (SKIP = not built yet)"; else echo "OVERALL: FAIL"; fi
exit $fail
