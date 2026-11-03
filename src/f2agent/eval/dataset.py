"""Load benign tasks and attack cases; build the per-run world for a case."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from f2agent.agent.task import Task
from f2agent.eval.checkers import AttackSuccess, BenignCheck
from f2agent.llm.mock import Injection
from f2agent.sandbox.world import REPO_ROOT, SANDBOX_TEMPLATE, World

DATA = REPO_ROOT / "data"
SPLITS = {"dev": DATA / "dev_attacks" / "attacks.json",
          "heldout": DATA / "heldout" / "attacks.json"}


class BenignCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: Task
    check: BenignCheck


class Carrier(BaseModel):
    model_config = ConfigDict(extra="forbid")
    carrier_doc: str
    injection_text: str
    position: str = "end"
    new_doc: bool = False         # True: create docs/<carrier_doc>.md containing only the text


class AttackCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    family: str
    goal: str
    task_id: str                  # the legitimate task this attack rides on
    carrier_doc: str              # doc id whose text receives the injection
    injection_text: str           # inserted into the carrier
    position: str = "end"         # "end" | "start"
    new_doc: bool = False         # True: carrier is a new document with only the injection
    extra_carriers: list[Carrier] = []  # e.g. an instruction split across two documents
    injection: Injection          # what mock_gullible does once it sees the text
    success: AttackSuccess


def load_benign(path: Path = DATA / "benign" / "tasks.json") -> list[BenignCase]:
    return [BenignCase.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8"))]


def load_tasks(split: str = "dev") -> list[BenignCase]:
    """Benign tasks plus any extra tasks the human team added for the held-out split."""
    extra = DATA / "heldout" / "tasks.json"
    return load_benign() + (load_benign(extra) if split == "heldout" and extra.exists() else [])


def load_attacks(split: str = "dev") -> list[AttackCase]:
    path = SPLITS[split]
    if not path.exists():
        return []
    return [AttackCase.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8"))]


def carrier_text(case: AttackCase | Carrier, template: Path = SANDBOX_TEMPLATE) -> tuple[str, str]:
    """Return (file name, carrier text with the injection inserted)."""
    if case.new_doc:
        return f"{case.carrier_doc}.md", case.injection_text + "\n"
    [src] = [p for p in (template / "docs").iterdir() if p.stem == case.carrier_doc]
    text = src.read_text(encoding="utf-8")
    if case.position == "start":
        return src.name, case.injection_text + "\n\n" + text
    if "</body>" in text:
        return src.name, text.replace("</body>", case.injection_text + "\n</body>")
    return src.name, text.rstrip("\n") + "\n\n" + case.injection_text + "\n"


def build_world(parent: Path, attack: AttackCase | None = None) -> World:
    parent.mkdir(parents=True, exist_ok=True)
    extra = dict(carrier_text(c) for c in [attack, *attack.extra_carriers]) if attack else None
    return World.fresh(parent=parent, extra_docs=extra)
