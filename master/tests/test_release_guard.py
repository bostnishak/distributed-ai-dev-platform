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
