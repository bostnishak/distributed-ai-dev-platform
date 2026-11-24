"""CNC Technical Drawing Ballooning & Quality Inspection Engine.

Supports multi-format ingestion (PDF, PNG/JPG/WEBP/TIFF/BMP, DOCX, XLSX/XLSM):
- Vector PDF: exact text + bounding box extraction via PyMuPDF (fitz), merged with ISO 2768-mK / ISO 286 rules.
- Raster Images / Scanned PDFs: Vision-LLM (Ollama: cnc-ballooner / qwen3.5:9b / qwen3.5:4b / gemma4:e4b) structured extraction.
- DOCX / XLSX: extracts embedded drawings + dimension/tolerance tables.

Produces:
- High-resolution annotated PNG with non-overlapping numbered red balloons & leader lines.
- Multi-page annotated PDF (ballooned drawing + AS9102/FAI inspection table).
- Styled Excel (.xlsx) AS9102/FAI inspection report with live OK/NOK formulas.
- Styled Word (.docx) inspection report with embedded ballooned drawing.
"""

from __future__ import annotations

import base64
import io
import json
import math
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pymupdf as fitz
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import config

# --- ISO 2768-m (Medium) General Linear Tolerances (mm) ---
ISO_2768_M_LINEAR = [
    (0.5, 3.0, 0.1),
    (3.0, 6.0, 0.1),
    (6.0, 30.0, 0.2),
    (30.0, 120.0, 0.3),
    (120.0, 400.0, 0.5),
    (400.0, 1000.0, 0.8),
    (1000.0, 2000.0, 1.2),
    (2000.0, 4000.0, 2.0),
]

# --- ISO 286 Common CNC Fit Deviations (upper_um, lower_um) by upper diameter bound (mm) ---
ISO_286_FITS: dict[str, list[tuple[float, float, float]]] = {
    "H7": [
        (3, 10, 0), (6, 12, 0), (10, 15, 0), (18, 18, 0), (30, 21, 0),
        (50, 25, 0), (80, 30, 0), (120, 35, 0), (180, 40, 0), (250, 46, 0),
    ],
    "H8": [
        (3, 14, 0), (6, 18, 0), (10, 22, 0), (18, 27, 0), (30, 33, 0),
        (50, 39, 0), (80, 46, 0), (120, 54, 0), (180, 63, 0), (250, 72, 0),
    ],
    "H6": [
        (3, 6, 0), (6, 8, 0), (10, 9, 0), (18, 11, 0), (30, 13, 0),
        (50, 16, 0), (80, 19, 0), (120, 22, 0), (180, 25, 0), (250, 29, 0),
    ],
    "g6": [
        (3, -2, -8), (6, -4, -12), (10, -5, -14), (18, -6, -17), (30, -7, -20),
        (50, -9, -25), (80, -10, -29), (120, -12, -34), (180, -14, -39), (250, -15, -44),
    ],
    "h6": [
        (3, 0, -6), (6, 0, -8), (10, 0, -9), (18, 0, -11), (30, 0, -13),
        (50, 0, -16), (80, 0, -19), (120, 0, -22), (180, 0, -25), (250, 0, -29),
    ],
    "h7": [
        (3, 0, -10), (6, 0, -12), (10, 0, -15), (18, 0, -18), (30, 0, -21),
        (50, 0, -25), (80, 0, -30), (120, 0, -35), (180, 0, -40), (250, 0, -46),
    ],
    "f7": [
        (3, -6, -16), (6, -10, -22), (10, -13, -28), (18, -16, -34), (30, -20, -41),
        (50, -25, -50), (80, -30, -60), (120, -36, -71), (180, -43, -83), (250, -50, -96),
    ],
    "k6": [
        (3, 6, 0), (6, 9, 1), (10, 10, 1), (18, 12, 1), (30, 15, 2),
        (50, 18, 2), (80, 21, 2), (120, 25, 3), (180, 28, 3), (250, 33, 4),
    ],
}

GDT_KEYWORDS = {
    "⏥": "Düzlemsellik (Flatness)",
    "∥": "Paralellik (Parallelism)",
    "⊥": "Diklik (Perpendicularity)",
    "◎": "Eşmerkezlilik (Concentricity)",
    "⌖": "Konum (True Position)",
    "↗": "Salgı (Runout)",
    "⌭": "Silindiriklik (Cylindricity)",
    "FLAT": "Düzlemsellik (Flatness)",
    "PERP": "Diklik (Perpendicularity)",
    "PARA": "Paralellik (Parallelism)",
    "CONC": "Eşmerkezlilik (Concentricity)",
    "POS": "Konum (True Position)",
    "RUNOUT": "Salgı (Runout)",
}


@dataclass
class BalloonItem:
    balloon_no: int
    raw_text: str
    category: str  # Cap, Lineer, Dis/Vida, Radius/Pah, Yuzey Puruzlulugu, GD&T, Aci, Not
    nominal: float | None = None
    unit: str = "mm"
    tol_plus: float | None = None
    tol_minus: float | None = None
    min_limit: float | None = None
    max_limit: float | None = None
    fit_class: str = ""
    quantity: int = 1
    gage: str = "Dijital Kumpas"
    criticality: str = "Majör"  # Kritik, Majör, Minör
    notes: str = ""
    x_pct: float = 50.0  # 0..100 normalized X on drawing image
    y_pct: float = 50.0  # 0..100 normalized Y on drawing image
    w_pct: float = 4.0
    h_pct: float = 2.0
    zone: str = ""
    operation: str = "OP10 · CNC İşleme"
    tooling: str = "Karbür Kesici Takım"
    inspection_freq: str = "İlk Parça + 1/10"
    datum_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def enrich_cnc_engineering_fields(item: BalloonItem) -> BalloonItem:
    """Populate senior CNC manufacturing fields (OP routing, tooling, sampling/SPC, datum)."""
    cat = item.category
    span = (
        round(abs(item.max_limit - item.min_limit), 4)
        if (item.min_limit is not None and item.max_limit is not None)
        else None
    )

    if cat == "Yüzey Pürüzlülüğü":
        if item.nominal is not None and item.nominal <= 0.8:
            item.operation = "OP40 · Silindirik / Yüzey Taşlama"
            item.tooling = "Al2O3 / CBN Taşlama Taşı (veya Wiper Finiş Uç)"
            item.inspection_freq = "%100 (İlk + Seri · Profilometre)"
        else:
            item.operation = "OP10 · CNC Torna / Finiş Pasosu"
            item.tooling = "VNMG / DCMT Finiş Karbür Uç (R0.4)"
            item.inspection_freq = "İlk Parça + 1/10"
    elif cat == "GD&T":
        m_dat = re.search(r"Datum\s+([A-Z])", item.notes)
        if m_dat:
            item.datum_ref = m_dat.group(1)
        item.operation = "OP10/OP40 · Tek Bağlamada Finiş / Taşlama"
        item.tooling = "Hassas Finiş Bara / Yumuşak Çene Referanslama"
        item.inspection_freq = "%100 (CMM · SPC Cp/Cpk ≥ 1.33)"
    elif cat == "Diş / Vida":
        m_tap = re.search(r"M(\d+(?:\.\d+)?)\s*[xX\u00d7]?\s*(\d+(?:\.\d+)?)?", item.raw_text, re.IGNORECASE)
        pre_drill = ""
        if m_tap:
            d = float(m_tap.group(1))
            pitch = float(m_tap.group(2)) if m_tap.group(2) else (1.25 if d == 8 else (1.5 if d == 10 else 1.0))
            pre_drill = f"Ön Delik Ø{d - pitch:.1f} Karbür Matkap + "
        item.operation = "OP30 · CNC Delik Delme & Kılavuz"
        item.tooling = f"{pre_drill}HSS-E Makine Kılavuzu"
        item.inspection_freq = "%100 (Go/No-Go Vida Mastarı)"
    elif cat == "Çap (Ø)":
        if item.fit_class or (span is not None and span <= 0.05):
            item.operation = "OP10/OP20 · Hassas Bara / Raybalama"
            item.tooling = f"Mikrometrik Hassas Bara Kafası / {item.fit_class or 'H7'} Rayba"
            item.inspection_freq = "%100 (İlk + Seri · SPC Cp/Cpk ≥ 1.33)"
        elif "THRU" in item.raw_text.upper() or item.quantity > 1:
            item.operation = "OP30 · CNC Dik İşleme (Delik)"
            item.tooling = f"Ø{item.nominal:g} İçten Soğutmalı Karbür Matkap" if item.nominal else "Karbür Matkap"
            item.inspection_freq = "İlk Parça + 1/10"
        else:
            item.operation = "OP10 · CNC Torna (Kaba + Finiş)"
            item.tooling = "CNMG 120408 (Kaba) + DNMG 150404 (Finiş)"
            item.inspection_freq = "İlk Parça + 1/5" if item.criticality == "Kritik" else "İlk Parça + 1/10"
    elif cat == "Pah (Chamfer)":
        item.operation = "OP20 · Pah Kırma / Çapak Alma"
        item.tooling = "90° Karbür Pah Frezesi / Torna Pah Pasosu"
        item.inspection_freq = "İlk Parça Onayı (FAI)"
    elif cat == "Radyüs (R)":
        item.operation = "OP10/OP20 · Kontur Finiş"
        item.tooling = "Radyüs Profil Uç / Küresel Parmak Freze"
        item.inspection_freq = "İlk Parça Onayı (FAI)"
    elif cat == "Açı":
        item.operation = "OP20 · C-Ekseni / İndeksleme"
        item.tooling = "CNC C-Eksen / 4. Eksen Divizör"
        item.inspection_freq = "İlk Parça + 1/20"
    else:
        item.operation = "OP10/OP20 · CNC Alın / Boy İşleme"
        item.tooling = "CNMG Alın Torna / Ø50 Tarama Kafası"
        item.inspection_freq = "%100 (İlk + Seri)" if item.criticality == "Kritik" else "İlk Parça + 1/10"

    return item


MATERIAL_CUTTING_DB: list[tuple[tuple[str, ...], dict[str, str]]] = [
    (("4140", "4340", "CRMO", "ALLOY STEEL", "ISLAH"), {
        "group": "ISO P (Alaşımlı Islah Çeliği)",
        "vc_turn": "160 - 210 m/dk",
        "vc_mill": "120 - 160 m/dk",
        "feed": "0.12 - 0.25 mm/dev (Finiş: 0.08-0.12)",
        "coolant": "Yüksek Basınçlı Emülsiyon (%7-9)",
        "note": "Yüksek kesme kuvveti; rijit bağlama ve TiAlN/CVD kaplamalı uç önerilir.",
    }),
    (("6061", "7075", "ALUM", "AL "), {
        "group": "ISO N (Alüminyum Alaşımı)",
        "vc_turn": "350 - 600 m/dk",
        "vc_mill": "300 - 500 m/dk",
        "feed": "0.10 - 0.22 mm/dev",
        "coolant": "Bol Emülsiyon veya MQL (Talaş Yapışmasını Önle)",
        "note": "Keskin pozitif geometrili DLC/kaplamasız parlatılmış karbür uç kullanın.",
    }),
    (("304", "316", "STAINLESS", "PASLANMAZ"), {
        "group": "ISO M (Östenitik Paslanmaz Çelik)",
        "vc_turn": "110 - 150 m/dk",
        "vc_mill": "80 - 120 m/dk",
        "feed": "0.10 - 0.18 mm/dev",
        "coolant": "Yoğun İçten Soğutma (Isıl Sertleşmeyi Önle)",
        "note": "Kesme duraksaması yapmayın; iş parçası sertleşmesine (work-hardening) karşı keskin kenar koruyun.",
    }),
]


def build_cnc_manufacturing_plan(balloons: list[BalloonItem], metadata: dict[str, str]) -> dict[str, Any]:
    """Generate a senior CNC Manufacturing Process Plan (OP10..OP50, cutting params, DFM risks)."""
    mat_upper = (metadata.get("material") or "").upper()
    cutting = {
        "group": "ISO P (Genel İmalat Çeliği / Standart)",
        "vc_turn": "180 - 240 m/dk",
        "vc_mill": "130 - 180 m/dk",
        "feed": "0.12 - 0.25 mm/dev",
        "coolant": "Emülsiyon (%6-8)",
        "note": "Malzeme sertifikasına göre kesme hızını doğrulayın.",
    }
    for keys, spec in MATERIAL_CUTTING_DB:
        if any(k in mat_upper for k in keys):
            cutting = spec
            break

    # Group balloons by operation prefix (OP10, OP20, OP30, OP40)
    op_groups: dict[str, list[int]] = {"OP10": [], "OP20": [], "OP30": [], "OP40": []}
    for b in balloons:
        if "OP40" in b.operation:
            op_groups["OP40"].append(b.balloon_no)
        elif "OP30" in b.operation:
            op_groups["OP30"].append(b.balloon_no)
        elif "OP20" in b.operation:
            op_groups["OP20"].append(b.balloon_no)
        else:
            op_groups["OP10"].append(b.balloon_no)

    operations = [
        {
            "op": "OP10",
            "name": "CNC Torna — Kaba & Finiş + Datum A Oluşturma",
            "machine": "CNC Torna (C-Eksenli)",
            "fixture": "3 Ayaklı Hidrolik Ayna (Sert Çene → Yumuşak Çene)",
            "balloons": op_groups["OP10"],
            "notes": "Alın temizleme (Datum A), dış çap ve merkez delik kaba+finiş; taşlama payı (0.15 mm) bırak.",
        },
        {
            "op": "OP20",
            "name": "CNC İşleme Merkezi — Kontur, Pah & Hassas Özellikler",
            "machine": "3/5 Eksen CNC Dik İşleme Merkezi",
            "fixture": "Datum A Oturmalı Hassas Mengene / Fikstür",
            "balloons": op_groups["OP20"],
            "notes": "Kama kanalı, radyüs, açısal indeksleme ve pah operasyonları.",
        },
        {
            "op": "OP30",
            "name": "Delik Delme, Raybalama & Kılavuz Çekme",
            "machine": "CNC Dik İşleme Merkezi",
            "fixture": "Merkezleme Pimli Bağlama Aparatı",
            "balloons": op_groups["OP30"],
            "notes": "PCD delik çemberi konum kontrolü, ön delik + HSS-E makine kılavuzu + çapak alma.",
        },
    ]
    if op_groups["OP40"]:
        operations.append({
            "op": "OP40",
            "name": "Hassas Taşlama (Ra ≤ 0.8 / GD&T)",
            "machine": "Üniversal Silindirik / Yüzey Taşlama Tezgâhı",
            "fixture": "Hassas Mandrel / Manyetik Tabla",
            "balloons": op_groups["OP40"],
            "notes": "Ra ≤ 0.8 yüzeyler ve kritik GD&T toleransları için tek bağlamada finiş taşlama.",
        })
    operations.append({
        "op": "OP50",
        "name": "Final Kalite Kontrol (FAI / AS9102) & Paketleme",
        "machine": "CMM + Profilometre + Kalibrasyonlu Mastarlar",
        "fixture": "20°C ±1°C İklimlendirilmiş Ölçüm Odası",
        "balloons": [b.balloon_no for b in balloons if b.criticality == "Kritik"],
        "notes": "İlk parça onayı (FAI), kritik ölçülerde %100 CMM raporu, koruyucu yağlama ve etiketleme.",
    })

    # DFM & Quality Risk Warnings
    risks: list[str] = []
    fit_balloons = [b for b in balloons if b.fit_class]
    if fit_balloons:
        tags = ", ".join(f"#{b.balloon_no} ({b.raw_text})" for b in fit_balloons)
        risks.append(f"Hassas ISO Geçme Riski [{tags}]: İşleme sırasında ısıl genleşme etkisini azaltmak için finiş öncesi parçayı 20°C'de dengeleyin; mikrometrik bara veya rayba kullanın.")
    ra_tight = [b for b in balloons if b.category == "Yüzey Pürüzlülüğü" and b.nominal is not None and b.nominal <= 0.8]
    if ra_tight:
        tags = ", ".join(f"#{b.balloon_no} ({b.raw_text})" for b in ra_tight)
        risks.append(f"Yüksek Yüzey Kalitesi [{tags}]: Standart tornalama ile Ra ≤ 0.8 tutturmak risklidir; OP40 taşlama veya wiper uç planlayın.")
    gdt_tight = [b for b in balloons if b.category == "GD&T"]
    if gdt_tight:
        tags = ", ".join(f"#{b.balloon_no} ({b.raw_text})" for b in gdt_tight)
        risks.append(f"Geometrik Tolerans (GD&T) [{tags}]: Datum A referans yüzeyi ile ilgili çap/yüzeyleri mümkünse tek bağlamada (aynı ayna sıkımında) işleyin; bağlama salgı hatası ≤ 0.005 mm olmalı.")
    threads = [b for b in balloons if b.category == "Diş / Vida"]
    if threads:
        tags = ", ".join(f"#{b.balloon_no} ({b.raw_text})" for b in threads)
        risks.append(f"Diş Kalitesi [{tags}]: Kılavuz öncesi havşa (pah) açın ve her partide Go/No-Go vida mastarı ile %100 kontrol uygulayın.")
    if not risks:
        risks.append("Standart CNC tolerans bandı; ISO 2768-mK genel toleransları geçerlidir.")

    return {
        "cutting_parameters": cutting,
        "operations": operations,
        "dfm_risks": risks,
        "cost_estimate": estimate_cnc_cost_and_time(balloons, metadata),
        "gcode_template": generate_fanuc_gcode_template(balloons, metadata),
        "summary": {
            "total": len(balloons),
            "critical": sum(1 for b in balloons if b.criticality == "Kritik"),
            "major": sum(1 for b in balloons if b.criticality == "Majör"),
            "minor": sum(1 for b in balloons if b.criticality == "Minör"),
        },
    }


def estimate_cnc_cost_and_time(balloons: list[BalloonItem], metadata: dict[str, str]) -> dict[str, Any]:
    """Calculate raw stock dimensions, weight (kg), CNC cycle time (min), and unit price quotes (1/10/100 pcs)."""
    mat_upper = (metadata.get("material") or "").upper()
    # Density (g/cm3), raw material price (TL/kg), machine hourly rate (TL/hr)
    if any(k in mat_upper for k in ("6061", "7075", "ALUM", "AL ")):
        density, kg_price, hourly_rate = 2.70, 240.0, 1600.0
    elif any(k in mat_upper for k in ("304", "316", "STAINLESS", "PASLANMAZ")):
        density, kg_price, hourly_rate = 7.93, 210.0, 1950.0
    else:
        density, kg_price, hourly_rate = 7.85, 95.0, 1750.0

    diameters = [b.nominal for b in balloons if b.category == "Çap (Ø)" and b.nominal is not None and b.quantity == 1]
    linears = [b.nominal for b in balloons if b.category == "Lineer Ölçü" and b.nominal is not None]

    max_d = max(diameters) if diameters else (max(linears) if linears else 80.0)
    max_l = max(linears) if linears else 35.0
    stock_d = round(max_d + 5.0, 1)
    stock_l = round(max_l + 4.0, 1)

    # Cylinder volume in cm3
    vol_cm3 = math.pi * ((stock_d / 20.0) ** 2) * (stock_l / 10.0)
    raw_weight_kg = round(max(0.08, (vol_cm3 * density) / 1000.0), 3)
    net_weight_kg = round(raw_weight_kg * 0.58, 3)

    hole_count = sum(b.quantity for b in balloons if b.category in ("Diş / Vida", "Çap (Ø)") and b.quantity > 1)
    crit_count = sum(1 for b in balloons if b.criticality == "Kritik")
    has_grind = any(b.category == "Yüzey Pürüzlülüğü" and b.nominal is not None and b.nominal <= 0.8 for b in balloons)

    setup_min = 35.0
    turn_mill_min = round(4.5 + (stock_d * stock_l) / 950.0 + len(balloons) * 0.45, 1)
    drill_tap_min = round(hole_count * 0.65, 1)
    grind_min = 6.5 if has_grind else 0.0
    qc_min = round(2.0 + crit_count * 0.9, 1)
    cycle_min = round(turn_mill_min + drill_tap_min + grind_min + qc_min, 1)

    mat_cost = round(raw_weight_kg * kg_price, 2)
    machining_cost = round((cycle_min / 60.0) * hourly_rate, 2)
    tooling_cost = round(machining_cost * 0.12, 2)
    setup_cost_total = round((setup_min / 60.0) * hourly_rate, 2)

    base_unit = mat_cost + machining_cost + tooling_cost
    quote_1 = round((base_unit + setup_cost_total) * 1.25, 2)
    quote_10 = round((base_unit + setup_cost_total / 10.0) * 1.20, 2)
    quote_100 = round((base_unit + setup_cost_total / 100.0) * 1.15, 2)

    return {
        "stock_dimensions": f"Ø{stock_d:g} x {stock_l:g} mm",
        "raw_weight_kg": raw_weight_kg,
        "net_weight_kg": net_weight_kg,
        "setup_time_min": setup_min,
        "cycle_time_min": cycle_min,
        "breakdown_min": {
            "turn_mill": turn_mill_min,
            "drill_tap": drill_tap_min,
            "grinding": grind_min,
            "quality_cmm": qc_min,
        },
        "material_cost_tl": mat_cost,
        "machining_cost_tl": machining_cost,
        "tooling_cost_tl": tooling_cost,
        "unit_quote_1_tl": quote_1,
        "unit_quote_10_tl": quote_10,
        "unit_quote_100_tl": quote_100,
    }


def generate_fanuc_gcode_template(balloons: list[BalloonItem], metadata: dict[str, str]) -> str:
    """Generate a starter Fanuc ISO G-code template tailored to the part's real dimensions."""
    pn = metadata.get("part_number") or "CNC-PART"
    mat = metadata.get("material") or "STEEL"
    diameters = sorted(
        [b.nominal for b in balloons if b.category == "Çap (Ø)" and b.nominal is not None and b.quantity == 1],
        reverse=True,
    )
    linears = sorted([b.nominal for b in balloons if b.category == "Lineer Ölçü" and b.nominal is not None], reverse=True)
    holes = [b for b in balloons if b.category == "Çap (Ø)" and b.quantity > 1 and b.nominal is not None]
    threads = [b for b in balloons if b.category == "Diş / Vida"]

    od = diameters[0] if diameters else 100.0
    id_bore = diameters[-1] if len(diameters) > 1 else 40.0
    length = linears[0] if linears else 35.0
    pcd = diameters[1] if len(diameters) > 2 else round(od * 0.72, 1)

    lines = [
        "%",
        f"O2026 ({pn} - {mat} - FANuc TASLAK G-KODU)",
        f"(OTOMATIK URETILDI - DIS CAP: {od:g}MM, IC CAP: {id_bore:g}MM, BOY: {length:g}MM)",
        "G21 G40 G80 G99",
        "",
        "(--- OP10: ALIN VE DIS CAP KABA/FINIS TORNALAMA ---)",
        "T0101 (CNMG 120408 KABA TORNA KALEMI)",
        "G54",
        "G50 S2200",
        "G96 S180 M03",
        f"G00 X{od + 4.0:.1f} Z2.0 M08",
        "G01 Z0.0 F0.22",
        "G01 X-1.6 F0.18 (ALIN TEMIZLEME - DATUM A)",
        f"G00 X{od:.1f} Z2.0",
        f"G01 Z-{length:.1f} F0.22 (DIS CAP BOY TORNALAMA)",
        f"G00 X{od + 5.0:.1f} Z5.0",
        "",
        f"(--- IC CAP BARA / H7 GECME: CAP {id_bore:g}MM ---)",
        "T0303 (HASSAS IC CAP BARA KALEMI)",
        "G96 S150 M03",
        f"G00 X{max(10.0, id_bore - 2.0):.1f} Z2.0",
        f"G01 X{id_bore:.3f} Z0.0 F0.10",
        f"G01 Z-{length:.1f} F0.08",
        "G00 Z10.0 M09",
        "G28 U0.0 W0.0 M05",
    ]
    if holes:
        h = holes[0]
        r_pcd = round(pcd / 2.0, 2)
        lines.extend([
            "",
            f"(--- OP30: {h.quantity}x CAP {h.nominal:g}MM DELIK DELME DONGUSU - PCD {pcd:g} ---)",
            "T0505 (KARBUR MATKAP)",
            "G17 G94 G97 S1800 M03",
            f"G00 X{r_pcd:.2f} Y0.0 Z5.0 M08",
            f"G83 Z-{length + 2.0:.1f} R2.0 Q4.0 F160",
            f"X0.0 Y{r_pcd:.2f}",
            f"X-{r_pcd:.2f} Y0.0",
            f"X0.0 Y-{r_pcd:.2f}",
            "G80 Z25.0",
        ])
    if threads:
        th = threads[0]
        lines.extend([
            "",
            f"(--- OP30: KILAVUZ CEKME - {th.raw_text} ---)",
            "T0606 (HSS-E MAKINE KILAVUZU)",
            "G97 S400 M03",
            f"G84 Z-18.0 R3.0 F500 ({th.raw_text})",
            "G80 G00 Z50.0 M09",
        ])
    lines.extend(["M30", "%"])
    return "\n".join(lines)


def lookup_iso2768_m(nominal: float) -> float:
    val = abs(nominal)
    for lo, hi, tol in ISO_2768_M_LINEAR:
        if lo <= val <= hi:
            return tol
    return 0.1 if val < 0.5 else 2.0


def lookup_iso286_fit(nominal: float, fit_code: str) -> tuple[float, float] | None:
    table = ISO_286_FITS.get(fit_code)
    if not table:
        return None
    for upper_d, upper_um, lower_um in table:
        if nominal <= upper_d:
            return round(upper_um / 1000.0, 4), round(lower_um / 1000.0, 4)
    _, upper_um, lower_um = table[-1]
    return round(upper_um / 1000.0, 4), round(lower_um / 1000.0, 4)


def compute_zone(x_pct: float, y_pct: float) -> str:
    """Compute standard engineering drawing grid zone (e.g. A1..D6)."""
    rows = ["A", "B", "C", "D"]
    r_idx = min(3, max(0, int(y_pct / 25.0)))
    c_idx = min(6, max(1, int(x_pct / (100.0 / 6.0)) + 1))
    return f"{rows[r_idx]}{c_idx}"


# --- Regex patterns for CNC dimension classification ---
_RE_QTY = re.compile(r"^(\d+)\s*[xX\u00d7]\s*")
_RE_ROUGHNESS = re.compile(r"\b(Ra|Rz)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_RE_THREAD = re.compile(
    r"\b(M\d+(?:[.,]\d+)?(?:\s*[xX\u00d7]\s*\d+(?:[.,]\d+)?)?(?:-[45678][gGhH])?|"
    r"G\s*\d+/\d+\"?|NPT\s*\d+/\d+)\b",
    re.IGNORECASE,
)
_RE_DIAMETER = re.compile(
    r"(?:Ø|⌀|Φ|DIA\.?)\s*(\d+(?:[.,]\d+)?)"
    r"(?:\s*([A-Za-z]{1,2}\d))?"
    r"(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?"
    r"(?:\s*\+(\d+(?:[.,]\d+)?)\s*/\s*([+-]?\d+(?:[.,]\d+)?))?",
    re.IGNORECASE,
)
_RE_CHAMFER = re.compile(r"\b(?:C\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*[xX\u00d7]\s*45°?)\b", re.IGNORECASE)
_RE_RADIUS = re.compile(r"\bR\s*(\d+(?:[.,]\d+)?)(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?\b")
_RE_ANGLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*°(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?)\s*°?)?")
_RE_LINEAR = re.compile(
    r"^(\d+(?:[.,]\d+)?)"
    r"(?:\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?))?"
    r"(?:\s*\+(\d+(?:[.,]\d+)?)\s*/\s*([+-]?\d+(?:[.,]\d+)?))?"
    r"(?:\s*mm)?$",
    re.IGNORECASE,
)
_RE_GDT_VAL = re.compile(r"(⏥|∥|⊥|◎|⌖|↗|⌭|FLAT|PERP|PARA|CONC|POS|RUNOUT)\s*(?:Ø|⌀)?\s*(\d+(?:[.,]\d+)?)(?:\s+([A-Z]))?", re.IGNORECASE)

_NON_DIMENSION_WORDS = (
    "SCALE", "ÖLÇEK", "OLCEK", "SHEET", "SAYFA", "DATE", "TARİH", "TARIH",
    "REV", "MATERIAL", "MALZEME", "PART NO", "PARÇA NO", "DRAWN", "ÇİZEN",
    "UNIT", "BİRİM", "TOLERANCE", "ISO 2768", "TITLE", "PROJECTION", "WEIGHT",
    "AĞIRLIK", "FLANGE", "SHAFT", "HOUSING", "SECTION", "KESİT", "DETAIL",
    "VIEW", "GÖRÜNÜŞ", "NOTE:", "NOT:", "ALL DIMENSIONS", "TÜM ÖLÇÜLER",
    "UNLESS OTHERWISE", "ALUMINUM", "STEEL", "4140", "6061", "304", "AISI",
    "DIN", "CNC", "MILLIMETER", "MM", "APPROVED", "CHECKED", "COMPANY",
)


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_cnc_dimension(
    raw_text: str,
    x_pct: float = 50.0,
    y_pct: float = 50.0,
    w_pct: float = 4.0,
    h_pct: float = 2.0,
) -> BalloonItem | None:
    """Parse a raw text string from a CNC technical drawing into a structured BalloonItem.

    Returns None if the text is not a measurable CNC characteristic.
    """
    text = " ".join(raw_text.strip().split())
    if not text or len(text) > 70:
        return None

    upper = text.upper()
    if any(w in upper for w in _NON_DIMENSION_WORDS):
        return None
    # Skip dates like 2026-11-23 or 23.11.2026
    if re.search(r"\b\d{2,4}[-./]\d{2}[-./]\d{2,4}\b", text):
        return None
    # Skip scales like 1:1 or 1:2
    if re.fullmatch(r"\d+\s*:\s*\d+", text):
        return None

    qty = 1
    work = text
    m_qty = _RE_QTY.match(work)
    if m_qty and "45" not in work:
        qty = int(m_qty.group(1))
        work = work[m_qty.end():].strip()

    zone = compute_zone(x_pct, y_pct)

    # 1. Surface Roughness (Ra / Rz)
    m_ra = _RE_ROUGHNESS.search(work)
    if m_ra:
        val = _to_float(m_ra.group(2))
        crit = "Kritik" if (val is not None and val <= 0.8) else "Majör"
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Yüzey Pürüzlülüğü",
            nominal=val, unit="µm", max_limit=val, min_limit=0.0,
            quantity=qty, gage="Yüzey Pürüzlülük Cihazı (Profilometre)",
            criticality=crit, notes=f"Maksimum {m_ra.group(1)} {val} µm",
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 2. GD&T Tolerance
    m_gdt = _RE_GDT_VAL.search(work)
    if m_gdt:
        sym = m_gdt.group(1).upper()
        val = _to_float(m_gdt.group(2))
        datum = m_gdt.group(3) or ""
        gdt_name = GDT_KEYWORDS.get(m_gdt.group(1), GDT_KEYWORDS.get(sym, "GD&T"))
        return BalloonItem(
            balloon_no=0, raw_text=text, category="GD&T",
            nominal=val, unit="mm", max_limit=val, min_limit=0.0,
            quantity=qty, gage="CMM / Komparatör Saati",
            criticality="Kritik",
            notes=f"{gdt_name}" + (f" · Datum {datum}" if datum else ""),
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 3. Thread (M8x1.25-6H, G1/4, etc.)
    m_th = _RE_THREAD.search(work)
    if m_th:
        thread_spec = m_th.group(1)
        depth_m = re.search(r"(?:DEPTH|DERİNLİK|↧)\s*(\d+(?:[.,]\d+)?)", work, re.IGNORECASE)
        note = f"Diş: {thread_spec}"
        if depth_m:
            note += f", Derinlik {depth_m.group(1)} mm"
        if "THRU" in upper or "BOYUNCA" in upper:
            note += ", Boydan Boya (THRU)"
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Diş / Vida",
            nominal=None, unit="mm", quantity=qty,
            gage="Vida Geçer/Geçmez Mastarı (Go/No-Go)",
            criticality="Kritik", notes=note,
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 4. Diameter (Ø42 H7, Ø80 ±0.05, 4x Ø9 THRU)
    m_dia = _RE_DIAMETER.search(work)
    if m_dia:
        nom = _to_float(m_dia.group(1))
        fit = m_dia.group(2) or ""
        sym_tol = _to_float(m_dia.group(3))
        pos_tol = _to_float(m_dia.group(4))
        neg_tol = _to_float(m_dia.group(5))

        tol_p: float | None = None
        tol_m: float | None = None
        note_parts = []
        if fit and nom is not None:
            fit_res = lookup_iso286_fit(nom, fit)
            if fit_res:
                tol_p, tol_m = fit_res
                note_parts.append(f"ISO 286 Geçme: {fit}")
        if sym_tol is not None:
            tol_p, tol_m = sym_tol, -sym_tol
        elif pos_tol is not None and neg_tol is not None:
            tol_p = pos_tol
            tol_m = neg_tol if neg_tol <= 0 else -neg_tol
        elif tol_p is None and nom is not None:
            iso_t = lookup_iso2768_m(nom)
            tol_p, tol_m = iso_t, -iso_t
            note_parts.append("ISO 2768-m genel tolerans")

        if "THRU" in upper or "BOYUNCA" in upper:
            note_parts.append("Boydan boya delik")

        min_l = round(nom + tol_m, 4) if (nom is not None and tol_m is not None) else None
        max_l = round(nom + tol_p, 4) if (nom is not None and tol_p is not None) else None
        tol_span = abs((tol_p or 0) - (tol_m or 0))
        if fit or tol_span <= 0.05:
            gage = "İç/Dış Çap Mikrometresi veya CMM"
            crit = "Kritik"
        elif tol_span <= 0.15:
            gage = "Dijital Mikrometre / Hassas Kumpas"
            crit = "Majör"
        else:
            gage = "Dijital Kumpas"
            crit = "Majör"

        return BalloonItem(
            balloon_no=0, raw_text=text, category="Çap (Ø)",
            nominal=nom, unit="mm", tol_plus=tol_p, tol_minus=tol_m,
            min_limit=min_l, max_limit=max_l, fit_class=fit, quantity=qty,
            gage=gage, criticality=crit, notes=" · ".join(note_parts),
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 5. Chamfer (2x45°, C2)
    m_ch = _RE_CHAMFER.search(text)
    if m_ch:
        val = _to_float(m_ch.group(1) or m_ch.group(2))
        tol = lookup_iso2768_m(val) if val is not None else 0.2
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Pah (Chamfer)",
            nominal=val, unit="mm", tol_plus=tol, tol_minus=-tol,
            min_limit=round(val - tol, 4) if val is not None else None,
            max_limit=round(val + tol, 4) if val is not None else None,
            quantity=1, gage="Pah Mastarı / Dijital Kumpas",
            criticality="Minör", notes="45° Pah",
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 6. Radius (R5, R2.5 ±0.1)
    m_rad = _RE_RADIUS.search(work)
    if m_rad:
        nom = _to_float(m_rad.group(1))
        sym_tol = _to_float(m_rad.group(2))
        tol = sym_tol if sym_tol is not None else (lookup_iso2768_m(nom) if nom is not None else 0.2)
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Radyüs (R)",
            nominal=nom, unit="mm", tol_plus=tol, tol_minus=-tol,
            min_limit=round(nom - tol, 4) if nom is not None else None,
            max_limit=round(nom + tol, 4) if nom is not None else None,
            quantity=qty, gage="Radyüs Mastarı / Optik Profil Projektör",
            criticality="Minör" if tol >= 0.2 else "Majör",
            notes="ISO 2768-m" if sym_tol is None else "Açık toleranslı radyüs",
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 7. Angle (45° ±0.5°)
    m_ang = _RE_ANGLE.search(work)
    if m_ang:
        nom = _to_float(m_ang.group(1))
        tol = _to_float(m_ang.group(2)) or 0.5
        return BalloonItem(
            balloon_no=0, raw_text=text, category="Açı",
            nominal=nom, unit="°", tol_plus=tol, tol_minus=-tol,
            min_limit=round(nom - tol, 4) if nom is not None else None,
            max_limit=round(nom + tol, 4) if nom is not None else None,
            quantity=qty, gage="Universal Açıölçer / CMM",
            criticality="Majör", notes="Açısal ölçü",
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    # 8. Linear dimension (120.0 ±0.1, 24.0 +0.05/-0.02, 18.5)
    m_lin = _RE_LINEAR.match(work)
    if m_lin:
        nom = _to_float(m_lin.group(1))
        if nom is None or nom <= 0 or nom > 5000:
            return None
        sym_tol = _to_float(m_lin.group(2))
        pos_tol = _to_float(m_lin.group(3))
        neg_tol = _to_float(m_lin.group(4))
        note = ""
        if sym_tol is not None:
            tol_p, tol_m = sym_tol, -sym_tol
        elif pos_tol is not None and neg_tol is not None:
            tol_p = pos_tol
            tol_m = neg_tol if neg_tol <= 0 else -neg_tol
        else:
            iso_t = lookup_iso2768_m(nom)
            tol_p, tol_m = iso_t, -iso_t
            note = "ISO 2768-m genel tolerans"
        tol_span = abs(tol_p - tol_m)
        if tol_span <= 0.06:
            gage, crit = "Dijital Mikrometre / CMM", "Kritik"
        elif tol_span <= 0.2:
            gage, crit = "Dijital Kumpas (0.01 mm)", "Majör"
        else:
            gage, crit = "Dijital Kumpas", "Minör"

        return BalloonItem(
            balloon_no=0, raw_text=text, category="Lineer Ölçü",
            nominal=nom, unit="mm", tol_plus=tol_p, tol_minus=tol_m,
            min_limit=round(nom + tol_m, 4), max_limit=round(nom + tol_p, 4),
            quantity=qty, gage=gage, criticality=crit, notes=note,
            x_pct=x_pct, y_pct=y_pct, w_pct=w_pct, h_pct=h_pct, zone=zone,
        )

    return None


def _extract_metadata_from_texts(texts: list[str]) -> dict[str, str]:
    joined = "\n".join(texts)
    meta = {
        "part_number": "",
        "part_name": "",
        "material": "",
        "revision": "A",
        "standard": "ISO 2768-mK",
    }
    m_pn = re.search(r"(?:PART\s*NO\.?|PARÇA\s*NO\.?|DWG\s*NO\.?)[:\s]+([A-Z0-9_-]{3,30})", joined, re.IGNORECASE)
    if m_pn:
        meta["part_number"] = m_pn.group(1).strip()
    m_mat = re.search(r"(?:MATERIAL|MALZEME)[:\s]+([^\n|]{2,40})", joined, re.IGNORECASE)
    if m_mat:
        meta["material"] = m_mat.group(1).strip()
    m_rev = re.search(r"(?:REV\.?|REVİZYON)[:\s]+([A-Z0-9.]{1,8})", joined, re.IGNORECASE)
    if m_rev:
        meta["revision"] = m_rev.group(1).strip()
    m_std = re.search(r"(ISO\s*2768-[a-zA-Z]{1,2}|ASME\s*Y14\.5)", joined, re.IGNORECASE)
    if m_std:
        meta["standard"] = m_std.group(1).strip()
    m_name = re.search(r"(?:PART\s*NAME|PARÇA\s*ADI|TITLE)[:\s]+([^\n|]{3,50})", joined, re.IGNORECASE)
    if m_name:
        meta["part_name"] = m_name.group(1).strip()
    return meta


async def _pick_vision_model(preferred: str | None = None) -> str:
    """Select the best installed Ollama vision model."""
    candidates = [
        preferred,
        config.CNC_VISION_MODEL,
        "cnc-ballooner",
        "qwen3.5:9b",
        "qwen3.5:4b",
        "gemma4:e4b",
        config.MASTER_MODEL,
    ]
    candidates = [c for c in candidates if c]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            installed = {m.get("name", "") for m in resp.json().get("models", [])}
            installed_base = {name.split(":")[0] for name in installed}
            for cand in candidates:
                if cand in installed or cand in installed_base:
                    return cand
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
    return config.MASTER_MODEL


CNC_VISION_SYSTEM_PROMPT = (
    "Sen uzman bir CNC imalat ve kalite kontrol (AS9102 / ISO 2768 / ASME Y14.5 GD&T) mühendisisin. "
    "Sana verilen teknik çizimdeki TÜM ölçülebilir karakteristikleri (çaplar Ø, lineer ölçüler, "
    "toleranslar ± / +-, ISO geçmeler H7/g6, dişler M8x1.25, radyüsler R, pahlar 2x45°/C2, "
    "yüzey pürüzlülükleri Ra, GD&T sembolleri ve açılar) eksiksiz tespit et.\n"
    "SADECE geçerli bir JSON objesi döndür, başka hiçbir açıklama yazma:\n"
    "{\n"
    '  "metadata": {"part_number": "", "part_name": "", "material": "", "revision": "", "standard": "ISO 2768-mK"},\n'
    '  "balloons": [\n'
    '    {"raw_text": "Ø42 H7", "x_pct": 32.5, "y_pct": 44.0, "notes": "Rulman yatağı çapı"}\n'
    "  ]\n"
    "}\n"
    "Kurallar:\n"
    "- x_pct ve y_pct değerleri 0 ile 100 arasında (sol üst 0,0; sağ alt 100,100) ölçünün görsel üzerindeki merkez koordinatı olmalıdır.\n"
    "- Antet (title block) içindeki tarih, ölçek, sayfa numarası gibi ölçü olmayan yazıları balloons listesine EKLEME.\n"
    "- Tüm ölçüleri eksiksiz listele."
)


async def _analyze_image_with_vlm(
    img: Image.Image,
    model_override: str | None = None,
    extra_text_context: str = "",
) -> tuple[list[BalloonItem], dict[str, str], str]:
    """Use local Ollama vision model to detect CNC dimensions and approximate coordinates."""
    model = await _pick_vision_model(model_override)

    # Resize large images for VLM while keeping text crisp
    vlm_img = img.convert("RGB")
    max_side = 1400
    if max(vlm_img.size) > max_side:
        ratio = max_side / max(vlm_img.size)
        vlm_img = vlm_img.resize((int(vlm_img.width * ratio), int(vlm_img.height * ratio)), Image.Resampling.LANCZOS)
    vlm_img = ImageEnhance.Contrast(vlm_img).enhance(1.15)
    vlm_img = ImageEnhance.Sharpness(vlm_img).enhance(1.2)

    buf = io.BytesIO()
    vlm_img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    user_prompt = "Bu teknik çizimdeki tüm CNC ölçülerini, toleransları, dişleri, yüzey pürüzlülüklerini ve GD&T sembollerini eksiksiz çıkar ve JSON olarak ver."
    if extra_text_context:
        user_prompt += f"\n\nEk doküman metni:\n{extra_text_context[:3000]}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": CNC_VISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt, "images": [img_b64]},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }

    items: list[BalloonItem] = []
    meta: dict[str, str] = {"part_number": "", "part_name": "", "material": "", "revision": "A", "standard": "ISO 2768-mK"}

    try:
        import gateway

        gw_res = await gateway.default_client.chat(
            payload["messages"],
            model=model,
            profile="factual",
            num_predict=4096,
            timeout_s=180.0,
            feature="cnc_ballooning",
            max_retries=0,
        )
        content = gw_res.content
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError, AttributeError):
        return items, meta, model

    # Parse JSON block from model output
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        return items, meta, model

    try:
        parsed = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return items, meta, model

    if isinstance(parsed.get("metadata"), dict):
        for k in meta:
            if parsed["metadata"].get(k):
                meta[k] = str(parsed["metadata"][k])

    for raw_b in parsed.get("balloons", []):
        if not isinstance(raw_b, dict):
            continue
        raw_text = str(raw_b.get("raw_text", "")).strip()
        if not raw_text:
            continue
        x_pct = float(raw_b.get("x_pct", 50.0))
        y_pct = float(raw_b.get("y_pct", 50.0))
        x_pct = max(3.0, min(97.0, x_pct))
        y_pct = max(3.0, min(95.0, y_pct))
        item = parse_cnc_dimension(raw_text, x_pct=x_pct, y_pct=y_pct)
        if item is None:
            item = BalloonItem(
                balloon_no=0,
                raw_text=raw_text,
                category="Genel Özellik / Not",
                notes=str(raw_b.get("notes", "")),
                x_pct=x_pct,
                y_pct=y_pct,
                zone=compute_zone(x_pct, y_pct),
            )
        elif raw_b.get("notes") and not item.notes:
            item.notes = str(raw_b["notes"])
        items.append(item)

    return items, meta, model


def _extract_dxf_balloons(raw_bytes: bytes) -> tuple[Image.Image, list[BalloonItem], dict[str, str]]:
    """Parse ASCII DXF CAD entities (LINE, CIRCLE, TEXT, MTEXT, DIMENSION), render CAD canvas, and extract balloons."""
    text = raw_bytes.decode("utf-8", errors="ignore")
    raw_lines = [line.strip() for line in text.splitlines()]
    pairs: list[tuple[int, str]] = []
    for i in range(0, len(raw_lines) - 1, 2):
        try:
            pairs.append((int(raw_lines[i]), raw_lines[i + 1]))
        except ValueError:
            continue

    lines_geom: list[tuple[float, float, float, float]] = []
    circles_geom: list[tuple[float, float, float]] = []
    texts_geom: list[tuple[float, float, str]] = []

    idx = 0
    n = len(pairs)
    while idx < n:
        code, val = pairs[idx]
        if code == 0 and val in ("LINE", "CIRCLE", "TEXT", "MTEXT", "DIMENSION"):
            etype = val
            idx += 1
            props: dict[int, str] = {}
            while idx < n and pairs[idx][0] != 0:
                c, v = pairs[idx]
                props[c] = v
                idx += 1
            try:
                if etype == "LINE":
                    lines_geom.append((
                        float(props.get(10, 0)), float(props.get(20, 0)),
                        float(props.get(11, 0)), float(props.get(21, 0)),
                    ))
                elif etype == "CIRCLE":
                    circles_geom.append((
                        float(props.get(10, 0)), float(props.get(20, 0)), float(props.get(40, 10)),
                    ))
                elif etype in ("TEXT", "MTEXT", "DIMENSION"):
                    raw_t = props.get(1, "").strip()
                    # Clean DXF MTEXT formatting codes like \A1; or %%c (diameter Ø)
                    clean_t = re.sub(r"\\[A-Za-z0-9]+;", "", raw_t).replace("%%c", "Ø").replace("%%C", "Ø").replace("%%p", "±").replace("%%d", "°").strip()
                    if clean_t:
                        tx = float(props.get(10, props.get(11, 0)))
                        ty = float(props.get(20, props.get(21, 0)))
                        texts_geom.append((tx, ty, clean_t))
            except ValueError:
                continue
        else:
            idx += 1

    # Compute bounding box of CAD geometry
    xs: list[float] = [0.0, 200.0]
    ys: list[float] = [0.0, 140.0]
    for x1, y1, x2, y2 in lines_geom:
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    for cx, cy, r in circles_geom:
        xs.extend([cx - r, cx + r])
        ys.extend([cy - r, cy + r])
    for tx, ty, _ in texts_geom:
        xs.append(tx)
        ys.append(ty)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(10.0, max_x - min_x)
    span_y = max(10.0, max_y - min_y)
    pad_x, pad_y = span_x * 0.12, span_y * 0.14
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    span_x = max_x - min_x
    span_y = max_y - min_y

    W, H = 1650, 1160
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, W - 16, H - 16], outline=(20, 30, 50), width=3)
    font = _load_font(17, bold=False)

    def to_px(x: float, y: float) -> tuple[float, float]:
        px = 40 + ((x - min_x) / span_x) * (W - 80)
        py = H - 40 - ((y - min_y) / span_y) * (H - 80)
        return px, py

    for x1, y1, x2, y2 in lines_geom:
        p1, p2 = to_px(x1, y1), to_px(x2, y2)
        draw.line([p1, p2], fill=(20, 30, 50), width=2)

    for cx, cy, r in circles_geom:
        px, py = to_px(cx, cy)
        rx = (r / span_x) * (W - 80)
        ry = (r / span_y) * (H - 80)
        draw.ellipse([px - rx, py - ry, px + rx, py + ry], outline=(20, 30, 50), width=2)

    balloons: list[BalloonItem] = []
    all_texts: list[str] = []
    for tx, ty, txt in texts_geom:
        all_texts.append(txt)
        px, py = to_px(tx, ty)
        draw.text((px, py - 8), txt, fill=(25, 70, 140), font=font)
        x_pct = max(3.0, min(97.0, (px / W) * 100.0))
        y_pct = max(3.0, min(95.0, (py / H) * 100.0))
        item = parse_cnc_dimension(txt, x_pct=x_pct, y_pct=y_pct)
        if item is not None:
            balloons.append(item)

    meta = _extract_metadata_from_texts(all_texts)
    return img, balloons, meta


def _extract_pdf_vector_balloons(pdf_bytes: bytes) -> tuple[Image.Image, list[BalloonItem], dict[str, str]]:
    """Render first page of PDF to high-DPI PNG and extract vector dimension callouts with exact positions."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=220)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    pw, ph = page.rect.width, page.rect.height
    text_dict: Any = page.get_text("dict")
    blocks = text_dict.get("blocks", []) if isinstance(text_dict, dict) else []

    all_texts: list[str] = []
    balloons: list[BalloonItem] = []

    # Collect lines (merging spans on the same baseline so "Ø42" + "H7" stays together)
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            line_text = " ".join(s.get("text", "").strip() for s in spans if s.get("text", "").strip())
            if not line_text:
                continue
            all_texts.append(line_text)

            x0, y0, x1, y1 = line.get("bbox", (0, 0, 0, 0))
            cx_pct = ((x0 + x1) / 2.0) / pw * 100.0
            cy_pct = ((y0 + y1) / 2.0) / ph * 100.0
            w_pct = max(2.0, (x1 - x0) / pw * 100.0)
            h_pct = max(1.5, (y1 - y0) / ph * 100.0)

            # Skip title block area (typically bottom-right corner: x > 62% and y > 78%)
            if cx_pct > 62.0 and cy_pct > 78.0:
                continue

            item = parse_cnc_dimension(line_text, x_pct=cx_pct, y_pct=cy_pct, w_pct=w_pct, h_pct=h_pct)
            if item is not None:
                balloons.append(item)

    meta = _extract_metadata_from_texts(all_texts)
    doc.close()
    return img, balloons, meta


def _render_spec_sheet_image(title: str, lines: list[str]) -> Image.Image:
    """Fallback visual sheet when DOCX/XLSX has dimension tables but no embedded drawing image."""
    width = 1600
    height = max(900, 180 + len(lines) * 44)
    img = Image.new("RGB", (width, height), (252, 253, 255))
    draw = ImageDraw.Draw(img)
    font_title = _load_font(26, bold=True)
    font_body = _load_font(18, bold=False)

    draw.rectangle([20, 20, width - 20, height - 20], outline=(30, 41, 59), width=3)
    draw.rectangle([20, 20, width - 20, 88], fill=(30, 41, 59))
    draw.text((44, 40), f"CNC TEKNİK ÖZELLİK VE ÖLÇÜ LİSTESİ — {title}", fill=(255, 255, 255), font=font_title)

    y = 120
    for line in lines:
        draw.line([(40, y + 32), (width - 40, y + 32)], fill=(226, 232, 240), width=1)
        draw.text((110, y), line[:115], fill=(15, 23, 42), font=font_body)
        y += 44
    return img


def _extract_largest_zip_image(raw: bytes, prefix: str) -> Image.Image | None:
    best_img: Image.Image | None = None
    best_area = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if not info.filename.startswith(prefix):
                    continue
                if not info.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff")):
                    continue
                try:
                    im = Image.open(io.BytesIO(zf.read(info.filename))).convert("RGB")
                    area = im.width * im.height
                    if area > best_area:
                        best_area = area
                        best_img = im
                except (OSError, ValueError, TypeError, KeyError, RuntimeError, zipfile.BadZipFile, SyntaxError) as _exc:
                    import logging

                    logging.getLogger(__name__).debug("Recoverable error skipped in loop: %s", _exc)
                    continue
    except zipfile.BadZipFile:
        return None
    return best_img


async def process_drawing(
    filename: str,
    raw_bytes: bytes,
    model_override: str | None = None,
    use_vlm: bool = True,
) -> tuple[Image.Image, list[BalloonItem], dict[str, str], str]:
    """Ingest PDF / Image / DOCX / XLSX and return (base_image, balloons, metadata, engine_used)."""
    lower = filename.lower()
    engine_used = "vector+rules"

    if lower.endswith(".pdf"):
        img, balloons, meta = _extract_pdf_vector_balloons(raw_bytes)
        if not balloons and use_vlm:
            vlm_balloons, vlm_meta, model = await _analyze_image_with_vlm(img, model_override=model_override)
            balloons = vlm_balloons
            for k, v in vlm_meta.items():
                if v and not meta.get(k):
                    meta[k] = v
            engine_used = f"vlm:{model}"
        else:
            engine_used = "pymupdf-vector+iso2768"

    elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")):
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        if use_vlm:
            balloons, meta, model = await _analyze_image_with_vlm(img, model_override=model_override)
            engine_used = f"vlm:{model}"
        else:
            balloons, meta = [], {"part_number": "", "part_name": "", "material": "", "revision": "A", "standard": "ISO 2768-mK"}
            engine_used = "manual"

    elif lower.endswith(".docx"):
        doc = Document(io.BytesIO(raw_bytes))
        lines: list[str] = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    lines.extend(cells)
        meta = _extract_metadata_from_texts(lines)
        embedded_img = _extract_largest_zip_image(raw_bytes, "word/media/")

        if embedded_img is not None:
            img = embedded_img
            if use_vlm:
                balloons, vlm_meta, model = await _analyze_image_with_vlm(
                    img, model_override=model_override, extra_text_context="\n".join(lines)
                )
                for k, v in vlm_meta.items():
                    if v and not meta.get(k):
                        meta[k] = v
                engine_used = f"docx-img+vlm:{model}"
            else:
                balloons = []
                engine_used = "docx-img"
        else:
            balloons = []
            matched_lines = []
            for text_line in lines:
                item = parse_cnc_dimension(text_line)
                if item:
                    matched_lines.append((text_line, item))
            img = _render_spec_sheet_image(filename, [t for t, _ in matched_lines] or lines[:20])
            for idx, (_, item) in enumerate(matched_lines):
                item.x_pct = 8.0
                item.y_pct = min(96.0, (128 + idx * 44) / img.height * 100.0)
                item.zone = compute_zone(item.x_pct, item.y_pct)
                balloons.append(item)
            engine_used = "docx-table+iso2768"

    elif lower.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(raw_bytes), data_only=True)
        cell_texts: list[str] = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                for val in row:
                    if val is not None and str(val).strip():
                        cell_texts.append(str(val).strip())
        meta = _extract_metadata_from_texts(cell_texts)
        embedded_img = _extract_largest_zip_image(raw_bytes, "xl/media/")

        if embedded_img is not None:
            img = embedded_img
            if use_vlm:
                balloons, vlm_meta, model = await _analyze_image_with_vlm(
                    img, model_override=model_override, extra_text_context="\n".join(cell_texts[:150])
                )
                for k, v in vlm_meta.items():
                    if v and not meta.get(k):
                        meta[k] = v
                engine_used = f"xlsx-img+vlm:{model}"
            else:
                balloons = []
                engine_used = "xlsx-img"
        else:
            balloons = []
            matched_lines = []
            for text_val in cell_texts:
                item = parse_cnc_dimension(text_val)
                if item:
                    matched_lines.append((text_val, item))
            img = _render_spec_sheet_image(filename, [t for t, _ in matched_lines] or cell_texts[:20])
            for idx, (_, item) in enumerate(matched_lines):
                item.x_pct = 8.0
                item.y_pct = min(96.0, (128 + idx * 44) / img.height * 100.0)
                item.zone = compute_zone(item.x_pct, item.y_pct)
                balloons.append(item)
            engine_used = "xlsx-table+iso2768"
    elif lower.endswith(".dxf"):
        img, balloons, meta = _extract_dxf_balloons(raw_bytes)
        engine_used = "dxf-cad-vector+iso2768"
    else:
        raise ValueError(f"Desteklenmeyen teknik çizim formatı: {filename}")

    # Sort balloons cleanly top-to-bottom, left-to-right (reading order) and assign sequential numbers
    balloons.sort(key=lambda b: (round(b.y_pct / 8.0), b.x_pct))
    for i, b in enumerate(balloons, start=1):
        b.balloon_no = i
        if not b.zone:
            b.zone = compute_zone(b.x_pct, b.y_pct)
        enrich_cnc_engineering_fields(b)

    if not meta.get("part_name"):
        meta["part_name"] = Path(filename).stem

    return img, balloons, meta, engine_used


# --- Visual Ballooning Renderer ---

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["arialbd.ttf", "DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold
        else ["arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_ballooned_image(
    base_img: Image.Image,
    balloons: list[BalloonItem],
    metadata: dict[str, str],
) -> Image.Image:
    """Draw non-overlapping numbered red CNC balloons + leader lines onto the technical drawing."""
    w, h = base_img.size
    footer_h = max(48, int(h * 0.045))
    canvas = Image.new("RGB", (w, h + footer_h), (255, 255, 255))
    canvas.paste(base_img, (0, 0))
    draw = ImageDraw.Draw(canvas)

    radius = max(14, min(26, int(min(w, h) * 0.016)))
    font_num = _load_font(max(12, int(radius * 1.1)), bold=True)
    font_foot = _load_font(max(13, int(footer_h * 0.36)), bold=False)

    placed_centers: list[tuple[float, float]] = []
    min_dist = radius * 2.45

    # Candidate radial offsets around the dimension box
    offsets = [
        (-2.2, -1.9), (2.2, -1.9), (-2.2, 1.9), (2.2, 1.9),
        (0.0, -2.5), (0.0, 2.5), (-3.0, 0.0), (3.0, 0.0),
        (-3.2, -2.6), (3.2, -2.6), (-3.2, 2.6), (3.2, 2.6),
    ]

    for b in balloons:
        tx = b.x_pct / 100.0 * w
        ty = b.y_pct / 100.0 * h
        bw = max(radius * 1.5, b.w_pct / 100.0 * w * 0.5)
        bh = max(radius * 0.8, b.h_pct / 100.0 * h * 0.5)

        best_cx, best_cy = tx - radius * 2.2, ty - radius * 1.8
        for ox, oy in offsets:
            cx = tx + ox * radius + (bw * 0.35 if ox > 0 else (-bw * 0.35 if ox < 0 else 0))
            cy = ty + oy * radius + (bh * 0.35 if oy > 0 else (-bh * 0.35 if oy < 0 else 0))
            cx = max(radius + 6, min(w - radius - 6, cx))
            cy = max(radius + 6, min(h - radius - 6, cy))
            if all(math.hypot(cx - px, cy - py) >= min_dist for px, py in placed_centers):
                best_cx, best_cy = cx, cy
                break

        placed_centers.append((best_cx, best_cy))

        # Leader line from balloon center toward dimension anchor
        dx, dy = tx - best_cx, ty - best_cy
        dist = math.hypot(dx, dy) or 1.0
        # Stop leader line slightly before exact text center so text stays readable
        anchor_x = best_cx + dx * max(0.35, 1.0 - (min(bw, bh) * 0.45) / dist)
        anchor_y = best_cy + dy * max(0.35, 1.0 - (min(bw, bh) * 0.45) / dist)

        # White halo behind leader line for readability on dark CAD lines
        draw.line([(best_cx, best_cy), (anchor_x, anchor_y)], fill=(255, 255, 255), width=max(4, radius // 4 + 2))
        draw.line([(best_cx, best_cy), (anchor_x, anchor_y)], fill=(220, 38, 38), width=max(2, radius // 7))

        # Small anchor dot
        dot_r = max(3, radius // 6)
        draw.ellipse([anchor_x - dot_r, anchor_y - dot_r, anchor_x + dot_r, anchor_y + dot_r], fill=(220, 38, 38))

        # Outer white ring + crimson balloon circle
        ring = max(2, radius // 7)
        draw.ellipse(
            [best_cx - radius - ring, best_cy - radius - ring, best_cx + radius + ring, best_cy + radius + ring],
            fill=(255, 255, 255),
        )
        draw.ellipse(
            [best_cx - radius, best_cy - radius, best_cx + radius, best_cy + radius],
            fill=(220, 38, 38),
            outline=(153, 27, 27),
            width=2,
        )

        # Centered balloon number
        label = str(b.balloon_no)
        bbox = draw.textbbox((0, 0), label, font=font_num)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((best_cx - tw / 2, best_cy - th / 2 - bbox[1] * 0.65), label, fill=(255, 255, 255), font=font_num)

    # Bottom status/legend strip
    draw.rectangle([0, h, w, h + footer_h], fill=(15, 23, 42))
    pn = metadata.get("part_number") or "—"
    pname = metadata.get("part_name") or "Teknik Çizim"
    mat = metadata.get("material") or "—"
    std = metadata.get("standard") or "ISO 2768-mK"
    foot_text = (
        f"CNC BALONLAMA RAPORU  |  Parça: {pname} ({pn})  |  Malzeme: {mat}  |  "
        f"Standart: {std}  |  Toplam Balon: {len(balloons)}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    draw.text((18, h + int(footer_h * 0.28)), foot_text, fill=(241, 245, 249), font=font_foot)
    return canvas


# --- Exporters (PDF, Excel .xlsx, Word .docx) ---

def export_ballooned_pdf(
    ballooned_img: Image.Image,
    balloons: list[BalloonItem],
    metadata: dict[str, str],
    out_path: Path,
) -> Path:
    """Create a multi-page PDF: Page 1 = high-res ballooned drawing, Page 2+ = AS9102 inspection table."""
    doc = fitz.open()

    # Page 1: Landscape A4 with ballooned drawing
    page = doc.new_page(width=842, height=595)
    img_buf = io.BytesIO()
    ballooned_img.save(img_buf, format="PNG")
    page.insert_image(fitz.Rect(16, 16, 826, 579), stream=img_buf.getvalue(), keep_proportion=True)

    # Page 2+: Inspection Table
    rows_per_page = 24
    chunks = [balloons[i:i + rows_per_page] for i in range(0, max(1, len(balloons)), rows_per_page)]
    headers = ["No", "Bölge", "Karakteristik / Ölçü", "Kategori", "Nominal", "+Tol", "-Tol", "Min", "Max", "Ölçüm Aleti", "Kritiklik"]
    col_x = [24, 52, 88, 215, 315, 365, 412, 460, 510, 565, 745]

    for p_idx, chunk in enumerate(chunks, start=1):
        tp = doc.new_page(width=842, height=595)
        tp.draw_rect(fitz.Rect(20, 18, 822, 54), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
        tp.insert_text(
            (30, 41),
            f"CNC BALONLAMA VE KALITE KONTROL FORMU (AS9102 / FAI)  -  "
            f"Parca: {metadata.get('part_name', '')} ({metadata.get('part_number', '-')})  |  Sayfa {p_idx}/{len(chunks)}",
            fontsize=10.5,
            color=(1, 1, 1),
        )
        # Header row
        y = 72
        tp.draw_rect(fitz.Rect(20, y - 12, 822, y + 6), color=(0.86, 0.15, 0.15), fill=(0.86, 0.15, 0.15))
        for cx, htext in zip(col_x, headers, strict=False):
            tp.insert_text((cx, y), htext, fontsize=8.5, color=(1, 1, 1))
        y += 20

        for idx, b in enumerate(chunk):
            if idx % 2 == 1:
                tp.draw_rect(fitz.Rect(20, y - 11, 822, y + 7), color=(0.96, 0.97, 0.98), fill=(0.96, 0.97, 0.98))
            vals = [
                str(b.balloon_no),
                b.zone or "-",
                b.raw_text[:22],
                b.category[:16],
                f"{b.nominal:g}" if b.nominal is not None else "-",
                f"+{b.tol_plus:g}" if b.tol_plus is not None else "-",
                f"{b.tol_minus:g}" if b.tol_minus is not None else "-",
                f"{b.min_limit:g}" if b.min_limit is not None else "-",
                f"{b.max_limit:g}" if b.max_limit is not None else "-",
                b.gage[:30],
                b.criticality,
            ]
            for cx, val in zip(col_x, vals, strict=False):
                tp.insert_text((cx, y), val, fontsize=8, color=(0.1, 0.1, 0.15))
            y += 20

    doc.save(str(out_path))
    doc.close()
    return out_path


def export_excel_report(
    balloons: list[BalloonItem],
    metadata: dict[str, str],
    out_path: Path,
) -> Path:
    """Create a comprehensive 4-sheet AS9102 / FAI & CNC Manufacturing Process Excel workbook."""
    plan = build_cnc_manufacturing_plan(balloons, metadata)
    wb = Workbook()

    navy_fill = PatternFill("solid", fgColor="1E293B")
    slate_fill = PatternFill("solid", fgColor="334155")
    red_fill = PatternFill("solid", fgColor="DC2626")
    soft_fill = PatternFill("solid", fgColor="F8FAFC")
    meta_fill = PatternFill("solid", fgColor="EFF6FF")
    crit_fill = PatternFill("solid", fgColor="FEE2E2")
    warn_fill = PatternFill("solid", fgColor="FEF3C7")
    thin_side = Side(style="thin", color="CBD5E1")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # =========================================================================
    # SHEET 1: AS9102 FORM 3 — DETAILED BALLOON INSPECTION SHEET (Primary Tab)
    # =========================================================================
    ws: Any = wb.active
    assert ws is not None
    ws.title = "Form 3 - Balonlama (FAI)"

    ws.merge_cells("A1:T1")
    ws["A1"].value = "AS9102 FORM 3 — CNC TEKNİK ÇİZİM BALONLAMA, TOLERANS VE KALİTE KONTROL RAPORU"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    meta_rows = [
        ("Parça No:", metadata.get("part_number") or "—", "Parça Adı:", metadata.get("part_name") or "—", "Revizyon:", metadata.get("revision") or "A", "Toplam Balon:", str(plan["summary"]["total"])),
        ("Malzeme:", metadata.get("material") or "—", "Standart:", metadata.get("standard") or "ISO 2768-mK", "Tarih:", datetime.now().strftime("%Y-%m-%d %H:%M"), "Kritik / Majör / Minör:", f"{plan['summary']['critical']} / {plan['summary']['major']} / {plan['summary']['minor']}"),
    ]
    for r_offset, mrow in enumerate(meta_rows, start=2):
        ws.row_dimensions[r_offset].height = 20
        for idx_m, val in enumerate(mrow):
            c = ws.cell(row=r_offset, column=idx_m + 1, value=val)
            c.border = border
            if idx_m % 2 == 0:
                c.font = Font(bold=True, size=10, color="1E293B")
                c.fill = meta_fill
            else:
                c.font = Font(size=10)

    headers = [
        "Balon No", "Bölge", "Çizim İfadesi", "Kategori", "Adet",
        "Nominal", "+Tol", "-Tol", "Min Limit", "Max Limit", "Tol. Bandı",
        "Operasyon (OP)", "Önerilen Kesici Takım", "Ölçüm Ekipmanı", "Kontrol Sıklığı",
        "Numune 1", "Numune 2", "Numune 3", "Ortalama", "Sonuç (OK/NOK)",
    ]
    header_row = 5
    ws.row_dimensions[header_row].height = 26
    for col_i, htext in enumerate(headers, start=1):
        c = ws.cell(row=header_row, column=col_i, value=htext)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = red_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    for idx, b in enumerate(balloons, start=1):
        r = header_row + idx
        ws.row_dimensions[r].height = 22
        span = round(abs(b.max_limit - b.min_limit), 4) if (b.min_limit is not None and b.max_limit is not None) else None
        avg_formula = f'=IF(COUNT(P{r}:R{r})=0,"",ROUND(AVERAGE(P{r}:R{r}),4))'
        if b.min_limit is not None and b.max_limit is not None:
            res_formula = f'=IF(S{r}="","",IF(AND(MIN(P{r}:R{r})>=I{r},MAX(P{r}:R{r})<=J{r}),"OK","NOK"))'
        else:
            res_formula = f'=IF(P{r}="","","MANUEL ONAY")'

        row_vals = [
            b.balloon_no, b.zone or "—", b.raw_text, b.category, b.quantity,
            b.nominal, b.tol_plus, b.tol_minus, b.min_limit, b.max_limit, span,
            b.operation, b.tooling, b.gage, b.inspection_freq,
            None, None, None, avg_formula, res_formula,
        ]
        for col_i, val in enumerate(row_vals, start=1):
            c = ws.cell(row=r, column=col_i, value=val)
            c.border = border
            c.alignment = Alignment(
                horizontal="left" if col_i in (3, 4, 12, 13, 14, 15) else "center",
                vertical="center",
                wrap_text=col_i in (12, 13, 14, 15),
            )
            if idx % 2 == 0:
                c.fill = soft_fill
            if col_i == 1:
                c.font = Font(bold=True, color="DC2626")
            if b.criticality == "Kritik" and col_i == 3:
                c.fill = crit_fill
                c.font = Font(bold=True, color="991B1B")

    widths = [9, 7, 20, 17, 6, 10, 9, 9, 10, 10, 10, 26, 30, 26, 22, 11, 11, 11, 11, 15]
    for col_i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col_i)].width = width
    ws.freeze_panes = "D6"

    # =========================================================================
    # SHEET 2: CNC PROSES & OPERASYON PLANI + DFM RİSK ANALİZİ
    # =========================================================================
    ws_op: Any = wb.create_sheet("CNC Proses & Operasyon Planı")
    ws_op.merge_cells("A1:F1")
    ws_op["A1"].value = "CNC İMALAT PROSES ROTASI, KESME PARAMETRELERİ VE DFM RİSK ANALİZİ"
    ws_op["A1"].font = Font(size=13, bold=True, color="FFFFFF")
    ws_op["A1"].fill = navy_fill
    ws_op["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_op.row_dimensions[1].height = 28

    cp = plan["cutting_parameters"]
    ws_op["A3"].value = "MALZEME KESME PARAMETRE REHBERİ"
    ws_op["A3"].font = Font(bold=True, size=11, color="1E293B")
    param_rows = [
        ("ISO Malzeme Grubu", cp["group"]),
        ("Torna Kesme Hızı (Vc)", cp["vc_turn"]),
        ("Freze Kesme Hızı (Vc)", cp["vc_mill"]),
        ("İlerleme (f)", cp["feed"]),
        ("Soğutma Sıvısı", cp["coolant"]),
        ("Takım / Proses Notu", cp["note"]),
    ]
    for i, (k, v) in enumerate(param_rows, start=4):
        c1, c2 = ws_op.cell(i, 1, k), ws_op.cell(i, 2, v)
        ws_op.merge_cells(start_row=i, start_column=2, end_row=i, end_column=6)
        c1.font = Font(bold=True)
        c1.fill = meta_fill
        c1.border = border
        c2.border = border

    op_start = 11
    ws_op.cell(op_start, 1, "OPERASYON ROTASI (OP10 - OP50)").font = Font(bold=True, size=11, color="1E293B")
    op_headers = ["OP", "Operasyon Adı", "Tezgâh", "Bağlama / Fikstür", "Kapsanan Balonlar", "Mühendislik / Setup Notu"]
    for ci, ht in enumerate(op_headers, start=1):
        c = ws_op.cell(op_start + 1, ci, ht)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = slate_fill
        c.border = border
    for idx_o, op in enumerate(plan["operations"], start=op_start + 2):
        b_list = ", ".join(f"#{n}" for n in op["balloons"]) if op["balloons"] else "Genel"
        vals = [op["op"], op["name"], op["machine"], op["fixture"], b_list, op["notes"]]
        for ci, val in enumerate(vals, start=1):
            c = ws_op.cell(idx_o, ci, val)
            c.border = border
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws_op.row_dimensions[idx_o].height = 28

    risk_start = op_start + 3 + len(plan["operations"])
    ws_op.cell(risk_start, 1, "DFM VE KRİTİK KALİTE RİSK UYARILARI").font = Font(bold=True, size=11, color="991B1B")
    for idx_r, rtext in enumerate(plan["dfm_risks"], start=risk_start + 1):
        ws_op.merge_cells(start_row=idx_r, start_column=1, end_row=idx_r, end_column=6)
        c = ws_op.cell(idx_r, 1, f"[RİSK] {rtext}")
        c.fill = warn_fill
        c.border = border
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws_op.row_dimensions[idx_r].height = 26

    for ci, w in enumerate([10, 32, 26, 30, 22, 46], start=1):
        ws_op.column_dimensions[get_column_letter(ci)].width = w

    # =========================================================================
    # SHEET 3: AS9102 FORM 1 & FORM 2 (PARÇA & MALZEME İZLENEBİLİRLİK)
    # =========================================================================
    ws_f1: Any = wb.create_sheet("Form 1-2 - Parça & Malzeme")
    ws_f1.merge_cells("A1:D1")
    ws_f1["A1"].value = "AS9102 FORM 1 & 2 — PARÇA TANIMLAMA, MALZEME VE İZLENEBİLİRLİK"
    ws_f1["A1"].font = Font(size=12, bold=True, color="FFFFFF")
    ws_f1["A1"].fill = navy_fill
    ws_f1.row_dimensions[1].height = 26

    f1_rows = [
        ("1. Parça Numarası", metadata.get("part_number") or "—", "2. Parça Adı", metadata.get("part_name") or "—"),
        ("3. Revizyon", metadata.get("revision") or "A", "4. Genel Tolerans", metadata.get("standard") or "ISO 2768-mK"),
        ("5. Ham Malzeme", metadata.get("material") or "—", "6. Malzeme Sertifikası (3.1)", "Bekleniyor / Lot No: ____"),
        ("7. Isıl İşlem / Sertlik", "Çizim notlarına göre", "8. Yüzey Kaplama", "Çizim notlarına göre"),
        ("9. Toplam Karakteristik", str(plan["summary"]["total"]), "10. Kritik Karakteristik", str(plan["summary"]["critical"])),
        ("11. Hazırlayan (Mühendis)", "____________________", "12. Kalite Onayı (FAI)", "____________________"),
    ]
    for r_i, tup in enumerate(f1_rows, start=3):
        for c_i, v in enumerate(tup, start=1):
            cell = ws_f1.cell(r_i, c_i, v)
            cell.border = border
            if c_i in (1, 3):
                cell.font = Font(bold=True)
                cell.fill = meta_fill
    for ci, w in enumerate([26, 30, 26, 30], start=1):
        ws_f1.column_dimensions[get_column_letter(ci)].width = w

    # =========================================================================
    # SHEET 4: OTOMATİK MALİYET, SÜRE TEKLİFİ & FANUC G-KODU TASLAĞI
    # =========================================================================
    ws_cost: Any = wb.create_sheet("Maliyet & Fanuc G-Kodu")
    ws_cost.merge_cells("A1:D1")
    ws_cost["A1"].value = "CNC OTOMATİK MALİYET, İŞLEME SÜRESİ TEKLİFİ VE FANUC G-KODU TASLAĞI"
    ws_cost["A1"].font = Font(size=12, bold=True, color="FFFFFF")
    ws_cost["A1"].fill = navy_fill
    ws_cost.row_dimensions[1].height = 26

    ce = plan.get("cost_estimate", {})
    bd = ce.get("breakdown_min", {})
    cost_rows = [
        ("Önerilen Ham Kütük Boyutu", ce.get("stock_dimensions", "-"), "Ham / Net Ağırlık (kg)", f"{ce.get('raw_weight_kg', 0)} kg / {ce.get('net_weight_kg', 0)} kg"),
        ("Hazırlık / Setup Süresi", f"{ce.get('setup_time_min', 0)} dk", "Parça Başı İşleme Süresi (Cycle)", f"{ce.get('cycle_time_min', 0)} dk"),
        ("Torna / Freze Süresi", f"{bd.get('turn_mill', 0)} dk", "Delik / Kılavuz Süresi", f"{bd.get('drill_tap', 0)} dk"),
        ("Taşlama Süresi", f"{bd.get('grinding', 0)} dk", "CMM / Kalite Kontrol Süresi", f"{bd.get('quality_cmm', 0)} dk"),
        ("Ham Malzeme Maliyeti", f"{ce.get('material_cost_tl', 0)} TL", "CNC İşçilik + Takım Maliyeti", f"{round(ce.get('machining_cost_tl', 0) + ce.get('tooling_cost_tl', 0), 2)} TL"),
        ("1 Adet (Prototip) Birim Teklif", f"{ce.get('unit_quote_1_tl', 0)} TL", "10 Adet Birim Teklif", f"{ce.get('unit_quote_10_tl', 0)} TL"),
        ("100 Adet (Seri) Birim Teklif", f"{ce.get('unit_quote_100_tl', 0)} TL", "Teklif Para Birimi", "TRY (KDV Hariç)"),
    ]
    for r_i, tup in enumerate(cost_rows, start=3):
        for c_i, v in enumerate(tup, start=1):
            cell = ws_cost.cell(r_i, c_i, v)
            cell.border = border
            if c_i in (1, 3):
                cell.font = Font(bold=True)
                cell.fill = meta_fill

    ws_cost.cell(12, 1, "BAŞLANGIÇ FANUC ISO G-KODU TASLAĞI").font = Font(bold=True, size=11, color="1E293B")
    for idx_g, gline in enumerate((plan.get("gcode_template") or "").splitlines(), start=13):
        ws_cost.merge_cells(start_row=idx_g, start_column=1, end_row=idx_g, end_column=4)
        gc = ws_cost.cell(idx_g, 1, gline)
        gc.font = Font(name="Consolas", size=9.5)
    for ci, w in enumerate([28, 28, 28, 28], start=1):
        ws_cost.column_dimensions[get_column_letter(ci)].width = w

    wb.save(str(out_path))
    return out_path


def export_word_report(
    ballooned_img_path: Path,
    balloons: list[BalloonItem],
    metadata: dict[str, str],
    out_path: Path,
) -> Path:
    """Create a comprehensive Mechanical Engineering CNC Ballooning & Process Plan Word (.docx) report."""
    plan = build_cnc_manufacturing_plan(balloons, metadata)
    doc = Document()

    title = doc.add_heading("CNC İmalat, Teknik Çizim Balonlama ve Kalite Kontrol Raporu (AS9102 / FAI)", level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    meta_table = doc.add_table(rows=3, cols=4)
    meta_table.style = "Table Grid"
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    pairs = [
        ("Parça No", metadata.get("part_number") or "—", "Parça Adı", metadata.get("part_name") or "—"),
        ("Malzeme", metadata.get("material") or "—", "Standart / Rev", f"{metadata.get('standard', 'ISO 2768-mK')} / Rev {metadata.get('revision', 'A')}"),
        ("Toplam Balon", str(plan["summary"]["total"]), "Kritik / Majör / Minör", f"{plan['summary']['critical']} / {plan['summary']['major']} / {plan['summary']['minor']}"),
    ]
    for r_i, (k1, v1, k2, v2) in enumerate(pairs):
        cells = meta_table.rows[r_i].cells
        cells[0].text, cells[1].text, cells[2].text, cells[3].text = k1, v1, k2, v2
        for idx in (0, 2):
            for p in cells[idx].paragraphs:
                for run in p.runs:
                    run.bold = True

    doc.add_heading("1. Balonlanmış Teknik Çizim", level=1)
    if ballooned_img_path.exists():
        doc.add_picture(str(ballooned_img_path), width=Inches(6.3))

    doc.add_heading(f"2. AS9102 Form 3 — Karakteristik, Operasyon ve Ölçüm Tablosu ({len(balloons)} Balon)", level=1)
    tbl = doc.add_table(rows=1, cols=9)
    tbl.style = "Table Grid"
    hdr = ["No", "Bölge", "Ölçü", "Kategori", "Min / Max", "Operasyon", "Kesici Takım", "Ölçüm Aleti", "Sıklık"]
    for i, text in enumerate(hdr):
        cell = tbl.rows[0].cells[i]
        cell.text = text
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(8)

    for b in balloons:
        row_cells = tbl.add_row().cells
        mm = f"{b.min_limit:g} / {b.max_limit:g}" if (b.min_limit is not None and b.max_limit is not None) else "—"
        vals = [
            str(b.balloon_no), b.zone or "—", b.raw_text, b.category,
            mm, b.operation, b.tooling, b.gage, b.inspection_freq,
        ]
        for i, val in enumerate(vals):
            row_cells[i].text = val
            for p in row_cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(7.5)

    doc.add_heading("3. CNC Operasyon Rotası ve Kesme Parametreleri", level=1)
    cp = plan["cutting_parameters"]
    doc.add_paragraph(
        f"Malzeme Grubu: {cp['group']} | Torna Vc: {cp['vc_turn']} | Freze Vc: {cp['vc_mill']} | "
        f"İlerleme: {cp['feed']} | Soğutma: {cp['coolant']}. Not: {cp['note']}"
    )
    op_tbl = doc.add_table(rows=1, cols=5)
    op_tbl.style = "Table Grid"
    for i, ht in enumerate(["OP", "Operasyon", "Tezgâh", "Bağlama / Fikstür", "Balonlar"]):
        op_tbl.rows[0].cells[i].text = ht
        for p in op_tbl.rows[0].cells[i].paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(8.5)
    for op in plan["operations"]:
        rc = op_tbl.add_row().cells
        b_str = ", ".join(f"#{n}" for n in op["balloons"]) if op["balloons"] else "Genel"
        for i, val in enumerate([op["op"], op["name"], op["machine"], op["fixture"], b_str]):
            rc[i].text = val
            for p in rc[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8)

    doc.add_heading("4. DFM ve Kritik İmalat Risk Analizi", level=1)
    for risk in plan["dfm_risks"]:
        doc.add_paragraph(risk, style="List Bullet")

    ce = plan.get("cost_estimate") or {}
    if ce:
        doc.add_heading("5. Otomatik Maliyet, İşleme Süresi ve Teklif Hesabı", level=1)
        doc.add_paragraph(
            f"Ham Kütük: {ce.get('stock_dimensions')} ({ce.get('raw_weight_kg')} kg ham / {ce.get('net_weight_kg')} kg net) | "
            f"Parça Başı İşleme Süresi: {ce.get('cycle_time_min')} dk (Setup: {ce.get('setup_time_min')} dk) | "
            f"Birim Teklif: 1 Adet = {ce.get('unit_quote_1_tl')} TL · 10 Adet = {ce.get('unit_quote_10_tl')} TL · 100 Adet = {ce.get('unit_quote_100_tl')} TL."
        )
    if plan.get("gcode_template"):
        doc.add_heading("6. Başlangıç Fanuc G-Kodu Taslağı", level=1)
        p_g = doc.add_paragraph(plan["gcode_template"])
        for r in p_g.runs:
            r.font.size = Pt(8)

    doc.save(str(out_path))
    return out_path


# --- Realistic Synthetic CNC Technical Drawing Generator (Demo & Dataset) ---

def generate_sample_cnc_drawing_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    """Generate a realistic vector CNC Machined Bearing Housing Flange technical drawing (PDF + optional PNG)."""
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)  # A4 Landscape

    navy = (0.08, 0.12, 0.2)
    dim_col = (0.12, 0.28, 0.55)
    center_col = (0.75, 0.15, 0.15)
    light = (0.55, 0.6, 0.68)

    # Outer drawing border + grid zones
    page.draw_rect(fitz.Rect(18, 18, 824, 577), color=navy, width=1.6)
    page.draw_rect(fitz.Rect(24, 24, 818, 571), color=navy, width=0.6)

    # --- LEFT: Front View of Bearing Housing Flange ---
    cx, cy = 245, 290
    r_outer = 128   # Ø110
    r_pcd = 96      # Ø80 PCD
    r_boss = 66     # Ø56
    r_bore = 48     # Ø42 H7

    # Centerlines
    page.draw_line((cx - 155, cy), (cx + 155, cy), color=center_col, width=0.7, dashes="[6 3 1 3]")
    page.draw_line((cx, cy - 155), (cx, cy + 155), color=center_col, width=0.7, dashes="[6 3 1 3]")

    # Main concentric circles
    page.draw_circle((cx, cy), r_outer, color=navy, width=1.8)
    page.draw_circle((cx, cy), r_pcd, color=center_col, width=0.7, dashes="[5 3]")
    page.draw_circle((cx, cy), r_boss, color=navy, width=1.2)
    page.draw_circle((cx, cy), r_bore, color=navy, width=1.8)

    # 4x Bolt holes on PCD (45°, 135°, 225°, 315°)
    for deg in (45, 135, 225, 315):
        rad = math.radians(deg)
        hx = cx + r_pcd * math.cos(rad)
        hy = cy + r_pcd * math.sin(rad)
        page.draw_circle((hx, hy), 10, color=navy, width=1.3)
        page.draw_circle((hx, hy), 13, color=light, width=0.6, dashes="[3 2]")
        page.draw_line((hx - 15, hy), (hx + 15, hy), color=center_col, width=0.5)
        page.draw_line((hx, hy - 15), (hx, hy + 15), color=center_col, width=0.5)

    # Keyway slot on top of bore
    page.draw_rect(fitz.Rect(cx - 10, cy - r_bore - 9, cx + 10, cy - r_bore + 2), color=navy, fill=(1, 1, 1), width=1.4)

    # Front View Dimension Callouts
    front_dims = [
        ((cx - 52, cy - 144), "Ø110 ±0.05"),
        ((cx + 78, cy - 122), "Ø80 ±0.03"),
        ((cx - 34, cy - 8), "Ø42 H7"),
        ((cx + 72, cy + 88), "4x Ø9 THRU"),
        ((cx - 148, cy + 118), "4x M8x1.25-6H"),
        ((cx - 150, cy - 105), "R5 ±0.1"),
        ((cx + 98, cy - 42), "45° ±0.5°"),
        ((cx - 28, cy - 72), "10.0 +0.03/-0.00"),
    ]
    for (tx, ty), txt in front_dims:
        page.insert_text((tx, ty), txt, fontsize=10, color=dim_col)

    page.insert_text((cx - 55, cy + 168), "FRONT VIEW (A-A)", fontsize=9, color=navy)

    # --- RIGHT: Side / Section View ---
    sx, sy = 575, 290
    # Flange base plate (width 36, height 256) + protruding hub (width 52, height 132)
    page.draw_rect(fitz.Rect(sx - 55, sy - 128, sx - 15, sy + 128), color=navy, width=1.8)
    page.draw_rect(fitz.Rect(sx - 15, sy - 66, sx + 55, sy + 66), color=navy, width=1.8)
    # Bore dashed lines
    page.draw_line((sx - 55, sy - 48), (sx + 55, sy - 48), color=navy, width=1.0, dashes="[4 3]")
    page.draw_line((sx - 55, sy + 48), (sx + 55, sy + 48), color=navy, width=1.0, dashes="[4 3]")
    # Centerline
    page.draw_line((sx - 80, sy), (sx + 85, sy), color=center_col, width=0.7, dashes="[6 3 1 3]")

    # Dimension lines on side view
    page.draw_line((sx - 55, sy - 148), (sx + 55, sy - 148), color=dim_col, width=0.8)
    page.draw_line((sx - 55, sy - 128), (sx - 55, sy - 154), color=dim_col, width=0.6)
    page.draw_line((sx + 55, sy - 66), (sx + 55, sy - 154), color=dim_col, width=0.6)

    page.draw_line((sx - 55, sy + 148), (sx - 15, sy + 148), color=dim_col, width=0.8)
    page.draw_line((sx + 88, sy - 66), (sx + 88, sy + 66), color=dim_col, width=0.8)

    side_dims = [
        ((sx - 25, sy - 155), "36.0 ±0.05"),
        ((sx - 60, sy + 162), "14.0 ±0.05"),
        ((sx + 94, sy - 4), "Ø56 h6"),
        ((sx + 62, sy - 88), "2x45°"),
        ((sx + 62, sy + 88), "Ra 0.8"),
        ((sx - 118, sy - 92), "Ra 1.6"),
        ((sx + 58, sy - 122), "FLAT 0.02"),
        ((sx + 58, sy + 124), "PERP 0.03 A"),
        ((sx - 135, sy + 95), "CONC 0.02 A"),
    ]
    for (tx, ty), txt in side_dims:
        if txt.startswith(("FLAT", "PERP", "CONC")):
            page.draw_rect(fitz.Rect(tx - 4, ty - 11, tx + len(txt) * 6.2 + 4, ty + 4), color=dim_col, width=0.8)
        page.insert_text((tx, ty), txt, fontsize=10, color=dim_col)

    page.insert_text((sx - 45, sy + 184), "SECTION VIEW A-A", fontsize=9, color=navy)

    # --- Title Block (Bottom Right, excluded from ballooning) ---
    tb = fitz.Rect(525, 470, 818, 571)
    page.draw_rect(tb, color=navy, fill=(0.97, 0.98, 1.0), width=1.4)
    page.draw_line((525, 496), (818, 496), color=navy, width=0.8)
    page.draw_line((525, 522), (818, 522), color=navy, width=0.8)
    page.draw_line((525, 546), (818, 546), color=navy, width=0.8)
    page.draw_line((670, 496), (670, 571), color=navy, width=0.8)

    page.insert_text((533, 487), "PART NAME: CNC BEARING HOUSING FLANGE", fontsize=9, color=navy)
    page.insert_text((533, 513), "PART NO: FLN-2026-042", fontsize=8.5, color=navy)
    page.insert_text((678, 513), "REV: B", fontsize=8.5, color=navy)
    page.insert_text((533, 538), "MATERIAL: AISI 4140 STEEL", fontsize=8.5, color=navy)
    page.insert_text((678, 538), "SCALE: 1:1", fontsize=8.5, color=navy)
    page.insert_text((533, 562), "TOLERANCE: ISO 2768-mK", fontsize=8.5, color=navy)
    page.insert_text((678, 562), "UNIT: MM", fontsize=8.5, color=navy)

    # General Notes (Bottom Left)
    page.insert_text((34, 540), "NOTE: ALL DIMENSIONS IN MM. DEBURR ALL SHARP EDGES 0.3 MAX.", fontsize=8, color=navy)
    page.insert_text((34, 556), "UNLESS OTHERWISE SPECIFIED: ISO 2768-mK · CNC 5-AXIS TURNING/MILLING", fontsize=8, color=navy)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf))

    if out_png is not None:
        pix = page.get_pixmap(dpi=220)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))

    doc.close()
    return out_pdf


def evaluate_cmm_measurements(
    balloons: list[BalloonItem],
    measurements: dict[int, list[float]],
) -> dict[str, Any]:
    """Evaluate CMM / operator measured sample values against balloon tolerances and compute SPC (Cp/Cpk)."""
    results: list[dict[str, Any]] = []
    ok_count = 0
    nok_count = 0

    for b in balloons:
        samples = [float(x) for x in measurements.get(b.balloon_no, []) if x is not None]
        if not samples:
            continue
        mean_val = sum(samples) / len(samples)
        dev = round(mean_val - b.nominal, 4) if b.nominal is not None else 0.0

        status = "OK"
        if b.min_limit is not None and any(s < b.min_limit for s in samples):
            status = "NOK (ALT LİMİT DIŞI)"
        elif b.max_limit is not None and any(s > b.max_limit for s in samples):
            status = "NOK (ÜST LİMİT DIŞI)"

        if status == "OK":
            ok_count += 1
        else:
            nok_count += 1

        cp: float | None = None
        cpk: float | None = None
        if len(samples) >= 2 and b.min_limit is not None and b.max_limit is not None:
            variance = sum((s - mean_val) ** 2 for s in samples) / (len(samples) - 1)
            sigma = math.sqrt(variance)
            if sigma > 1e-7:
                tol_band = b.max_limit - b.min_limit
                cp = round(tol_band / (6.0 * sigma), 2)
                cpu = (b.max_limit - mean_val) / (3.0 * sigma)
                cpl = (mean_val - b.min_limit) / (3.0 * sigma)
                cpk = round(min(cpu, cpl), 2)

        results.append({
            "balloon_no": b.balloon_no,
            "raw_text": b.raw_text,
            "min_limit": b.min_limit,
            "max_limit": b.max_limit,
            "samples": samples,
            "mean": round(mean_val, 4),
            "deviation": dev,
            "cp": cp,
            "cpk": cpk,
            "status": status,
        })

    return {
        "evaluated_count": len(results),
        "ok_count": ok_count,
        "nok_count": nok_count,
        "first_pass_yield_pct": round((ok_count / len(results)) * 100.0, 1) if results else 100.0,
        "items": results,
    }


def generate_sample_cnc_dxf(out_dxf: Path) -> Path:
    """Generate a realistic AutoCAD ASCII .DXF technical drawing of the CNC Bearing Housing Flange."""
    entities: list[str] = ["0", "SECTION", "2", "ENTITIES"]

    def add_circle(cx: float, cy: float, r: float) -> None:
        entities.extend(["0", "CIRCLE", "8", "0", "10", f"{cx}", "20", f"{cy}", "40", f"{r}"])

    def add_line(x1: float, y1: float, x2: float, y2: float) -> None:
        entities.extend(["0", "LINE", "8", "0", "10", f"{x1}", "20", f"{y1}", "11", f"{x2}", "21", f"{y2}"])

    def add_text(x: float, y: float, text: str) -> None:
        entities.extend(["0", "TEXT", "8", "DIMS", "10", f"{x}", "20", f"{y}", "40", "4.0", "1", text])

    # Concentric circles (Front view)
    add_circle(120, 150, 55)
    add_circle(120, 150, 40)
    add_circle(120, 150, 28)
    add_circle(120, 150, 21)
    for deg in (45, 135, 225, 315):
        rad = math.radians(deg)
        add_circle(round(120 + 40 * math.cos(rad), 2), round(150 + 40 * math.sin(rad), 2), 4.5)

    # Side section view lines
    add_line(240, 95, 260, 95)
    add_line(260, 95, 260, 205)
    add_line(260, 205, 240, 205)
    add_line(240, 205, 240, 95)
    add_line(260, 122, 295, 122)
    add_line(295, 122, 295, 178)
    add_line(295, 178, 260, 178)

    # Dimension & GD&T callouts
    callouts = [
        (95, 215, "%%c110 %%p0.05"),
        (155, 198, "%%c80 %%p0.03"),
        (108, 150, "%%c42 H7"),
        (155, 108, "4x %%c9 THRU"),
        (60, 98, "4x M8x1.25-6H"),
        (62, 195, "R5 %%p0.1"),
        (252, 218, "36.0 %%p0.05"),
        (235, 82, "14.0 %%p0.05"),
        (302, 150, "%%c56 h6"),
        (275, 190, "2x45%%d"),
        (275, 110, "Ra 0.8"),
        (215, 185, "Ra 1.6"),
        (275, 205, "FLAT 0.02"),
        (275, 92, "PERP 0.03 A"),
        (210, 112, "CONC 0.02 A"),
        (20, 35, "PART NAME: CNC BEARING HOUSING FLANGE"),
        (20, 25, "PART NO: FLN-2026-042"),
        (20, 15, "MATERIAL: AISI 4140 STEEL"),
    ]
    for tx, ty, txt in callouts:
        add_text(tx, ty, txt)

    entities.extend(["0", "ENDSEC", "0", "EOF"])
    out_dxf.parent.mkdir(parents=True, exist_ok=True)
    out_dxf.write_text("\n".join(entities), encoding="utf-8")
    return out_dxf
