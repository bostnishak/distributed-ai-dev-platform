"""From the numbers the model read out of a request to a validated G-code job: unit conversion, missing-essentials questions, assumptions."""

from __future__ import annotations

import re
from typing import Any

import gcode_gen as gg
from gcode_patterns import missing_for

_WORDS = {
    "face": r"(yüzey|yuzey|faceleme|facing|düzle|duzle|tıraş|tiras|face\b)",
    "pocket": r"(\bcep\b|cebi|cepl|pocket|\bcep\w*)",
    "round_pocket": r"(\bcep\b|cebi|cepl|pocket|havuz)",
    "slot": r"(yuva|kanal|\bslot\b|kama\b|oluk)",
    "profile": r"(kontur|profil|dış\s+ölçü|dis\s+olcu|çevre\w*\s+kes|contour|kes\b|kesil|dairesel\s+parça|yuvarlak\s+parça|disk)",
    "hole": r"(delik|delin|matkap|drill|hole|bore|civata|bolt)",
    "engrave": r"(kazı|kazi|oyma|gravür|gravur|engrave|desen|şekil|sekil|yıldız|yildiz|altıgen|altigen)",
}
_LENGTH_KEYS = ("x", "y", "z", "cx", "cy", "x0", "y0", "pcd", "pitch_x", "pitch_y", "dx", "dy", "inset", "diameter", "width", "length", "depth", "x1", "y1", "x2", "y2", "mill_diameter")
_KINDS = ("face", "hole", "holes", "pocket", "round_pocket", "slot", "profile", "engrave")
INCH = 25.4


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def _asked_for(kind: str, request: str) -> bool:
    """Operations the model added on its own (e.g. copied from an example) are dropped: each must be named in the request."""
    key = "hole" if kind in ("hole", "holes") else kind
    return bool(re.search(_WORDS[key], request, re.IGNORECASE))


def _to_mm(raw: Any) -> Any:
    """Inch input -> millimetres for every length field (counts, angles and sides stay as they are)."""
    if isinstance(raw, dict):
        return {k: (round(v * INCH, 4) if k in _LENGTH_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool) else _to_mm(v)) for k, v in raw.items()}
    if isinstance(raw, list):
        return [(round(x * INCH, 4) if isinstance(x, (int, float)) and not isinstance(x, bool) else _to_mm(x)) for x in raw]
    return raw


def _hole(op: dict[str, Any], stock: tuple[float, ...]) -> tuple[dict[str, Any] | None, str]:
    dia = _num(op.get("diameter"))
    if dia is None:
        return None, "Delik çaplarını (mm) belirtir misin?"
    op = {**op, "diameter": dia, "type": "holes"}
    if op.get("pattern") is None and not op.get("points"):
        op["points"] = [(_num(op.get("x")) or stock[0] / 2, _num(op.get("y")) or stock[1] / 2)]
    return (None, question) if (question := missing_for(op)) else (op, "")


def _need(op: dict[str, Any], keys: tuple[str, ...], question: str) -> str:
    return question if None in (_num(op.get(k)) for k in keys) else ""


def _slot(op: dict[str, Any], stock: tuple[float, ...]) -> tuple[dict[str, Any] | None, str]:
    if q := _need(op, ("width", "length", "depth"), "Yuvanın genişlik, uzunluk ve derinliğini (mm) belirtir misin?"):
        return None, q
    x, y = _num(op.get("x")) or stock[0] / 2, _num(op.get("y")) or stock[1] / 2
    if float(op["length"]) <= float(op["width"]):
        return None, "Yuvanın uzunluğu genişliğinden büyük olmalı; yuva uzunluğunu (uçtan uca, mm) belirtir misin?"
    half = (float(op["length"]) - float(op["width"])) / 2  # `length` is end to end, the tool-centre path runs between the two end-circle centres
    vertical = str(op.get("orientation") or "x").lower().startswith("y")
    ends = ((x, y - half), (x, y + half)) if vertical else ((x - half, y), (x + half, y))
    return {**op, "x1": ends[0][0], "y1": ends[0][1], "x2": ends[1][0], "y2": ends[1][1]}, ""


def _shape_op(kind: str, op: dict[str, Any], stock: tuple[float, ...]) -> tuple[dict[str, Any] | None, str]:
    """Operations with their own geometry: pocket, round pocket, slot, profile, engraving; positions default to the stock centre."""
    pos = {"x": _num(op.get("x")) or stock[0] / 2, "y": _num(op.get("y")) or stock[1] / 2}
    if kind in ("pocket", "round_pocket", "slot") and _num(op.get("depth")) is None:
        op = {**op, "depth": round(min(3.0, stock[2] / 2), 1)}  # depth not given: a shallow default (half the thickness, at most 3 mm), shown under "Varsayımlar"
    if kind == "pocket":
        return ({**op, **pos}, "") if not (q := _need(op, ("width", "length", "depth"), "Cebin genişlik, uzunluk ve derinliğini (mm) belirtir misin?")) else (None, q)
    if kind == "round_pocket":
        return ({**op, **pos}, "") if not (q := _need(op, ("diameter", "depth"), "Dairesel cebin çap ve derinliğini (mm) belirtir misin?")) else (None, q)
    if kind == "slot":
        return _slot(op, stock)
    if kind == "engrave":
        if _num(op.get("diameter")) is None and not (_num(op.get("width")) and _num(op.get("length"))):
            return None, "Kazınacak şeklin boyutunu (çap ya da genişlik x uzunluk, mm) belirtir misin?"
        return {**op, **pos, "depth": _num(op.get("depth")) or 0.5}, ""
    shape = str(op.get("shape") or "rect").lower()
    if shape == "circle":
        return ({**op, **pos, "shape": "circle", "depth": _num(op.get("depth")) or stock[2]}, "") if _num(op.get("diameter")) else (None, "Kesilecek dairesel parçanın çapını (mm) belirtir misin?")
    return {**op, **pos, "shape": "rect", "depth": _num(op.get("depth")) or stock[2]}, ""


def _clean_op(op: dict[str, Any], stock: tuple[float, ...]) -> tuple[dict[str, Any] | None, str]:
    """(operation with every number filled, '') or (None, question) when a required number is missing."""
    kind = op["type"]
    if kind in ("hole", "holes"):
        return _hole(op, stock)
    if kind == "face":
        return {**op, "depth": _num(op.get("depth")) or 0.5}, ""
    return _shape_op(kind, op, stock)


def _assumptions(raw: dict[str, Any], ops: list[dict[str, Any]], job: gg.Job) -> list[str]:
    """Everything the request did not say and the program therefore assumes; shown to the user next to the result."""
    out = []
    if not gg.material_key(str(raw.get("material") or "")):
        out.append("Malzeme belirtilmediği için alüminyum alındı (devir/ilerleme buna göre; farklıysa söyle)")
    if not _num(raw.get("mill_diameter")):
        out.append(f"Freze çapı işlere göre otomatik seçildi: Ø{job.mill_dia:g} mm, {job.flutes} kesme ağızlı karbür parmak freze")
    if any(op.get("pattern") == "corners" and not _num(op.get("inset")) for op in ops):
        out.append("Köşe deliklerinin kenara uzaklığı belirtilmediği için 8 mm alındı")
    if any(op["type"] in ("pocket", "round_pocket", "profile", "slot") and not raw_has_depth(raw, op) for op in ops):
        out.append("Derinliği verilmeyen cep/kontur/yuva için parça kalınlığı ya da istenen değer kullanıldı")
    if not raw.get("flavor"):
        out.append("Denetleyici dili belirtilmediği için FANUC (G-code) kullanıldı")
    if job.units == "inch":
        out.append("Ölçüler inç olarak verildiği için program G20 (inç) çıktı; kesme parametreleri mm hesabından dönüştürüldü")
    out.append("Sıfır noktası parçanın sol alt köşesi/üst yüzeyi; soğutma sıvısı açık")
    return out


def raw_has_depth(raw: dict[str, Any], op: dict[str, Any]) -> bool:
    return any(isinstance(o, dict) and o.get("type") == op["type"] and _num(o.get("depth")) for o in raw.get("operations") or [])


def build_job(raw: dict[str, Any], request: str = "") -> tuple[gg.Job | None, str]:
    """(job, '') or (None, question for the user) when something essential is missing."""
    units = "inch" if str(raw.get("units") or "mm").lower().startswith("in") else "mm"
    if units == "inch":
        raw = {**_to_mm(raw), "units": "inch"}
    stock_raw = raw.get("stock") or {}
    dims = [_num(stock_raw.get(k)) for k in ("x", "y", "z")]
    ops = [op for op in raw.get("operations") or [] if isinstance(op, dict) and op.get("type") in _KINDS and (not request or _asked_for(op["type"], request))]
    if None in dims:
        return None, "Parçanın ölçülerini (uzunluk x genişlik x kalınlık) yazar mısın? G-code'daki koordinatlar ve derinlikler buna göre hesaplanıyor."
    if not ops:
        return None, "Hangi işlemleri istediğini yazar mısın? (ör. yüzey frezeleme, delik, cep, yuva, dış kontur)"
    stock = (float(dims[0] or 0), float(dims[1] or 0), float(dims[2] or 0))
    clean: list[dict[str, Any]] = []
    for op in ops:
        fixed, question = _clean_op(op, stock)
        if fixed is None:
            return None, question
        clean.append(fixed)
    flavor = str(raw.get("flavor") or "fanuc").lower()
    mill = _num(raw.get("mill_diameter")) or gg.auto_mill_dia(clean)
    material = gg.material_key(str(raw.get("material") or "")) or "aluminum"
    job = gg.Job(material, stock, clean, mill, 3, flavor if flavor in ("fanuc", "mach3", "grbl") else "fanuc", units)
    job.assumptions = _assumptions(raw, clean, job)
    return job, ""
