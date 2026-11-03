"""Tool registry and dispatcher. Unknown tools and invalid arguments fail closed."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from f2agent.sandbox.canary import find_canaries
from f2agent.sandbox.world import SandboxEscapeError, World
from f2agent.tools.schemas import (
    DocIdArgs,
    FetchUrlArgs,
    NoArgs,
    Provenance,
    ReadFileArgs,
    SearchArgs,
    SendEmailArgs,
    ToolResult,
    WriteNoteArgs,
)

U, T = Provenance.UNTRUSTED_DOC, Provenance.TRUSTED_USER


@dataclass(frozen=True)
class ToolSpec:
    name: str
    args_model: type[BaseModel]
    run: Callable[[World, BaseModel], tuple[str, Provenance]]
    side_effect: bool = False
    outbound: bool = False
    description: str = ""


def _read_file(w: World, a: ReadFileArgs) -> tuple[str, Provenance]:
    in_secrets = w.resolve_inside(a.path).is_relative_to(w.secrets_dir)
    return w.read_file(a.path), Provenance.SECRET if in_secrets else U


def _write_note(w: World, a: WriteNoteArgs) -> tuple[str, Provenance]:
    w.write_file(a.filename, a.content)
    return f"wrote {a.filename}", T


def _send_email(w: World, a: SendEmailArgs) -> tuple[str, Provenance]:
    w.append_outbox(a.to, a.subject, a.body)
    return f"email sent to {a.to}", T


def _fetch_url(w: World, a: FetchUrlArgs) -> tuple[str, Provenance]:
    page = w.fetch(a.url)
    if page is None:
        raise LookupError(f"404 not found: {a.url}")
    return page, U


def _delete(w: World, a: DocIdArgs) -> tuple[str, Provenance]:
    w.delete_document(a.doc_id)
    return f"deleted {a.doc_id}", T


def _dump(x: object) -> str:
    return json.dumps(x, ensure_ascii=False)


TOOLS: dict[str, ToolSpec] = {s.name: s for s in [
    ToolSpec("list_documents", NoArgs, lambda w, a: (_dump(w.list_documents()), U),
             description="List document ids and titles."),
    ToolSpec("read_document", DocIdArgs, lambda w, a: (w.read_document(a.doc_id), U),
             description="Read one document by id."),
    ToolSpec("search_documents", SearchArgs,
             lambda w, a: (_dump(w.search_documents(a.query)), U),
             description="Case-insensitive text search over documents."),
    ToolSpec("read_file", ReadFileArgs, _read_file,
             description="Read a file by path relative to the workspace."),
    ToolSpec("write_note", WriteNoteArgs, _write_note, side_effect=True,
             description="Write a text file (e.g. output/summary.md)."),
    ToolSpec("send_email", SendEmailArgs, _send_email, side_effect=True, outbound=True,
             description="Send an email."),
    ToolSpec("fetch_url", FetchUrlArgs, _fetch_url, side_effect=True, outbound=True,
             description="Fetch a web page by URL."),
    ToolSpec("delete_document", DocIdArgs, _delete, side_effect=True,
             description="Delete a document by id."),
]}


def parse_args(name: str, raw_args: object) -> BaseModel:
    """Validate raw arguments for a tool. Raises KeyError / ValidationError / TypeError."""
    if name not in TOOLS:
        raise KeyError(f"unknown tool: {name}")
    if not isinstance(raw_args, dict):
        raise TypeError("arguments must be a JSON object")
    return TOOLS[name].args_model.model_validate(raw_args)


def execute(world: World, name: str, raw_args: object) -> ToolResult:
    """Run one tool call. Any failure returns ok=False; a canary in output forces SECRET."""
    try:
        args = parse_args(name, raw_args)
        content, prov = TOOLS[name].run(world, args)
    except KeyError as e:
        return ToolResult(ok=False, error=str(e).strip("'\""))
    except (ValidationError, TypeError, SandboxEscapeError, LookupError, OSError) as e:
        return ToolResult(ok=False, error=f"{type(e).__name__}: {e}"[:500])
    if find_canaries(content):
        prov = Provenance.SECRET
    return ToolResult(ok=True, content=content, provenance=prov)
