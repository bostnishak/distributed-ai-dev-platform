"""Validate the model's block-based document spec and resolve every {key} against the code-computed values."""

from __future__ import annotations

import re
from typing import Any

import doc_calc
import doc_polish
from document_chart import to_number

_MAX_BLOCKS = 80
CALC_HEADERS = ["Kalem", "Değer", "Tür"]


_REQUEST = {"text": ""}


def _pct(text: str) -> str:
    """Percentages the user never wrote are guesses: they become '%[....]' unless the request itself contains that number."""
    request = _REQUEST["text"]
    return doc_polish.blank_invented_percentages(text, request) if request else text


def _texts(items: Any, shown: dict[str, str], limit: int = 40) -> list[str]:
    return [doc_calc.fill(_pct(str(i)), shown).strip() for i in (items or [])[:limit] if str(i).strip()] if isinstance(items, list) else []


def _cell(value: Any, shown: dict[str, str]) -> str:
    """One table cell as text: nested lists are flattened, plain numbers get Turkish formatting (850000.0 -> 850.000), {keys} are resolved."""
    if isinstance(value, list):
        return " ".join(_cell(v, shown) for v in value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value) == int(value) and 1900 <= int(value) <= 2100:
            return str(int(value))
        return doc_calc.fmt_number(doc_calc.unscale(float(value), shown))
    text = doc_calc.fill(_pct(str(value)), shown)
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|(?:19|20)\d\d", text.strip()):  # already Turkish-formatted (129.600) or a year
        return text
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?", text.strip()):  # a bare number cell (the Turkish-formatted 129,6 included)
        return doc_calc.fmt_number(doc_calc.unscale(float(text.strip().replace(",", ".")), shown))
    return text


def _table(raw: dict[str, Any], shown: dict[str, str]) -> dict[str, Any] | None:
    headers = _texts(raw.get("headers"), shown, 8)
    rows = [[_cell(c, shown) for c in (r + [""] * len(headers))[: len(headers)]] for r in (raw.get("rows") or [])[:40] if isinstance(r, list)]
    rows = [r for r in rows if any(c.strip() for c in r)]
    return {"type": "table", "headers": headers, "rows": rows, "caption": doc_calc.fill(str(raw.get("caption") or ""), shown)} if len(headers) >= 2 and rows else None


def _chart(raw: dict[str, Any], values: dict[str, float], shown: dict[str, str]) -> dict[str, Any] | None:
    labels, nums = _texts(raw.get("labels"), shown, 12), []
    for v in (raw.get("values") or [])[:12]:
        key = str(v).strip("{} ")
        nums.append(values.get(key) if key in values else to_number(v))
    if len(labels) < 2 or len(labels) != len(nums) or any(n is None or n < 0 for n in nums):  # the bar renderer draws non-negative values only
        return None
    return {"type": "chart", "title": doc_calc.fill(str(raw.get("title") or ""), shown), "labels": labels, "values": nums}


def _block(raw: Any, values: dict[str, float], shown: dict[str, str], calc_rows: list[dict[str, str]]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("type", "")).lower()
    text = doc_calc.fill(_pct(str(raw.get("text") or "")), shown).strip()
    if kind == "heading" and text:
        return {"type": "heading", "text": text, "level": 2 if raw.get("level") == 2 else 1}
    if kind in ("para", "paragraph") and text:
        return {"type": "para", "text": text}
    if kind in ("numbered", "bullets") and (items := _texts(raw.get("items"), shown)):
        own = kind == "numbered" and all(re.match(r"(?:Madde\s*\d+|\d+[.)])\s", i, re.IGNORECASE) for i in items)
        return {"type": kind, "items": items, "own_numbers": own}
    if kind == "table":
        return _table(raw, shown)
    if kind == "calc_table" and calc_rows:
        return {"type": "table", "headers": CALC_HEADERS, "rows": [[r["label"], r["value"], r["kind"]] for r in calc_rows], "caption": ""}
    if kind == "signature" and (parties := _texts(raw.get("parties"), shown, 4)):
        return {"type": "signature", "parties": parties}
    if kind == "chart":
        return _chart(raw, values, shown)
    return None


_DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{4}\b")


def _no_invented_dates(text: str, request: str) -> str:
    """A date the user never wrote is a guess: it becomes a fill-in blank."""
    return _DATE_RE.sub(lambda m: m.group(0) if m.group(0) in request else "[..../..../....]", text)


def parse(raw: dict[str, Any] | None, request: str = "") -> dict[str, Any] | None:
    """{"title","subtitle","blocks"} with all numbers resolved, or None when the JSON is not a usable document."""
    if not isinstance(raw, dict) or not isinstance(raw.get("blocks"), list) or not str(raw.get("title") or "").strip():
        return None
    _REQUEST["text"] = request
    values, shown, calc_rows = doc_calc.run(raw.get("calc"))
    blocks = [b for b in (_block(x, values, shown, calc_rows) for x in raw["blocks"][:_MAX_BLOCKS]) if b]
    if sum(1 for b in blocks if b["type"] in ("para", "numbered", "bullets", "table")) < 2:
        return None
    if request:
        for b in blocks:
            for key in ("text", "caption"):
                if key in b:
                    b[key] = _no_invented_dates(b[key], request)
            if "items" in b:
                b["items"] = [_no_invented_dates(i, request) for i in b["items"]]
        blocks = doc_polish.polish(blocks, request)
    return {"title": doc_calc.fill(str(raw["title"]), shown).strip()[:120], "subtitle": doc_calc.fill(str(raw.get("subtitle") or ""), shown).strip()[:200], "blocks": blocks}
