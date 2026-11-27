"""Where each part of a chat prompt goes, so the model can reuse what it has already read.

The local model server keeps the computation for the longest unchanged beginning of a prompt. So the beginning holds
only what stays the same from turn to turn (system instructions, the user's profile, agent instructions, pinned
rules, then the conversation so far), and everything that changes with each question (clock, retrieved memory,
search results, per-question guidance) is written next to the question at the very end.
"""

from __future__ import annotations

from typing import Any

OPEN = "[BU SORU İÇİN BAĞLAM - talimat ve bilgi; yanıtta bu bölümden söz etme]"
CLOSE = "[KULLANICININ MESAJI]"


def system_message(system_prompt: str, stable: list[str]) -> list[dict[str, Any]]:
    text = "\n\n".join(p for p in (system_prompt, *stable) if p)
    return [{"role": "system", "content": text}] if text else []


def question(prompt: str, volatile: list[str]) -> str:
    context = "\n\n".join(v for v in volatile if v)
    return f"{OPEN}\n{context}\n\n{CLOSE}\n{prompt}" if context else prompt


def shared_prefix(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> int:
    """Characters at the start that two prompts have in common (what the server can reuse)."""
    a = "".join(f"<{m['role']}>{m['content']}" for m in first)
    b = "".join(f"<{m['role']}>{m['content']}" for m in second)
    length = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        length += 1
    return length
