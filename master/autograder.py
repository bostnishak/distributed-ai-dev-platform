"""Grade a student's Python function without ever running it inside the platform.

The submission runs in the offline hardened container. Only the arguments go in; the expected values stay here and the
comparison is made here, so a submission cannot read the answers it is graded against.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from typing import Any

from sandbox import runner

_LIMIT = 20_000
Run = Callable[[str], dict[str, Any]]


def _script(code: str, function_name: str, arguments: list[list[Any]], marker: str) -> str:
    payload = json.dumps({"code": code, "name": function_name, "args": arguments})
    return "\n".join([
        "import json",
        f"data = json.loads({payload!r})",
        "space = {}",
        "exec(compile(data['code'], '<submission>', 'exec'), space)",
        "function = space.get(data['name'])",
        "results = []",
        "for args in data['args'] if callable(function) else []:",
        "    try:",
        "        results.append({'got': function(*args)})",
        "    except Exception as error:",
        "        results.append({'error': f'{type(error).__name__}: {error}'[:200]})",
        f"print({marker!r} + json.dumps({{'defined': callable(function), 'results': results}}, default=repr))",
    ])


def _failure(message: str) -> dict[str, Any]:
    return {"passed": False, "score": 0.0, "error": message, "results": []}


def grade(code: str, function_name: str, test_cases: list[dict[str, Any]], run: Run = runner.run_python_code) -> dict[str, Any]:
    """{passed, score, results[, error]}; nothing is graded when the sandbox is not available."""
    if len(code) > _LIMIT:
        return _failure(f"Kod {_LIMIT} karakterden uzun.")
    try:
        compile(code, "<submission>", "exec")
    except (SyntaxError, ValueError) as exc:
        return _failure(f"Sözdizimi hatası (satır {getattr(exc, 'lineno', '?')}): {getattr(exc, 'msg', exc)}")
    marker = f"__not_{secrets.token_hex(8)}__"
    done = run(_script(code, function_name, [list(case.get("args") or []) for case in test_cases], marker))
    if not done.get("docker_available", True):
        return _failure("Yalıtılmış kutu (Docker) kapalı: kod güvenli biçimde çalıştırılamadığı için değerlendirilmedi.")
    line = next((text for text in str(done.get("stdout", "")).splitlines() if text.startswith(marker)), "")
    if not line:
        return _failure("Kod çalıştırılamadı: " + (str(done.get("stderr", "")).strip().splitlines() or ["çıktı yok"])[-1][:300])
    report = json.loads(line[len(marker) :])
    if not report["defined"]:
        return _failure(f"`{function_name}` fonksiyonu tanımlı değil.")
    results = []
    for case, outcome in zip(test_cases, report["results"], strict=False):
        expected = case.get("expected")
        ok = "error" not in outcome and outcome.get("got") == json.loads(json.dumps(expected))
        results.append({"args": case.get("args") or [], "expected": expected, "got": outcome.get("got", f"Hata: {outcome.get('error')}"), "ok": ok})
    passed = sum(r["ok"] for r in results)
    return {"passed": bool(results) and passed == len(test_cases), "score": round(passed / max(1, len(test_cases)) * 100, 1), "results": results}
