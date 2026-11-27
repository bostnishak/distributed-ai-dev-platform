"""Every benchmark run as a point (how much it passed, how long it took), the runs no other run beats on both, and a
written incident report when a run gets worse than the champion.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

import atomic_io
import config


def _history() -> Path:
    return config.data_dir() / "champion" / "history.jsonl"


def add(results: list[dict[str, Any]], label: str = "") -> dict[str, Any]:
    """One run's point; `results` are {name, ok, seconds}."""
    point = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": label, "passed": sum(bool(r["ok"]) for r in results), "total": len(results),
             "median_s": round(statistics.median([float(r.get("seconds", 0)) for r in results] or [0.0]), 1)}
    _history().parent.mkdir(parents=True, exist_ok=True)
    with _history().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(point, ensure_ascii=False) + "\n")
    return point


def points() -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in _history().read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return []


def frontier(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Runs that no other run beats on pass rate without being slower, or on speed without passing less."""
    def rate(run: dict[str, Any]) -> float:
        return run["passed"] / run["total"] if run["total"] else 0.0

    def beaten(run: dict[str, Any]) -> bool:
        return any(rate(o) >= rate(run) and o["median_s"] <= run["median_s"] and (rate(o), -o["median_s"]) != (rate(run), -run["median_s"]) for o in runs)

    return sorted((run for run in runs if not beaten(run)), key=lambda r: r["median_s"])


def describe() -> str:
    runs = points()
    if not runs:
        return "Henüz ölçüm geçmişi yok."
    best = frontier(runs)
    lines = [f"- {r['at'][:16]} {r['passed']}/{r['total']} geçti, medyan {r['median_s']} sn{' ' + r['label'] if r['label'] else ''}" for r in best]
    latest = runs[-1]
    note = "Son ölçüm bu sınırın üzerinde." if latest in best else "Son ölçüm sınırın gerisinde: daha önce hem daha çok geçen hem daha hızlı bir koşu var."
    return "\n".join([f"Pareto sınırı ({len(runs)} koşudan {len(best)} tanesi):", *lines, note])


def incident(lost: list[str], results: list[dict[str, Any]], changed: list[str], restored: list[str]) -> Path:
    """What got worse, what had changed, and what was put back."""
    notes = {r["name"]: r.get("note", "") for r in results}
    body = "\n".join([f"# Olay raporu: ölçüm geriledi ({time.strftime('%Y-%m-%d %H:%M')})", "", "## Daha önce geçip şimdi kalan senaryolar",
                      *[f"- {name}: {notes.get(name) or 'ayrıntı yok'}" for name in lost], "", "## Şampiyondan beri değişen istem dosyaları",
                      *([f"- {name}" for name in changed] or ["- Yok: gerileme istemlerden kaynaklanmıyor (model, kod ya da ortam)."]), "", "## Yapılan",
                      f"- Geri alınan dosyalar: {', '.join(restored)}" if restored else "- Hiçbir dosya geri alınmadı.", ""])
    target = config.data_dir() / "reports" / f"olay-{time.strftime('%Y%m%d-%H%M%S')}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(target, body)
    return target
