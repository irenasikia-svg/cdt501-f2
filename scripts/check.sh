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

E2E_DIR="$(mktemp -d)"
run_step "e2e mock (dev): C0/C1 attacked, C2 ASR=0, C2 BU>=0.90" \
  uv run python scripts/run_eval.py --backend mock_gullible --split dev \
  --out-dir "$E2E_DIR" --assert-gates
rm -rf "$E2E_DIR"

run_step "results metadata complete" uv run python scripts/check_results_metadata.py

echo; echo "================ SUMMARY ================"
fail=0
for i in "${!NAMES[@]}"; do
  printf '%-55s %s\n' "${NAMES[$i]}" "${STATUS[$i]}"
  [[ "${STATUS[$i]}" == FAIL ]] && fail=1
done
if [[ $fail -eq 0 ]]; then echo "OVERALL: PASS (SKIP = not built yet)"; else echo "OVERALL: FAIL"; fi
exit $fail
