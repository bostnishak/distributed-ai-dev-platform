"""One set of numbers, four deliverables, checked against each other to the last decimal.

SymPy computes the reference values exactly. The workbook computes them again with its own formulas (recalculated by
LibreOffice), the web dashboard computes them again in its own script, the slides carry a native chart and table, the
PDF a printed table. Each file is then read back by an independent reader; any difference blocks the delivery.

  tutarlı rapor: Depo gideri; koli 120 x 4,50; bant 35 x 12,75; kdv 20
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import sympy
from fastapi.responses import StreamingResponse

_ITEM_RE = re.compile(r"^\s*(?P<name>.+?)\s+(?P<quantity>\d+(?:[.,]\d+)?)\s*(?:adet\s*)?[x\u00d7*]\s*(?P<price>\d+(?:[.,]\d+)?)\s*(?:tl|₺)?\s*$", re.IGNORECASE)
_VAT_RE = re.compile(r"^\s*kdv\s*%?\s*(\d{1,2})\s*%?\s*$", re.IGNORECASE)
SUBTOTAL, VAT, TOTAL, AVERAGE, LARGEST = "Ara toplam", "KDV", "Genel toplam", "Ortalama kalem tutarı", "En yüksek kalem tutarı"
SUMMARY = (SUBTOTAL, VAT, TOTAL, AVERAGE, LARGEST)
CHART = "sunum grafiği"  # shows the line items only, so the totals are not expected in it


@dataclass(frozen=True)
class Item:
    name: str
    quantity: Decimal
    price: Decimal


@dataclass(frozen=True)
class Report:
    title: str
    items: tuple[Item, ...]
    vat: int = 20


def parse(text: str) -> Report | None:
    """Title; one "name quantity x price" per part; optional "kdv N". None when there are no items."""
    parts = [p.strip() for p in re.split(r"[;\n]", text) if p.strip()]
    items, vat, title = [], 20, ""
    for part in parts:
        if match := _ITEM_RE.match(part):
            items.append(Item(match["name"].strip()[:40], Decimal(match["quantity"].replace(",", ".")), Decimal(match["price"].replace(",", "."))))
        elif match := _VAT_RE.match(part):
            vat = int(match[1])
        elif not title:
            title = part[:80]
    names = [item.name for item in items]
    return Report(title or "Hesap raporu", tuple(items), vat) if items and len(set(names)) == len(names) else None


def _money(value: sympy.Rational) -> Decimal:
    """Rounded half up to two decimals, from the exact rational."""
    cents = sympy.floor(value * 100 + sympy.Rational(1, 2))
    return Decimal(int(cents)) / 100


def figures(report: Report) -> dict[str, Decimal]:
    """The reference values, computed exactly."""
    lines = {item.name: _money(sympy.Rational(str(item.quantity)) * sympy.Rational(str(item.price))) for item in report.items}
    exact = [sympy.Rational(str(v)) for v in lines.values()]
    subtotal = sum(exact)
    vat = _money(subtotal * report.vat / 100)
    return {
        **lines,
        SUBTOTAL: _money(subtotal),
        VAT: vat,
        TOTAL: _money(subtotal + sympy.Rational(str(vat))),
        AVERAGE: _money(subtotal / len(exact)),
        LARGEST: _money(max(exact)),
    }


def turkish(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):,.2f}".replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def read_turkish(text: str) -> Decimal:
    return Decimal(text.strip().replace("TL", "").strip().replace(".", "").replace(",", "."))


def mismatches(reference: dict[str, Decimal], sources: dict[str, dict[str, Decimal]]) -> list[str]:
    """Every figure of every deliverable that is missing or differs from the reference."""
    found = []
    for source, values in sources.items():
        for name, expected in reference.items():
            if source == CHART and name in SUMMARY:
                continue
            if name not in values:
                found.append(f"{source}: '{name}' yok")
            elif values[name].quantize(Decimal("0.01")) != expected.quantize(Decimal("0.01")):
                found.append(f"{source}: '{name}' {values[name]} yazıyor, doğrusu {expected}")
    return found


def deliver(report: Report, folder: Path) -> tuple[dict[str, Path], list[str], dict[str, dict[str, Decimal]]]:
    """(files, mismatches, what each file was read to say)."""
    import consistency_files

    folder.mkdir(parents=True, exist_ok=True)
    reference = figures(report)
    files = consistency_files.build(report, reference, folder)
    sources = consistency_files.read_all(report, files)
    return files, mismatches(reference, sources), sources


_COMMAND_RE = re.compile(r"^\s*tutarlı\s+rapor\s*:\s*(?P<body>.+)$", re.IGNORECASE | re.DOTALL)


def answer(prompt: str) -> tuple[str, dict | None]:
    """(reply, workspace) for the chat command; the files are only offered when all four agree."""
    import workspace_builder as wb

    report = parse(_COMMAND_RE.match(prompt)["body"])
    if report is None:
        return "Kalemleri `ad adet x fiyat` biçiminde, noktalı virgülle ayırarak yaz. Örnek: `tutarlı rapor: Depo gideri; koli 120 x 4,50; bant 35 x 12,75; kdv 20`", None
    ws_id = f"tutarli-rapor-{time.strftime('%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    folder = wb.safe_workspace_dir(ws_id)
    files, differences, sources = deliver(report, folder)
    if differences:
        return "Teslim engellendi: dosyalar birbiriyle tutmuyor.\n" + "\n".join(f"- {line}" for line in differences[:8]), None
    meta = {"id": ws_id, "name": report.title, "project_type": "web", "entry_point": "index.html", "description": "Dört tutarlı çıktı"}
    wb.save_workspace_meta(folder, meta)
    values = figures(report)
    shown = "\n".join(f"| {name} | {turkish(values[name])} |" for name in SUMMARY)
    checked = ", ".join(f"{kind} ({len(sources[kind])} değer)" for kind in sources)
    return (f"## {report.title}\n| Kalem | TL |\n|---|---|\n{shown}\n\nDosyalar: " + ", ".join(f"`{p.name}`" for p in files.values())
            + f"\n\nDoğrulama: her dosya bağımsız okundu ve tüm değerler son haneye kadar eşleşti: {checked}."), meta


async def _stream(prompt: str) -> AsyncIterator[str]:
    import assistant_stream_fastpaths as fp
    import workspace_builder as wb

    yield fp.sse_event({"type": "status", "message": "Dört çıktı üretiliyor ve birbirine karşı denetleniyor..."})
    try:
        text, meta = await asyncio.to_thread(answer, prompt)
        yield fp.sse_event({"type": "token", "content": text})
        if meta:
            yield fp.sse_event(fp._attach_workspace_flags(wb, meta, wb.build_file_tree(wb.safe_workspace_dir(meta["id"]))))
        yield fp.sse_event({"type": "done", "model": "tutarlilik", "task_type": "analiz"})
    except Exception as exc:  # noqa: BLE001, RUF100  # any failure is reported instead of a half-made report
        yield fp.sse_event({"type": "error", "content": f"Rapor üretilemedi: {type(exc).__name__}: {exc}"})


def fastpath(prompt: str) -> StreamingResponse | None:
    return StreamingResponse(_stream(prompt), media_type="text/event-stream") if _COMMAND_RE.match(prompt) else None
