"""LLM backends: deterministic mocks and real OpenAI-compatible / Anthropic models."""

from f2agent.llm.base import LLMBackend, LLMResponse, ToolCall
from f2agent.llm.mock import Injection, PlannedCall, ScriptedModel

BACKENDS = ("mock_gullible", "mock_compliant", "openai_compat", "anthropic")


def make_backend(name: str, task=None, injections=()) -> LLMBackend:
    """Create a backend. Mocks need the trusted task's reference plan (and the injections)."""
    if name in ("mock_gullible", "mock_compliant"):
        obey = name == "mock_gullible"
        return ScriptedModel(task.reference_plan, injections=injections, obey=obey, name=name)
    if name == "openai_compat":
        from f2agent.llm.openai_compat import OpenAICompatBackend
        return OpenAICompatBackend.from_env()
    if name == "anthropic":
        from f2agent.llm.anthropic_backend import AnthropicBackend
        return AnthropicBackend.from_env()
    raise ValueError(f"unknown backend: {name}")


__all__ = ["BACKENDS", "Injection", "LLMBackend", "LLMResponse", "PlannedCall", "ScriptedModel",
           "ToolCall", "make_backend"]
