"""Every file in results/ must carry complete metadata (run, commit, model, data hash...)."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from f2agent.eval.runner import META_KEYS  # noqa: E402

CSV_KEYS = ["run_id", "split", "backend", "model_id", "condition", "git_commit", "temperature",
            "seed", "prompt_hash", "manifest_hash", "timestamp"]


def missing(d: dict, keys) -> list[str]:
    return [k for k in keys if k not in d or d[k] in ("", None) and k not in ("seed",)]


def main(results: Path = ROOT / "results") -> int:
    problems = []
    for p in sorted(results.rglob("*")):
        if p.is_dir() or p.name == ".gitkeep":
            continue
        rel = p.relative_to(results).as_posix()
        if p.suffix == ".jsonl":
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
                if m := missing(json.loads(line), META_KEYS):
                    problems.append(f"{rel}:{i + 1} missing {m}")
        elif p.suffix == ".csv":
            for i, row in enumerate(csv.DictReader(p.open(encoding="utf-8"))):
                if m := missing(row, CSV_KEYS):
                    problems.append(f"{rel}:{i + 2} missing {m}")
        elif p.suffix == ".png":
            meta = json.loads((p.parent / "meta.json").read_text())
            if p.name not in meta.get("files", []) or not meta.get("git_commits"):
                problems.append(f"{rel} not described in figures/meta.json")
        elif p.name == "meta.json" or (p.suffix == ".md" and "git_commit" in p.read_text()):
            continue
        else:
            problems.append(f"{rel}: unknown file without metadata")
    for x in problems[:30]:
        print("FAIL", x)
    print(f"results metadata: {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
