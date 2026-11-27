"""Remove what piles up over months, after showing it first.

Only things that can be produced again are candidates: generated media, finished run records, the platform's own
temporary folders, sandbox dependency caches and old logs, each past its own age. Projects, databases, memory,
skills and settings are never candidates. "disk durumu" lists, "disk temizle" shows what would go,
"disk temizle uygula" removes it.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import atomic_io
import config

_ASK_RE = re.compile(r"^\s*disk\s+(?P<what>durumu|temizle(?P<apply>\s+uygula)?)\s*\??\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Policy:
    name: str
    folder: Path
    pattern: str
    days: float


def policies() -> list[Policy]:
    data, temp = config.data_dir(), Path(tempfile.gettempdir())
    return [
        Policy("üretilen dosyalar (görsel, belge, ses)", data / "media", "*", float(os.environ.get("KEEP_MEDIA_DAYS", "30"))),
        Policy("bitmiş iş kayıtları", data / "runs", "*.jsonl", 14),
        Policy("günlükler", data / "logs", "*", 14),
        Policy("geçici çalışma klasörleri", temp, "cm6453_*", 1),
        Policy("kod kutusu paket önbelleği", temp / "cm6453_sandbox_deps", "*", 14),
    ]


def candidates(now: float | None = None) -> list[tuple[str, Path, int]]:
    """(policy name, path, bytes) of everything older than its policy allows."""
    now = time.time() if now is None else now
    found = []
    for policy in policies():
        if not policy.folder.is_dir():
            continue
        for path in policy.folder.glob(policy.pattern):
            if policy.name == "geçici çalışma klasörleri" and path.name == "cm6453_sandbox_deps":
                continue
            try:
                if now - path.stat().st_mtime >= policy.days * 86400:
                    found.append((policy.name, path, atomic_io.size_of(path)))
            except OSError:
                continue
    return found


def collect(apply: bool = False, now: float | None = None) -> tuple[int, int, list[str]]:
    """(entries, bytes, one line per policy). Nothing is removed unless `apply`."""
    found = candidates(now)
    removed = []
    for name, path, size in found:
        if apply:
            try:
                atomic_io.remove_tree(path) if path.is_dir() else atomic_io.retrying(lambda p=path: p.unlink(missing_ok=True))
            except OSError:
                continue  # in use: it will be offered again next time
        removed.append((name, size))
    lines = []
    for name in dict.fromkeys(n for n, _s in removed):
        sizes = [s for n, s in removed if n == name]
        lines.append(f"- {name}: {len(sizes)} öğe, {sum(sizes) / 2**20:.1f} MB")
    return len(removed), sum(s for _n, s in removed), lines


def status() -> str:
    usage = shutil.disk_usage(config.data_dir())
    lines = [f"Disk: {usage.free / 2**30:.0f} GB boş / {usage.total / 2**30:.0f} GB (%{100 * usage.used // usage.total} dolu)",
             f"Platform verisi: {atomic_io.size_of(config.data_dir()) / 2**20:.0f} MB"]
    return "\n".join(lines)


def answer(prompt: str) -> str:
    match = _ASK_RE.match(prompt)
    if not match:
        return ""
    if match["what"].casefold() == "durumu":
        count, size, _lines = collect()
        return f"{status()}\nSüresi dolmuş, silinebilecek: {count} öğe, {size / 2**20:.1f} MB (`disk temizle` ile gör)."
    count, size, lines = collect(apply=bool(match["apply"]))
    if not count:
        return "Silinecek bir şey yok."
    body = "\n".join(lines)
    if match["apply"]:
        return f"Silindi: {count} öğe, {size / 2**20:.1f} MB\n{body}"
    return f"Silinecek (henüz hiçbir şey silinmedi): {count} öğe, {size / 2**20:.1f} MB\n{body}\nSilmek için: `disk temizle uygula`"
