"""Reject a repair that makes the checks pass without making the program right.

Checked for every file a repair wants to write: the builder may not touch the oracle folder; a test file may not lose
checks, gain a skip, loosen a threshold or turn a check into a tautology; program code may not special-case a value
that only the tests use. Attempts are written down and quoted back to later repairs as things not to do.
"""

from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path

import config

ORACLE_DIR = ".ai-os/oracles"
_SKIP_RE = re.compile(r"pytest\.mark\.(?:skip|xfail)|pytest\.(?:skip|xfail)\(|unittest\.skip|\b(?:it|test|describe)\.(?:skip|only)\b|\bxit\(|\bxdescribe\(")
_JS_CHECK_RE = re.compile(r"\bexpect\s*\(|\bassert\w*\s*[.(]")
_JS_TAUTOLOGY_RE = re.compile(r"expect\s*\(\s*(true|false|1|0)\s*\)\s*\.\s*to(?:Be|Equal)\s*\(\s*\1\s*\)")
_LITERAL_RE = re.compile(r"[\"']([^\"'\n]{3,80})[\"']")


def is_test(path: str) -> bool:
    name = Path(path).name
    return path.startswith(("tests/", ORACLE_DIR)) or name.startswith("test_") or bool(re.search(r"\.(?:test|spec)\.[jt]sx?$|_test\.py$", name))


def is_oracle(path: str) -> bool:
    return path.replace("\\", "/").lstrip("./").startswith(ORACLE_DIR.lstrip("."))


def _tree(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _tautology(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, ast.Compare) and len(node.comparators) == 1:
        return ast.dump(node.left) == ast.dump(node.comparators[0])
    return False


def checks_of(source: str) -> tuple[int, int]:
    """(real checks, tautologies) of a Python test file or a JavaScript one."""
    tree = _tree(source)
    if tree is None:
        return len(_JS_CHECK_RE.findall(source)) - len(_JS_TAUTOLOGY_RE.findall(source)), len(_JS_TAUTOLOGY_RE.findall(source))
    real = empty = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            empty += _tautology(node.test)
            real += not _tautology(node.test)
        elif isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            real += name == "raises" or name.startswith(("assert", "expect"))
    return real, empty


def _limits(source: str) -> list[tuple[str, str, float]]:
    """(left side, operator, number) of every numeric bound asserted."""
    tree = _tree(source)
    out = []
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and len(node.test.comparators) == 1:
            bound = node.test.comparators[0]
            if isinstance(bound, ast.Constant) and isinstance(bound.value, int | float) and not isinstance(bound.value, bool):
                out.append((ast.dump(node.test.left), type(node.test.ops[0]).__name__, float(bound.value)))
    return out


def loosened(old: str, new: str) -> bool:
    """A bound moved the easy way: an upper limit raised or a lower limit lowered."""
    after = {(left, op): number for left, op, number in _limits(new)}
    for left, op, number in _limits(old):
        now = after.get((left, op))
        if now is not None and ((op in ("Lt", "LtE") and now > number) or (op in ("Gt", "GtE") and now < number)):
            return True
    return False


def _special_cases(source: str) -> set[str]:
    """Literals the program compares an input with."""
    tree = _tree(source)
    if tree is None:
        return set(re.findall(r"[!=]==?\s*[\"']([^\"'\n]{3,80})[\"']", source)) | set(re.findall(r"case\s+[\"']([^\"'\n]{3,80})[\"']", source))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If | ast.IfExp):
            for part in ast.walk(node.test):
                if isinstance(part, ast.Compare) and any(isinstance(o, ast.Eq | ast.In) for o in part.ops):
                    for value in (part.left, *part.comparators):
                        if isinstance(value, ast.Constant) and isinstance(value.value, str) and len(value.value) >= 3 and value.value != "__main__":
                            found.add(value.value)
    return found


def test_literals(tests: dict[str, str]) -> set[str]:
    return {m for source in tests.values() for m in _LITERAL_RE.findall(source)}


def review(path: str, old: str, new: str, literals: set[str] = frozenset()) -> list[str]:
    """Why this change must be rejected ([] when it may be written)."""
    if is_oracle(path):
        return [f"{path}: kehanet klasörüne yalnız mimar, denetçi ya da kullanıcı yazabilir"]
    if is_test(path):
        before, after = checks_of(old), checks_of(new)
        found = []
        if old.strip() and not new.strip():
            found.append("test dosyası boşaltıldı")
        if after[0] < before[0]:
            found.append(f"denetim sayısı {before[0]} → {after[0]}")
        if after[1] > before[1]:
            found.append("her zaman doğru olan denetim eklendi")
        if len(_SKIP_RE.findall(new)) > len(_SKIP_RE.findall(old)):
            found.append("test atlatıldı (skip/xfail/only)")
        if loosened(old, new):
            found.append("eşik gevşetildi")
        return [f"{path}: {reason}" for reason in found]
    added = (_special_cases(new) - _special_cases(old)) & set(literals)
    return [f"{path}: yalnız testte geçen değer koda gömüldü: {value!r}" for value in sorted(added)]


def _log_file() -> Path:
    return config.data_dir() / "cheats.jsonl"


def record(violations: list[str]) -> None:
    if not violations:
        return
    _log_file().parent.mkdir(parents=True, exist_ok=True)
    with _log_file().open("a", encoding="utf-8") as handle:
        for violation in violations:
            handle.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": "REWARD_HACK_ATTEMPT", "detail": violation}, ensure_ascii=False) + "\n")


def guardrails(limit: int = 4) -> str:
    """Recent rejected shortcuts, as an instruction for the next repair."""
    try:
        lines = _log_file().read_text(encoding="utf-8").splitlines()[-limit:]
        details = [json.loads(line)["detail"] for line in lines]
    except (OSError, ValueError, KeyError):
        return ""
    return "ŞUNLAR DAHA ÖNCE REDDEDİLDİ, TEKRARLAMA (testi değil programı düzelt):\n" + "\n".join(f"- {d}" for d in dict.fromkeys(details))
