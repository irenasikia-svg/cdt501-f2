"""Property tests: path handling and tool dispatch never fail open."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from f2agent.sandbox.world import SandboxEscapeError, World
from f2agent.tools import TOOLS, execute

SETTINGS = settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
path_parts = st.sampled_from(["..", ".", "_state", "secrets", "output", "docs", "x", "/", "~"])
paths = st.lists(path_parts, min_size=1, max_size=6).map("/".join) | st.text(max_size=40)


@SETTINGS
@given(rel=paths)
def test_resolved_paths_stay_inside_root_and_outside_state(tmp_path, rel):
    w = World(tmp_path)
    try:
        p = w.resolve_inside(rel)
    except (SandboxEscapeError, ValueError, OSError):
        return
    assert p.is_relative_to(w.root)
    assert not p.is_relative_to(w.root / "_state")


@SETTINGS
@given(name=st.text(max_size=20).filter(lambda n: n not in TOOLS),
       args=st.dictionaries(st.text(max_size=5), st.text(max_size=5), max_size=3))
def test_unknown_tools_never_succeed(tmp_path, name, args):
    assert not execute(World(tmp_path), name, args).ok
