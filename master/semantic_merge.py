"""Three-way merge of Python by symbol, not by line.

Functions, classes (method by method), imports and other top-level statements are compared one by one: changes to
different symbols never conflict, imports are united, a rename on one side is followed by the other side's edit.
Only when both sides changed the same symbol differently is it a conflict, which the caller may hand to a resolver.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

import ts_symbols


@dataclass
class Conflict:
    name: str
    base: str
    ours: str
    theirs: str


def _segment(lines: list[str], node: ast.stmt) -> str:
    start = min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])
    return "\n".join(lines[start - 1 : node.end_lineno])


def _key(node: ast.stmt, text: str) -> str:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return f"def {node.name}"
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, ast.Import | ast.ImportFrom):
        return f"import {ast.dump(node)}"
    if isinstance(node, ast.Assign | ast.AnnAssign):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return "set " + ",".join(ast.unparse(t) for t in targets)
    return f"stmt {' '.join(text.split())[:200]}"


def symbols(source: str) -> dict[str, str]:
    """{symbol key: its source text}, in file order. SyntaxError when the file does not parse."""
    lines = source.splitlines()
    out: dict[str, str] = {}
    for node in ast.parse(source).body:
        text = _segment(lines, node)
        out[_key(node, text)] = text
    return out


def _shape(text: str, key: str) -> str:
    """A function or class without its own name: equal shapes mean one was renamed into the other."""
    name = key.split(" ", 1)[1]
    return re.sub(rf"\b{re.escape(name)}\b", "_", text)


def _renames(base: dict[str, str], side: dict[str, str]) -> dict[str, str]:
    removed = {k: _shape(v, k) for k, v in base.items() if k not in side and k.startswith(("def ", "class "))}
    added = {k: _shape(v, k) for k, v in side.items() if k not in base and k.startswith(("def ", "class "))}
    return {old: new for old, shape in removed.items() for new, other in added.items() if shape == other}


def _follow(base: dict[str, str], renamed: dict[str, str], other: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Move the other side (and the base) to the new names, so its edits land on the renamed symbol."""
    for old, new in renamed.items():
        old_name, new_name = old.split(" ", 1)[1], new.split(" ", 1)[1]

        def rename(text: str, old_name: str = old_name, new_name: str = new_name) -> str:
            return re.sub(rf"\b{re.escape(old_name)}\b", new_name, text)

        base = {(new if k == old else k): rename(v) for k, v in base.items()}
        other = {(new if k == old else k): rename(v) for k, v in other.items()}
    return base, other


def _class_parts(text: str) -> tuple[str, dict[str, str]]:
    """(class header, {member key: source}) of one class segment."""
    node = ast.parse(text).body[0]
    lines = text.splitlines()
    head = "\n".join(lines[: node.body[0].lineno - 1]) if node.body[0].lineno > node.lineno else lines[0]
    members = {}
    for member in node.body:
        segment = _segment(lines, member)
        members[_key(member, segment)] = segment
    return head, members


def _pick(key: str, versions: tuple[str | None, str | None, str | None], conflicts: list[Conflict]) -> str | None:
    base, ours, theirs = versions
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    if key.startswith("class ") and base and ours and theirs:
        parts = [_class_parts(t) for t in (base, ours, theirs)]
        head = _pick(f"{key} başlığı", (parts[0][0], parts[1][0], parts[2][0]), conflicts)
        inner: list[Conflict] = []
        members = _combine(parts[0][1], parts[1][1], parts[2][1], inner)
        conflicts.extend(Conflict(f"{key}.{c.name}", c.base, c.ours, c.theirs) for c in inner)
        return head + "\n" + "\n\n".join(members)
    conflicts.append(Conflict(key, base or "", ours or "", theirs or ""))
    return ours if ours is not None else theirs


def _combine(base: dict[str, str], ours: dict[str, str], theirs: dict[str, str], conflicts: list[Conflict]) -> list[str]:
    order = list(ours) + [k for k in theirs if k not in ours]
    out = []
    for key in order:
        chosen = _pick(key, (base.get(key), ours.get(key), theirs.get(key)), conflicts)
        if chosen is not None:
            out.append(chosen)
    return out


def merge(base: str, ours: str, theirs: str) -> tuple[str, list[Conflict]]:
    """(merged source, conflicts). Where there is a conflict our version stands until it is resolved."""
    if ours == base or ours == theirs:
        return theirs, []
    if theirs == base:
        return ours, []
    b, o, t = symbols(base), symbols(ours), symbols(theirs)
    ours_renames = _renames(b, o)
    b, t = _follow(b, ours_renames, t)
    theirs_renames = _renames(b, t)
    b, o = _follow(b, theirs_renames, o)
    conflicts: list[Conflict] = []
    parts = _combine(b, o, t, conflicts)
    imports = [p for p in parts if p.startswith(("import ", "from "))]
    rest = [p for p in parts if p not in imports]
    merged = ("\n".join(imports) + "\n\n\n" if imports else "") + "\n\n\n".join(rest) + "\n"
    ast.parse(merged)
    return merged, conflicts


def merge_script(base: str, ours: str, theirs: str, suffix: str) -> tuple[str, list[Conflict]] | None:
    """The same three-way merge for JavaScript and TypeScript, symbol by symbol; None when a version does not parse."""
    parsed = [ts_symbols.top_level(text, suffix) for text in (base, ours, theirs)]
    if any(p is None for p in parsed):
        return None
    if ours == base or ours == theirs:
        return theirs, []
    if theirs == base:
        return ours, []
    b, o, t = ({s.key: s.text for s in p} for p in parsed)
    renamed = _renames(b, o)
    b, t = _follow(b, renamed, t)
    b, o = _follow(b, _renames(b, t), o)
    conflicts: list[Conflict] = []
    parts = _combine(b, o, t, conflicts)
    imports = [p for p in parts if p.startswith("import ")]
    merged = "\n".join(imports) + ("\n\n" if imports else "") + "\n\n".join(p for p in parts if p not in imports) + "\n"
    return (merged, conflicts) if ts_symbols.top_level(merged, suffix) is not None else None


def replace_symbol(source: str, name: str, text: str) -> str:
    """Put a resolved version of one top-level symbol (or `class X.def y`) into the merged source."""
    top = name.split(".", 1)[0]
    current = symbols(source)
    if top not in current:
        return source
    if "." not in name:
        result = source.replace(current[top], text, 1)
    else:
        _head, members = _class_parts(current[top])
        old = members.get(name.split(".", 1)[1], "")
        indent = " " * (len(old) - len(old.lstrip())) if old else "    "
        body = "\n".join(indent + line if line.strip() else line for line in _dedent(text))
        result = source.replace(current[top], current[top].replace(old, body, 1), 1) if old else source
    ast.parse(result)
    return result


def _dedent(text: str) -> list[str]:
    lines = text.strip("\n").splitlines()
    margin = min((len(x) - len(x.lstrip()) for x in lines if x.strip()), default=0)
    return [x[margin:] for x in lines]
