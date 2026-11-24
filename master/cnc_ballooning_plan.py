"""CNC Ballooning Core Data Model, ISO 2768/286 Tables, Manufacturing Plan, Costing & Fanuc G-Code."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any

ISO_2768_M_LINEAR = [
    (0.5, 3.0, 0.1), (3.0, 6.0, 0.1), (6.0, 30.0, 0.2), (30.0, 120.0, 0.3),
    (120.0, 400.0, 0.5), (400.0, 1000.0, 0.8), (1000.0, 2000.0, 1.2), (2000.0, 4000.0, 2.0),
]

ISO_286_FITS: dict[str, list[tuple[float, float, float]]] = {
    "H7": [(3, 10, 0), (6, 12, 0), (10, 15, 0), (18, 18, 0), (30, 21, 0), (50, 25, 0), (80, 30, 0), (120, 35, 0), (180, 40, 0), (250, 46, 0)],
    "H8": [(3, 14, 0), (6, 18, 0), (10, 22, 0), (18, 27, 0), (30, 33, 0), (50, 39, 0), (80, 46, 0), (120, 54, 0), (180, 63, 0), (250, 72, 0)],
    "H6": [(3, 6, 0), (6, 8, 0), (10, 9, 0), (18, 11, 0), (30, 13, 0), (50, 16, 0), (80, 19, 0), (120, 22, 0), (180, 25, 0), (250, 29, 0)],
    "g6": [(3, -2, -8), (6, -4, -12), (10, -5, -14), (18, -6, -17), (30, -7, -20), (50, -9, -25), (80, -10, -29), (120, -12, -34), (180, -14, -39), (250, -15, -44)],
    "h6": [(3, 0, -6), (6, 0, -8), (10, 0, -9), (18, 0, -11), (30, 0, -13), (50, 0, -16), (80, 0, -19), (120, 0, -22), (180, 0, -25), (250, 0, -29)],
    "h7": [(3, 0, -10), (6, 0, -12), (10, 0, -15), (18, 0, -18), (30, 0, -21), (50, 0, -25), (80, 0, -30), (120, 0, -35), (180, 0, -40), (250, 0, -46)],
    "f7": [(3, -6, -16), (6, -10, -22), (10, -13, -28), (18, -16, -34), (30, -20, -41), (50, -25, -50), (80, -30, -60), (120, -36, -71), (180, -43, -83), (250, -50, -96)],
    "k6": [(3, 6, 0), (6, 9, 1), (10, 10, 1), (18, 12, 1), (30, 15, 2), (50, 18, 2), (80, 21, 2), (120, 25, 3), (180, 28, 3), (250, 33, 4)],
}

GDT_KEYWORDS = {
    "⏥": "Düzlemsellik (Flatness)", "∥": "Paralellik (Parallelism)",
    "⊥": "Diklik (Perpendicularity)", "◎": "Eşmerkezlilik (Concentricity)",
    "⌖": "Konum (True Position)", "↗": "Salgı (Runout)", "⌭": "Silindiriklik (Cylindricity)",
    "FLAT": "Düzlemsellik (Flatness)", "PERP": "Diklik (Perpendicularity)",
    "PARA": "Paralellik (Parallelism)", "CONC": "Eşmerkezlilik (Concentricity)",
    "POS": "Konum (True Position)", "RUNOUT": "Salgı (Runout)",
}

MATERIAL_CUTTING_DB: list[tuple[tuple[str, ...], dict[str, str]]] = [
    (("4140", "4340", "CRMO", "ALLOY STEEL", "ISLAH"), {
        "group": "ISO P (Alaşımlı Islah Çeliği)",
        "vc_turn": "160 - 210 m/dk", "vc_mill": "120 - 160 m/dk",
        "feed": "0.12 - 0.25 mm/dev (Finiş: 0.08-0.12)",
        "coolant": "Yüksek Basınçlı Emülsiyon (%7-9)",
        "note": "Yüksek kesme kuvveti; rijit bağlama ve TiAlN/CVD kaplamalı uç önerilir.",
    }),
    (("6061", "7075", "ALUM", "AL "), {
        "group": "ISO N (Alüminyum Alaşımı)",
        "vc_turn": "350 - 600 m/dk", "vc_mill": "300 - 500 m/dk",
        "feed": "0.10 - 0.22 mm/dev",
        "coolant": "Bol Emülsiyon veya MQL (Talaş Yapışmasını Önle)",
        "note": "Keskin pozitif geometrili DLC/kaplamasız parlatılmış karbür uç kullanın.",
    }),
    (("304", "316", "STAINLESS", "PASLANMAZ"), {
        "group": "ISO M (Östenitik Paslanmaz Çelik)",
        "vc_turn": "110 - 150 m/dk", "vc_mill": "80 - 120 m/dk",
        "feed": "0.10 - 0.18 mm/dev",
        "coolant": "Yoğun İçten Soğutma (Isıl Sertleşmeyi Önle)",
        "note": "Kesme duraksaması yapmayın; iş parçası sertleşmesine (work-hardening) karşı keskin kenar koruyun.",
    }),
]


@dataclass
class BalloonItem:
    balloon_no: int
    raw_text: str
    category: str
    nominal: float | None = None
    unit: str = "mm"
    tol_plus: float | None = None
    tol_minus: float | None = None
    min_limit: float | None = None
    max_limit: float | None = None
    fit_class: str = ""
    quantity: int = 1
    gage: str = "Dijital Kumpas"
    criticality: str = "Majör"
    notes: str = ""
    x_pct: float = 50.0
    y_pct: float = 50.0
    w_pct: float = 4.0
    h_pct: float = 2.0
    zone: str = ""
    operation: str = "OP10 · CNC İşleme"
    tooling: str = "Karbür Kesici Takım"
    inspection_freq: str = "İlk Parça + 1/10"
    datum_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _enrich_diameter(item: BalloonItem, span: float | None) -> None:
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


def _enrich_thread(item: BalloonItem) -> None:
    m_tap = re.search(r"M(\d+(?:\.\d+)?)\s*[xX\u00d7]?\s*(\d+(?:\.\d+)?)?", item.raw_text, re.IGNORECASE)
    pre_drill = ""
    if m_tap:
        d = float(m_tap.group(1))
        default_p = 1.25 if d == 8 else (1.5 if d == 10 else 1.0)
        pitch = float(m_tap.group(2)) if m_tap.group(2) else default_p
        pre_drill = f"Ön Delik Ø{d - pitch:.1f} Karbür Matkap + "
    item.operation = "OP30 · CNC Delik Delme & Kılavuz"
    item.tooling = f"{pre_drill}HSS-E Makine Kılavuzu"
    item.inspection_freq = "%100 (Go/No-Go Vida Mastarı)"


_STATIC_ENRICH: dict[str, tuple[str, str, str]] = {
    "Pah (Chamfer)": ("OP20 · Pah Kırma / Çapak Alma", "90° Karbür Pah Frezesi / Torna Pah Pasosu", "İlk Parça Onayı (FAI)"),
    "Radyüs (R)": ("OP10/OP20 · Kontur Finiş", "Radyüs Profil Uç / Küresel Parmak Freze", "İlk Parça Onayı (FAI)"),
    "Açı": ("OP20 · C-Ekseni / İndeksleme", "CNC C-Eksen / 4. Eksen Divizör", "İlk Parça + 1/20"),
}


def enrich_cnc_engineering_fields(item: BalloonItem) -> BalloonItem:
    """Populate senior CNC manufacturing fields (OP routing, tooling, sampling/SPC, datum)."""
    cat = item.category
    span = round(abs(item.max_limit - item.min_limit), 4) if (item.min_limit is not None and item.max_limit is not None) else None
    if cat == "Yüzey Pürüzlülüğü":
        tight = item.nominal is not None and item.nominal <= 0.8
        item.operation = "OP40 · Silindirik / Yüzey Taşlama" if tight else "OP10 · CNC Torna / Finiş Pasosu"
        item.tooling = "Al2O3 / CBN Taşlama Taşı (veya Wiper Finiş Uç)" if tight else "VNMG / DCMT Finiş Karbür Uç (R0.4)"
        item.inspection_freq = "%100 (İlk + Seri · Profilometre)" if tight else "İlk Parça + 1/10"
    elif cat == "GD&T":
        if (m_dat := re.search(r"Datum\s+([A-Z])", item.notes)):
            item.datum_ref = m_dat.group(1)
        item.operation = "OP10/OP40 · Tek Bağlamada Finiş / Taşlama"
        item.tooling = "Hassas Finiş Bara / Yumuşak Çene Referanslama"
        item.inspection_freq = "%100 (CMM · SPC Cp/Cpk ≥ 1.33)"
    elif cat == "Diş / Vida":
        _enrich_thread(item)
    elif cat == "Çap (Ø)":
        _enrich_diameter(item, span)
    elif cat in _STATIC_ENRICH:
        item.operation, item.tooling, item.inspection_freq = _STATIC_ENRICH[cat]
    else:
        item.operation = "OP10/OP20 · CNC Alın / Boy İşleme"
        item.tooling = "CNMG Alın Torna / Ø50 Tarama Kafası"
        item.inspection_freq = "%100 (İlk + Seri)" if item.criticality == "Kritik" else "İlk Parça + 1/10"
    return item


def _lookup_cutting_spec(mat_upper: str) -> dict[str, str]:
    for keys, spec in MATERIAL_CUTTING_DB:
        if any(k in mat_upper for k in keys):
            return spec
    return {
        "group": "ISO P (Genel İmalat Çeliği / Standart)",
        "vc_turn": "180 - 240 m/dk", "vc_mill": "130 - 180 m/dk",
        "feed": "0.12 - 0.25 mm/dev", "coolant": "Emülsiyon (%6-8)",
        "note": "Malzeme sertifikasına göre kesme hızını doğrulayın.",
    }


def _group_balloons_by_op(balloons: list[BalloonItem]) -> dict[str, list[int]]:
    op_groups: dict[str, list[int]] = {"OP10": [], "OP20": [], "OP30": [], "OP40": []}
    for b in balloons:
        key = next((k for k in ("OP40", "OP30", "OP20") if k in b.operation), "OP10")
        op_groups[key].append(b.balloon_no)
    return op_groups


def _build_dfm_risks(balloons: list[BalloonItem]) -> list[str]:
    checks = [
        ([b for b in balloons if b.fit_class], "Hassas ISO Geçme Riski [{tags}]: İşleme sırasında ısıl genleşme etkisini azaltmak için finiş öncesi parçayı 20°C'de dengeleyin; mikrometrik bara veya rayba kullanın."),
        ([b for b in balloons if b.category == "Yüzey Pürüzlülüğü" and b.nominal is not None and b.nominal <= 0.8], "Yüksek Yüzey Kalitesi [{tags}]: Standart tornalama ile Ra ≤ 0.8 tutturmak risklidir; OP40 taşlama veya wiper uç planlayın."),
        ([b for b in balloons if b.category == "GD&T"], "Geometrik Tolerans (GD&T) [{tags}]: Datum A referans yüzeyi ile ilgili çap/yüzeyleri mümkünse tek bağlamada (aynı ayna sıkımında) işleyin; bağlama salgı hatası ≤ 0.005 mm olmalı."),
        ([b for b in balloons if b.category == "Diş / Vida"], "Diş Kalitesi [{tags}]: Kılavuz öncesi havşa (pah) açın ve her partide Go/No-Go vida mastarı ile %100 kontrol uygulayın."),
    ]
    risks = [
        tmpl.format(tags=", ".join(f"#{b.balloon_no} ({b.raw_text})" for b in subset))
        for subset, tmpl in checks if subset
    ]
    return risks or ["Standart CNC tolerans bandı; ISO 2768-mK genel toleransları geçerlidir."]


def build_cnc_manufacturing_plan(balloons: list[BalloonItem], metadata: dict[str, str]) -> dict[str, Any]:
    """Generate a senior CNC Manufacturing Process Plan (OP10..OP50, cutting params, DFM risks)."""
    cutting = _lookup_cutting_spec((metadata.get("material") or "").upper())
    op_groups = _group_balloons_by_op(balloons)
    operations = [
        {"op": "OP10", "name": "CNC Torna — Kaba & Finiş + Datum A Oluşturma", "machine": "CNC Torna (C-Eksenli)",
         "fixture": "3 Ayaklı Hidrolik Ayna (Sert Çene → Yumuşak Çene)", "balloons": op_groups["OP10"],
         "notes": "Alın temizleme (Datum A), dış çap ve merkez delik kaba+finiş; taşlama payı (0.15 mm) bırak."},
        {"op": "OP20", "name": "CNC İşleme Merkezi — Kontur, Pah & Hassas Özellikler", "machine": "3/5 Eksen CNC Dik İşleme Merkezi",
         "fixture": "Datum A Oturmalı Hassas Mengene / Fikstür", "balloons": op_groups["OP20"],
         "notes": "Kama kanalı, radyüs, açısal indeksleme ve pah operasyonları."},
        {"op": "OP30", "name": "Delik Delme, Raybalama & Kılavuz Çekme", "machine": "CNC Dik İşleme Merkezi",
         "fixture": "Merkezleme Pimli Bağlama Aparatı", "balloons": op_groups["OP30"],
         "notes": "PCD delik çemberi konum kontrolü, ön delik + HSS-E makine kılavuzu + çapak alma."},
    ]
    if op_groups["OP40"]:
        operations.append({
            "op": "OP40", "name": "Hassas Taşlama (Ra ≤ 0.8 / GD&T)", "machine": "Üniversal Silindirik / Yüzey Taşlama Tezgâhı",
            "fixture": "Hassas Mandrel / Manyetik Tabla", "balloons": op_groups["OP40"],
            "notes": "Ra ≤ 0.8 yüzeyler ve kritik GD&T toleransları için tek bağlamada finiş taşlama.",
        })
    operations.append({
        "op": "OP50", "name": "Final Kalite Kontrol (FAI / AS9102) & Paketleme", "machine": "CMM + Profilometre + Kalibrasyonlu Mastarlar",
        "fixture": "20°C ±1°C İklimlendirilmiş Ölçüm Odası", "balloons": [b.balloon_no for b in balloons if b.criticality == "Kritik"],
        "notes": "İlk parça onayı (FAI), kritik ölçülerde %100 CMM raporu, koruyucu yağlama ve etiketleme.",
    })
    return {
        "cutting_parameters": cutting,
        "operations": operations,
        "dfm_risks": _build_dfm_risks(balloons),
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
    stock_d, stock_l = round(max_d + 5.0, 1), round(max_l + 4.0, 1)

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
    setup_cost = round((setup_min / 60.0) * hourly_rate, 2)
    base_unit = mat_cost + machining_cost + tooling_cost
    return {
        "stock_dimensions": f"Ø{stock_d:g} x {stock_l:g} mm",
        "raw_weight_kg": raw_weight_kg, "net_weight_kg": net_weight_kg,
        "setup_time_min": setup_min, "cycle_time_min": cycle_min,
        "breakdown_min": {"turn_mill": turn_mill_min, "drill_tap": drill_tap_min, "grinding": grind_min, "quality_cmm": qc_min},
        "material_cost_tl": mat_cost, "machining_cost_tl": machining_cost, "tooling_cost_tl": tooling_cost,
        "unit_quote_1_tl": round((base_unit + setup_cost) * 1.25, 2),
        "unit_quote_10_tl": round((base_unit + setup_cost / 10.0) * 1.20, 2),
        "unit_quote_100_tl": round((base_unit + setup_cost / 100.0) * 1.15, 2),
    }


def generate_fanuc_gcode_template(balloons: list[BalloonItem], metadata: dict[str, str]) -> str:
    """Generate a starter Fanuc ISO G-code template tailored to the part's real dimensions."""
    pn, mat = metadata.get("part_number") or "CNC-PART", metadata.get("material") or "STEEL"
    diameters = sorted([b.nominal for b in balloons if b.category == "Çap (Ø)" and b.nominal is not None and b.quantity == 1], reverse=True)
    linears = sorted([b.nominal for b in balloons if b.category == "Lineer Ölçü" and b.nominal is not None], reverse=True)
    holes = [b for b in balloons if b.category == "Çap (Ø)" and b.quantity > 1 and b.nominal is not None]
    threads = [b for b in balloons if b.category == "Diş / Vida"]

    od = diameters[0] if diameters else 100.0
    id_bore = diameters[-1] if len(diameters) > 1 else 40.0
    length = linears[0] if linears else 35.0
    pcd = diameters[1] if len(diameters) > 2 else round(od * 0.72, 1)

    lines = [
        "%", f"O2026 ({pn} - {mat} - FANuc TASLAK G-KODU)",
        f"(OTOMATIK URETILDI - DIS CAP: {od:g}MM, IC CAP: {id_bore:g}MM, BOY: {length:g}MM)",
        "G21 G40 G80 G99", "", "(--- OP10: ALIN VE DIS CAP KABA/FINIS TORNALAMA ---)",
        "T0101 (CNMG 120408 KABA TORNA KALEMI)", "G54", "G50 S2200", "G96 S180 M03",
        f"G00 X{od + 4.0:.1f} Z2.0 M08", "G01 Z0.0 F0.22", "G01 X-1.6 F0.18 (ALIN TEMIZLEME - DATUM A)",
        f"G00 X{od:.1f} Z2.0", f"G01 Z-{length:.1f} F0.22 (DIS CAP BOY TORNALAMA)", f"G00 X{od + 5.0:.1f} Z5.0", "",
        f"(--- IC CAP BARA / H7 GECME: CAP {id_bore:g}MM ---)", "T0303 (HASSAS IC CAP BARA KALEMI)",
        "G96 S150 M03", f"G00 X{max(10.0, id_bore - 2.0):.1f} Z2.0",
        f"G01 X{id_bore:.3f} Z0.0 F0.10", f"G01 Z-{length:.1f} F0.08", "G00 Z10.0 M09", "G28 U0.0 W0.0 M05",
    ]
    if holes:
        h = holes[0]
        r_pcd = round(pcd / 2.0, 2)
        lines.extend([
            "", f"(--- OP30: {h.quantity}x CAP {h.nominal:g}MM DELIK DELME DONGUSU - PCD {pcd:g} ---)",
            "T0505 (KARBUR MATKAP)", "G17 G94 G97 S1800 M03", f"G00 X{r_pcd:.2f} Y0.0 Z5.0 M08",
            f"G83 Z-{length + 2.0:.1f} R2.0 Q4.0 F160", f"X0.0 Y{r_pcd:.2f}", f"X-{r_pcd:.2f} Y0.0", f"X0.0 Y-{r_pcd:.2f}", "G80 Z25.0",
        ])
    if threads:
        lines.extend([
            "", f"(--- OP30: KILAVUZ CEKME - {threads[0].raw_text} ---)", "T0606 (HSS-E MAKINE KILAVUZU)",
            "G97 S400 M03", f"G84 Z-18.0 R3.0 F500 ({threads[0].raw_text})", "G80 G00 Z50.0 M09",
        ])
    lines.extend(["M30", "%"])
    return "\n".join(lines)
