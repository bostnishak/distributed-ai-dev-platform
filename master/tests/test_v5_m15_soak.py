"""v5 milestone 15: the burn-in harness judges memory growth, log errors and leftovers; a short real run is clean."""

from __future__ import annotations

import subprocess
import sys

import psutil
import pytest

import soak

pytestmark = pytest.mark.integration


def _samples(values):
    return [soak.Sample(i, v, 10, 0, 1, 0, 1.0) for i, v in enumerate(values)]


def test_steady_memory_passes_and_steady_growth_fails(tmp_path):
    steady = soak.Run("", tmp_path, False, samples=_samples([100, 160, 200, 201, 199, 202, 200, 201, 203, 200, 202, 201]))
    assert abs(soak.growth(steady.samples)) < 0.05 and soak.verdict(steady, "normal günlük", []) == []
    leaking = soak.Run("", tmp_path, False, samples=_samples([100 + 40 * i for i in range(16)]))
    assert "bellek sürekli büyüyor" in soak.verdict(leaking, "", [])[0]


def test_lock_errors_failures_and_leftovers_are_problems(tmp_path):
    run = soak.Run("", tmp_path, False, failures=["durum: HTTPError: 500"], samples=_samples([100] * 10))
    found = soak.verdict(run, "sqlite3.OperationalError: database is locked\nCUDA error", ["açık kalan port: 8001"])
    assert found == ["günlükte 'database is locked'", "günlükte 'CUDA error'", "durum: HTTPError: 500", "açık kalan port: 8001"]


def test_leftover_process_and_port_are_noticed():
    child = subprocess.Popen([sys.executable, "-c", "import socket,time; s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(); print(s.getsockname()[1], flush=True); time.sleep(60)"],
                             stdout=subprocess.PIPE, text=True)
    try:
        port = int(child.stdout.readline())
        sampled = soak.sample(soak.Run("", __import__("pathlib").Path(__file__).parent / "yok", False), psutil.Process(child.pid), 0.0)
        assert sampled.rss_mb > 1 and sampled.ports >= 1
        assert soak._stop(child, [port]) == [], "durdurulan süreçten artık kalmaz"
    finally:
        child.kill()


def test_a_short_real_burn_in_without_a_model_is_clean(tmp_path):
    report = soak.soak(1.5 / 60, model=False, out=tmp_path / "soak.json")
    assert report["problems"] == [], report["problems"]
    assert set(report["tasks"]) == set(soak.CPU_TASKS) and (tmp_path / "soak.json").is_file()
    assert len(report["samples"]) >= 8 and report["peak_rss_mb"] > 50


def test_chat_commands_report_snapshots_and_the_last_burn_in(tmp_path, monkeypatch):
    import ops_chat
    import recovery

    monkeypatch.setattr(ops_chat, "_REPORT", tmp_path / "soak.json")
    monkeypatch.setattr(recovery, "available", lambda: [("20261128-120000", 3 * 2**20)])
    monkeypatch.setattr(recovery, "snapshot", lambda: "20261128-130000")
    assert "20261128-130000" in ops_chat.answer("yedek al")
    assert "ai_os.py restore" in ops_chat.answer("yedekler") and ops_chat.answer("yedek nasıl alınır?") == ""
    assert "Kayıtlı yakma testi yok" in ops_chat.answer("dayanıklılık raporu")
    (tmp_path / "soak.json").write_text('{"hours": 4, "model": false, "tasks": {"durum": 9}, "problems": [], "peak_rss_mb": 210.5}', encoding="utf-8")
    said = ops_chat.answer("Dayanıklılık raporu.")
    assert "4 saat" in said and "TEMİZ" in said and "9 iş" in said
