"""Post-process a model-written deck outline: no invented statistics, and the slide count the user asked for."""

from __future__ import annotations

import re
from typing import Any

_STAT_RE = re.compile(r"(%\s*\d|\d\s*%|[$€£₺]\s*\d|\d\s*[$€£₺]|\b\d+(?:[.,]\d+)?\s*(?:x|kat|milyar|milyon|bin|million|billion)\b)", re.IGNORECASE)
_DATA_LAYOUTS = {"kpi_grid", "chart"}


_COUNT_PHRASE_RE = re.compile(r"\d+\s*(?:adet|tane)?\s*(?:slayt|sayfa|slide|page)\w*", re.IGNORECASE)


def _has_numbers(text: str) -> bool:
    """Digits in the request count as source data, except the slide count itself ("6 slaytlık")."""
    return bool(re.search(r"\d", _COUNT_PHRASE_RE.sub("", text or "")))


def _plain(sl: dict[str, Any], keep_stats: bool) -> dict[str, Any]:
    out = dict(sl)
    if not keep_stats:
        for key in ("bullets",):
            out[key] = [b for b in (sl.get(key) or []) if not _STAT_RE.search(str(b))]
        cols = dict(sl.get("columns") or {})
        for key in ("left_bullets", "right_bullets"):
            if key in cols:
                cols[key] = [b for b in cols[key] if not _STAT_RE.search(str(b))]
        if cols:
            out["columns"] = cols
        if _STAT_RE.search(str(sl.get("key_fact") or "")):
            out["key_fact"] = ""
        if sl.get("layout") in _DATA_LAYOUTS:
            out["layout"] = "bullets"
            out.pop("kpis", None)
            out.pop("chart", None)
            if not out.get("bullets"):
                out["bullets"] = [str(k.get("label")) for k in (sl.get("kpis") or []) if isinstance(k, dict) and k.get("label")]
    return out


def clean_spec(spec: dict[str, Any], source_text: str, content_slides: int) -> dict[str, Any]:
    """Without numbers in the request/source, drop statistic-like claims and KPI/chart slides; trim to the requested length."""
    slides = spec.get("slides")
    if not isinstance(slides, list):
        return spec
    keep_stats = _has_numbers(source_text)
    cleaned = [_plain(s, keep_stats) for s in slides if isinstance(s, dict)]
    cleaned = [s for s in cleaned if s.get("bullets") or (s.get("columns") or {}).get("left_bullets") or s.get("kpis") or s.get("table")]
    if len(cleaned) > content_slides:
        cleaned = [*cleaned[: content_slides - 1], cleaned[-1]]
    return {**spec, "slides": cleaned}
