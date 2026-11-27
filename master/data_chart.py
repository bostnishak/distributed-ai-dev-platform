"""A chart drawn from the uploaded file's real numbers: grouped in code, rendered locally, with the table behind it."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import document_chart
import eda

_log = logging.getLogger(__name__)
_ASK_RE = re.compile(r"\bgrafi[kğ]\w*|\bchart\b|\bplot\b", re.IGNORECASE)
_MEAN_RE = re.compile(r"\bortalama\w*|\baverage\b|\bmean\b", re.IGNORECASE)
_MAX_BARS = 20


def aggregate(rows: list[dict[str, str]], prompt: str) -> tuple[str, str, list[tuple[str, float]], str] | None:
    """(category column, value column, [(label, value)], "toplam"/"ortalama") chosen from the question and the data."""
    if not rows:
        return None
    columns = list(rows[0])
    numeric = [c for c in columns if sum(eda._number(str(r.get(c, ""))) is not None for r in rows) >= 0.8 * len(rows)]
    labels = [c for c in columns if c not in numeric] or columns[:1]
    values = [c for c in numeric if c not in labels]
    if not values:
        return None
    value = eda.target_of(prompt, values) or next((c for c in values if not re.fullmatch(r"(?i)(.*_)?id|no|yıl|year", c)), values[0])
    label = eda.target_of(prompt, [c for c in columns if c != value]) or labels[0]
    groups: dict[str, list[float]] = {}
    for row in rows:
        number = eda._number(str(row.get(value, "")))
        if number is not None:
            groups.setdefault(str(row.get(label, "")).strip() or "(boş)", []).append(number)
    mean = bool(_MEAN_RE.search(prompt))
    totals = [(name, sum(v) / len(v) if mean else sum(v)) for name, v in groups.items()]
    if len(totals) > _MAX_BARS:
        totals = sorted(totals, key=lambda item: -item[1])[:_MAX_BARS]
    return label, value, totals, "ortalama" if mean else "toplam"


def make(text: str, prompt: str) -> str:
    """Chat markdown with the saved chart and its numbers; an explanation when no chart can be drawn."""
    import multimodal_studio as mms

    found = aggregate(eda.rows_of(text), prompt)
    if not found or not found[2]:
        return "Grafik için en az bir sayısal sütun ve veri satırı gerekiyor; dosyada bulamadım."
    label, value, pairs, how = found
    png = document_chart.render_bar_chart_png([label, value], [[name, number] for name, number in pairs], f"{label} bazında {value} ({how})", (None, None))
    if png is None:
        return "Bu veriden çubuk grafik çizilemedi."
    name = f"chart-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.png"
    (mms.media_dir() / name).write_bytes(png)
    table = "\n".join(f"| {n} | {v:,.2f} |" for n, v in pairs)
    return (f"![{label} bazında {value}](/api/assistant/media/{name})\n\n| {label} | {value} ({how}) |\n|---|---|\n{table}\n\n"
            "_Rakamlar dosyadan kodla hesaplandı._")


def fastpath(prompt: str, file: UploadFile) -> StreamingResponse | None:
    if not (file.filename or "").lower().endswith((".csv", ".tsv")) or not _ASK_RE.search(prompt):
        return None
    raw = file.file.read(20_000_000)
    file.file.seek(0)
    text = raw.decode("utf-8-sig", "replace")

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def gen():
        try:
            yield sse({"type": "token", "content": make(text, prompt)})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            _log.warning("chart failed: %r", exc)
            yield sse({"type": "error", "content": f"Grafik çizilemedi: {exc}"})
        yield sse({"type": "done", "model": "chart", "task_type": "analiz"})

    return StreamingResponse(gen(), media_type="text/event-stream")
