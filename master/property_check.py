"""A business rule the user stated ("the balance can never go negative") is attacked with random inputs.

The local model writes a Hypothesis test for the rule; it runs in the offline Docker sandbox. A counterexample is a
concrete input that broke the rule and is reported as such; a passing run is reported as "not broken in N tries",
which is evidence, not a proof.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

import gateway
import symbolic
import workspace_docker
from prompt_loader import load_prompt
from workspace_checks import extract_file

_log = logging.getLogger(__name__)
_RULE_RE = re.compile(r"[^.!?\n]*\b(?:asla|hiçbir zaman|negatif olamaz|olmamalı|geçemez|aşamaz|izin verilmemeli|never|must not|cannot)\b[^.!?\n]*", re.IGNORECASE)
_BAD_TEST_RE = re.compile(r"HypothesisException|InvalidArgument|SyntaxError|ImportError|ModuleNotFoundError|NameError|fixture '|error during collection|FailedHealthCheck")
_SKIP = {".history", "venv", ".venv", "tests", "__pycache__"}

Writer = Callable[[str, str], Awaitable[str]]


def rules(request: str) -> list[str]:
    return [m.strip() for m in _RULE_RE.findall(request) if 10 <= len(m.strip()) <= 200][:3]


async def _write(system: str, user: str) -> str:
    res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b",
                                            profile="code", num_predict=1500, num_ctx=8192, timeout_s=300.0, feature="property_check", max_retries=0)
    return res.content


def _sources(ws_dir: Path) -> str:
    files = [p for p in sorted(ws_dir.rglob("*.py")) if not _SKIP & set(p.relative_to(ws_dir).parts)]
    return "\n\n".join(f"### {p.relative_to(ws_dir).as_posix()}\n{p.read_text(encoding='utf-8', errors='replace')[:3000]}" for p in files)[:10000]


def usable(test: str) -> bool:
    """A real property test: parses, uses given(), asserts something."""
    try:
        ast.parse(test)
    except SyntaxError:
        return False
    return "@given" in test and ".example()" not in test and bool(re.search(r"\bassert\b", test))


def run_test(ws_dir: Path, test: str, pkgs: list[str]) -> str:
    """'' when the rule held, else the end of the pytest output."""
    with tempfile.TemporaryDirectory(prefix="cm6453_prop_") as tmp:
        stage = Path(tmp) / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", "__pycache__", "tests"))
        (stage / "tests").mkdir()
        (stage / "tests" / "test_rule.py").write_text(test, encoding="utf-8")
        return workspace_docker.test_log(stage, sorted({*pkgs, "pytest", "hypothesis"}))


async def report(ws_dir: Path, request: str, pkgs: list[str], writer: Writer = _write, runner: Callable[[Path, str, list[str]], str] = run_test) -> str:
    stated = rules(request)
    if stated and (proven := await asyncio.to_thread(symbolic.report, ws_dir, "; ".join(stated))):
        return proven  # decided by the solver: no model and no sampling needed
    sources = _sources(ws_dir) if stated else ""
    if not stated or not sources or (runner is run_test and not workspace_docker.available()):
        return ""
    ask = f"İŞ KURALI: {'; '.join(stated)}\n\n{sources}"
    feedback, log = "", None
    for _attempt in range(2):  # a test that is itself broken goes back to the model once, with the error
        try:
            test = extract_file(await writer(load_prompt("agent_property.md"), ask + feedback), ".py")
        except (OSError, RuntimeError, ValueError) as exc:
            _log.warning("property test could not be written: %s", exc)
            return ""
        if not usable(test):
            feedback = "\n\nÖnceki yanıtın geçerli bir özellik testi değildi (@given ve assert şart, .example() yasak). Yeniden yaz."
            continue
        log = await asyncio.to_thread(runner, ws_dir, test, pkgs)
        if not log or "Falsifying example" in log or not _BAD_TEST_RE.search(log):
            break
        feedback = f"\n\nÖnceki testin kendisi hata verdi, düzeltip yeniden yaz:\n{log[-900:]}"
        log = None
    return _verdict(stated[0], log)


def _verdict(rule: str, log: str | None) -> str:
    """The chat line for the outcome of the test run (None: no usable test could be written)."""
    if log is None:
        return f"İş kuralı denetlenemedi (geçerli bir özellik testi yazılamadı): {rule}"
    if not log:
        return f"İş kuralı 60 rastgele denemede bozulmadı: \"{rule}\" (bu bir kanıt değil, denemedir)."
    if found := re.search(r"Falsifying example:[\s\S]{0,300}?\)\s", log):
        return f"İş kuralı İHLAL EDİLDİ: \"{rule}\". Karşı örnek: " + " ".join(found.group(0).split())
    reason = next((line.strip() for line in log.splitlines() if line.startswith("E ")), log.strip().splitlines()[-1])
    if "AssertionError" in reason:
        return f"İş kuralı İHLAL EDİLDİ: \"{rule}\". Rastgele denemede bulunan durum: {reason.lstrip('E ')[:200]}"
    return f"İş kuralı testi başarısız oldu (\"{rule}\"): {reason[:160]} — hata kuralda da testin kendisinde de olabilir."
