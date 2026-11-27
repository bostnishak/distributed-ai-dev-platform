"""Champion prompts, regression rollback, platform commands and containment of host processes."""

import subprocess
import sys

import pytest

import isolation
import ops_commands
import release_guard

pytestmark = pytest.mark.unit


@pytest.fixture
def places(tmp_path, monkeypatch):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "a.md").write_text("good", encoding="utf-8")
    monkeypatch.setattr(release_guard, "PROMPTS", prompts)
    monkeypatch.setattr(release_guard, "_store", lambda: tmp_path / "champion")
    return prompts


def test_a_regression_restores_the_last_good_prompts(places, tmp_path):
    assert "Henüz ölçüm yok" in release_guard.status()
    assert release_guard.compare({"x": True, "y": False})[0] == "promote"
    release_guard.promote({"x": True, "y": False})
    (places / "a.md").write_text("worse", encoding="utf-8")
    assert "a.md" in release_guard.status()
    verdict, lost, _ = release_guard.compare({"x": False, "y": True})
    assert verdict == "regressed" and lost == ["x"]
    assert release_guard.rollback() == ["a.md"]
    assert (places / "a.md").read_text(encoding="utf-8") == "good"
    assert next((tmp_path / "champion" / "rejected").rglob("a.md")).read_text(encoding="utf-8") == "worse"


def test_a_partial_run_does_not_replace_the_champion(places):
    release_guard.promote({"x": True, "y": True})
    assert release_guard.compare({"x": True})[0] == "keep"
    assert release_guard.compare({"x": True, "y": True, "z": True})[0] == "promote"


def test_platform_commands_only_match_exact_phrases():
    assert ops_commands.answer("kalite durumu nedir diye sorma") == ""
    assert ops_commands.answer("kalite durumu")


@pytest.mark.skipif(sys.platform != "win32", reason="Job Object is Windows only")
def test_a_contained_process_dies_when_the_job_is_closed():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    handle = isolation.contain(proc, memory_mb=256, processes=4)
    assert handle is not None and proc.poll() is None
    isolation.release(handle)
    assert proc.wait(timeout=10) is not None


def test_a_dead_project_server_is_recorded_once(tmp_path, monkeypatch):
    import event_log
    import watchdog

    class Dead:
        def poll(self):
            return 3

    monkeypatch.setattr(watchdog.ops, "_RUNNING_SERVERS", {"w": (9999, Dead())})
    monkeypatch.setattr(watchdog.ops, "safe_workspace_dir", lambda _id: tmp_path)
    assert watchdog.check_servers() == ["w"] and watchdog.check_servers() == []
    assert event_log.read(tmp_path)[0]["detail"] == "çıkış kodu 3"


def test_night_measurement_runs_once_a_day_only_when_idle(monkeypatch):
    import time

    import watchdog

    monkeypatch.setitem(watchdog._state, "last_eval_day", "")
    three = time.strptime("2026-11-27 03:10", "%Y-%m-%d %H:%M")
    assert not watchdog.nightly_due(three, "", lambda: True)
    assert not watchdog.nightly_due(three, "3", lambda: False)
    assert watchdog.nightly_due(three, "3", lambda: True)
    monkeypatch.setitem(watchdog._state, "last_eval_day", "2026-11-27")
    assert not watchdog.nightly_due(three, "3", lambda: True)
