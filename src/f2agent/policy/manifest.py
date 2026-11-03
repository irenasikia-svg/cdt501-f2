"""Task capability manifest. Built ONLY from the trusted task, never from model or doc text."""

from __future__ import annotations

import posixpath

from pydantic import BaseModel, ConfigDict

READ_TOOLS = frozenset({"list_documents", "read_document", "search_documents", "read_file"})
OUTPUT_ROOT = "output/"


class TaskCapabilities(BaseModel):
    """Written by humans together with the task (trusted). Empty = read-only task."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    write_paths: list[str] = []      # path prefixes under output/; grants write_note
    email_to: list[str] = []         # exact recipients; grants send_email
    fetch_urls: list[str] = []       # exact URLs; grants fetch_url
    delete_docs: list[str] = []      # exact doc ids; grants delete_document
    untrusted_to_sink: bool = False  # may document content flow to an outbound sink?


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    task_id: str
    allowed_tools: frozenset[str]
    write_prefixes: tuple[str, ...]
    recipients: frozenset[str]
    urls: frozenset[str]
    deletable: frozenset[str]
    untrusted_to_sink: bool

    @classmethod
    def from_capabilities(cls, task_id: str, caps: TaskCapabilities) -> Manifest:
        prefixes = tuple(_output_prefix(p) for p in caps.write_paths)
        grants = {"write_note": prefixes, "send_email": caps.email_to,
                  "fetch_url": caps.fetch_urls, "delete_document": caps.delete_docs}
        tools = READ_TOOLS | {t for t, granted in grants.items() if granted}
        return cls(task_id=task_id, allowed_tools=tools, write_prefixes=prefixes,
                   recipients=frozenset(r.lower() for r in caps.email_to),
                   urls=frozenset(caps.fetch_urls), deletable=frozenset(caps.delete_docs),
                   untrusted_to_sink=caps.untrusted_to_sink)

    def trusted_values(self) -> frozenset[str]:
        return self.recipients | self.urls | self.deletable


def _output_prefix(p: str) -> str:
    norm = posixpath.normpath(p).rstrip("/") + "/"
    if not (norm + "x").startswith(OUTPUT_ROOT) or ".." in norm.split("/"):
        raise ValueError(f"write path must be under {OUTPUT_ROOT}: {p!r}")
    return norm
