"""Run the Python code and pytest tests the assistant just wrote inside the Docker sandbox, and repair it when they fail.

A code answer that ships tests is only as good as those tests passing, so after the answer is streamed the blocks are
written to a temporary project (module name taken from the test's import, placeholder imports rewritten), executed offline,
and the user gets either a confirmation or a corrected version that was re-run until it passed.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

_BLOCK_RE = re.compile(r"```(?:python|py)\n(.*?)```", re.DOTALL)
_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))", re.MULTILINE)
_PLACEHOLDER_RE = re.compile(r"(your|my|module|file|name|here|example|solution)", re.IGNORECASE)
_STDLIB = set(sys.stdlib_module_names) | {"pytest", "pytest_asyncio"}
MAX_REPAIRS = 2


def split_blocks(answer: str) -> tuple[list[str], list[str]]:
    """(implementation blocks, test blocks) of the Python code in an answer."""
    blocks = [b.strip() for b in _BLOCK_RE.findall(answer)]
    tests = [b for b in blocks if re.search(r"^def test_|^class Test|unittest\.TestCase", b, re.MULTILINE)]
    return [b for b in blocks if b not in tests], tests


def _local_modules(test_code: str) -> list[str]:
    mods = [(a or b).split(".")[0] for a, b in _IMPORT_RE.findall(test_code)]
    return [m for m in dict.fromkeys(mods) if m not in _STDLIB]


def build_project(impls: list[str], tests: list[str], root: Path) -> list[str]:
    """Write files so the tests import the implementation; returns the names of the files written."""
    written: list[str] = []
    test_code = "\n\n".join(tests)
    local = _local_modules(test_code)
    name = local[0] if local else "solution"
    if local and _PLACEHOLDER_RE.search(name) and name not in ("solution",):
        test_code = re.sub(rf"\b{re.escape(name)}\b", "solution", test_code)
        name = "solution"
    if not local:
        test_code = f"from {name} import *  # noqa: F403\n" + test_code
    (root / f"{name}.py").write_text("\n\n".join(impls), encoding="utf-8")
    (root / "test_generated.py").write_text(test_code, encoding="utf-8")
    written += [f"{name}.py", "test_generated.py"]
    return written


def run_tests(impls: list[str], tests: list[str]) -> tuple[bool, str]:
    """(passed, output tail) from running pytest in the offline sandbox; (True, '') when no sandbox is available."""
    from sandbox import runner

    with tempfile.TemporaryDirectory(prefix="cm6453_code_") as tmp:
        build_project(impls, tests, Path(tmp))
        res = runner.run_workspace_command(Path(tmp), ["python", "-m", "pytest", "-x", "-q", "--tb=short", "-p", "no:cacheprovider"], read_only_mount=False, timeout_s=60)
    if not res.get("docker_available", True):
        return True, ""
    if res["timed_out"]:
        return False, "Testler zaman aşımına uğradı (60 sn): sonsuz döngü ya da kilitlenme olabilir."
    return bool(res["ok"]), (res["stdout"] + res["stderr"])[-1800:]


async def _repair(prompt: str, impls: list[str], tests: list[str], log: str) -> tuple[list[str], list[str]] | None:
    import gateway
    import multimodal_studio as mms

    ask = (
        f"Kullanıcının isteği: {prompt}\n\nAşağıdaki kod ve testler çalıştırıldı ve test başarısız oldu.\n\nÇIKTI:\n{log}\n\n"
        "KOD:\n```python\n" + "\n\n".join(impls) + "\n```\n\nTESTLER:\n```python\n" + "\n\n".join(tests) + "\n```\n\n"
        'Hatanın gerçek nedenini bul (kod mu yanlış, test mi) ve ikisini birden düzelt. SADECE JSON döndür: {"code": "<tam uygulama kodu>", "tests": "<tam pytest dosyası>"}. '
        'Test dosyası uygulamayı "from solution import ..." ile içe aktarsın.'
    )
    model = await mms.pick_best_model("code")
    try:
        res = await gateway.default_client.chat([{"role": "user", "content": ask}], model=model, profile="factual", num_predict=3500, timeout_s=240.0, feature="code_verify", max_retries=0)
        m = re.search(r"\{[\s\S]*\}", res.content)
        data = json.loads(m.group(0)) if m else {}
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError):
        return None
    code, test = str(data.get("code") or "").strip(), str(data.get("tests") or "").strip()
    return ([code], [test]) if code and test else None


def _fence(blocks: list[str]) -> str:
    return "```python\n" + "\n\n".join(blocks) + "\n```"


async def verify(prompt: str, answer: str) -> str:
    """Markdown note to append to a code answer ('' when there is nothing to run)."""
    impls, tests = split_blocks(answer)
    if not impls or not tests:
        return ""
    ok, log = await asyncio.to_thread(run_tests, impls, tests)
    if ok:
        return "\n\n---\n✅ **Doğrulama:** kod ve testleri izole Docker ortamında çalıştırdım; testlerin hepsi geçti." if log else ""
    last = log.strip().splitlines()[-1] if log.strip() else "test başarısız"
    for _ in range(MAX_REPAIRS):
        fixed = await _repair(prompt, impls, tests, log)
        if fixed is None:
            break
        impls, tests = fixed
        ok, log = await asyncio.to_thread(run_tests, impls, tests)
        if ok:
            return (
                f"\n\n---\n⚠ **Doğrulama:** yukarıdaki sürüm testten geçmedi (`{last[:140]}`). Hatayı düzeltip yeniden çalıştırdım; "
                f"**aşağıdaki sürümde testlerin hepsi geçiyor** (kullanılması gereken bu):\n\n**solution.py**\n{_fence(impls)}\n\n**test_generated.py**\n{_fence(tests)}"
            )
    return f"\n\n---\n⚠ **Doğrulama:** kodu çalıştırdım ama testler geçmedi: `{last[:160]}`. Yukarıdaki kodu olduğu gibi kullanma; hatayı birlikte düzeltebiliriz."


async def wrap(source: AsyncIterator[Any], prompt: str) -> AsyncIterator[Any]:
    """Pass the SSE stream through; before its final `done` event append the verification result for code answers."""
    collected: list[str] = []
    async for chunk in source:
        text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        evt: dict[str, Any] = {}
        if text.startswith("data: "):
            try:
                evt = json.loads(text[6:].strip())
            except ValueError:
                evt = {}
        if evt.get("type") == "token":
            collected.append(str(evt.get("content") or ""))
        elif evt.get("type") == "done" and evt.get("task_type") == "kod":
            answer = "".join(collected)
            if "```" in answer and "def test_" in answer:
                yield "data: " + json.dumps({"type": "status", "message": "Kod ve testler izole ortamda çalıştırılıyor..."}, ensure_ascii=False) + "\n\n"
                note = await verify(prompt, answer)
                if note:
                    yield "data: " + json.dumps({"type": "token", "content": note}, ensure_ascii=False) + "\n\n"
        yield chunk
