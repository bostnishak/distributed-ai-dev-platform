"""After two failed repairs the model starts over from a clean context.

A small model that has seen its own broken attempts repeats them. The fresh prompt carries only the frozen
requirements, the current file, the measured failure and one line per approach that already failed.
"""

from __future__ import annotations

import difflib

from prompt_loader import load_prompt

AFTER_FAILURES = 2


def failed_approach(before: str, after: str, outcome: str) -> str:
    """One line describing a patch that did not help, for the ban list."""
    added = [line[1:].strip() for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0) if line.startswith("+") and not line.startswith("+++") and line[1:].strip()]
    change = added[0][:100] if added else "hiçbir satır eklenmedi"
    return f"{len(added)} satır eklenen deneme ('{change}') -> sonuç: {(outcome.strip().splitlines() or ['aynı hata'])[-1][:140]}"


def ban_list(banned: list[str]) -> str:
    return "\n\nDENENİP BAŞARISIZ OLAN YOLLAR (TEKRARLAMA):\n" + "\n".join(f"- {line}" for line in banned[-5:]) if banned else ""


def prompt(requirements: str, name: str, code: str, diagnosis: str, banned: list[str]) -> str:
    return (
        load_prompt("clean_slate.txt")
        + (f"\nKOŞULLAR:\n{requirements}\n" if requirements else "")
        + f"\nÖLÇÜLEN SORUN:\n{diagnosis}\n\nMEVCUT `{name}`:\n{code}"
        + ban_list(banned)
    )
