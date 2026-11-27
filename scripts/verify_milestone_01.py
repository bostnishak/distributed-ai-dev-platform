"""v5 milestone 01 exit proof, run against real processes, a real server, real SQLite files and real Windows locks.

Usage: python scripts/verify_milestone_01.py      (exit 0 only when every check passes)
It starts its own server on a spare port with a temporary data folder; the user's data is not touched.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing
from ctypes import wintypes
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "master"
sys.path.insert(0, str(MASTER))

import atomic_io  # noqa: E402
import db_health  # noqa: E402
import dbconn  # noqa: E402
import gpu_watch  # noqa: E402
import process_registry  # noqa: E402
import turkish  # noqa: E402

PYTHON = str(MASTER / "venv" / "Scripts" / "python.exe")
PORT = 8047
PROOF = ROOT / "eval" / "reports" / "milestone_01.json"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def answers(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def wait_for(condition, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.5)
    return condition()


def start_master(env: dict[str, str]) -> subprocess.Popen:
    check(process_registry.free_port(PORT), f"{PORT} portu dolu: başka bir süreç yanıt verirse kanıt geçersiz olur")
    server = subprocess.Popen([PYTHON, "-m", "uvicorn", "app:app", "--app-dir", str(MASTER), "--host", "127.0.0.1", "--port", str(PORT)],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_for(lambda: answers(f"http://127.0.0.1:{PORT}/"), 90):
        force_kill(server)
        check(False, "sunucu açılmadı")
    return server


def force_kill(server: subprocess.Popen) -> None:
    """Task-Manager style: only the server process, no chance to clean up."""
    root = psutil.Process(server.pid)
    # the venv launcher starts the real interpreter as its child: that child is the server
    for process in [*root.children(), root]:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            continue
    server.wait(timeout=20)


_OWNER = """
import subprocess, sys, time, config, process_registry
config.data_dir = lambda: __import__('pathlib').Path(sys.argv[1])
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
process_registry.track(child, 'deneme alt süreci')
print(child.pid, flush=True)
time.sleep(120)
"""


def gone(process: psutil.Process) -> bool:
    try:
        return not process.is_running() or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


def kill_and_recover() -> str:
    with tempfile.TemporaryDirectory(prefix="m01_", ignore_cleanup_errors=True) as tmp:
        data = Path(tmp) / "veri"
        data.mkdir()
        env = {**os.environ, "DB_PATH": str(data / "platform.db"), "WORKSPACES_DIR": str(data / "workspaces"), "PYTHONUTF8": "1", "PYTHONPATH": str(MASTER)}
        owner = subprocess.Popen([PYTHON, "-c", _OWNER, str(data)], env=env, stdout=subprocess.PIPE, text=True)
        child = psutil.Process(int(owner.stdout.readline()))
        # the venv launcher is a parent of the real interpreter: kill the interpreter that holds the job, as Task Manager would
        (psutil.Process(owner.pid).children() or [psutil.Process(owner.pid)])[0].kill()
        check(wait_for(lambda: gone(child), 15), "sahibi zorla kapatılınca alt süreç açık kaldı")
        server = start_master(env)
        force_kill(server)
        check(wait_for(lambda: not answers(f"http://127.0.0.1:{PORT}/"), 15), "sunucu kapanmadı")
        server = start_master(env)
        try:
            remaining = json.loads((data / "processes.json").read_text(encoding="utf-8"))
            check(remaining == [], f"yeniden açılışta eski kayıt temizlenmedi: {remaining}")
            check(list((data / "backups" / "db").glob("platform-boot-*.db")), "açılış yedeği yok")
            check(db_health.quick_check(data / "platform.db") == "ok", "zorla kapatma sonrası veritabanı bozuk")
        finally:
            force_kill(server)
        return f"sahibi zorla kapatılan alt süreç (pid {child.pid}) de kapandı; sunucu zorla kapatılıp temiz yeniden açıldı, veritabanı sağlam, açılış yedeği alındı"


def orphan_reaper() -> str:
    with tempfile.TemporaryDirectory(prefix="m01_", ignore_cleanup_errors=True) as tmp:
        import config

        config.data_dir = lambda: Path(tmp)
        orphan = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(120)"])
        born = process_registry._identity(orphan.pid)
        process_registry._save([{"pid": orphan.pid, "born": born, "owner": 999_999, "owner_born": 1.0, "purpose": "iş nesnesinden kaçan süreç", "port": 0}])
        ended = process_registry.reap()
        check(len(ended) == 1 and wait_for(lambda: orphan.poll() is not None, 10), f"yetim süreç kapanmadı: {ended}")
        return "iş nesnesi dışında kalan yetim süreç açılışta kapatıldı"


_WRITER = """
import sys, dbconn
for i in range(150):
    with dbconn.connection(sys.argv[1]) as conn:
        conn.execute("INSERT INTO t (who, n) VALUES (?, ?)", (sys.argv[2], i))
"""


def sqlite_stress() -> str:
    with tempfile.TemporaryDirectory(prefix="m01_", ignore_cleanup_errors=True) as tmp:
        database = Path(tmp) / "yük.db"
        with dbconn.connection(database) as conn:
            conn.execute("CREATE TABLE t (who TEXT, n INTEGER)")
        env = {**os.environ, "PYTHONPATH": str(MASTER), "PYTHONUTF8": "1"}
        started = time.time()
        writers = [subprocess.Popen([PYTHON, "-c", _WRITER, str(database), f"süreç-{i}"], env=env, stderr=subprocess.PIPE, text=True, encoding="utf-8") for i in range(8)]
        copies = []
        while any(w.poll() is None for w in writers):
            copies.append(db_health.quick_check(db_health_copy(database, Path(tmp))))
            time.sleep(0.4)
        errors = [w.stderr.read()[-200:] for w in writers if w.wait() != 0]
        check(not errors, f"yazma hatası: {errors[:2]}")
        with closing(dbconn.open_db(database)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        check(count == 1200 and db_health.quick_check(database) == "ok", f"satır {count}/1200")
        check(copies and all(c == "ok" for c in copies), f"yazma sırasında alınan yedek bozuk: {copies}")
        return f"8 süreç eşzamanlı 1200 satır yazdı, hata yok, {len(copies)} canlı yedek sağlam ({time.time() - started:.1f} sn)"


def db_health_copy(database: Path, folder: Path) -> Path:
    import config

    config.data_dir = lambda: folder
    return db_health.hot_backup(database, "stress")


def _exclusive_handle(path: str):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(path, 0x80000000, 0, None, 3, 0x80, None)  # read, share nothing, open existing
    check(handle != wintypes.HANDLE(-1).value, "dosya kilitlenemedi")
    return kernel, handle


def locked_long_turkish_path() -> str:
    with tempfile.TemporaryDirectory(prefix="m01_", ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        for i in range(10):
            folder = folder / f"ığdır-şubesi-İstanbul-çöğü-{i}"
        target = folder / "ödeme-özeti.txt"
        atomic_io.write_text(target, "ilk")
        kernel, handle = _exclusive_handle(atomic_io.long_path(target))
        threading.Timer(1.2, lambda: kernel.CloseHandle(handle)).start()
        started = time.time()
        atomic_io.write_text(target, "İkinci sürüm: şğüçöı\r\n")
        waited = time.time() - started
        check(atomic_io.read_text(target) == "İkinci sürüm: şğüçöı\n", "içerik bozuldu")
        check(waited >= 1.0, f"kilit hiç beklenmedi ({waited:.2f} sn): deneme geçersiz")
        atomic_io.remove_tree(Path(tmp) / "ığdır-şubesi-İstanbul-çöğü-0")
        check(turkish.upper("istanbul ığdır") == "İSTANBUL IĞDIR", "Türkçe büyük harf yanlış")
        return f"{len(str(target))} karakterlik Türkçe yol; gerçek Windows kilidi {waited:.1f} sn beklenip yazıldı"


def gpu() -> str:
    reading = gpu_watch.read()
    check(reading is not None and 20 < reading.temperature < 110 and reading.total_mb > 7000, f"ekran kartı okunamadı: {reading}")
    return gpu_watch.summary()


TESTS = (("zorla kapatma ve toparlanma", kill_and_recover), ("yetim süreç temizliği", orphan_reaper), ("eşzamanlı SQLite yükü", sqlite_stress),
         ("kilitli uzun Türkçe yol", locked_long_turkish_path), ("ekran kartı bekçisi", gpu))


def main() -> int:
    results = {}
    for name, test in TESTS:
        try:
            detail, ok = test(), True
        except Exception as exc:  # noqa: BLE001 - every failure is recorded and the run goes on
            detail, ok = f"{type(exc).__name__}: {exc}"[:400], False
        results[name] = {"ok": ok, "detail": detail}
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name}: {detail}", flush=True)
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
