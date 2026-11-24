"""Multi-format CNC Drawing Ingestion, Regex Dimension Parser, DXF Parser & VLM Extraction."""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pymupdf as fitz
from docx import Document
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageEnhance

import config
from cnc_ballooning_plan import (
    GDT_KEYWORDS,
    BalloonItem,
    compute_zone,
    enrich_cnc_engineering_fields,
    lookup_iso286_fit,
    lookup_iso2768_m,
)
from cnc_ballooning_render import _load_font, _render_spec_sheet_image
from prompt_loader import load_prompt

log = logging.getLogger(__name__)
CNC_VISION_SYSTEM_PROMPT = load_prompt("b2_cnc_vision_prompt.txt")

_RE_QTY = re.compile(r"^(\d+)\s*[xX\u00d7]\s*")
_RE_ROUGHNESS = re.compile(r"\b(Ra|Rz)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_RE_THREAD = re.compile(
    r"\b(M\d+(?:[.,]\d+)?(?:\s*[xX\u00d7]\s*\d+(?:[.,]\d+)?)?(?:-[45678][gGhH])?|G\s*\d+/\d+\"?|NPT\s*\d+/\d+)\b",
    re.IGNORECASE,
)
_RE_DIAMETER = re.compile(
    r"(?:Ø|⌀|Φ|DIA\.?)\s*(\d+(?:[.,]\d+)?)(?:\s*([A-Za-z]{1,2}\d))?"
    r"(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?(?:\s*\+(\d+(?:[.,]\d+)?)\s*/\s*([+-]?\d+(?:[.,]\d+)?))?",
    re.IGNORECASE,
)
_RE_CHAMFER = re.compile(r"\b(?:C\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*[xX\u00d7]\s*45°?)\b", re.IGNORECASE)
_RE_RADIUS = re.compile(r"\bR\s*(\d+(?:[.,]\d+)?)(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?\b")
_RE_ANGLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*°(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?)\s*°?)?")
_RE_LINEAR = re.compile(
    r"^(\d+(?:[.,]\d+)?)(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?"
    r"(?:\s*\+(\d+(?:[.,]\d+)?)\s*/\s*([+-]?\d+(?:[.,]\d+)?))?(?:\s*mm)?$",
    re.IGNORECASE,
)
_RE_GDT_VAL = re.compile(r"(⏥|∥|⊥|◎|⌖|↗|⌭|FLAT|PERP|PARA|CONC|POS|RUNOUT)\s*(?:Ø|⌀)?\s*(\d+(?:[.,]\d+)?)(?:\s+([A-Z]))?", re.IGNORECASE)
_NON_DIMENSION_WORDS = (
    "SCALE", "ÖLÇEK", "OLCEK", "SHEET", "SAYFA", "DATE", "TARİH", "TARIH", "REV", "MATERIAL", "MALZEME",
    "PART NO", "PARÇA NO", "DRAWN", "ÇİZEN", "UNIT", "BİRİM", "TOLERANCE", "ISO 2768", "TITLE",
    "PROJECTION", "WEIGHT", "AĞIRLIK", "FLANGE", "SHAFT", "HOUSING", "SECTION", "KESİT", "DETAIL",
    "VIEW", "GÖRÜNÜŞ", "NOTE:", "NOT:", "ALL DIMENSIONS", "TÜM ÖLÇÜLER", "UNLESS OTHERWISE",
    "ALUMINUM", "STEEL", "4140", "6061", "304", "AISI", "DIN", "CNC", "MILLIMETER", "MM", "APPROVED", "CHECKED", "COMPANY",
)


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _base_geo(box: tuple[float, float, float, float]) -> dict[str, Any]:
    x_pct, y_pct, w_pct, h_pct = box
    return {"x_pct": x_pct, "y_pct": y_pct, "w_pct": w_pct, "h_pct": h_pct, "zone": compute_zone(x_pct, y_pct)}


def _parse_special_char(work: str, text: str, qty: int, geo: dict[str, Any]) -> BalloonItem | None:
    if (m_ra := _RE_ROUGHNESS.search(work)):
        val = _to_float(m_ra.group(2))
        crit = "Kritik" if (val is not None and val <= 0.8) else "Majör"
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Yüzey Pürüzlülüğü", nominal=val, unit="µm",
            max_limit=val, min_limit=0.0, quantity=qty, gage="Yüzey Pürüzlülük Cihazı (Profilometre)",
            criticality=crit, notes=f"Maksimum {m_ra.group(1)} {val} µm", **geo,
        )
    if (m_gdt := _RE_GDT_VAL.search(work)):
        val, datum = _to_float(m_gdt.group(2)), m_gdt.group(3) or ""
        gdt_name = GDT_KEYWORDS.get(m_gdt.group(1), GDT_KEYWORDS.get(m_gdt.group(1).upper(), "GD&T"))
        return BalloonItem(
            balloon_no=0, raw_text=text, category="GD&T", nominal=val, unit="mm",
            max_limit=val, min_limit=0.0, quantity=qty, gage="CMM / Komparatör Saati",
            criticality="Kritik", notes=f"{gdt_name}" + (f" · Datum {datum}" if datum else ""), **geo,
        )
    if (m_th := _RE_THREAD.search(work)):
        note = f"Diş: {m_th.group(1)}"
        if (depth_m := re.search(r"(?:DEPTH|DERİNLİK|↧)\s*(\d+(?:[.,]\d+)?)", work, re.IGNORECASE)):
            note += f", Derinlik {depth_m.group(1)} mm"
        if "THRU" in text.upper() or "BOYUNCA" in text.upper():
            note += ", Boydan Boya (THRU)"
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Diş / Vida", nominal=None, unit="mm", quantity=qty,
            gage="Vida Geçer/Geçmez Mastarı (Go/No-Go)", criticality="Kritik", notes=note, **geo,
        )
    return None


def _parse_diameter(work: str, text: str, qty: int, geo: dict[str, Any]) -> BalloonItem | None:
    m_dia = _RE_DIAMETER.search(work)
    if not m_dia:
        return None
    nom, fit = _to_float(m_dia.group(1)), m_dia.group(2) or ""
    sym_tol, pos_tol, neg_tol = _to_float(m_dia.group(3)), _to_float(m_dia.group(4)), _to_float(m_dia.group(5))
    tol_p: float | None = None
    tol_m: float | None = None
    notes: list[str] = []
    if fit and nom is not None and (fit_res := lookup_iso286_fit(nom, fit)):
        tol_p, tol_m = fit_res
        notes.append(f"ISO 286 Geçme: {fit}")
    if sym_tol is not None:
        tol_p, tol_m = sym_tol, -sym_tol
    elif pos_tol is not None and neg_tol is not None:
        tol_p, tol_m = pos_tol, (neg_tol if neg_tol <= 0 else -neg_tol)
    elif tol_p is None and nom is not None:
        iso_t = lookup_iso2768_m(nom)
        tol_p, tol_m = iso_t, -iso_t
        notes.append("ISO 2768-m genel tolerans")
    if "THRU" in text.upper() or "BOYUNCA" in text.upper():
        notes.append("Boydan boya delik")
    tol_span = abs((tol_p or 0) - (tol_m or 0))
    gage, crit = ("İç/Dış Çap Mikrometresi veya CMM", "Kritik") if (fit or tol_span <= 0.05) else (
        ("Dijital Mikrometre / Hassas Kumpas", "Majör") if tol_span <= 0.15 else ("Dijital Kumpas", "Majör")
    )
    return BalloonItem(
        balloon_no=0, raw_text=text, category="Çap (Ø)", nominal=nom, unit="mm",
        tol_plus=tol_p, tol_minus=tol_m,
        min_limit=round(nom + tol_m, 4) if (nom is not None and tol_m is not None) else None,
        max_limit=round(nom + tol_p, 4) if (nom is not None and tol_p is not None) else None,
        fit_class=fit, quantity=qty, gage=gage, criticality=crit, notes=" · ".join(notes), **geo,
    )


def _parse_geo_or_linear(work: str, text: str, qty: int, geo: dict[str, Any]) -> BalloonItem | None:
    if (m_ch := _RE_CHAMFER.search(text)):
        val = _to_float(m_ch.group(1) or m_ch.group(2))
        tol = lookup_iso2768_m(val) if val is not None else 0.2
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Pah (Chamfer)", nominal=val, unit="mm", tol_plus=tol, tol_minus=-tol,
            min_limit=round(val - tol, 4) if val is not None else None, max_limit=round(val + tol, 4) if val is not None else None,
            quantity=1, gage="Pah Mastarı / Dijital Kumpas", criticality="Minör", notes="45° Pah", **geo,
        )
    if (m_rad := _RE_RADIUS.search(work)):
        nom, sym_tol = _to_float(m_rad.group(1)), _to_float(m_rad.group(2))
        tol = sym_tol if sym_tol is not None else (lookup_iso2768_m(nom) if nom is not None else 0.2)
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Radyüs (R)", nominal=nom, unit="mm", tol_plus=tol, tol_minus=-tol,
            min_limit=round(nom - tol, 4) if nom is not None else None, max_limit=round(nom + tol, 4) if nom is not None else None,
            quantity=qty, gage="Radyüs Mastarı / Optik Profil Projektör", criticality="Minör" if tol >= 0.2 else "Majör",
            notes="ISO 2768-m" if sym_tol is None else "Açık toleranslı radyüs", **geo,
        )
    if (m_ang := _RE_ANGLE.search(work)):
        nom, tol = _to_float(m_ang.group(1)), _to_float(m_ang.group(2)) or 0.5
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Açı", nominal=nom, unit="°", tol_plus=tol, tol_minus=-tol,
            min_limit=round(nom - tol, 4) if nom is not None else None, max_limit=round(nom + tol, 4) if nom is not None else None,
            quantity=qty, gage="Universal Açıölçer / CMM", criticality="Majör", notes="Açısal ölçü", **geo,
        )
    return _parse_linear(work, text, qty, geo)


def _parse_linear(work: str, text: str, qty: int, geo: dict[str, Any]) -> BalloonItem | None:
    m_lin = _RE_LINEAR.match(work)
    if not m_lin:
        return None
    nom = _to_float(m_lin.group(1))
    if nom is None or nom <= 0 or nom > 5000:
        return None
    sym_tol, pos_tol, neg_tol = _to_float(m_lin.group(2)), _to_float(m_lin.group(3)), _to_float(m_lin.group(4))
    note = ""
    if sym_tol is not None:
        tol_p, tol_m = sym_tol, -sym_tol
    elif pos_tol is not None and neg_tol is not None:
        tol_p, tol_m = pos_tol, (neg_tol if neg_tol <= 0 else -neg_tol)
    else:
        iso_t = lookup_iso2768_m(nom)
        tol_p, tol_m, note = iso_t, -iso_t, "ISO 2768-m genel tolerans"
    span = abs(tol_p - tol_m)
    gage, crit = ("Dijital Mikrometre / CMM", "Kritik") if span <= 0.06 else (
        ("Dijital Kumpas (0.01 mm)", "Majör") if span <= 0.2 else ("Dijital Kumpas", "Minör")
    )
    return BalloonItem(
        balloon_no=0, raw_text=text, category="Lineer Ölçü", nominal=nom, unit="mm", tol_plus=tol_p, tol_minus=tol_m,
        min_limit=round(nom + tol_m, 4), max_limit=round(nom + tol_p, 4),
        quantity=qty, gage=gage, criticality=crit, notes=note, **geo,
    )


def parse_cnc_dimension(
    raw_text: str, x_pct: float = 50.0, y_pct: float = 50.0, w_pct: float = 4.0, h_pct: float = 2.0
) -> BalloonItem | None:
    """Parse a raw text string from a CNC technical drawing into a structured BalloonItem."""
    text = " ".join(raw_text.strip().split())
    if not text or len(text) > 70 or any(w in text.upper() for w in _NON_DIMENSION_WORDS):
        return None
    if re.search(r"\b\d{2,4}[-./]\d{2}[-./]\d{2,4}\b", text) or re.fullmatch(r"\d+\s*:\s*\d+", text):
        return None
    qty, work = 1, text
    if (m_qty := _RE_QTY.match(work)) and "45" not in work:
        qty, work = int(m_qty.group(1)), work[m_qty.end():].strip()
    geo = _base_geo((x_pct, y_pct, w_pct, h_pct))
    return _parse_special_char(work, text, qty, geo) or _parse_diameter(work, text, qty, geo) or _parse_geo_or_linear(work, text, qty, geo)


def _extract_metadata_from_texts(texts: list[str]) -> dict[str, str]:
    joined = "\n".join(texts)
    meta = {"part_number": "", "part_name": "", "material": "", "revision": "A", "standard": "ISO 2768-mK"}
    patterns = (
        ("part_number", r"(?:PART\s*NO\.?|PARÇA\s*NO\.?|DWG\s*NO\.?)[:\s]+([A-Z0-9_-]{3,30})"),
        ("material", r"(?:MATERIAL|MALZEME)[:\s]+([^\n|]{2,40})"),
        ("revision", r"(?:REV\.?|REVİZYON)[:\s]+([A-Z0-9.]{1,8})"),
        ("standard", r"(ISO\s*2768-[a-zA-Z]{1,2}|ASME\s*Y14\.5)"),
        ("part_name", r"(?:PART\s*NAME|PARÇA\s*ADI|TITLE)[:\s]+([^\n|]{3,50})"),
    )
    for key, pat in patterns:
        if (m := re.search(pat, joined, re.IGNORECASE)):
            meta[key] = m.group(1).strip()
    return meta


async def _pick_vision_model(preferred: str | None = None) -> str:
    """Select the best installed Ollama vision model."""
    candidates = [c for c in (preferred, config.CNC_VISION_MODEL, "cnc-ballooner", "qwen3.5:9b", "qwen3.5:4b", "gemma4:e4b", config.MASTER_MODEL) if c]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            installed = {m.get("name", "") for m in resp.json().get("models", [])}
            installed_base = {name.split(":")[0] for name in installed}
            for cand in candidates:
                if cand in installed or cand in installed_base:
                    return cand
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as exc:
        log.debug("Vision model probe skipped: %s", exc)
    return config.MASTER_MODEL


def _parse_vlm_json_response(content: str, meta: dict[str, str]) -> list[BalloonItem]:
    items: list[BalloonItem] = []
    if not (json_match := re.search(r"\{[\s\S]*\}", content)):
        return items
    try:
        parsed = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return items
    if isinstance(parsed.get("metadata"), dict):
        for k in meta:
            if parsed["metadata"].get(k):
                meta[k] = str(parsed["metadata"][k])
    for raw_b in parsed.get("balloons", []):
        if not isinstance(raw_b, dict) or not (raw_text := str(raw_b.get("raw_text", "")).strip()):
            continue
        x_pct = max(3.0, min(97.0, float(raw_b.get("x_pct", 50.0))))
        y_pct = max(3.0, min(95.0, float(raw_b.get("y_pct", 50.0))))
        item = parse_cnc_dimension(raw_text, x_pct=x_pct, y_pct=y_pct)
        if item is None:
            item = BalloonItem(
                balloon_no=0, raw_text=raw_text, category="Genel Özellik / Not",
                notes=str(raw_b.get("notes", "")), x_pct=x_pct, y_pct=y_pct, zone=compute_zone(x_pct, y_pct),
            )
        elif raw_b.get("notes") and not item.notes:
            item.notes = str(raw_b["notes"])
        items.append(item)
    return items


async def _analyze_image_with_vlm(
    img: Image.Image, model_override: str | None = None, extra_text_context: str = ""
) -> tuple[list[BalloonItem], dict[str, str], str]:
    """Use local Ollama vision model to detect CNC dimensions and approximate coordinates."""
    model = await _pick_vision_model(model_override)
    vlm_img = img.convert("RGB")
    if max(vlm_img.size) > 1400:
        ratio = 1400 / max(vlm_img.size)
        vlm_img = vlm_img.resize((int(vlm_img.width * ratio), int(vlm_img.height * ratio)), Image.Resampling.LANCZOS)
    vlm_img = ImageEnhance.Sharpness(ImageEnhance.Contrast(vlm_img).enhance(1.15)).enhance(1.2)
    buf = io.BytesIO()
    vlm_img.save(buf, format="PNG")
    user_prompt = "Bu teknik çizimdeki tüm CNC ölçülerini, toleransları, dişleri, yüzey pürüzlülüklerini ve GD&T sembollerini eksiksiz çıkar ve JSON olarak ver."
    if extra_text_context:
        user_prompt += f"\n\nEk doküman metni:\n{extra_text_context[:3000]}"
    messages = [
        {"role": "system", "content": CNC_VISION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt, "images": [base64.b64encode(buf.getvalue()).decode("ascii")]},
    ]
    meta = {"part_number": "", "part_name": "", "material": "", "revision": "A", "standard": "ISO 2768-mK"}
    try:
        import gateway

        gw_res = await gateway.default_client.chat(
            messages, model=model, profile="factual", num_predict=4096, timeout_s=180.0, feature="cnc_ballooning", max_retries=0
        )
        return _parse_vlm_json_response(gw_res.content, meta), meta, model
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError, AttributeError):
        return [], meta, model


def _parse_dxf_entities(raw_bytes: bytes) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float]], list[tuple[float, float, str]]]:
    raw_lines = [line.strip() for line in raw_bytes.decode("utf-8", errors="ignore").splitlines()]
    pairs: list[tuple[int, str]] = []
    for i in range(0, len(raw_lines) - 1, 2):
        try:
            pairs.append((int(raw_lines[i]), raw_lines[i + 1]))
        except ValueError:
            continue
    lines_g: list[tuple[float, float, float, float]] = []
    circles_g: list[tuple[float, float, float]] = []
    texts_g: list[tuple[float, float, str]] = []
    idx, n = 0, len(pairs)
    while idx < n:
        code, val = pairs[idx]
        if code != 0 or val not in ("LINE", "CIRCLE", "TEXT", "MTEXT", "DIMENSION"):
            idx += 1
            continue
        etype, idx, props = val, idx + 1, {}
        while idx < n and pairs[idx][0] != 0:
            props[pairs[idx][0]] = pairs[idx][1]
            idx += 1
        _append_dxf_entity(etype, props, lines_g, circles_g, texts_g)
    return lines_g, circles_g, texts_g


def _append_dxf_entity(
    etype: str, props: dict[int, str],
    lines_g: list[tuple[float, float, float, float]], circles_g: list[tuple[float, float, float]], texts_g: list[tuple[float, float, str]],
) -> None:
    try:
        if etype == "LINE":
            lines_g.append((float(props.get(10, 0)), float(props.get(20, 0)), float(props.get(11, 0)), float(props.get(21, 0))))
        elif etype == "CIRCLE":
            circles_g.append((float(props.get(10, 0)), float(props.get(20, 0)), float(props.get(40, 10))))
        else:
            raw_t = props.get(1, "").strip()
            clean_t = re.sub(r"\\[A-Za-z0-9]+;", "", raw_t).replace("%%c", "Ø").replace("%%C", "Ø").replace("%%p", "±").replace("%%d", "°").strip()
            if clean_t:
                texts_g.append((float(props.get(10, props.get(11, 0))), float(props.get(20, props.get(21, 0))), clean_t))
    except ValueError:
        return


def _extract_dxf_balloons(raw_bytes: bytes) -> tuple[Image.Image, list[BalloonItem], dict[str, str]]:
    """Parse ASCII DXF CAD entities (LINE, CIRCLE, TEXT, MTEXT, DIMENSION), render CAD canvas, and extract balloons."""
    lines_g, circles_g, texts_g = _parse_dxf_entities(raw_bytes)
    xs = [0.0, 200.0, *(v for ln in lines_g for v in (ln[0], ln[2])), *(v for c in circles_g for v in (c[0] - c[2], c[0] + c[2])), *(t[0] for t in texts_g)]
    ys = [0.0, 140.0, *(v for ln in lines_g for v in (ln[1], ln[3])), *(v for c in circles_g for v in (c[1] - c[2], c[1] + c[2])), *(t[1] for t in texts_g)]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    pad_x, pad_y = max(10.0, max_x - min_x) * 0.12, max(10.0, max_y - min_y) * 0.14
    min_x, max_x, min_y, max_y = min_x - pad_x, max_x + pad_x, min_y - pad_y, max_y + pad_y
    span_x, span_y = max_x - min_x, max_y - min_y

    W, H = 1650, 1160
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, W - 16, H - 16], outline=(20, 30, 50), width=3)
    font = _load_font(17, bold=False)

    def to_px(x: float, y: float) -> tuple[float, float]:
        return 40 + ((x - min_x) / span_x) * (W - 80), H - 40 - ((y - min_y) / span_y) * (H - 80)

    for x1, y1, x2, y2 in lines_g:
        draw.line([to_px(x1, y1), to_px(x2, y2)], fill=(20, 30, 50), width=2)
    for cx, cy, r in circles_g:
        px, py = to_px(cx, cy)
        rx, ry = (r / span_x) * (W - 80), (r / span_y) * (H - 80)
        draw.ellipse([px - rx, py - ry, px + rx, py + ry], outline=(20, 30, 50), width=2)

    balloons: list[BalloonItem] = []
    for tx, ty, txt in texts_g:
        px, py = to_px(tx, ty)
        draw.text((px, py - 8), txt, fill=(25, 70, 140), font=font)
        item = parse_cnc_dimension(txt, x_pct=max(3.0, min(97.0, px / W * 100.0)), y_pct=max(3.0, min(95.0, py / H * 100.0)))
        if item is not None:
            balloons.append(item)
    return img, balloons, _extract_metadata_from_texts([t[2] for t in texts_g])


def _extract_pdf_vector_balloons(pdf_bytes: bytes) -> tuple[Image.Image, list[BalloonItem], dict[str, str]]:
    """Render first page of PDF to high-DPI PNG and extract vector dimension callouts with exact positions."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    img = Image.open(io.BytesIO(page.get_pixmap(dpi=220).tobytes("png"))).convert("RGB")
    pw, ph = page.rect.width, page.rect.height
    text_dict: Any = page.get_text("dict")
    all_texts: list[str] = []
    balloons: list[BalloonItem] = []

    for b in (text_dict.get("blocks", []) if isinstance(text_dict, dict) else []):
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            line_text = " ".join(s.get("text", "").strip() for s in line.get("spans", []) if s.get("text", "").strip())
            if not line_text:
                continue
            all_texts.append(line_text)
            x0, y0, x1, y1 = line.get("bbox", (0, 0, 0, 0))
            cx_pct, cy_pct = ((x0 + x1) / 2.0) / pw * 100.0, ((y0 + y1) / 2.0) / ph * 100.0
            if cx_pct > 62.0 and cy_pct > 78.0:
                continue
            item = parse_cnc_dimension(line_text, x_pct=cx_pct, y_pct=cy_pct, w_pct=max(2.0, (x1 - x0) / pw * 100.0), h_pct=max(1.5, (y1 - y0) / ph * 100.0))
            if item is not None:
                balloons.append(item)
    doc.close()
    return img, balloons, _extract_metadata_from_texts(all_texts)


def _extract_largest_zip_image(raw: bytes, prefix: str) -> Image.Image | None:
    best_img: Image.Image | None = None
    best_area = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if not info.filename.startswith(prefix) or not info.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff")):
                    continue
                try:
                    im = Image.open(io.BytesIO(zf.read(info.filename))).convert("RGB")
                    if im.width * im.height > best_area:
                        best_area, best_img = im.width * im.height, im
                except (OSError, ValueError, TypeError, KeyError, RuntimeError, zipfile.BadZipFile, SyntaxError) as exc:
                    log.debug("Skipped unreadable zip image: %s", exc)
    except zipfile.BadZipFile:
        return None
    return best_img


async def _process_office_drawing(
    filename: str, texts: list[str], embedded_img: Image.Image | None, opts: tuple[str, str | None, bool]
) -> tuple[Image.Image, list[BalloonItem], dict[str, str], str]:
    tag, model_override, use_vlm = opts
    meta = _extract_metadata_from_texts(texts)
    if embedded_img is not None:
        if not use_vlm:
            return embedded_img, [], meta, f"{tag}-img"
        balloons, vlm_meta, model = await _analyze_image_with_vlm(embedded_img, model_override=model_override, extra_text_context="\n".join(texts[:150]))
        for k, v in vlm_meta.items():
            if v and not meta.get(k):
                meta[k] = v
        return embedded_img, balloons, meta, f"{tag}-img+vlm:{model}"
    matched = [(t, it) for t in texts if (it := parse_cnc_dimension(t))]
    img = _render_spec_sheet_image(filename, [t for t, _ in matched] or texts[:20])
    balloons: list[BalloonItem] = []
    for idx, (_, item) in enumerate(matched):
        item.x_pct, item.y_pct = 8.0, min(96.0, (128 + idx * 44) / img.height * 100.0)
        item.zone = compute_zone(item.x_pct, item.y_pct)
        balloons.append(item)
    return img, balloons, meta, f"{tag}-table+iso2768"


async def _ingest_drawing_by_ext(
    filename: str, raw_bytes: bytes, model_override: str | None, use_vlm: bool
) -> tuple[Image.Image, list[BalloonItem], dict[str, str], str]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        img, balloons, meta = _extract_pdf_vector_balloons(raw_bytes)
        if balloons or not use_vlm:
            return img, balloons, meta, "pymupdf-vector+iso2768"
        balloons, vlm_meta, model = await _analyze_image_with_vlm(img, model_override=model_override)
        for k, v in vlm_meta.items():
            if v and not meta.get(k):
                meta[k] = v
        return img, balloons, meta, f"vlm:{model}"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")):
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        if not use_vlm:
            return img, [], {"part_number": "", "part_name": "", "material": "", "revision": "A", "standard": "ISO 2768-mK"}, "manual"
        balloons, meta, model = await _analyze_image_with_vlm(img, model_override=model_override)
        return img, balloons, meta, f"vlm:{model}"
    if lower.endswith(".docx"):
        doc = Document(io.BytesIO(raw_bytes))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        lines.extend(c.text.strip() for t in doc.tables for row in t.rows for c in row.cells if c.text.strip())
        return await _process_office_drawing(filename, lines, _extract_largest_zip_image(raw_bytes, "word/media/"), ("docx", model_override, use_vlm))
    if lower.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(raw_bytes), data_only=True)
        cells = [str(val).strip() for s in wb.worksheets for row in s.iter_rows(values_only=True) for val in row if val is not None and str(val).strip()]
        return await _process_office_drawing(filename, cells, _extract_largest_zip_image(raw_bytes, "xl/media/"), ("xlsx", model_override, use_vlm))
    if lower.endswith(".dxf"):
        img, balloons, meta = _extract_dxf_balloons(raw_bytes)
        return img, balloons, meta, "dxf-cad-vector+iso2768"
    raise ValueError(f"Desteklenmeyen teknik çizim formatı: {filename}")


async def process_drawing(
    filename: str, raw_bytes: bytes, model_override: str | None = None, use_vlm: bool = True
) -> tuple[Image.Image, list[BalloonItem], dict[str, str], str]:
    """Ingest PDF / Image / DOCX / XLSX / DXF and return (base_image, balloons, metadata, engine_used)."""
    img, balloons, meta, engine_used = await _ingest_drawing_by_ext(filename, raw_bytes, model_override, use_vlm)
    balloons.sort(key=lambda b: (round(b.y_pct / 8.0), b.x_pct))
    for i, b in enumerate(balloons, start=1):
        b.balloon_no = i
        if not b.zone:
            b.zone = compute_zone(b.x_pct, b.y_pct)
        enrich_cnc_engineering_fields(b)
    if not meta.get("part_name"):
        meta["part_name"] = Path(filename).stem
    return img, balloons, meta, engine_used
