"""Drop-folder automation: a file put into data/inbox is processed without asking a model and the report is written to inbox/out.

Runs quietly: it waits while the machine is on battery or the GPU is hot, only reads the dropped file and only writes
inside the inbox folder.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

import httpx
import psutil
from pypdf.errors import PyPdfError

import config
import extract
import injection
import table_stats
import watchdog
from process_utils import run_process

_log = logging.getLogger(__name__)
_KINDS = {".csv", ".xlsx", ".pdf", ".docx", ".pptx", ".txt", ".md", ".log"}
_MAX_BYTES = 20_000_000
_INTERVAL_S = 20
_HOT_C = 80


def folder() -> Path:
    return config.data_dir() / "inbox"


def busy_reason() -> str:
    battery = psutil.sensors_battery()
    if battery is not None and not battery.power_plugged:
        return "pil gücünde"
    smi = shutil.which("nvidia-smi")
    if not smi:
        return ""
    try:
        done = run_process([smi, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], timeout_s=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return "GPU sıcak" if done.stdout.strip().isdigit() and int(done.stdout.strip()) > _HOT_C else ""


def gpu_in_use() -> bool:
    """True while a model is loaded, i.e. someone is (or was moments ago) using it."""
    try:
        return bool(httpx.get(f"{config.OLLAMA_URL}/api/ps", timeout=3).json().get("models"))
    except (httpx.HTTPError, ValueError):
        return True


def describe(path: Path) -> str:
    """A report computed in code: exact figures for tables, size and outline for documents."""
    raw = path.read_bytes()
    text = raw.decode("utf-8", "replace") if path.suffix.lower() == ".log" else extract.extract_text(path.name, raw)
    lines = [f"# {path.name}", "", f"İşlendi: {datetime.now():%Y-%m-%d %H:%M} | {len(raw)} bayt | {len(text.splitlines())} satır metin"]
    if injection.detect_injection(text)["flagged"]:
        lines.append("UYARI: Dosya, bir modele talimat vermeye çalışan ifadeler içeriyor.")
    if table_stats.looks_tabular(text) and (figures := table_stats.summary(text)):
        lines += ["", "## Hesaplanan değerler", *[line for line in figures.strip().splitlines() if not line.startswith("---")]]  # header is a note for the model
    else:
        lines += ["", "## İlk satırlar", *[line for line in text.splitlines() if line.strip()][:25]]
    return "\n".join(lines) + "\n"


def run_once(root: Path) -> list[Path]:
    """Process every waiting file once; each is moved to done/ (or failed/) so it is never processed twice."""
    reports: list[Path] = []
    for path in sorted(root.glob("*")) if root.is_dir() else []:
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in _KINDS or path.stat().st_size > _MAX_BYTES:
            continue
        target = "done"
        try:
            report = root / "out" / f"{path.name}.md"
            report.parent.mkdir(exist_ok=True)
            report.write_text(describe(path), encoding="utf-8")
            reports.append(report)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile, PyPdfError, extract.UnsupportedFileError) as exc:  # one unreadable file must not stop the watcher
            _log.warning("inbox: %s okunamadı: %s", path.name, exc)
            target = "failed"
        (root / target).mkdir(exist_ok=True)
        shutil.move(str(path), str(root / target / f"{datetime.now():%Y%m%d%H%M%S}-{path.name}"))
    return reports


async def loop() -> None:
    root = folder()
    root.mkdir(parents=True, exist_ok=True)
    while True:
        await asyncio.sleep(_INTERVAL_S)
        try:
            await asyncio.to_thread(watchdog.tick, lambda: not busy_reason() and not gpu_in_use())
            if any(p.is_file() for p in root.iterdir()) and not await asyncio.to_thread(busy_reason):
                for report in await asyncio.to_thread(run_once, root):
                    _log.info("inbox raporu: %s", report)
        except OSError as exc:
            _log.warning("inbox taraması başarısız: %s", exc)
