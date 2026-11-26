"""Scenario tests for generated web pages: the model writes 2-3 short user scenarios from the request, jsdom (offline Docker sandbox) runs them.

Catches what clicking every control cannot: a calculator whose '=' never calculates, a to-do list that does not list what was added.
A failing scenario goes back to the repair loop as a concrete problem ("after 7 + 8 = the screen should show 15").
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import json_repair
import workspace_web
from prompt_loader import load_prompt
from sandbox import runner

_RUNNER = (Path(__file__).parent / "prompts" / "jsdom_behavior.js.txt").read_text(encoding="utf-8")
_MAX_STEPS = 8


def _clean(raw: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Only well-formed scenarios: known actions, a target for click/type, short expectations."""
    tests = []
    for t in (raw or {}).get("tests") or []:
        steps = [s for s in (t.get("steps") or [])[:_MAX_STEPS] if isinstance(s, dict) and s.get("action") in ("click", "type", "submit") and (s.get("action") == "submit" or s.get("target"))]
        expect = [str(e) for e in (t.get("expect") or []) if str(e).strip() and len(str(e)) <= 40]
        if steps and expect:
            tests.append({"name": str(t.get("name") or "senaryo")[:40], "steps": steps, "expect": expect[:3]})
    return tests[:3]


async def tests_for(request: str, ws_dir: Path, generate: Any) -> list[dict[str, Any]]:
    """Scenarios for this product (empty when the model gave nothing usable)."""
    html = (ws_dir / "index.html").read_text(encoding="utf-8", errors="replace")[:5000]
    ask = f"{load_prompt('b4_behavior_tests.txt')}\n\nKULLANICININ İSTEĞİ:\n{request[:1500]}\n\nSAYFA HTML:\n{html}"
    try:
        return _clean(json_repair.loads_top(await generate(None, ask)))
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError):
        return []


def run(ws_dir: Path, tests: list[dict[str, Any]]) -> list[str]:
    """Failure descriptions of the scenarios (empty list: all passed or the sandbox is unavailable)."""
    if not tests or not workspace_web._ensure_jsdom():
        return []
    with tempfile.TemporaryDirectory(prefix="cm6453_beh_") as tmp:
        stage = Path(tmp) / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", "node_modules"))
        (stage / ".behavior.js").write_text(_RUNNER, encoding="utf-8")
        (stage / ".tests.json").write_text(json.dumps(tests, ensure_ascii=False), encoding="utf-8")
        cache = workspace_web._CACHE / "node_modules"
        args = ["docker", "run", *workspace_web._HARDENING, "--network", "none", "-v", f"{stage.resolve()}:/sandbox", "-v", f"{cache.resolve()}:/node_modules:ro",
                "-w", "/sandbox", "-e", "NODE_PATH=/node_modules", workspace_web.NODE_IMAGE, "timeout", "40", "node", ".behavior.js"]
        proc = runner._run_docker_cmd(args, timeout_s=80)
    line = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("{")), "")
    try:
        return [str(f) for f in json.loads(line).get("failures", [])]
    except ValueError:
        return []


def problem(ws_dir: Path, failures: list[str]) -> tuple[Path | None, str]:
    """(file to repair, repair text) for failed scenarios."""
    text = "\n".join(f"- {f}" for f in failures)
    return workspace_web._main_script(ws_dir), (
        "Kullanıcı senaryosu testi başarısız oldu (sayfa gerçekten tıklanıp yazıldığında beklenen sonuç ekranda görünmüyor):\n" + text +
        "\nOlay dinleyicilerinin doğru düğmelere bağlandığını (sınıf/id seçicileri HTML ile uyuşmalı), işlem mantığını ve ekranın güncellenmesini düzelt."
    )
