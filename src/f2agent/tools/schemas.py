"""Typed (pydantic) arguments and results for the eight sandbox tools."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
URL_PATTERN = r"^https?://[^\s]+$"


class Provenance(StrEnum):
    TRUSTED_USER = "trusted_user"
    UNTRUSTED_DOC = "untrusted_doc"
    SECRET = "secret"  # noqa: S105 (a label, not a password)


class Args(BaseModel):
    """Base: unknown arguments and type coercion are rejected (fail closed)."""

    model_config = ConfigDict(extra="forbid", strict=True)


class NoArgs(Args):
    pass


class DocIdArgs(Args):
    doc_id: str = Field(min_length=1, max_length=64)


class SearchArgs(Args):
    query: str = Field(min_length=1, max_length=200)


class ReadFileArgs(Args):
    path: str = Field(min_length=1, max_length=256)


class WriteNoteArgs(Args):
    filename: str = Field(min_length=1, max_length=256)
    content: str = Field(max_length=20_000)


class SendEmailArgs(Args):
    to: str = Field(pattern=EMAIL_PATTERN, max_length=254)
    subject: str = Field(max_length=300)
    body: str = Field(max_length=20_000)


class FetchUrlArgs(Args):
    url: str = Field(pattern=URL_PATTERN, max_length=2048)


class ToolResult(BaseModel):
    ok: bool
    content: str = ""
    provenance: Provenance = Provenance.TRUSTED_USER
    error: str = ""
