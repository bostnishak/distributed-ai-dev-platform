"""CAD/CAM, CNC Ballooning, Project Build detectors & deterministic extended calculation helpers for `assistant.py`."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import UploadFile

CNC_BALLOON_KEYWORDS = (
    "balonla", "balonlama", "teknik çizim", "teknik cizim", "as9102", "fai",
    "tolerans tablosu", "cnc parça", "cnc parca", "cnc çizim", "cnc cizim",
    "ölçüleri çıkar", "olculeri cikar", "kalite kontrol formu",
)

CODE_ONLY_RE = re.compile(
    r"(kodunu\s*(ver|yaz|göster|goster|at)|kod\s*halini|sadece\s*kod|kodu\s*(ver|yaz))",
    re.IGNORECASE,
)

PROJECT_NOUN_RE = re.compile(
    r"(web\s*site\w*|e-?ticaret|oyun\w*|masaüstü|masaustu|bilgisayarda\s*çalış\w*|bilgisayarda\s*calis\w*|"
    r"\.exe|\bexe\b|uygulama\w*|program\w*|proje\w*|site\w*|dosyalar\w*)",
    re.IGNORECASE,
)

PROJECT_ACTION_RE = re.compile(
    r"(yap\w*|oluştur\w*|olustur\w*|hazırla\w*|hazirla\w*|geliştir\w*|gelistir\w*|tasarla\w*|kur\w*|üret\w*|uret\w*)",
    re.IGNORECASE,
)

_UNIT_FACTORS: dict[tuple[str, str], float] = {
    ("km", "m"): 1000.0, ("m", "km"): 0.001,
    ("m", "cm"): 100.0, ("cm", "m"): 0.01,
    ("cm", "mm"): 10.0, ("mm", "cm"): 0.1,
    ("m", "mm"): 1000.0, ("mm", "m"): 0.001,
    ("kg", "g"): 1000.0, ("g", "kg"): 0.001,
    ("gb", "mb"): 1024.0, ("mb", "gb"): 1.0 / 1024.0,
}


def is_cnc_balloon_request(prompt: str, file: UploadFile | None) -> bool:
    if file is None or not file.filename:
        return False
    if file.filename.lower().endswith(".dxf"):
        return True
    lower = prompt.lower()
    return any(kw in lower for kw in CNC_BALLOON_KEYWORDS)


def is_3d_cad_request(file: UploadFile | None) -> bool:
    if file is None or not file.filename:
        return False
    return file.filename.lower().endswith((".step", ".stp", ".iges", ".igs", ".stl"))


def is_zip_workspace_request(prompt: str, file: UploadFile | None) -> bool:
    if file is None or not file.filename or not file.filename.lower().endswith(".zip"):
        return False
    lower = prompt.lower()
    return any(
        k in lower
        for k in ("proje", "aç", "ac", "geliştir", "gelistir", "düzenle", "duzenle", "exe", "çalıştır", "calistir", "kod", "ekle")
    )


def is_project_build_request(prompt: str, file: UploadFile | None) -> bool:
    if file is not None and file.filename:
        return False
    lower = prompt.lower().strip()
    if CODE_ONLY_RE.search(lower):
        return False
    if any(q in lower for q in ("nedir", "ne demek", "açıkla", "acikla", "farkı ne", "farki ne")):
        return False
    return bool(PROJECT_NOUN_RE.search(lower) and PROJECT_ACTION_RE.search(lower))


def detect_project_type(prompt: str) -> tuple[str, bool]:
    """Return (project_type, wants_exe) for a project build prompt."""
    lower = prompt.lower()
    is_web = any(k in lower for k in ("web", "site", "e-ticaret", "eticaret", "html", "tarayıcı", "tarayici"))
    is_game = any(k in lower for k in ("oyun", "game", "arcade", "snake", "yılan", "tetris"))
    is_desktop = any(k in lower for k in ("bilgisayarda", "masaüstü", "masaustu", "exe", "uygulama", "program"))
    if is_web and not any(k in lower for k in ("exe", "bilgisayarda", "masaüstü")):
        return "web", False
    if is_game:
        return "game", True
    if is_desktop:
        return "desktop", True
    return "auto", False


def _calc_compound_or_kdv(low: str) -> str | None:
    m_ci = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:tl|usd|eur|\$|€)?\s*%(\d+(?:[.,]\d+)?)\s*(\d+)\s*(?:yıl|yil|year).*bileşik\s*faiz",
        low,
    )
    if m_ci:
        p = Decimal(m_ci.group(1).replace(",", "."))
        r = Decimal(m_ci.group(2).replace(",", ".")) / Decimal("100")
        n = int(m_ci.group(3))
        total = (p * ((Decimal("1") + r) ** n)).quantize(Decimal("0.01"))
        return f"Bileşik faiz ({p} x (1 + {r})^{n}) = {total}"

    m_kdv = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:tl|₺)?\s*%(\d+(?:[.,]\d+)?)\s*kdv", low)
    if m_kdv:
        base = Decimal(m_kdv.group(1).replace(",", "."))
        rate = Decimal(m_kdv.group(2).replace(",", ".")) / Decimal("100")
        kdv = (base * rate).quantize(Decimal("0.01"))
        return f"KDV (%{m_kdv.group(2)}): {kdv}, Toplam = {(base + kdv).quantize(Decimal('0.01'))}"

    m_pct = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:'?[ıiuü]n)?\s*%(\d+(?:[.,]\d+)?)", low)
    if m_pct:
        val = Decimal(m_pct.group(1).replace(",", "."))
        pct = Decimal(m_pct.group(2).replace(",", "."))
        res = val * pct / Decimal("100")
        res_s = format(res, "f").rstrip("0").rstrip(".") if "." in format(res, "f") else format(res, "f")
        return f"{val} x %{pct} = {res_s}"
    return None


def _calc_date_or_unit(low: str) -> str | None:
    m_date = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})", low)
    if m_date and any(k in low for k in ("gün", "gun", "days", "fark")):
        try:
            d1, d2 = date.fromisoformat(m_date.group(1)), date.fromisoformat(m_date.group(2))
            return f"{d1.isoformat()} .. {d2.isoformat()} = {abs((d2 - d1).days)} gün"
        except ValueError:
            return None

    m_unit = re.search(
        r"(-?\d+(?:[.,]\d+)?)\s*(km|m|cm|mm|kg|g|gb|mb|c|f)\s*(?:kaç|kac|to|->)\s*(km|m|cm|mm|kg|g|gb|mb|c|f)\b",
        low,
    )
    if not m_unit:
        return None
    val = float(m_unit.group(1).replace(",", "."))
    u_from, u_to = m_unit.group(2), m_unit.group(3)
    if (u_from, u_to) in _UNIT_FACTORS:
        out = round(val * _UNIT_FACTORS[(u_from, u_to)], 6)
        return f"{val:g} {u_from} = {int(out) if float(out).is_integer() else out} {u_to}"
    if (u_from, u_to) == ("c", "f"):
        return f"{val:g} C = {round(val * 9.0 / 5.0 + 32.0, 2)} F"
    if (u_from, u_to) == ("f", "c"):
        return f"{val:g} F = {round((val - 32.0) * 5.0 / 9.0, 2)} C"
    return None


def try_extended_calculation(prompt: str) -> str | None:
    """DEF-22: Deterministic percentages, KDV, unit conversions, date diffs, and compound interest."""
    raw = prompt.strip()
    if not raw or len(raw) > 200:
        return None
    low = raw.lower()
    return _calc_compound_or_kdv(low) or _calc_date_or_unit(low)


async def run_3d_cad_cam_from_chat(file: UploadFile, prompt: str) -> str:
    """Execute 3D STEP/IGES/STL Feature Recognition, Kienzle Cutting Physics, FEA & 4-Controller G-Code Engine."""
    import cad_cam_physics as ccp
    import enterprise_security_mcp as esm

    raw = await file.read()
    fname = file.filename or "part.step"
    cad = ccp.analyze_3d_cad_file(fname, raw)
    bbox = cad.get("bounding_box_mm", {})
    dx, dy, dz = float(bbox.get("x", 60.0)), float(bbox.get("y", 60.0)), float(bbox.get("z", 40.0))

    lower = prompt.lower()
    material = next(
        (m for m in ("AL 7075", "AL 6061", "AISI 316L", "AISI 304", "TI-6AL-4V", "AISI 1045", "AISI 4140")
         if m.lower() in lower or m.split()[-1].lower() in lower),
        "AISI 4140",
    )
    phys = ccp.simulate_cutting_physics_and_fea(
        material=material,
        vc_m_min=185.0 if "4140" in material else 240.0,
        ap_mm=2.5,
        feed_mm_rev=0.22,
        cutter_diameter_mm=max(dx, dy, 25.0),
        tool_stickout_mm=min(max(dz * 0.9, 35.0), 75.0),
        tool_shank_diameter_mm=16.0,
        ring_mean_radius_mm=max(dx, dy) / 2.0,
        wall_thickness_mm=3.0,
    )
    spec = {
        "part_number": cad.get("product_name") or fname, "material": material,
        "outer_diameter_mm": round(max(dx, dy), 2), "finish_od_mm": round(max(dx, dy) - 2.0, 2),
        "length_mm": round(dz, 2), "hole_diameter_mm": 12.0,
        "hole_depth_mm": round(min(dz * 0.8, 35.0), 2), "thread_pitch_mm": 1.5,
        "thread_depth_mm": round(min(dz * 0.5, 20.0), 2), "vc_m_min": 185,
    }
    gcodes = {c: ccp.generate_multi_controller_gcode(c, spec) for c in ("fanuc", "siemens", "heidenhain", "haas")}
    cmm_offset = ccp.generate_cmm_wear_offset_gcode(
        controller="fanuc", tool_no=2, nominal=spec["finish_od_mm"], measured_mean=round(spec["finish_od_mm"] + 0.014, 4)
    )
    esm.AuditTrail().append_event(
        actor="assistant_3d_cad", action="3D_CAD_CAM_ANALYSIS",
        payload={"filename": fname, "format": cad.get("format"), "features": len(cad.get("features", []))},
    )
    meta = {"fname": fname, "cad": cad, "material": material, "dims": (dx, dy, dz)}
    return _format_3d_cad_report(meta, phys, cmm_offset, gcodes)


def _format_3d_cad_report(
    meta: dict[str, Any], phys: dict[str, Any], cmm_offset: dict[str, Any], gcodes: dict[str, str],
) -> str:
    fname, cad, material = meta["fname"], meta["cad"], meta["material"]
    dx, dy, dz = meta["dims"]
    lines = [
        f"## 3B CAD B-Rep Unsur Tanima, Kesme Fizigi ve Coklu Kontrolcu CAM Raporu ({fname})",
        f"- **Format:** `{cad.get('format')}` | **Urun:** `{cad.get('product_name')}` | **Malzeme:** `{material}`",
        f"- **Sinirlayici Kutu (Bounding Box):** `{dx} x {dy} x {dz} mm` | **Hacim:** `{cad.get('volume_cm3')} cm3` | **Yuzey Alani:** `{cad.get('surface_area_cm2')} cm2`",
        "",
        "### 1. Taninan 3B Geometrik Unsurlar ve 2B-3B MBD Balon Eslestirmesi",
        "| Balon No | Unsur Kimligi | Unsur Tipi | B-Rep Yuzey | Gorunus | Nominal Olcu (mm) | Tolerans Sinifi |",
        "|---|---|---|---|---|---|---|",
        *(
            f"| **#{m['balloon_no']}** | `{m['feature_id']}` | **{m['feature_type']}** | `{m['face_id']}` | "
            f"{m['view']} | `{m['nominal_mm']}` | `{m['tolerance']}` |"
            for m in cad.get("mbd_2d_3d_matches", [])
        ),
        "",
        "### 2. Kienzle Kesme Kuvveti, Takim Sehimi ve 3 Ayakli Ayna FEA Ovalizasyon Analizi",
        "| Tegetsel Kuvvet (Fc) | Radyal Kuvvet (Fr) | Is Mili Gucu (Pc) | Tork | Taylor Takim Omru | Takim Sehimi (delta) | Ayna Ovalizasyonu | Yuzey Puruzlulugu (Ra) |",
        "|---|---|---|---|---|---|---|---|",
        f"| **{phys['cutting_force_fc_n']} N** | {phys['radial_force_fr_n']} N | **{phys['spindle_power_kw']} kW** | "
        f"{phys['spindle_torque_nm']} Nm | **{phys['taylor_tool_life_min']} dk** | `{phys['tool_deflection_mm']} mm` | "
        f"`{phys['chuck_ovalization_mm']} mm` | **Ra {phys['surface_roughness_ra_um']} um** |",
    ]
    if phys.get("dfm_warnings"):
        lines.extend(["", "#### Fiziksel DFM ve Titresim (Chatter) Uyarilari", *(f"- {w}" for w in phys["dfm_warnings"])])
    lines.extend([
        "",
        "### 3. Kapali Cevrim CMM Asinma Ofset Telafisi (Closed-Loop G10)",
        f"- **Olculen Ortalama Sapma:** `{cmm_offset['deviation_mm']:+.4f} mm` -> **Otomatik Ofset Komutu:** `{cmm_offset['offset_gcode']}` (Cp: `{cmm_offset['spc']['cp']}`, Cpk: `{cmm_offset['spc']['cpk']}`)",
        "",
        "### 4. Coklu Tezgah Kontrolcu Post-Processor Ciktisi (4 Diyalekt)",
        f"#### A) Fanuc 0i / 31i ISO G-Kodu\n```gcode\n{gcodes['fanuc']}\n```",
        f"#### B) Siemens Sinumerik 840D / ONE\n```gcode\n{gcodes['siemens']}\n```",
        f"#### C) Heidenhain TNC 640 Diyalog Programi\n```gcode\n{gcodes['heidenhain']}\n```",
        f"#### D) Haas NGC G-Kodu\n```gcode\n{gcodes['haas']}\n```",
    ])
    return "\n".join(lines)


async def run_cnc_balloon_from_chat(file: UploadFile) -> str:
    """Execute the full Senior Mechanical Engineer CNC ballooning pipeline directly from Chat."""
    import cnc_api

    job: dict[str, Any] = await cnc_api.create_balloon_job(
        file=file, part_number="", part_name="", material="", revision="", standard="", model=""
    )
    jid = job["id"]
    meta: dict[str, Any] = job.get("metadata") or {}
    balloons: list[dict[str, Any]] = job.get("balloons") or []
    plan: dict[str, Any] = job.get("manufacturing_plan") or {}
    summary: dict[str, Any] = plan.get("summary") or {}
    lines = [
        f"## CNC Teknik Çizim Balonlama ve İmalat Raporu ({meta.get('part_number') or job['filename']})",
        f"- **Parça:** {meta.get('part_name') or job['filename']} · **Malzeme:** {meta.get('material') or '-'} · **Standart:** {meta.get('standard') or 'ISO 2768-mK'}",
        f"- **Tespit Edilen Karakteristik:** {len(balloons)} adet (**Kritik:** {summary.get('critical', 0)} · **Majör:** {summary.get('major', 0)} · **Minör:** {summary.get('minor', 0)}) · **Motor:** `{job.get('engine_used', '')}`",
        "", f"![Balonlanmış Teknik Çizim](/api/cnc/jobs/{jid}/file/ballooned.png)", "",
        "### Raporları İndir (AS9102 / FAI Paketi)",
        f"- [AS9102 Excel Raporu (.xlsx)](/api/cnc/jobs/{jid}/file/report.xlsx)",
        f"- [Mühendislik Word Raporu (.docx)](/api/cnc/jobs/{jid}/file/report.docx)",
        f"- [Balonlu PDF Çizim + Tablo (.pdf)](/api/cnc/jobs/{jid}/file/ballooned.pdf)",
        f"- [Yüksek Çözünürlüklü Balonlu PNG](/api/cnc/jobs/{jid}/file/ballooned.png)", "",
        "### AS9102 Form 3 - Karakteristik, Operasyon ve Ölçüm Tablosu",
        "| No | Bölge | Ölçü | Kategori | Min / Max | Operasyon | Kesici Takım | Ölçüm Ekipmanı | Sıklık | Kritiklik |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for b in balloons:
        mm = f"{b['min_limit']} / {b['max_limit']}" if (b.get("min_limit") is not None and b.get("max_limit") is not None) else "-"
        lines.append(
            f"| **{b['balloon_no']}** | {b.get('zone', '-')} | `{b['raw_text']}` | {b['category']} | {mm} | "
            f"{b.get('operation', '-')} | {b.get('tooling', '-')} | {b.get('gage', '-')} | "
            f"{b.get('inspection_freq', '-')} | {b.get('criticality', 'Majör')} |"
        )
    _append_cnc_plan_sections(lines, plan)
    return "\n".join(lines)


def _append_cnc_plan_sections(lines: list[str], plan: dict[str, Any]) -> None:
    cp: dict[str, Any] = plan.get("cutting_parameters") or {}
    ops = plan.get("operations") or []
    if ops:
        lines.extend(["", "### CNC İmalat Proses Rotası (OP10-OP50) ve Kesme Parametreleri"])
        if cp:
            lines.extend([
                f"- **Malzeme Grubu:** {cp.get('group', '-')} · **Torna Vc:** {cp.get('vc_turn', '-')} · "
                f"**Freze Vc:** {cp.get('vc_mill', '-')} · **İlerleme:** {cp.get('feed', '-')} · **Soğutma:** {cp.get('coolant', '-')}",
                "",
            ])
        lines.extend(["| OP | Operasyon | Tezgâh | Bağlama / Fikstür | Balonlar |", "|---|---|---|---|---|"])
        for op in ops:
            blist = ", ".join(f"#{n}" for n in (op.get("balloons") or [])) or "Genel"
            lines.append(f"| **{op['op']}** | {op['name']} | {op['machine']} | {op['fixture']} | {blist} |")
    if plan.get("dfm_risks"):
        lines.extend(["", "### DFM ve Kritik Kalite Risk Uyarıları", *(f"- {r}" for r in plan["dfm_risks"])])
    ce = plan.get("cost_estimate") or {}
    if ce:
        bd = ce.get("breakdown_min") or {}
        lines.extend([
            "", "### Otomatik Maliyet, İşleme Süresi ve Teklif Özeti",
            "| Kütük Boyutu | Ham / Net Ağırlık | Parça Başı Süre (Cycle) | 1 Adet (Prototip) | 10 Adet Birim | 100 Adet (Seri) |",
            "|---|---|---|---|---|---|",
            f"| `{ce.get('stock_dimensions', '-')}` | {ce.get('raw_weight_kg', 0)} kg / {ce.get('net_weight_kg', 0)} kg | "
            f"**{ce.get('cycle_time_min', 0)} dk** (Torna/Freze: {bd.get('turn_mill', 0)} dk, Delik/Diş: {bd.get('drill_tap', 0)} dk, Kalite: {bd.get('quality_cmm', 0)} dk) | "
            f"**{ce.get('unit_quote_1_tl', 0)} TL** | **{ce.get('unit_quote_10_tl', 0)} TL** | **{ce.get('unit_quote_100_tl', 0)} TL** |",
        ])
    if plan.get("gcode_template"):
        lines.extend(["", "### Başlangıç Fanuc ISO G-Kodu Taslağı", f"```gcode\n{plan['gcode_template']}\n```"])
