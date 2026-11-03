"""Mock sandbox world. Every run works on a fresh copy; sinks only write local state files."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[3]
SANDBOX_TEMPLATE = REPO_ROOT / "sandbox"
STATE_DIR = "_state"
DOC_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
DOC_SUFFIXES = (".md", ".html", ".csv", ".txt")


class SandboxEscapeError(ValueError):
    """A path tried to leave the world root or touch the evaluator's state files."""


class World:
    def __init__(self, root: Path):
        self.root = root.resolve()
        (self.root / STATE_DIR).mkdir(exist_ok=True)

    @classmethod
    def fresh(cls, parent: Path | None = None, template: Path = SANDBOX_TEMPLATE,
              extra_docs: dict[str, str] | None = None) -> World:
        root = Path(tempfile.mkdtemp(prefix="world_", dir=parent)) / "world"
        shutil.copytree(template, root, ignore=shutil.ignore_patterns(STATE_DIR, ".gitkeep"))
        (root / "output").mkdir(exist_ok=True)
        for name, text in (extra_docs or {}).items():
            (root / "docs" / Path(name).name).write_text(text, encoding="utf-8")
        return cls(root)

    # ---- locations -------------------------------------------------------
    docs_dir = property(lambda self: self.root / "docs")
    secrets_dir = property(lambda self: self.root / "secrets")
    output_dir = property(lambda self: self.root / "output")
    outbox_path = property(lambda self: self.root / STATE_DIR / "outbox.jsonl")
    fetch_log_path = property(lambda self: self.root / STATE_DIR / "fetch_log.jsonl")
    deleted_path = property(lambda self: self.root / STATE_DIR / "deleted.json")

    def resolve_inside(self, rel_path: str) -> Path:
        """Resolve a world-relative path; refuse anything outside root or inside _state/."""
        if not rel_path or Path(rel_path).is_absolute():
            raise SandboxEscapeError(f"path must be relative: {rel_path!r}")
        p = (self.root / rel_path).resolve()
        state = (self.root / STATE_DIR).resolve()
        if not p.is_relative_to(self.root) or p == state or p.is_relative_to(state):
            raise SandboxEscapeError(f"path outside sandbox: {rel_path!r}")
        return p

    # ---- documents -------------------------------------------------------
    def _doc_path(self, doc_id: str) -> Path:
        if not DOC_ID_RE.match(doc_id) or doc_id in self.deleted_docs():
            raise KeyError(doc_id)
        for suffix in DOC_SUFFIXES:
            p = self.docs_dir / f"{doc_id}{suffix}"
            if p.is_file():
                return p
        raise KeyError(doc_id)

    def _doc_ids(self) -> list[str]:
        deleted = set(self.deleted_docs())
        ids = {p.stem for p in self.docs_dir.iterdir() if p.suffix in DOC_SUFFIXES}
        return sorted(i for i in ids if DOC_ID_RE.match(i) and i not in deleted)

    def list_documents(self) -> list[dict[str, str]]:
        return [{"id": i, "title": _title(self._doc_path(i))} for i in self._doc_ids()]

    def read_document(self, doc_id: str) -> str:
        return self._doc_path(doc_id).read_text(encoding="utf-8")

    def search_documents(self, query: str) -> list[dict[str, str]]:
        q, hits = query.casefold(), []
        for d in self.list_documents():
            text = self.read_document(d["id"])
            pos = text.casefold().find(q)
            if pos >= 0:
                hits.append({**d, "snippet": text[max(0, pos - 40): pos + 80]})
        return hits

    def delete_document(self, doc_id: str) -> None:
        self._doc_path(doc_id)  # raises KeyError if unknown
        self.deleted_path.write_text(json.dumps(self.deleted_docs() + [doc_id]))

    def deleted_docs(self) -> list[str]:
        return json.loads(self.deleted_path.read_text()) if self.deleted_path.exists() else []

    # ---- files -----------------------------------------------------------
    def read_file(self, rel_path: str) -> str:
        return self.resolve_inside(rel_path).read_text(encoding="utf-8")

    def write_file(self, rel_path: str, content: str) -> Path:
        p = self.resolve_inside(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def contacts(self) -> dict[str, str]:
        return json.loads((self.root / "contacts.json").read_text(encoding="utf-8"))

    # ---- simulated outbound sinks ---------------------------------------
    def append_outbox(self, to: str, subject: str, body: str) -> None:
        _append_jsonl(self.outbox_path, {"to": to, "subject": subject, "body": body})

    def outbox(self) -> list[dict]:
        return _read_jsonl(self.outbox_path)

    def fetch(self, url: str) -> str | None:
        """Log the attempted URL, then serve it from local fixtures only (no network)."""
        _append_jsonl(self.fetch_log_path, {"url": url})
        parts = urlsplit(url)
        key = f"{parts.scheme}://{parts.netloc}{parts.path}"
        fixtures = json.loads((self.root / "fixtures/urls.json").read_text(encoding="utf-8"))
        return fixtures.get(key)

    def fetch_log(self) -> list[dict]:
        return _read_jsonl(self.fetch_log_path)


def _title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        first = text.splitlines()[0] if text else ""
        return first.removeprefix("# ").strip() or path.name
    if path.suffix == ".html":
        m = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
        return m.group(1).strip() if m else path.name
    return path.name


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
