"""Write data/MANIFEST.sha256 for every file in the frozen data folders.

Run by the human team after (re)writing data. `scripts/verify_data.py` checks it.
Usage: uv run python scripts/freeze_data.py
"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_DIRS = ["data/benign", "data/dev_attacks", "data/heldout", "data/frozen"]
MANIFEST = ROOT / "data" / "MANIFEST.sha256"


def frozen_files() -> list[Path]:
    files = []
    for d in FROZEN_DIRS:
        files += [p for p in (ROOT / d).rglob("*") if p.is_file() and p.name != ".gitkeep"]
    return sorted(files)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    lines = [f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}" for p in frozen_files()]
    MANIFEST.write_text("\n".join(lines) + "\n")
    print(f"froze {len(lines)} files -> {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
