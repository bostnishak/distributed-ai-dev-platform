"""Where the time goes, from the calls that really happened: per model and per feature, from the gateway's own log."""

from __future__ import annotations

from typing import Any

import run_trace
from gateway import client_helpers

_RECENT = 500


def _percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(int(len(ordered) * share), len(ordered) - 1)] if ordered else 0


def _rows() -> list[dict[str, Any]]:
    client_helpers.init_gateway_db()
    with client_helpers.gw_conn() as conn:
        rows = conn.execute("SELECT model, feature, tokens_out, latency_ms, status FROM llm_calls ORDER BY created_at DESC LIMIT ?", (_RECENT,)).fetchall()
    return [dict(r) for r in rows]


def summarise(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row[key] or "-"), []).append(row)
    out = []
    for name, items in groups.items():
        good = [i for i in items if i["status"] == "ok" and i["latency_ms"] > 0]
        seconds = sum(i["latency_ms"] for i in good) / 1000
        out.append({
            "name": name, "calls": len(items), "errors": len(items) - len(good),
            "p50_ms": _percentile([i["latency_ms"] for i in good], 0.5), "p95_ms": _percentile([i["latency_ms"] for i in good], 0.95),
            "tokens_per_s": round(sum(i["tokens_out"] for i in good) / seconds, 1) if seconds else 0.0,
            "total_s": round(seconds),
        })
    return sorted(out, key=lambda item: -item["total_s"])


def report() -> str:
    rows = _rows()
    if not rows:
        return "Henüz kaydedilmiş model çağrısı yok."
    lines = [f"**Son {len(rows)} model çağrısı**", "", "| Model | çağrı | hata | ortanca sn | %95 sn | token/sn | toplam sn |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {m['name']} | {m['calls']} | {m['errors']} | {m['p50_ms'] / 1000:.1f} | {m['p95_ms'] / 1000:.1f} | {m['tokens_per_s']} | {m['total_s']} |" for m in summarise(rows, "model")[:8]]
    busiest = summarise(rows, "feature")[:5]
    lines += ["", "En çok zaman alan işler: " + ", ".join(f"{f['name']} ({f['total_s']} sn)" for f in busiest)]
    runs = run_trace.summary()
    if runs.get("runs"):
        lines.append(f"Proje üretimleri: {runs['runs']} koşu" + (f", başarı %{round(100 * runs['pass_rate'])}" if "pass_rate" in runs else ""))
    lines.append("_Süreler sıra bekleme ve model yükleme dahil gerçek çağrı süreleridir._")
    return "\n".join(lines)
