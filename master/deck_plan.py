"""Layout plan and request notes for a deck: guarantees visual variety and tells the model what data it may use.

The local model tends to write every slide as bullets (or to invent KPI cards and charts when the request has no numbers). The plan
fixes the layout of each slide up front, the request note states the data rules for this particular request, and `apply` pulls
the finished outline back to the plan whenever the content can be shown in the planned layout.
"""

from __future__ import annotations

import re
from typing import Any

import deck_facts

_CYCLE = ("bullets", "two_column", "steps", "table")
_CHART_RE = re.compile(r"grafik|chart|trend|büyüme|growth|karşılaştır\w* (?:grafi|chart)", re.IGNORECASE)
_COMPARE_RE = re.compile(r"karşılaştır|compare|versus|\bvs\b|farkları|difference", re.IGNORECASE)
_PROCESS_RE = re.compile(r"süreç|adım|yol haritası|plan|aşama|milestone|roadmap|kilometre|timeline|steps|process", re.IGNORECASE)


def layout_plan(content_slides: int, request: str) -> list[str]:
    """One layout name per content slide (the last is the closing slide); data layouts only when the request supplies numbers."""
    numbers = deck_facts.source_numbers(request)
    plan: list[str] = []
    if len(numbers) >= 2 and content_slides >= 4:
        plan.append("kpi_grid")
    if len(numbers) >= 3 and _CHART_RE.search(request) and content_slides >= 4:
        plan.append("chart")
    cycle = list(_CYCLE)
    if _COMPARE_RE.search(request):
        cycle = ["two_column", "table", "bullets", "steps"]
    elif _PROCESS_RE.search(request):
        cycle = ["steps", "bullets", "two_column", "table"]
    middle = max(0, content_slides - 1)
    out: list[str] = ["bullets"]
    pool, i = [p for p in plan], 0
    while len(out) < middle:
        nxt = pool.pop(0) if pool and len(out) >= 1 and (len(out) % 2 == 1) else cycle[i % len(cycle)]
        i += 0 if nxt in plan else 1
        if nxt == out[-1]:
            nxt = cycle[i % len(cycle)]
            i += 1
        out.append(nxt)
    out = out[:middle] if middle else []
    for leftover in pool:  # a data layout that did not get a slot replaces the second slide
        if leftover not in out and len(out) > 1:
            out[1] = leftover
    return [*out, "closing"][:content_slides]


def request_note(content_slides: int, request: str) -> str:
    """Text appended to the user's request: the planned layout sequence and what may be used as data."""
    plan = layout_plan(content_slides, request)
    order = ", ".join(f"{i}. slayt: {lay}" for i, lay in enumerate(plan, 1))
    numbers = deck_facts.source_numbers(request)
    if len(numbers) >= 2:
        data = "Kullanıcının verdiği sayıları (ve onlarla yapılan basit hesapları) kullan; başka sayı, yüzde, tarih icat etme."
    else:
        data = "İstekte sayısal veri yok: hiçbir sayı, yüzde, para tutarı, istatistik, araştırma/şirket/kanun adı yazma; kpi_grid ve chart KULLANMA, niteliksel anlat."
    return f"\n\n[SLAYT DÜZENİ (layout alanı tam bu sırayla olsun): {order}. {data}]"


def _can_show(slide: dict[str, Any], layout: str) -> bool:
    bullets = slide.get("bullets") or []
    cols = slide.get("columns") or {}
    if layout == "steps":
        return len(bullets) >= 3
    if layout == "two_column":
        return bool(cols.get("left_bullets") and cols.get("right_bullets")) or len(bullets) >= 4
    return False


def apply(slides: list[dict[str, Any]], plan: list[str]) -> list[dict[str, Any]]:
    """Move bullet slides to the planned steps / two_column layout when their content fits it (data layouts are never forced)."""
    out = []
    for i, sl in enumerate(slides):
        want = plan[i] if i < len(plan) else ""
        if want in ("steps", "two_column") and sl.get("layout") in (None, "", "bullets") and _can_show(sl, want):
            sl = {**sl, "layout": want}
        out.append(sl)
    return out
