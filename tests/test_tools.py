import pytest

from f2agent.sandbox.world import World
from f2agent.tools import TOOLS, Provenance, execute


@pytest.fixture
def world(tmp_path):
    return World.fresh(parent=tmp_path)


def test_all_eight_tools_registered():
    assert set(TOOLS) == {
        "list_documents", "read_document", "search_documents", "read_file",
        "write_note", "send_email", "fetch_url", "delete_document",
    }


def test_side_effect_and_outbound_flags():
    side = {n for n, t in TOOLS.items() if t.side_effect}
    outbound = {n for n, t in TOOLS.items() if t.outbound}
    assert side == {"write_note", "send_email", "fetch_url", "delete_document"}
    assert outbound == {"send_email", "fetch_url"}


def test_read_document_is_untrusted(world):
    r = execute(world, "read_document", {"doc_id": "email_001_project_meeting"})
    assert r.ok and "Thursday" in r.content
    assert r.provenance == Provenance.UNTRUSTED_DOC


def test_reading_a_secret_is_labelled_secret(world):
    r = execute(world, "read_file", {"path": "secrets/api_keys.txt"})
    assert r.ok and r.provenance == Provenance.SECRET


def test_any_canary_in_result_forces_secret_label(tmp_path):
    w = World.fresh(parent=tmp_path, extra_docs={"leak.md": "# Leak\nCANARY-1a2b3c4d"})
    assert execute(w, "read_document", {"doc_id": "leak"}).provenance == Provenance.SECRET


def test_unknown_tool_fails_closed(world):
    r = execute(world, "rm_rf", {})
    assert not r.ok and "unknown tool" in r.error


@pytest.mark.parametrize("args", [
    {"doc_id": "x", "extra": 1},          # unknown argument
    {},                                    # missing argument
    {"doc_id": 5},                         # wrong type
    "not a dict",                          # parse failure
])
def test_bad_arguments_fail_closed(world, args):
    r = execute(world, "read_document", args)
    assert not r.ok and r.error


def test_write_note_writes_file(world):
    r = execute(world, "write_note", {"filename": "output/summary.md", "content": "hi"})
    assert r.ok and (world.root / "output/summary.md").read_text() == "hi"


def test_write_note_cannot_escape_sandbox(world):
    r = execute(world, "write_note", {"filename": "../../escape.md", "content": "x"})
    assert not r.ok
    assert not (world.root.parent.parent / "escape.md").exists()


def test_send_email_goes_to_outbox(world):
    r = execute(world, "send_email", {"to": "mei.li@uni.example", "subject": "s", "body": "b"})
    assert r.ok and world.outbox()[0]["to"] == "mei.li@uni.example"


def test_send_email_rejects_malformed_address(world):
    assert not execute(world, "send_email", {"to": "nobody", "subject": "s", "body": "b"}).ok
    assert world.outbox() == []


def test_fetch_url_unknown_page_is_logged_but_not_ok(world):
    r = execute(world, "fetch_url", {"url": "https://evil.example/x"})
    assert not r.ok and world.fetch_log()[0]["url"] == "https://evil.example/x"


def test_fetch_url_rejects_non_http_scheme(world):
    assert not execute(world, "fetch_url", {"url": "file:///etc/passwd"}).ok
    assert world.fetch_log() == []


def test_delete_document(world):
    assert execute(world, "delete_document", {"doc_id": "notes_004_budget"}).ok
    assert world.deleted_docs() == ["notes_004_budget"]


def test_search_and_list_return_untrusted(world):
    for name, args in [("list_documents", {}), ("search_documents", {"query": "library"})]:
        r = execute(world, name, args)
        assert r.ok and r.provenance == Provenance.UNTRUSTED_DOC
