"""Verified clean-up of what the fitness scan finds, done by code and undone if anything stops working.

Unused CSS rules and uncalled functions are removed, exact copies of a function are replaced by one shared definition,
and an over-long module gives its largest self-contained functions to a helper module (they are imported back, so
callers keep working). After the change every Python file must parse, every name it exports must still be there and,
when the caller gives one, the project's own check must pass; otherwise the previous files are restored.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

import arch_scan
import atomic_io
import patch_edit
import refactor_move
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)
_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```")


def _snapshot(ws_dir: Path) -> dict[str, str]:
    return arch_scan.sources(ws_dir, ".py", ".css", ".html", ".js")


def _restore(ws_dir: Path, before: dict[str, str]) -> None:
    for path in _snapshot(ws_dir):
        if path not in before:
            (ws_dir / path).unlink(missing_ok=True)
    for path, text in before.items():
        atomic_io.write_text(ws_dir / path, text)


def _strip_css(text: str, selectors: set[str]) -> str:
    """Removes the dead selectors; a rule whose whole selector list is dead disappears."""

    def rewrite(match: re.Match) -> str:
        head, body = match.group(1), match.group(2)
        if head.lstrip().startswith("@"):
            return match.group(0)
        kept = [part for part in head.split(",") if not any(re.search(rf"{re.escape(s)}(?![\w-])", part) for s in selectors)]
        return ",".join(kept) + body if kept else ""

    return re.sub(r"([^{}<>;]+)(\{[^{}]*\})", rewrite, text)


_STYLE_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.DOTALL | re.IGNORECASE)


def _without(text: str, selectors: set[str], is_page: bool) -> str:
    if not is_page:
        return _strip_css(text, selectors)
    return _STYLE_RE.sub(lambda m: m.group(1) + _strip_css(m.group(2), selectors) + m.group(3), text)


def alive(ws_dir: Path) -> set[tuple[str, str]]:
    """(file, name) of every function and CSS selector that is in use now; taken before an edit."""
    dead = {(f.file, f.subject) for f in (*arch_scan.dead_functions(ws_dir), *arch_scan.dead_css(ws_dir))}
    names = {(path, n.name) for path, text in arch_scan.sources(ws_dir, ".py").items() for n in _parsed(text) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    styles = arch_scan.sources(ws_dir, ".css", ".html")
    names |= {(path, mark + name) for path, text in styles.items() for mark, name in arch_scan._CSS_RULE_RE.findall(text)}
    return names - dead


def _parsed(text: str) -> list[ast.stmt]:
    try:
        return ast.parse(text).body
    except SyntaxError:
        return []


def _removable(findings: list[arch_scan.Finding], used_before: set[tuple[str, str]] | None) -> list[arch_scan.Finding]:
    return [f for f in findings if used_before is None or (f.file, f.subject) in used_before]


def remove_dead_css(ws_dir: Path, used_before: set[tuple[str, str]] | None = None) -> list[str]:
    dead: dict[str, set[str]] = {}
    for finding in _removable(arch_scan.dead_css(ws_dir), used_before):
        dead.setdefault(finding.file, set()).add(finding.subject)
    for path, selectors in dead.items():
        atomic_io.write_text(ws_dir / path, _without((ws_dir / path).read_text(encoding="utf-8"), selectors, path.endswith(".html")))
    return [f"kullanılmayan CSS silindi: {path} ({', '.join(sorted(selectors))})" for path, selectors in dead.items()]


def _cut(source: str, name: str) -> str:
    node = next((n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == name), None)
    if node is None:
        return source
    lines = source.splitlines()
    start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
    return re.sub(r"\n{4,}", "\n\n\n", "\n".join([*lines[: start - 1], *lines[node.end_lineno :]]).rstrip() + "\n")


def remove_dead_functions(ws_dir: Path, used_before: set[tuple[str, str]] | None = None) -> list[str]:
    done = []
    for finding in _removable(arch_scan.dead_functions(ws_dir), used_before):
        path = ws_dir / finding.file
        atomic_io.write_text(path, _cut(path.read_text(encoding="utf-8"), finding.subject))
        done.append(f"çağrılmayan fonksiyon silindi: {finding.file}::{finding.subject}")
    return done


def _exact(source: str, name: str) -> str:
    return next((ast.dump(n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name), "")


def share_clones(ws_dir: Path) -> list[str]:
    """Two modules defining the very same function: the second imports it from the first."""
    done = []
    for finding in arch_scan.clones(ws_dir):
        first_file, _, first_name = finding.detail.split(" ")[0].partition("::")
        if not finding.file.endswith(".py") or finding.file == first_file or finding.subject != first_name:
            continue
        target = ws_dir / finding.file
        text = target.read_text(encoding="utf-8")
        definition = _exact(text, finding.subject)
        if not definition or definition != _exact((ws_dir / first_file).read_text(encoding="utf-8"), first_name):
            continue
        module = first_file[:-3].replace("/", ".")
        atomic_io.write_text(target, f"from {module} import {first_name}\n" + _cut(text, finding.subject))
        done.append(f"kopya fonksiyon ortak yardımcıya alındı: {finding.file}::{finding.subject} -> {first_file}")
    return done


def _movable(source: str) -> list[str]:
    """Undecorated top-level functions, longest first, that use no other definition of the module."""
    tree = ast.parse(source)
    own = {n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)}
    own |= {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    free = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and not n.decorator_list and n.name != "main"
        and not {x.id for x in ast.walk(n) if isinstance(x, ast.Name)} & (own - {n.name})
    ]
    return [n.name for n in sorted(free, key=lambda n: (n.end_lineno or 0) - n.lineno, reverse=True)]


def split_long_modules(ws_dir: Path) -> list[str]:
    done = []
    for path, text in arch_scan.sources(ws_dir, ".py").items():
        lines = text.count("\n") + 1
        if lines <= arch_scan.MAX_FILE_LINES or "/" in path or path.startswith("test_"):
            continue
        spans = {n.name: (n.end_lineno or n.lineno) - n.lineno + 3 for n in ast.parse(text).body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
        moving: list[str] = []
        for name in _movable(text):
            if lines <= arch_scan.MAX_FILE_LINES:
                break
            moving.append(name)
            lines -= spans[name]
        if moving:
            module = f"{Path(path).stem}_helpers"
            try:
                refactor_move.move(ws_dir, moving, module)
            except (ValueError, OSError, SyntaxError) as exc:
                _log.warning("modül bölünemedi (%s): %s", path, exc)
                continue
            done.append(f"uzun modül bölündü: {path} -> {module}.py ({len(moving)} fonksiyon)")
    return done


def _still_whole(ws_dir: Path, before: dict[str, str], check: Callable[[], bool] | None) -> bool:
    for path, text in arch_scan.sources(ws_dir, ".py").items():
        try:
            compile(text, path, "exec")
        except SyntaxError:
            return False
    return check is None or check() or not before


def heal(ws_dir: Path, check: Callable[[], bool] | None = None, used_before: set[tuple[str, str]] | None = None) -> list[str]:
    """What was cleaned up; [] when there was nothing to do or the clean-up had to be undone.

    With `used_before` (see `alive`) only what an edit has just orphaned is removed: code the user asked for but has not
    wired up yet is reported, not deleted. Without it, as for an explicit clean-up, all dead weight goes.
    """
    before = _snapshot(ws_dir)
    try:
        done = [*share_clones(ws_dir), *remove_dead_functions(ws_dir, used_before), *remove_dead_css(ws_dir, used_before), *split_long_modules(ws_dir)]
    except (OSError, SyntaxError, ValueError) as exc:
        _log.warning("mimari onarım yarıda kaldı, geri alınıyor: %s", exc)
        _restore(ws_dir, before)
        return []
    if done and not _still_whole(ws_dir, before, check):
        _restore(ws_dir, before)
        _log.warning("mimari onarım projeyi bozdu, geri alındı: %s", done)
        return []
    return done


_TOO_BIG = ("karmaşıklık", "uzun fonksiyon")


def _oversized(ws_dir: Path, path: str) -> list[arch_scan.Finding]:
    return [f for f in arch_scan.ceilings(ws_dir) if f.file == path and f.kind in _TOO_BIG]


def _acceptable(ws_dir: Path, path: str, candidate: str, works: Callable[[], bool] | None) -> bool:
    """Fewer oversized functions, still whole, and the project's check still passes; the file is left as it was otherwise."""
    target = ws_dir / path
    original = target.read_text(encoding="utf-8")
    before = len(_oversized(ws_dir, path))
    atomic_io.write_text(target, candidate)
    whole = "</html>" not in original.lower() or "</html>" in candidate.lower()
    if whole and len(_oversized(ws_dir, path)) < before and _still_whole(ws_dir, {path: original}, works):
        return True
    atomic_io.write_text(target, original)
    return False


async def decompose(ws_dir: Path, generate: Callable[[str, str], Awaitable[str]], works: Callable[[], bool] | None = None, rounds: int = 2) -> list[str]:
    """The model splits what is over the ceilings; every split is verified and refused when it does not help."""
    done: list[str] = []
    for path in sorted({f.file for f in arch_scan.ceilings(ws_dir) if f.kind in _TOO_BIG}):
        for _round in range(rounds):
            found = _oversized(ws_dir, path)
            if not found:
                break
            current = (ws_dir / path).read_text(encoding="utf-8")
            listed = "\n".join(f.line() for f in found)
            ask = f"{load_prompt('arch_decompose.txt')}{listed}\n\nMEVCUT `{path}`:\n{current}"
            candidate = await patch_edit.try_patch(generate, ask, current)
            if candidate is None:
                answer = await generate("Yalnız dosyanın eksiksiz yeni içeriğini ``` bloğunda döndür.", ask)
                candidate = max(_BLOCK_RE.findall(answer), key=len, default="")
            if candidate and await asyncio.to_thread(_acceptable, ws_dir, path, candidate, works):
                done.append(f"büyük fonksiyonlar bölündü: {path} ({len(found)} bulgudan {len(_oversized(ws_dir, path))} kaldı)")
    return done


def report(ws_dir: Path) -> list[str]:
    """One line per remaining problem, after nothing has been changed (read-only)."""
    return [f"Mimari sağlık: {finding.line()}" for finding in arch_scan.scan(ws_dir)[:6]]
