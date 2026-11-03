"""Fail if any frozen data file changed, disappeared, or was added without re-freezing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeze_data import MANIFEST, ROOT, frozen_files, sha256  # noqa: E402


def main() -> int:
    if not MANIFEST.exists():
        print("FAIL: data/MANIFEST.sha256 missing (run scripts/freeze_data.py)")
        return 1
    expected = dict(reversed(line.split("  ", 1)) for line in MANIFEST.read_text().splitlines())
    actual = {p.relative_to(ROOT).as_posix(): sha256(p) for p in frozen_files()}
    problems = [f"changed: {f}" for f in expected if f in actual and actual[f] != expected[f]]
    problems += [f"missing: {f}" for f in expected if f not in actual]
    problems += [f"not frozen: {f}" for f in actual if f not in expected]
    for p in problems:
        print("FAIL", p)
    print(f"{len(expected)} frozen files, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
