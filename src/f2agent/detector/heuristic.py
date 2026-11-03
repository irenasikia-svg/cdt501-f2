"""Heuristic prompt-injection detector (condition D). Detection is NOT containment."""

import re

PATTERNS = [
    r"\b(ignore|disregard|forget)\b.{0,20}\b(previous|prior|above|earlier|all)\b.{0,20}"
    r"\b(instructions?|directions?|rules)\b",
    r"\[\s*system\s*\]",
    r"^\s*(system|assistant)\s*(message)?\s*:",
    r"<!--.*?\b(system|instruction|ignore|send|email|forward|delete)\b.*?-->",
    r"\bnew instructions\b",
    r"\byou must (now )?(send|email|forward|delete|fetch|upload)\b",
    r"(忽略|無視|无视|忽視|忽视).{0,10}(指令|指示|说明|說明|要求)",
    r"(系统|系統)(消息|訊息|指令|通知)\s*[:：]",
]
_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL) for p in PATTERNS]


def flag_injection(text: str) -> bool:
    return any(r.search(text) for r in _RE)
