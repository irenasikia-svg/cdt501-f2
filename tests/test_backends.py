from types import SimpleNamespace as NS

from f2agent.llm.anthropic_backend import to_anthropic
from f2agent.llm.base import parse_arguments
from f2agent.llm.openai_compat import OpenAICompatBackend
from f2agent.tools.registry import openai_tool_schemas


def test_parse_arguments_keeps_raw_string_on_failure():
    assert parse_arguments('{"a": 1}') == {"a": 1}
    assert parse_arguments("{oops") == "{oops"
    assert parse_arguments("[1,2]") == "[1,2]"     # not an object -> raw, fails closed later
    assert parse_arguments(None) == {}


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        call = NS(id="c1", function=NS(name="read_document", arguments='{"doc_id": "x"}'))
        msg = NS(content=None, tool_calls=[call])
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=11, completion_tokens=3),
                  model="served-model")


def test_openai_compat_passes_settings_and_parses_tool_calls():
    comp = FakeCompletions()
    client = NS(chat=NS(completions=comp))
    b = OpenAICompatBackend(model_id="m", base_url="https://x.invalid", api_key="k",
                            temperature=0.0, seed=7, client=client)
    r = b.complete([{"role": "user", "content": "hi"}], openai_tool_schemas())
    assert comp.kwargs["model"] == "m" and comp.kwargs["seed"] == 7
    assert comp.kwargs["temperature"] == 0.0
    assert r.tool_calls[0].name == "read_document" and r.tool_calls[0].arguments == {"doc_id": "x"}
    assert (r.prompt_tokens, r.completion_tokens) == (11, 3)


def test_tool_schemas_forbid_extra_arguments():
    schemas = {s["function"]["name"]: s["function"]["parameters"] for s in openai_tool_schemas()}
    assert len(schemas) == 8
    assert schemas["send_email"]["additionalProperties"] is False


def test_anthropic_conversion_groups_tool_results():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "a", "type": "function",
                         "function": {"name": "list_documents", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "a", "content": "[]"},
    ]
    system, out = to_anthropic(msgs)
    assert system == "sys"
    assert out[1]["content"][0]["type"] == "tool_use"
    assert out[2]["role"] == "user" and out[2]["content"][0]["type"] == "tool_result"
