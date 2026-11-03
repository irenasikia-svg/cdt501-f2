"""Check that the configured real model can emit tool calls. Makes exactly ONE API call.

Usage: uv run python scripts/probe_llm.py --backend openai_compat --yes
Without --yes it only prints what it would do (cost guard, AGENTS.md rule 10).
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f2agent.llm import make_backend  # noqa: E402
from f2agent.prompts import BASE_PROMPT  # noqa: E402
from f2agent.tools.registry import openai_tool_schemas  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="openai_compat", choices=["openai_compat", "anthropic"])
    ap.add_argument("--yes", action="store_true", help="actually make the single API call")
    a = ap.parse_args()
    load_dotenv()
    est = len(json.dumps(openai_tool_schemas()) + BASE_PROMPT) // 4  # rough: 4 chars/token
    print(f"Plan: 1 call to backend={a.backend}, ~{est} prompt tokens (estimate).")
    if not a.yes:
        print("Dry run. Re-run with --yes to make the call.")
        return
    b = make_backend(a.backend)
    msgs = [{"role": "system", "content": BASE_PROMPT},
            {"role": "user", "content": "List the documents in the workspace."}]
    r = b.complete(msgs, openai_tool_schemas())
    print(f"model_id={b.model_id} served={getattr(b, 'served_model', None)}")
    print(f"tool_calls={[(c.name, c.arguments) for c in r.tool_calls]} text={r.content[:200]!r}")
    print(f"tokens prompt={r.prompt_tokens} completion={r.completion_tokens}")
    print("PASS: model emits tool calls" if r.tool_calls else "WARN: no tool call returned")


if __name__ == "__main__":
    main()
