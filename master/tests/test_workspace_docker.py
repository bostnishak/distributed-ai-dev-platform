"""Docker-backed smoke probe: result parsing and GUI-library tolerance (the container itself is mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

import workspace_docker

pytestmark = pytest.mark.unit


def _fake(stdout: str = "", stderr: str = "", timed_out: bool = False, ok: bool = True) -> dict:
    return {"ok": ok, "exit_code": 0 if ok else 1, "stdout": stdout, "stderr": stderr, "timed_out": timed_out, "docker_available": True}


def _probe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, result: dict) -> tuple[bool, str, list[str]]:
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(workspace_docker.runner, "run_workspace_command", lambda *a, **k: result)
    monkeypatch.setattr(workspace_docker, "_pip_install", lambda *a, **k: None)
    return workspace_docker.run_probe(tmp_path, tmp_path / "app.py", "print(1)", [])


def test_probe_ok_with_routes(monkeypatch, tmp_path):
    ok, _log, routes = _probe(monkeypatch, tmp_path, _fake('ROUTES=["/"]\nSMOKE_OK\n'))
    assert ok and routes == ["/"]


def test_probe_failure_returns_log(monkeypatch, tmp_path):
    ok, log, _ = _probe(monkeypatch, tmp_path, _fake(stderr="Traceback ... NameError", ok=False))
    assert not ok and "NameError" in log


def test_timeout_means_app_kept_running(monkeypatch, tmp_path):
    assert _probe(monkeypatch, tmp_path, _fake(timed_out=True, ok=False))[0] is True


def test_gui_library_errors_are_not_failures(monkeypatch, tmp_path):
    ok, _, _ = _probe(monkeypatch, tmp_path, _fake(stderr="ModuleNotFoundError: No module named 'tkinter'", ok=False))
    assert ok


def test_docker_unavailable_raises(monkeypatch, tmp_path):
    res = _fake(ok=False) | {"docker_available": False, "stderr": "Docker kurulu değil"}
    with pytest.raises(OSError):
        _probe(monkeypatch, tmp_path, res)
