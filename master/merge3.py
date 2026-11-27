"""Three-way merge so a change the user made by hand while the model was writing is never lost.

base is what the model was given, ai is what it produced, user is what is on disk now. Independent changes are both
kept; where both changed the same lines the user's lines win and the conflict is reported. A Python result that no
longer parses is rejected in favour of the user's file.
"""

from __future__ import annotations

import ast
import difflib


def _hunks(base: list[str], other: list[str]) -> list[tuple[int, int, list[str]]]:
    matcher = difflib.SequenceMatcher(a=base, b=other, autojunk=False)
    return [(i1, i2, other[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"]


def _overlap(first: tuple[int, int, list[str]], second: tuple[int, int, list[str]]) -> bool:
    a1, a2, _ = first
    b1, b2, _ = second
    return (a1 < b2 and b1 < a2) or a1 == b1 or (a1 == a2 and b1 < a1 < b2) or (b1 == b2 and a1 < b1 < a2)


def merge(base: str, ai: str, user: str, path: str = "") -> tuple[str, list[int]]:
    """(merged text, base line numbers where the model's change was dropped because the user had changed the same place)."""
    if user == base:
        return ai, []
    if ai == base or ai == user:
        return user, []
    lines = base.splitlines(keepends=True)
    mine = _hunks(lines, user.splitlines(keepends=True))
    theirs = _hunks(lines, ai.splitlines(keepends=True))
    conflicts: list[int] = []
    chosen = list(mine)
    for hunk in theirs:
        if hunk in mine:
            continue
        if any(_overlap(hunk, other) for other in mine):
            conflicts.append(hunk[0] + 1)
        else:
            chosen.append(hunk)
    out, position = [], 0
    for start, end, replacement in sorted(chosen, key=lambda h: (h[0], h[1])):
        out += lines[position:start]
        out += replacement
        position = max(position, end)
    out += lines[position:]
    merged = "".join(out)
    if path.endswith(".py"):
        try:
            ast.parse(merged)
        except SyntaxError:
            return user, sorted({h[0] + 1 for h in theirs})
    return merged, conflicts
