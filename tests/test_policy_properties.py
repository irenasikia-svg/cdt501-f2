"""Hypothesis invariants for the policy engine (fail-closed guarantees)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from f2agent.policy.engine import PolicyEngine
from f2agent.policy.manifest import Manifest, TaskCapabilities
from f2agent.tools import TOOLS

hexes = st.text(alphabet="0123456789abcdef", min_size=8, max_size=8)
canaries = hexes.map(lambda h: f"CANARY-{h}")
junk = st.text(max_size=30)
emails = st.sampled_from(["prof.chan@uni.example", "evil@attacker.example", "x@y.example"])
urls = st.sampled_from(["https://shuttle.uni.example/timetable", "https://evil.example/a"])

FULL = TaskCapabilities(write_paths=["output/"], email_to=["prof.chan@uni.example"],
                        fetch_urls=["https://shuttle.uni.example/timetable"],
                        delete_docs=["notes_004_budget"], untrusted_to_sink=True)
caps = st.builds(
    TaskCapabilities,
    write_paths=st.sampled_from([[], ["output/"]]),
    email_to=st.sampled_from([[], ["prof.chan@uni.example"]]),
    fetch_urls=st.sampled_from([[], ["https://shuttle.uni.example/timetable"]]),
    delete_docs=st.sampled_from([[], ["notes_004_budget"]]),
    untrusted_to_sink=st.booleans(),
)


@settings(max_examples=400)
@given(c=canaries, pre=junk, post=junk, to=emails, url=urls, field=st.sampled_from(
    ["subject", "body"]), argcheck=st.booleans())
def test_canary_in_any_argument_blocks_every_outbound_sink(c, pre, post, to, url, field,
                                                           argcheck):
    e = PolicyEngine(Manifest.from_capabilities("t", FULL), use_argcheck=argcheck)
    mail = {"to": to, "subject": "s", "body": "b", field: pre + c + post}
    assert not e.check("send_email", mail, []).allow
    assert not e.check("fetch_url", {"url": f"{url}?q={pre}{c}{post}"}, []).allow


@settings(max_examples=300)
@given(cap=caps, tool=st.sampled_from(sorted(TOOLS)), argcheck=st.booleans(),
       taint=st.booleans())
def test_any_tool_not_in_manifest_is_blocked(cap, tool, argcheck, taint):
    m = Manifest.from_capabilities("t", cap)
    e = PolicyEngine(m, use_taint=taint, use_argcheck=argcheck)
    if tool not in m.allowed_tools:
        d = e.check(tool, {}, [])
        assert not d.allow


@settings(max_examples=300)
@given(name=st.text(max_size=20), args=st.one_of(st.none(), st.text(), st.integers(),
       st.dictionaries(st.text(max_size=5), st.text(max_size=5), max_size=3)))
def test_check_never_raises_and_unknown_or_malformed_is_blocked(name, args):
    d = PolicyEngine(Manifest.from_capabilities("t", FULL)).check(name, args, [])
    if name not in TOOLS or not isinstance(args, dict):
        assert not d.allow


@settings(max_examples=400)
@given(path=st.lists(st.sampled_from(["output", "..", ".", "secrets", "docs", "a.md", ""]),
                     min_size=1, max_size=5).map("/".join))
def test_allowed_write_paths_normalise_inside_output(path):
    import posixpath
    e = PolicyEngine(Manifest.from_capabilities("t", FULL))
    if e.check("write_note", {"filename": path, "content": "x"}, []).allow:
        norm = posixpath.normpath(path)
        assert norm.startswith("output/") and ".." not in norm.split("/")
