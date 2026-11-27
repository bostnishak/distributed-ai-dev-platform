"""v5 milestone 01: ports, child processes, locked and long files, Turkish letters, GPU, databases, disk."""

import asyncio
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing

import pytest

import atomic_io
import db_health
import disk_gc
import eda
import gpu_watch
import os_kernel
import process_registry
import turkish
from gateway import priority_gate

pytestmark = pytest.mark.unit


@pytest.fixture
def data(tmp_path, monkeypatch):
    import config

    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setattr(config, "data_dir", lambda: folder)
    monkeypatch.setattr(config, "DB_PATH", folder / "platform.db")
    return folder


def test_a_port_in_use_or_already_leased_is_never_handed_out():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        busy = taken.getsockname()[1]
        assert not process_registry.free_port(busy)
    first = process_registry.lease_port()
    second = process_registry.lease_port()
    assert first != second and first in process_registry.PORTS
    process_registry.release_port(first)
    process_registry.release_port(second)


def _sleeper():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


def test_tracked_child_is_ended_and_forgotten(data):
    child = _sleeper()
    process_registry.track(child, "deneme", memory_mb=512)
    assert [e["pid"] for e in process_registry.listing()] == [child.pid]
    process_registry.untrack(child.pid)
    assert child.wait(timeout=10) is not None and process_registry.listing() == []


def test_orphans_of_a_dead_server_are_reaped_but_a_reused_pid_is_left_alone(data):
    orphan, innocent = _sleeper(), _sleeper()
    born = process_registry._identity(orphan.pid)
    process_registry._save([
        {"pid": orphan.pid, "born": born, "owner": 999_999, "owner_born": 1.0, "purpose": "eski sunucu", "port": 0},
        {"pid": innocent.pid, "born": 1.0, "owner": 999_999, "owner_born": 1.0, "purpose": "pid yeniden kullanılmış", "port": 0},
    ])
    try:
        assert process_registry.reap() == [f"eski sunucu (pid {orphan.pid})"]
        assert orphan.wait(timeout=10) is not None and innocent.poll() is None
    finally:
        innocent.kill()


def test_atomic_write_waits_out_a_lock_and_keeps_utf8_lf(tmp_path, monkeypatch):
    target = tmp_path / "şğü İ.txt"
    real, failures = os.replace, {"left": 3}

    def locked(src, dst):
        if failures["left"]:
            failures["left"] -= 1
            raise PermissionError(32, "başka bir süreç kullanıyor")
        real(src, dst)

    monkeypatch.setattr(os, "replace", locked)
    atomic_io.write_text(target, "İstanbul\r\nığdır\n")
    assert target.read_bytes() == "İstanbul\nığdır\n".encode() and not list(tmp_path.glob("*.tmp"))
    failures["left"] = 99
    monkeypatch.setattr(atomic_io.time, "sleep", lambda _s: None)
    with pytest.raises(PermissionError):
        atomic_io.write_text(target, "yeni")
    assert atomic_io.read_text(target) == "İstanbul\nığdır\n" and not list(tmp_path.glob("*.tmp"))


def test_paths_beyond_the_classic_limit_work_and_can_be_removed(tmp_path):
    deep = tmp_path / "kök"
    for i in range(12):
        deep = deep / f"çok-uzun-klasör-adı-{i:02d}"
    target = deep / "dosya.txt"
    assert len(str(target)) > 260
    atomic_io.write_text(target, "tamam")
    assert atomic_io.read_text(target) == "tamam"
    os.chmod(atomic_io.long_path(target), 0o444)
    atomic_io.remove_tree(tmp_path / "kök")
    assert not (tmp_path / "kök").exists()


def test_turkish_letters_and_order():
    assert turkish.lower("IĞDIR İSTANBUL") == "ığdır istanbul" and turkish.upper("ığdır istanbul") == "IĞDIR İSTANBUL"
    assert sorted(["İzmir", "Isparta", "Çorum", "Ceyhan", "Şile", "Siirt"], key=turkish.sort_key) == ["Ceyhan", "Çorum", "Isparta", "İzmir", "Siirt", "Şile"]
    assert turkish.matches("istanbul", "Büyük İSTANBUL ili") and eda.target_of("il bazında dağılım", ["İl", "Adet"]) == "İl"


def test_hot_card_or_low_battery_holds_only_background_work(monkeypatch):
    monkeypatch.setattr(gpu_watch, "on_low_battery", lambda: False)
    heat = {"t": 84}
    monkeypatch.setattr(gpu_watch, "read", lambda: gpu_watch.Reading(heat["t"], 6000, 8188, "test"))
    gpu_watch._CACHE["holding"] = False
    assert "84 °C" in gpu_watch.hold_reason()
    heat["t"] = 80
    assert gpu_watch.hold_reason()  # still cooling down
    heat["t"] = 77
    assert gpu_watch.hold_reason() == ""
    assert gpu_watch.context_budget(16384) == 4096 and gpu_watch.context_budget(16384, loaded_mb=5000) == 16384

    waited = []

    async def fake_wait():
        waited.append(1)

    monkeypatch.setattr(priority_gate, "_wait_until_safe", fake_wait)

    async def run():
        gate = priority_gate.PriorityGate(1)
        async with gate.slot("chat"):
            pass
        async with gate.slot("self_eval"):
            pass

    asyncio.run(run())
    assert waited == [1]


def test_broken_database_is_reported_and_backup_is_consistent_under_writes(data):
    good = data / "platform.db"
    with closing(sqlite3.connect(good)) as conn, conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (v INTEGER)")
    (data / "bozuk.db").write_bytes(b"SQLite format 3\x00" + b"\x07" * 4000)
    stop = threading.Event()

    def writer():
        with closing(sqlite3.connect(good, timeout=10)) as conn:
            while not stop.is_set():
                conn.execute("INSERT INTO t VALUES (1)")
                conn.commit()

    thread = threading.Thread(target=writer)
    thread.start()
    time.sleep(0.2)
    broken = db_health.startup_check()
    copy = db_health.hot_backup(good, "test")
    stop.set()
    thread.join()
    assert list(broken) == ["bozuk.db"] and db_health.quick_check(copy) == "ok"
    assert list((data / "backups" / "db").glob("platform-boot-*.db"))
    for _ in range(8):
        db_health.hot_backup(good, "many")
    assert len(list((data / "backups" / "db").glob("platform-many-*.db"))) == 5
    assert db_health.flush() >= 1


def test_disk_cleanup_shows_first_and_never_offers_projects(data, monkeypatch):
    monkeypatch.setattr(disk_gc.tempfile, "gettempdir", lambda: str(data.parent / "tmp"))
    old = time.time() - 90 * 86400
    for rel in ("media/eski.png", "media/yeni.png", "runs/a.jsonl", "workspaces/proje/index.html", "platform.db"):
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 100)
        if "yeni" not in rel:
            os.utime(path, (old, old))
    shown = disk_gc.answer("disk temizle")
    assert "henüz hiçbir şey silinmedi" in shown and (data / "media" / "eski.png").exists()
    assert "Silindi: 2 öğe" in disk_gc.answer("disk temizle uygula")
    assert (data / "media" / "yeni.png").exists() and (data / "workspaces" / "proje" / "index.html").exists() and (data / "platform.db").exists()
    assert "boş" in disk_gc.answer("disk durumu") and disk_gc.answer("disk nedir?") == ""


def test_sleep_is_noticed_and_status_answers(data):
    assert os_kernel.woke_from_sleep(600) and not os_kernel.woke_from_sleep(16)
    text = os_kernel.answer("sistem durumu")
    assert "Disk:" in text and "Çalışan alt süreç: 0" in text


def test_a_foreign_program_on_the_preview_port_never_receives_previews(monkeypatch):
    import preview_server

    with socket.socket() as foreign:
        foreign.bind(("127.0.0.1", 0))
        foreign.listen()
        taken = foreign.getsockname()[1]
        monkeypatch.setattr(preview_server.config, "PREVIEW_PORT", taken)
        monkeypatch.setattr(preview_server, "_STATE", {"port": 0})
        monkeypatch.setattr(preview_server, "_is_preview", lambda port: False)
        started = []
        monkeypatch.setattr(preview_server.threading.Thread, "start", lambda self: started.append(self.name))
        preview_server.start_preview_server_background()
        chosen = int(preview_server.get_preview_origin().rsplit(":", 1)[1])
        assert chosen != taken and started == ["preview-origin-server"]
        process_registry.release_port(chosen)


def test_computed_figures_are_written_the_turkish_way():
    import table_stats

    assert table_stats._fmt(3104) == "3.104" and table_stats._fmt(2345.5) == "2.345,5" and table_stats._fmt(7) == "7"
