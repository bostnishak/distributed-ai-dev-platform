"""Hypothesis-driven repair of a failing project test.

The model proposes root causes, each with a line copied from the test output; a hypothesis whose evidence is not in the
output is discarded. A fix is kept only when the tests then pass, and never by deleting assertions; otherwise the file
is put back exactly as it was.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

import gateway
import patch_edit
from prompt_loader import load_prompt
from workspace_checks import extract_file

_log = logging.getLogger(__name__)
_ASSERT_RE = re.compile(r"\bassert\w*\b")
_SKIP_RE = re.compile(r"@(?:pytest\.mark\.|unittest\.)(?:skip|xfail)")

Chat = Callable[[str, str, dict], Awaitable[str]]
Regenerate = Callable[[str, str], Awaitable[str]]


class Hypothesis(BaseModel):
    file: str
    evidence: str
    cause: str = ""


class Audit(BaseModel):
    hypotheses: list[Hypothesis] = []


async def _ask(system: str, user: str, schema: dict) -> str:
    res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b", profile="extract",
                                            format_schema=schema, num_predict=700, num_ctx=8192, timeout_s=240.0, feature="debugger", max_retries=0)
    return res.content


def sources(ws_dir: Path) -> dict[str, str]:
    skip = {".history", "venv", ".venv", "__pycache__"}
    return {p.relative_to(ws_dir).as_posix(): p.read_text(encoding="utf-8", errors="replace") for p in sorted(ws_dir.rglob("*.py")) if not skip & set(p.parts)}


def grounded(audit: Audit, log: str, files: dict[str, str]) -> list[Hypothesis]:
    """Hypotheses that point at a real file and quote the real output."""
    flat = " ".join(log.split())
    return [h for h in audit.hypotheses if h.file in files and len(h.evidence.strip()) >= 8 and " ".join(h.evidence.split()) in flat]


def weakens_tests(path: str, old: str, new: str) -> bool:
    if not (path.startswith("tests/") or Path(path).name.startswith("test_")):
        return False
    return len(_ASSERT_RE.findall(new)) < len(_ASSERT_RE.findall(old)) or len(_SKIP_RE.findall(new)) > len(_SKIP_RE.findall(old))


_CERTAIN = "yanlış modülden içe aktarma"
_IMPORT_RE = re.compile(r"cannot import name '(\w+)' from '(\w+)'")


def _defines(source: str, name: str) -> bool:
    try:
        body = ast.parse(source).body
    except SyntaxError:
        return False
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and node.name == name:
            return True
        if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in node.targets):
            return True
    return False


def fix_imports(log: str, files: dict[str, str]) -> dict[str, str]:
    """Model-free: a name imported from the wrong local module is imported from the one module that defines it."""
    found = _IMPORT_RE.search(log)
    if not found:
        return {}
    name, wrong = found.groups()
    owners = [path for path, body in files.items() if "/" not in path and path != f"{wrong}.py" and _defines(body, name)]
    if len(owners) != 1:
        return {}
    owner = owners[0][:-3]
    pattern = re.compile(rf"^([ \t]*)from {wrong} import ([\w ,]+)$", re.MULTILINE)

    def rewrite(match: re.Match) -> str:
        indent, names = match.group(1), [n.strip() for n in match.group(2).split(",")]
        moved = [n for n in names if n.split(" as ")[0] == name]
        if not moved:
            return match.group(0)
        kept = [n for n in names if n not in moved]
        lines = ([f"{indent}from {wrong} import {', '.join(kept)}"] if kept else []) + [f"{indent}from {owner} import {', '.join(moved)}"]
        return "\n".join(lines)

    changed = {path: pattern.sub(rewrite, body) for path, body in files.items() if path != owners[0]}
    return {path: body for path, body in changed.items() if body != files[path]}


async def _patch(system: str, user: str) -> str:
    res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b", profile="extract",
                                            num_predict=1800, num_ctx=8192, timeout_s=240.0, feature="debugger", max_retries=0)
    return res.content


async def _candidate(guess: Hypothesis, log: str, files: dict[str, str], regenerate: Regenerate, patcher: Callable[[str, str], Awaitable[str]]) -> str:
    """A new version of the guessed file: SEARCH/REPLACE blocks first, a whole-file rewrite when they do not apply."""
    old = files[guess.file]
    others = "\n\n".join(f"### {n}\n{b[:1800]}" for n, b in files.items() if n != guess.file)[:8000]
    ask = f"Dosya: `{guess.file}`\nKök neden: {guess.cause}\nKanıt: {guess.evidence}\n\nTEST ÇIKTISI:\n{log}\n\nDİĞER DOSYALAR:\n{others}\n\nMEVCUT `{guess.file}`:\n{old}"
    try:
        patched = patch_edit.apply(old, patch_edit.parse(await patcher(load_prompt("agent_debug_patch.md"), ask)))
    except (OSError, RuntimeError, ValueError) as exc:
        _log.warning("debugger patch failed: %s", exc)
        patched = None
    if patched and patched != old:
        return patched
    return extract_file(await regenerate(guess.file, ask + "\n\nDosyayı düzeltilmiş haliyle eksiksiz döndür. Test beklentilerini silme."), ".py")


def _headline(log: str) -> str:
    """The part of a failure that says what is wrong (so two runs can be compared)."""
    return next((line.strip() for line in log.splitlines() if line.startswith("E ")), "")


@dataclass(frozen=True)
class Models:
    """The two model calls of the debugger, replaceable in tests."""

    chat: Chat = _ask
    patcher: Callable[[str, str], Awaitable[str]] = _patch


def _write(ws_dir: Path, files: dict[str, str]) -> None:
    for path, body in files.items():
        (ws_dir / path).write_text(body, encoding="utf-8")


async def _propose(ws_dir: Path, log: str, regenerate: Regenerate, models: Models) -> tuple[dict[str, str], str]:
    """(file changes, cause) for one attempt; ({}, "") when there is nothing grounded to try."""
    files = sources(ws_dir)
    if certain := fix_imports(log, files):
        return certain, _CERTAIN
    listing = "\n\n".join(f"### {name}\n{body[:2500]}" for name, body in files.items())[:14000]
    try:
        audit = Audit.model_validate_json(await models.chat(load_prompt("agent_debugger.md"), f"TEST ÇIKTISI:\n{log}\n\nDOSYALAR:\n{listing}", Audit.model_json_schema()))
    except (ValidationError, ValueError, OSError, RuntimeError) as exc:
        _log.warning("debugger hypotheses failed: %s", exc)
        return {}, ""
    for guess in grounded(audit, log, files)[:2]:
        new = await _candidate(guess, log, files, regenerate, models.patcher)
        if new and new != files[guess.file] and not weakens_tests(guess.file, files[guess.file], new):
            return {guess.file: new}, f"{guess.file}: {guess.cause[:120]}"
    return {}, ""


def _verdict(first: str) -> str:
    last = (first.strip().splitlines() or ["test başarısız"])[-1]
    reason = _headline(first)
    return f"Projenin kendi testleri başarısız: {(reason + ' | ' if reason else '') + last}"[:240]


async def repair(ws_dir: Path, run_tests: Callable[[], str], regenerate: Regenerate, models: Models | None = None, rounds: int = 4) -> tuple[bool, str]:
    """(tests pass now, one line for the user). `run_tests` returns '' on success, else the output.

    Changes that move the failure forward are kept while working; unless every test passes in the end, they are undone.
    """
    log = first = await asyncio.to_thread(run_tests)
    if not log:
        return True, ""
    originals = sources(ws_dir)
    causes: list[str] = []
    seen = {_headline(log)}
    for _round in range(rounds):
        before = sources(ws_dir)
        changes, cause = await _propose(ws_dir, log, regenerate, models or Models())
        if not changes:
            break
        _write(ws_dir, changes)
        after = await asyncio.to_thread(run_tests)
        if not after:
            return True, f"Testler başta başarısızdı; kök neden bulundu ve düzeltildi ({'; '.join([*causes, cause])})."
        if _headline(after) in seen:  # no progress: take this attempt back
            _write(ws_dir, {path: before[path] for path in changes})
            continue
        if cause == _CERTAIN:
            originals.update(changes)  # a certain fix stays even if later failures remain
        seen.add(_headline(after))
        causes.append(cause)
        log = after
    _write(ws_dir, originals)
    return False, _verdict(first)
