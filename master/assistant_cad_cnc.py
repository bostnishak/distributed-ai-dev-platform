"""CAD/CAM, CNC Ballooning, Project Build detectors & deterministic extended calculation helpers for `assistant.py`."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import UploadFile

from workspace_batches import wants_single_html

CNC_BALLOON_KEYWORDS = (
    "balonla", "balonlama", "teknik çizim", "teknik cizim", "as9102", "fai",
    "tolerans tablosu", "cnc parça", "cnc parca", "cnc çizim", "cnc cizim",
    "ölçüleri çıkar", "olculeri cikar", "kalite kontrol formu",
)
_CNC_FAI_RE = re.compile(r"\bfai\b", re.IGNORECASE)

CODE_ONLY_RE = re.compile(
    r"(kodunu\s*(ver|yaz|göster|goster|at)|kod\s*halini|sadece\s*kod|kodu\s*(ver|yaz))",
    re.IGNORECASE,
)

_PAGE_NOUN_RE = re.compile(r"\b(?:tanıtım|açılış|karşılama|iniş|portfolyo)\s+sayfa(?:sı|s[ıi]n[ıi])?\b|\b(?:gösterge|gelir|satış|yönetim)\s+pano(?:su(?:nu)?)?\b|\blanding\s+page\b", re.IGNORECASE)

_NON_CODE_PROJECT_RE = re.compile(
    r"\b(?:"
    r"(?:diyet|ders|egzersiz|spor|antrenman|antreman|beslenme|çalışma|calisma|eğitim|egitim|"
    r"seyahat|tatil|gezi|etkinlik|toplantı|toplanti|staj|televizyon|tv|radyo|kurs|seminer|konferans)\s+program\w*"
    r"|proje\s*(?:rapor\w*|sunum\w*|özet\w*|ozet\w*|belge\w*|doküman\w*|dokuman\w*|öneri\w*|oneri\w*|metn\w*|teklif\w*|bütçe\w*|butce\w*|ödev\w*|odev\w*)"
    r")\b",
    re.IGNORECASE,
)

PROJECT_NOUN_RE = re.compile(
    r"(?:"
    r"\bweb\s*site\w*|\bwebsite\w*|\be-?ticaret|\boyun\w*|\bgames?\b|\bmasaüstü|\bmasaustu|"
    r"\bbilgisayarda\s*çalış\w*|\bbilgisayarda\s*calis\w*|\.exe\b|\bexe\b|"
    r"\buygulama\w*|\bapps?\b|\bapplication\w*|\bprogram\w*|"
    r"\bproje(?:si|yi|ye|de|den|ler\w*|m\w*)?\b|\bprojects?\b|"
    r"\bsite(?:si|yi|ye|de|den|ler\w*|m\w*)?\b|"
    r"\bklasör\s*yapı\w*|\bklasor\s*yapi\w*|\bdizin\s*yapı\w*|\bdizin\s*yapi\w*|\bfolder\s*structure\w*|"
    r"\bproje\s*klasör\w*|\bproje\s*klasor\w*|\bproje\s*dosyalar\w*|"
    r"\bapi\b|\bdashboard\w*|\bportf[öo]y\w*|\bportfolio\w*|\bblog(?:u|un|a|lar\w*|s)?\b|"
    r"\bbot(?:u|un|a|lar\w*)?\b|\bchatbot\w*|\bscripts?\b|\bhtml5\b"
    r")",
    re.IGNORECASE,
)

PROJECT_ACTION_RE = re.compile(
    r"\b(?:"
    r"yap(?:ar\w*|abil\w*|al[ıi]m|ın|iniz|mak|ma\b|ıyor\w*|iyor\w*|sana|sun|tır\w*|tir\w*)?|"
    r"oluştur\w*|olustur\w*|hazırla\w*|hazirla\w*|geliştir\w*|gelistir\w*|tasarla\w*|"
    r"kur(?:ar\w*|abil\w*|al[ıi]m|un|unuz|mak|ma\b|uyor\w*|sana|sun|ulum\w*)?|"
    r"üret\w*|uret\w*|kodla\w*|yaz(?:ar\w*|abil\w*|al[ıi]m|ın|ınız)?|"
    r"build(?:ing|s)?|creat(?:e|es|ing)|generat(?:e|es|ing)|mak(?:e|es|ing)|scaffold(?:ing|s)?"
    r")\b",
    re.IGNORECASE,
)

ZIP_INSPECT_RE = re.compile(
    r"\b(?:incele\w*|bak\b|bakalım|bakalim|özet\w*|ozet\w*|hatalar\w*|hata\s*bul\w*|bug\w*|"
    r"analiz\w*|açıkla\w*|acikla\w*|anlat\w*|nedir|ne\s*yapıyor|ne\s*yapiyor|oku\b|göster\w*|goster\w*|"
    r"summarize\w*|inspect\w*|review\w*|explain\w*|find\s+bugs?)\b",
    re.IGNORECASE,
)

_ZIP_WORKSPACE_EDIT_RE = re.compile(
    r"\b(?:çalışma\s*alan\w*|calisma\s*alan\w*|workspace|içe\s*aktar\w*|ice\s*aktar\w*|"
    r"aç|ac|geliştir\w*|gelistir\w*|düzenle\w*|duzenle\w*|exe|derle\w*|çalıştır\w*|calistir\w*|ekle|ekley\w*)\b",
    re.IGNORECASE,
)

_ZIP_EXPLICIT_IMPORT_RE = re.compile(
    r"\b(?:workspace|çalışma\s*alan\w*|calisma\s*alan\w*|içe\s*aktar\w*|ice\s*aktar\w*|exe|derle\w*)\b",
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
    if any(kw in lower for kw in CNC_BALLOON_KEYWORDS if kw != "fai"):
        return True
    return bool(_CNC_FAI_RE.search(lower))


def is_3d_cad_request(file: UploadFile | None) -> bool:
    if file is None or not file.filename:
        return False
    return file.filename.lower().endswith((".step", ".stp", ".iges", ".igs", ".stl"))


def is_zip_workspace_request(prompt: str, file: UploadFile | None) -> bool:
    if file is None or not file.filename or not file.filename.lower().endswith(".zip"):
        return False
    lower = prompt.lower()
    if ZIP_INSPECT_RE.search(lower) and not _ZIP_EXPLICIT_IMPORT_RE.search(lower):
        return False
    return bool(_ZIP_WORKSPACE_EDIT_RE.search(lower))


def is_project_build_request(prompt: str, file: UploadFile | None) -> bool:
    if file is not None and file.filename:
        return False
    lower = re.sub(r"<[^>]*>|```.*?```|`[^`]*`", " ", prompt.lower(), flags=re.S).strip()  # markup/code in the message is not a project noun
    if CODE_ONLY_RE.search(lower):
        return False
    if any(
        q in lower
        for q in (
            "nedir", "ne demek", "açıkla", "acikla", "farkı ne", "farki ne",
            "nasıl yapılır", "nasil yapilir", "nasıl oluşturulur", "nasil olusturulur", "how to ",
        )
    ):
        return False
    cleaned = _NON_CODE_PROJECT_RE.sub(" ", lower)
    named = PROJECT_NOUN_RE.search(cleaned) or wants_single_html(prompt) or _PAGE_NOUN_RE.search(cleaned)
    return bool(named and PROJECT_ACTION_RE.search(cleaned))


def detect_project_type(prompt: str) -> tuple[str, bool]:
    """Return (project_type, wants_exe) for a project build prompt."""
    lower = prompt.lower()
    if wants_single_html(prompt):
        return "web", False
    # "masaüstünde 260px" is responsive layout, not a request for a desktop program
    wants_exe = bool(re.search(r"(?:\.exe\b|\bexe\b|\b(?:masaüstü|masaustu) (?:için|icin|uygulama|program|oyun|yazılım)|\bbilgisayarda\b|\bdesktop (?:app|application|program|game))", lower))
    explicit_py_desktop = wants_exe or bool(re.search(r"\b(?:python|tkinter|pygame)\b", lower))
    is_fullstack = bool(
        re.search(r"\b(?:fullstack|full[\s-]stack|fastapi|backend|rest\s*api|api|flask|django|veritabanı|veritabani)\b", re.sub(r'"[^"\n]*"', " ", lower))  # quoted sample data ("API Gateway") is not a requirement
    )
    is_cli = bool(re.search(r"\b(?:cli|terminal|komut\s*satır\w*|komut\s*satir\w*|konsol|scripts?|bot)\b", lower))
    is_game = bool(re.search(r"\b(?:oyun\w*|games?|arcade|snake|yılan|yilan|tetris|pong)\b", lower))
    is_web = bool(re.search(r"\b(?:web|site\w*|e-?ticaret|eticaret|html5?|tarayıcı|tarayici|dashboard|portf[öo]y|portfolio|blog)\b", lower))

    if is_fullstack and not wants_exe:
        return "fullstack", False
    if is_cli and not is_web and not is_game and not wants_exe:
        return "cli", False
    if is_game:
        return ("game", wants_exe) if explicit_py_desktop else ("web", False)
    if explicit_py_desktop and not (is_web and not wants_exe):
        return "desktop", wants_exe
    return "web", False


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
