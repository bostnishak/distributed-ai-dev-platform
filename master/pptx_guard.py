"""Post-process a model-written deck outline: no invented statistics, no empty slides, and the slide count the user asked for.

A statistic survives only when its numbers come from the request/source document (or are simple arithmetic on them, see deck_facts);
slides that lose their data (KPI cards, charts) become plain bullet slides instead of being dropped, so the deck keeps its length.
"""

from __future__ import annotations

import re
from typing import Any

import deck_facts

_STAT_RE = re.compile(r"(yüzde\s*\d|%\s*\d|\d\s*%|[$€£₺]\s*\d|\d\s*[$€£₺]|\b\d+(?:[.,]\d+)?\s*(?:x|kat|milyar|milyon|bin|million|billion|TL|USD|EUR)\b)", re.IGNORECASE)
_PCT_RE = re.compile(r"%\s*\d+(?:[.,]\d+)?(?:\s*(?:oranında|oraninda|düzeyinde|seviyesinde|ile))?|\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)
_KICKER = {"tr": "ÖNEMLİ NOKTALAR", "en": "KEY POINTS"}
_BIG = 100


class _Facts:
    """Supported-number lookup for one deck (built once from the request/source text)."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.base, self.derived = deck_facts.supported_set(source)

    def supported(self, value: float, step: float = 0.0) -> bool:
        return deck_facts.is_supported(value, self.base, self.derived, step)

    def invented(self, text: Any) -> bool:
        """True when the text states a statistic (percent, money, scale word, or any number >= 100) the source does not support."""
        raw = str(text or "")
        if any(not deck_facts.fold_supported(v, self.base) for v in deck_facts.fold_claims(raw)):
            return True
        stat = bool(_STAT_RE.search(raw))
        for v, step in deck_facts.claims_in(raw):
            if 1900 <= v <= 2100 and not stat:
                continue
            if (stat or v >= _BIG) and not self.supported(v, step):
                return True
        return False


def _strip_stat(text: str) -> str:
    """'%90 Oranında Yüksek' -> 'Yüksek': the claim stays qualitative when the number was invented."""
    cleaned = re.sub(r"\s{2,}", " ", _PCT_RE.sub("", str(text))).strip(" -:,;")
    return cleaned or "—"


def _cell(text: Any, facts: _Facts) -> str:
    """A table cell with an unsupported statistic loses its percentage; if a figure is still unsupported the cell becomes a dash."""
    if not facts.invented(text):
        return str(text)
    cleaned = _strip_stat(str(text))
    return "—" if facts.invented(cleaned) else cleaned


def _clean_table(table: Any, facts: _Facts) -> Any:
    """Cells are checked one by one; rows whose data cells are all dashes carry no information and are dropped."""
    if not isinstance(table, dict):
        return table
    rows = [[_cell(c, facts) for c in row] for row in table.get("rows") or [] if isinstance(row, list)]
    rows = [r for r in rows if len(r) < 2 or any(c.strip(" —-") for c in r[1:])]
    return {**table, "rows": rows}


def _supported_kpis(kpis: Any, facts: _Facts) -> list[dict[str, Any]]:
    """KPI cards whose value is supported; an invented delta (+%15) is removed from the card, the card stays."""
    out = []
    for k in kpis or []:
        if isinstance(k, dict) and k.get("value") and not facts.invented(k["value"]):
            out.append({**k, "delta": "" if facts.invented(k.get("delta", "")) else k.get("delta", "")})
    return out


def _supported_chart(chart: Any, facts: _Facts) -> bool:
    """A chart is real only when every plotted value comes from the source (or arithmetic on it)."""
    if not isinstance(chart, dict) or not chart.get("values"):
        return False
    for v in chart["values"]:
        nums = deck_facts.numbers_in(str(v)) or ([float(v)] if isinstance(v, (int, float)) else [])
        if not nums or not deck_facts.scaled_supported(nums[0], facts.base, facts.derived):
            return False
    return True


def _drop_unsupported_notes(notes: Any, facts: _Facts) -> str:
    return " ".join(s for s in re.split(r"(?<=[.!?])\s+", str(notes or "")) if s and not facts.invented(s))


def _to_bullets(out: dict[str, Any], lang: str) -> dict[str, Any]:
    out.update(layout="bullets", kicker=_KICKER.get(lang, _KICKER["tr"]))
    out.pop("kpis", None)
    out.pop("chart", None)
    return out


def _plain(sl: dict[str, Any], facts: _Facts, lang: str) -> dict[str, Any]:
    out = dict(sl)
    out["bullets"] = [b for b in sl.get("bullets") or [] if not facts.invented(b)]
    cols = dict(sl.get("columns") or {})
    for key in ("left_bullets", "right_bullets"):
        if key in cols:
            cols[key] = [b for b in cols[key] if not facts.invented(b)]
    if cols:
        out["columns"] = cols
    if facts.invented(sl.get("key_fact")):
        out["key_fact"] = ""
    out["notes"] = _drop_unsupported_notes(sl.get("notes"), facts)
    if "table" in sl:
        out["table"] = _clean_table(sl["table"], facts)
    kpis = _supported_kpis(sl.get("kpis"), facts)
    if sl.get("kpis") is not None:
        out["kpis"] = kpis
    layout, chart_ok = sl.get("layout"), _supported_chart(sl.get("chart"), facts)
    if (layout == "kpi_grid" and len(kpis) < 2) or (layout == "chart" and not chart_ok):
        return _to_bullets(out, lang)
    if sl.get("chart") is not None and not chart_ok:
        out.pop("chart", None)
    return out


def _pad_bullets(sl: dict[str, Any]) -> dict[str, Any]:
    """A bullets slide with one or two points looks empty: add the model's own (checked) speaker-note sentences until there are three."""
    target = 2 if sl.get("layout") == "kpi_grid" else 3
    if sl.get("layout") not in (None, "bullets", "kpi_grid") or len(sl.get("bullets") or []) >= target:
        return sl
    extra = [x.strip().rstrip(".") + "." for x in re.split(r"(?<=[.!?])\s+", str(sl.get("notes") or "")) if len(x.strip()) > 20]
    bullets = list(sl.get("bullets") or [])
    bullets += [x for x in extra if x not in bullets and x != str(sl.get("key_fact") or "")][: target - len(bullets)]
    return {**sl, "bullets": bullets}


def clean_spec(spec: dict[str, Any], source_text: str, content_slides: int) -> dict[str, Any]:
    """Drop statistics the request/source does not support, keep every slide that still has content, trim to the requested length."""
    slides = spec.get("slides")
    if not isinstance(slides, list):
        return spec
    facts, lang = _Facts(source_text), str(spec.get("language") or "tr")
    cleaned = [_pad_bullets(_plain(s, facts, lang)) for s in slides if isinstance(s, dict)]
    cleaned = [s for s in cleaned if s.get("bullets") or (s.get("columns") or {}).get("left_bullets") or s.get("kpis") or s.get("table") or s.get("chart")]
    if len(cleaned) > content_slides:
        cleaned = [*cleaned[: content_slides - 1], cleaned[-1]]
    return {**spec, "slides": cleaned}
