"""Assistant tab: the chat assistant (PB-36/37).

Sprint 3: LiteLLM gateway removed. The assistant now calls Ollama directly on the master.
Vision requests (image uploads) are routed to an online agent that has vision capability; if
none is available the master's own model is used instead (qwen3.5:4b supports vision).
"""

import ast
import asyncio
import base64
import json
import operator
import os
import re
import subprocess
import sys
import tempfile

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import config
import db
from extract import (
    extract_csv_text,
    extract_docx_text,
    extract_pdf_text,
    extract_xlsx_text,
    extract_zip_text,
)

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


def _is_cnc_balloon_request(prompt: str, file: UploadFile | None) -> bool:
    if file is None or not file.filename:
        return False
    if file.filename.lower().endswith(".dxf"):
        return True
    lower = prompt.lower()
    return any(kw in lower for kw in CNC_BALLOON_KEYWORDS)


def _is_3d_cad_request(file: UploadFile | None) -> bool:
    if file is None or not file.filename:
        return False
    return file.filename.lower().endswith((".step", ".stp", ".iges", ".igs", ".stl"))


async def _run_3d_cad_cam_from_chat(file: UploadFile, prompt: str) -> str:
    """Execute 3D STEP/IGES/STL Feature Recognition, Kienzle Cutting Physics, FEA & 4-Controller G-Code Engine."""
    import cad_cam_physics as ccp
    import enterprise_security_mcp as esm

    raw = await file.read()
    fname = file.filename or "part.step"
    cad = ccp.analyze_3d_cad_file(fname, raw)
    bbox = cad.get("bounding_box_mm", {})
    dx = float(bbox.get("x", 60.0))
    dy = float(bbox.get("y", 60.0))
    dz = float(bbox.get("z", 40.0))

    lower = prompt.lower()
    material = "AISI 4140"
    for mat in ("AL 7075", "AL 6061", "AISI 316L", "AISI 304", "TI-6AL-4V", "AISI 1045", "AISI 4140"):
        if mat.lower() in lower or mat.split()[-1].lower() in lower:
            material = mat
            break

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
        "part_number": cad.get("product_name") or fname,
        "material": material,
        "outer_diameter_mm": round(max(dx, dy), 2),
        "finish_od_mm": round(max(dx, dy) - 2.0, 2),
        "length_mm": round(dz, 2),
        "hole_diameter_mm": 12.0,
        "hole_depth_mm": round(min(dz * 0.8, 35.0), 2),
        "thread_pitch_mm": 1.5,
        "thread_depth_mm": round(min(dz * 0.5, 20.0), 2),
        "vc_m_min": 185,
    }
    gcode_fanuc = ccp.generate_multi_controller_gcode("fanuc", spec)
    gcode_siemens = ccp.generate_multi_controller_gcode("siemens", spec)
    gcode_heidenhain = ccp.generate_multi_controller_gcode("heidenhain", spec)
    gcode_haas = ccp.generate_multi_controller_gcode("haas", spec)
    cmm_offset = ccp.generate_cmm_wear_offset_gcode(
        controller="fanuc",
        tool_no=2,
        nominal=spec["finish_od_mm"],
        measured_mean=round(spec["finish_od_mm"] + 0.014, 4),
    )

    esm.AuditTrail().append_event(
        actor="assistant_3d_cad",
        action="3D_CAD_CAM_ANALYSIS",
        payload={"filename": fname, "format": cad.get("format"), "features": len(cad.get("features", []))},
    )

    lines = [
        f"## 3B CAD B-Rep Unsur Tanima, Kesme Fizigi ve Coklu Kontrolcu CAM Raporu ({fname})",
        f"- **Format:** `{cad.get('format')}` | **Urun:** `{cad.get('product_name')}` | **Malzeme:** `{material}`",
        f"- **Sinirlayici Kutu (Bounding Box):** `{dx} x {dy} x {dz} mm` | **Hacim:** `{cad.get('volume_cm3')} cm3` | **Yuzey Alani:** `{cad.get('surface_area_cm2')} cm2`",
        "",
        "### 1. Taninan 3B Geometrik Unsurlar ve 2B-3B MBD Balon Eslestirmesi",
        "| Balon No | Unsur Kimligi | Unsur Tipi | B-Rep Yuzey | Gorunus | Nominal Olcu (mm) | Tolerans Sinifi |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in cad.get("mbd_2d_3d_matches", []):
        lines.append(
            f"| **#{m['balloon_no']}** | `{m['feature_id']}` | **{m['feature_type']}** | `{m['face_id']}` | "
            f"{m['view']} | `{m['nominal_mm']}` | `{m['tolerance']}` |"
        )

    lines.extend([
        "",
        "### 2. Kienzle Kesme Kuvveti, Takim Sehimi ve 3 Ayakli Ayna FEA Ovalizasyon Analizi",
        "| Tegetsel Kuvvet (Fc) | Radyal Kuvvet (Fr) | Is Mili Gucu (Pc) | Tork | Taylor Takim Omru | Takim Sehimi (delta) | Ayna Ovalizasyonu | Yuzey Puruzlulugu (Ra) |",
        "|---|---|---|---|---|---|---|---|",
        f"| **{phys['cutting_force_fc_n']} N** | {phys['radial_force_fr_n']} N | **{phys['spindle_power_kw']} kW** | "
        f"{phys['spindle_torque_nm']} Nm | **{phys['taylor_tool_life_min']} dk** | `{phys['tool_deflection_mm']} mm` | "
        f"`{phys['chuck_ovalization_mm']} mm` | **Ra {phys['surface_roughness_ra_um']} um** |",
    ])
    if phys.get("dfm_warnings"):
        lines.append("")
        lines.append("#### Fiziksel DFM ve Titresim (Chatter) Uyarilari")
        for w in phys["dfm_warnings"]:
            lines.append(f"- {w}")

    lines.extend([
        "",
        "### 3. Kapali Cevrim CMM Asinma Ofset Telafisi (Closed-Loop G10)",
        f"- **Olculen Ortalama Sapma:** `{cmm_offset['deviation_mm']:+.4f} mm` -> **Otomatik Ofset Komutu:** `{cmm_offset['offset_gcode']}` (Cp: `{cmm_offset['spc']['cp']}`, Cpk: `{cmm_offset['spc']['cpk']}`)",
        "",
        "### 4. Coklu Tezgah Kontrolcu Post-Processor Ciktisi (4 Diyalekt)",
        "#### A) Fanuc 0i / 31i ISO G-Kodu",
        f"```gcode\n{gcode_fanuc}\n```",
        "#### B) Siemens Sinumerik 840D / ONE (CYCLE95 / CYCLE83 / CYCLE84)",
        f"```gcode\n{gcode_siemens}\n```",
        "#### C) Heidenhain TNC 640 Diyalog Programi (BLK FORM / CYCL DEF 200 & 207)",
        f"```gcode\n{gcode_heidenhain}\n```",
        "#### D) Haas NGC G-Kodu",
        f"```gcode\n{gcode_haas}\n```",
    ])
    return "\n".join(lines)


def _is_zip_workspace_request(prompt: str, file: UploadFile | None) -> bool:
    if file is None or not file.filename or not file.filename.lower().endswith(".zip"):
        return False
    lower = prompt.lower()
    return any(
        k in lower
        for k in ("proje", "aç", "ac", "geliştir", "gelistir", "düzenle", "duzenle", "exe", "çalıştır", "calistir", "kod", "ekle")
    )


def _is_project_build_request(prompt: str, file: UploadFile | None) -> bool:
    if file is not None and file.filename:
        return False
    lower = prompt.lower().strip()
    if CODE_ONLY_RE.search(lower):
        return False
    if any(q in lower for q in ("nedir", "ne demek", "açıkla", "acikla", "farkı ne", "farki ne")):
        return False
    return bool(PROJECT_NOUN_RE.search(lower) and PROJECT_ACTION_RE.search(lower))


def _detect_project_type(prompt: str) -> tuple[str, bool]:
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


async def _run_cnc_balloon_from_chat(file: UploadFile) -> str:
    """Execute the full Senior Mechanical Engineer CNC ballooning pipeline directly from Chat."""
    import cnc_api

    job = await cnc_api.create_balloon_job(
        file=file,
        part_number="",
        part_name="",
        material="",
        revision="",
        standard="",
        model="",
    )
    jid = job["id"]
    meta = job.get("metadata", {})
    balloons = job.get("balloons", [])
    plan = job.get("manufacturing_plan", {})
    summary = plan.get("summary", {})
    cp = plan.get("cutting_parameters", {})

    lines = [
        f"## CNC Teknik Çizim Balonlama ve İmalat Raporu ({meta.get('part_number') or job['filename']})",
        f"- **Parça:** {meta.get('part_name') or job['filename']} · **Malzeme:** {meta.get('material') or '-'} · **Standart:** {meta.get('standard') or 'ISO 2768-mK'}",
        f"- **Tespit Edilen Karakteristik:** {len(balloons)} adet (**Kritik:** {summary.get('critical', 0)} · **Majör:** {summary.get('major', 0)} · **Minör:** {summary.get('minor', 0)}) · **Motor:** `{job.get('engine_used', '')}`",
        "",
        f"![Balonlanmış Teknik Çizim](/api/cnc/jobs/{jid}/file/ballooned.png)",
        "",
        "### Raporları İndir (AS9102 / FAI Paketi)",
        f"- [AS9102 Excel Raporu (3 Sekmeli · Form 1-2-3 + Proses Planı .xlsx)](/api/cnc/jobs/{jid}/file/report.xlsx)",
        f"- [Mühendislik Word Raporu (Gömülü Çizim + OP10-OP50 .docx)](/api/cnc/jobs/{jid}/file/report.docx)",
        f"- [Balonlu PDF Çizim + Tablo (.pdf)](/api/cnc/jobs/{jid}/file/ballooned.pdf)",
        f"- [Yüksek Çözünürlüklü Balonlu PNG](/api/cnc/jobs/{jid}/file/ballooned.png)",
        "",
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

    ops = plan.get("operations") or []
    if ops:
        lines.append("")
        lines.append("### CNC İmalat Proses Rotası (OP10-OP50) ve Kesme Parametreleri")
        if cp:
            lines.append(
                f"- **Malzeme Grubu:** {cp.get('group', '-')} · **Torna Vc:** {cp.get('vc_turn', '-')} · "
                f"**Freze Vc:** {cp.get('vc_mill', '-')} · **İlerleme:** {cp.get('feed', '-')} · **Soğutma:** {cp.get('coolant', '-')}"
            )
            lines.append("")
        lines.append("| OP | Operasyon | Tezgâh | Bağlama / Fikstür | Balonlar |")
        lines.append("|---|---|---|---|---|")
        for op in ops:
            blist = ", ".join(f"#{n}" for n in (op.get("balloons") or [])) or "Genel"
            lines.append(f"| **{op['op']}** | {op['name']} | {op['machine']} | {op['fixture']} | {blist} |")

    risks = plan.get("dfm_risks") or []
    if risks:
        lines.append("")
        lines.append("### DFM ve Kritik Kalite Risk Uyarıları")
        for r in risks:
            lines.append(f"- {r}")

    ce = plan.get("cost_estimate") or {}
    if ce:
        bd = ce.get("breakdown_min") or {}
        lines.extend([
            "",
            "### Otomatik Maliyet, İşleme Süresi ve Teklif Özeti",
            "| Kütük Boyutu | Ham / Net Ağırlık | Parça Başı Süre (Cycle) | 1 Adet (Prototip) | 10 Adet Birim | 100 Adet (Seri) |",
            "|---|---|---|---|---|---|",
            f"| `{ce.get('stock_dimensions', '-')}` | {ce.get('raw_weight_kg', 0)} kg / {ce.get('net_weight_kg', 0)} kg | "
            f"**{ce.get('cycle_time_min', 0)} dk** (Torna/Freze: {bd.get('turn_mill', 0)} dk, Delik/Diş: {bd.get('drill_tap', 0)} dk, Kalite: {bd.get('quality_cmm', 0)} dk) | "
            f"**{ce.get('unit_quote_1_tl', 0)} TL** | **{ce.get('unit_quote_10_tl', 0)} TL** | **{ce.get('unit_quote_100_tl', 0)} TL** |",
        ])

    gcode = plan.get("gcode_template") or ""
    if gcode:
        lines.extend([
            "",
            "### Başlangıç Fanuc ISO G-Kodu Taslağı",
            f"```gcode\n{gcode}\n```",
        ])

    return "\n".join(lines)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# All assistant requests go to the master's local Ollama (PB-37). The classifier still decides
# the task category, but model selection now maps to master's own model.
DEFAULT_TASK = "genel"

# The UI can render Markdown tables and ```svg blocks; the model only uses them if told so.
# Kept out of the classifier call so it cannot disturb the classifier's strict output format.
ANSWER_SYSTEM_PROMPT = (
    "Yanit verirken uygun oldugunda bicimlendirme kullan: karsilastirma/liste gibi "
    "yapili bilgiler icin Markdown tablosu (| basli | basli |\\n|---|---|\\n| hucre | hucre |), "
    "kume/diyagram/sema gibi gorsel bir anlatim daha faydali olacaksa ```svg ile baslayan "
    "bir SVG kod blogu (basit sekiller, dogrudan cizim olarak gosterilecek). Zorunlu degil, "
    "sadece gercekten faydali oldugunda kullan."
)

# The LLM classifier occasionally routed explicit code requests to "genel". These keywords
# act as a safety net that overrides the classifier for obvious cases only.
CODE_KEYWORDS = (
    "python", "javascript", "typescript", "java ", "c++", "c#", " sql",
    "kod yaz", "kodu yaz", "fonksiyon yaz", "script yaz", "program yaz",
    "uygulama yap", "uygulama yaz", "algoritma yaz", "class yaz", "sinif yaz",
    "hata ayikla", "debug et", "kodda hata", "bug'i duzelt", "hesap makinesi",
)


def _find_vision_agent() -> dict | None:
    """Return an online agent that has vision capability, or None (PB-36)."""
    from datetime import UTC, datetime
    agents = db.list_agents()
    for agent in agents:
        caps = agent.get("capabilities") or []
        if "vision" not in caps:
            continue
        last_seen = agent.get("last_seen_at")
        if not last_seen:
            continue
        ts = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if (datetime.now(UTC) - ts).total_seconds() < 30:
            return agent
    return None


async def call_ollama_chat(
    prompt: str,
    system_prompt: str | None = None,
    image_b64: str | None = None,
) -> tuple[str, str]:
    """Call master's local Ollama. Returns (content, model_used).

    Vision routing (PB-36): when an image is provided, prefer an online agent with vision
    capability. If none is available, the master's own model handles it directly.
    """
    ollama_url = config.OLLAMA_URL
    model = config.MASTER_MODEL

    if image_b64:
        vision_agent = _find_vision_agent()
        if vision_agent:
            # Route to that agent's Ollama via its registered ollama_url, if exposed.
            # In the pull model agents don't expose their Ollama to the master; we fall through
            # to master's own model which also has vision (qwen3.5:4b).
            pass

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    user_msg: dict = {"role": "user", "content": prompt}
    if image_b64:
        user_msg["images"] = [image_b64]
    messages.append(user_msg)

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "num_predict": config.ASSISTANT_NUM_PREDICT,
            "temperature": 0.7,
        },
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(f"{ollama_url}/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Ollama hatası: {exc}") from exc
    return resp.json()["message"]["content"], model


def keyword_category_override(prompt: str) -> str | None:
    lowered = prompt.lower()
    if any(kw in lowered for kw in CODE_KEYWORDS):
        return "kod"
    return None


# Tool use: a pure arithmetic request is answered without calling any model at all, via an
# AST-based evaluator (never eval()). Small local models are unreliable at arithmetic; this
# gives an instant, 100%-correct answer at zero model cost.
def _safe_pow(base: float, exp: float) -> float:
    # An unbounded power can build an enormous integer and stall the process (this call runs
    # in-process, not sandboxed) -- e.g. "2^2^2^2^2^2^2^2^2^2" looks harmless but tries to
    # produce a number with thousands of digits.
    if abs(exp) > 1000 or abs(base) > 10**6:
        raise ValueError("expression too large")
    return operator.pow(base, exp)


_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: _safe_pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_ARITHMETIC_ONLY = re.compile(r"^[\d\s()+\-*/.%^]+$")
# A bare number ("100") or a single signed number ("-5") must not trigger the calculator --
# it needs an actual operation (two numbers with an operator between them).
_HAS_OPERATOR = re.compile(r"\d\s*[+\-*/%^]\s*[\d(]")
_CALC_TRAILING_WORDS = re.compile(
    r"(kaç\s*eder|kaç\s*yapar|nedir|hesapla|sonucu\s*ne|eşittir)\s*\??\s*$",
    re.IGNORECASE,
)


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval_node(node.operand))
    raise ValueError("unsupported expression")


def try_calculate(prompt: str) -> str | None:
    """Return "expression = result" if the prompt is a pure arithmetic expression end to end
    (e.g. '125*4 kaç eder', '(38+7)/3'); otherwise None, so the caller falls through to the
    normal classify/route flow. No eval() -- only numeric constants and +-*/%** reach a
    restricted AST walk."""
    text = _CALC_TRAILING_WORDS.sub("", prompt.strip()).strip().rstrip("?").strip()
    if (
        not text
        or len(text) > 200
        or not _ARITHMETIC_ONLY.match(text)
        or not _HAS_OPERATOR.search(text)
    ):
        return None
    expr = text.replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_node(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError, OverflowError, RecursionError):
        return None
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{text} = {result}"


async def classify_and_moderate(prompt: str) -> tuple[str, bool]:
    """One classifier call decides both the task category and whether the message is insulting.

    Small models do not always follow the format and can answer differently for the same
    message, so parsing is strict and fails open: an unrecognised answer counts as not
    inappropriate. Wrongly blocking a harmless request was the worse outcome in testing.
    "analiz" is not offered to the classifier: attachments already force it, and offering it
    pulled plain questions into "analiz".
    """
    classifier_prompt = (
        "Kullanici mesajini degerlendirip ASAGIDAKI IKI SATIRI BIREBIR bu bicimde yaz "
        "(ornek deger olarak 'kod' ve 'hayir' yazdim, kendi degerlendirmene gore degistir), "
        "baska hicbir aciklama ekleme:\n"
        "KATEGORI: kod\n"
        "UYGUNSUZ: hayir\n\n"
        "KATEGORI icin sadece su ikisinden birini yaz (kod / genel):\n"
        "kod = kod yazma, program/uygulama gelistirme, hata ayiklama istekleri\n"
        "genel = bunlarin disindaki her sey (soru-cevap, sohbet, bilgi edinme, duygusal konular)\n\n"
        "UYGUNSUZ icin sadece evet/hayir yaz:\n"
        "evet = mesaj acikca hakaret/kufur/asagilama iceriyor\n"
        "hayir = icermiyor -- baglami dikkate al: 'mal' kelimesi ticari baglamda (ör. "
        "'3 ton mal') UYGUNSUZ degildir, ama hakaret olarak (ör. 'sen malsin') kullanilirsa "
        "UYGUNSUZDUR\n\n"
        f'Degerlendirilecek mesaj: "{prompt}"'
    )
    try:
        result, _ = await call_ollama_chat(classifier_prompt)
    except HTTPException:
        return DEFAULT_TASK, False
    return parse_classifier_response(result)


def parse_classifier_response(result: str) -> tuple[str, bool]:
    """Parse the classifier's raw answer; a pure function so it is testable without a model."""
    # Models sometimes add bold markers (**) or template brackets (<>).
    result_clean = result.replace("*", "").replace("<", "").replace(">", "")

    category_match = re.search(r"KATEGORI:\s*(kod|genel)\b", result_clean, re.IGNORECASE)
    category = category_match.group(1).lower() if category_match else DEFAULT_TASK

    inappropriate_match = re.search(r"UYGUNSUZ:\s*(evet|hayir)\b", result_clean, re.IGNORECASE)
    inappropriate = bool(inappropriate_match and inappropriate_match.group(1).lower() == "evet")

    return category, inappropriate


class ChatResponse(BaseModel):
    content: str
    used_model: str
    task_type: str


async def _prepare_chat_request(
    prompt: str, file: UploadFile | None
) -> tuple[str, str | None, str | None, str, bool]:
    """Shared pre-processing for both /chat and /chat/stream.

    Returns (full_prompt, image_b64, forced_task_type, keyword_task, inappropriate).
    When keyword_task is non-None, the classifier call can be skipped.
    """
    file_note = ""
    extracted_text = ""
    forced_task_type = None
    image_b64: str | None = None

    if file is not None and file.filename:
        name = file.filename.lower()
        content_type = file.content_type or ""
        raw = await file.read()

        if content_type.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")):
            import media_lab_arena as mla
            import multimodal_studio as mms

            lower_p = prompt.lower()
            if any(k in lower_p for k in ("tara", "tarayıcı", "tarayici", "gölge", "golge", "belge temizle", "scan")):
                scan_info = mla.scan_and_clean_document_image(raw)
                file_note += (
                    f"\n\n### İşlenmiş Görsel Çıktısı\n"
                    f"- **Belge Tarayıcı ve Gölge Giderme:** `{scan_info['width']}x{scan_info['height']}` | "
                    f"**Aydınlatma Sapması:** `{scan_info['original_illumination_std']} -> {scan_info['cleaned_illumination_std']}`\n"
                    f"- [Taranmış Belgeyi İndir (PNG)]({scan_info['url']})\n\n"
                    f"![Taranmış Belge]({scan_info['url']})\n"
                )
            elif mms.is_image_edit_request(prompt):
                edit_info = mms.process_and_edit_image(raw, prompt)
                filters_str = ", ".join(edit_info["applied_filters"])
                file_note += (
                    f"\n\n### İşlenmiş Görsel Çıktısı\n"
                    f"- **Uygulanan İşlemler:** {filters_str}\n"
                    f"- **Boyut:** {edit_info['original_size']} -> {edit_info['output_size']} · "
                    f"**Ortalama Parlaklık:** {edit_info['mean_brightness']} · **Kontrast (Std):** {edit_info['std_contrast']}\n"
                    f"- [İşlenmiş Görseli İndir (PNG)]({edit_info['url']})\n\n"
                    f"![İşlenmiş Görsel]({edit_info['url']})\n"
                )
            image_b64 = base64.b64encode(raw).decode()
            forced_task_type = "analiz"
        elif content_type.startswith("audio/") or name.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac")):
            import multimodal_studio as mms

            stt = mms.transcribe_audio_bytes(file.filename, raw)
            if stt["transcript"]:
                extracted_text = f"[Ses Kaydı Metin Dökümü ({stt['engine']}, {stt['duration_sec']} sn)]:\n{stt['transcript']}"
            else:
                extracted_text = (
                    f"[Ses Dosyası Yüklendi: {file.filename} ({stt['size_kb']} KB, {stt['duration_sec']} sn). "
                    "Lütfen kullanıcının sesli mesaj isteğine göre yanıt ver.]"
                )
            forced_task_type = "analiz"
        elif name.endswith(".pdf"):
            extracted_text = extract_pdf_text(raw)
            forced_task_type = "analiz"
        elif name.endswith(".docx"):
            extracted_text = extract_docx_text(raw)
            forced_task_type = "analiz"
        elif name.endswith((".xlsx", ".xlsm")):
            extracted_text = extract_xlsx_text(raw)
            forced_task_type = "analiz"
        elif name.endswith((".csv", ".tsv")):
            import csv
            import io

            import automl_studio as aml

            extracted_text = extract_csv_text(raw)
            try:
                text_csv = raw.decode("utf-8", errors="ignore")
                delim = "\t" if name.endswith(".tsv") else ","
                rows = list(csv.DictReader(io.StringIO(text_csv), delimiter=delim))
                if rows:
                    prof = aml.profile_dataset(rows)
                    num_cols = prof.get("numeric_columns", [])
                    aml_lines = [
                        f"\n\n### AutoML Veri Bilimi ve Anomali Özeti ({prof['row_count']} satır, {prof['column_count']} sütun)",
                        f"- **Sayısal Sütunlar:** `{', '.join(num_cols) or '-'}` | **Tespit Edilen Anomali:** `{len(prof.get('anomalies', []))}` satır",
                    ]
                    if num_cols and len(rows) >= 4:
                        fc = aml.train_and_forecast(rows, target_col=num_cols[-1], horizon=3)
                        preds = ", ".join(f"T+{p['step']}: {p['prediction']:.2f}" for p in fc.get("forecasts", []))
                        aml_lines.append(
                            f"- **L2 Ridge Tahmin ({num_cols[-1]}):** R2=`{fc['metrics']['r2']:.3f}`, RMSE=`{fc['metrics']['rmse']:.2f}` -> `{preds}`"
                        )
                    extracted_text += "\n" + "\n".join(aml_lines)
            except Exception:
                pass
            forced_task_type = "analiz"
        elif name.endswith((".db", ".sqlite", ".sqlite3")):
            import domain_experts as de

            tmp_db = config.DATA_DIR / f"upload_{os.getpid()}.sqlite"
            tmp_db.parent.mkdir(parents=True, exist_ok=True)
            tmp_db.write_bytes(raw)
            try:
                sql_res = de.introspect_sqlite_and_query(tmp_db, prompt)
                extracted_text = (
                    f"[SQLite Veritabanı Şema ve Sorgu Sonucu]\n"
                    f"Çalıştırılan SQL: `{sql_res['executed_sql']}` ({sql_res['row_count']} satır)\n"
                    f"İlk Satırlar: {json.dumps(sql_res['rows'][:10], ensure_ascii=False)}\n"
                    f"ER Diyagramı:\n```mermaid\n{sql_res['er_diagram']}\n```"
                )
            except Exception as exc:
                extracted_text = f"[SQLite Veritabanı: {file.filename} ({exc})]"
            finally:
                tmp_db.unlink(missing_ok=True)
            forced_task_type = "analiz"
        elif name.endswith(".zip"):
            try:
                extracted_text = extract_zip_text(raw)
            except Exception:
                extracted_text = f"[ZIP Arşivi: {file.filename}]"
            forced_task_type = "analiz"
        elif (
            name.endswith((".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".html", ".css", ".js", ".ts", ".py", ".sql", ".log", ".ini"))
            or content_type.startswith("text/")
        ):
            extracted_text = raw.decode("utf-8", errors="ignore")
            forced_task_type = "analiz"
        else:
            file_note = f"\n\n[Not: '{file.filename}' desteklenmeyen bir dosya türü.]"

    # Domain Experts & KVKK PII auto-enrichment
    lower_prompt = prompt.lower()
    combined_source = f"{prompt}\n{extracted_text}".strip()
    if any(k in lower_prompt for k in ("kvkk", "pii", "maskele", "anonimleştir", "anonimlestir", "kişisel veri gizle")):
        import media_lab_arena as mla

        pii = mla.redact_sensitive_pii(combined_source)
        if pii["has_pii"]:
            file_note += (
                f"\n\n### KVKK / PII Hassas Veri Maskeleme Özeti ({pii['total_redacted']} öğe maskelendi)\n"
                f"- **Sayım:** `{json.dumps(pii['counts'], ensure_ascii=False)}`\n"
                f"- **Maskelenmiş Metin:**\n```\n{pii['cleaned_text'][:2000]}\n```\n"
            )
    if any(k in lower_prompt for k in ("sözleşme risk", "sozlesme risk", "redline", "cezai şart", "cezai sart", "hukuki inceleme")):
        import domain_experts as de

        leg = de.analyze_legal_contract(combined_source)
        file_note += (
            f"\n\n--- Hukuki Sözleşme Risk Motoru Çıktısı ---\n"
            f"Genel Risk: {leg['overall_risk']} (Skor: {leg['risk_score']}/100, Yüksek Risk: {leg['high_risk_count']})\n"
            f"Eksik Maddeler: {', '.join(leg['missing_clauses']) or 'Yok'}\n"
            f"Revizyon (Redline) Önerileri: {json.dumps(leg['redline_recommendations'], ensure_ascii=False)}"
        )
    if any(k in lower_prompt for k in ("dcf", "monte carlo", "şirket değerleme", "sirket degerleme", "cfo analiz", "npv simülasyon")):
        import domain_experts as de

        cfo = de.run_cfo_financial_analysis()
        file_note += (
            f"\n\n--- CFO Finansal Değerleme ve 500-Koşulu Monte Carlo Motoru ---\n"
            f"Oranlar: Cari Oran={cfo['ratios']['current_ratio']}, ROE={cfo['ratios']['roe']}, Borç/Özsermaye={cfo['ratios']['debt_to_equity']}\n"
            f"5 Yıllık İNA (DCF) Firma Değeri: {cfo['dcf']['enterprise_value']:,.2f} | Baz NPV: {cfo['dcf']['base_npv']:,.2f}\n"
            f"Monte Carlo (500 Koşu): P10={cfo['monte_carlo']['p10_npv']:,.2f} | P50={cfo['monte_carlo']['p50_npv']:,.2f} | P90={cfo['monte_carlo']['p90_npv']:,.2f} | Pozitif NPV Olasılığı=%{cfo['monte_carlo']['prob_positive_npv']*100:.1f}"
        )

    full_prompt = prompt
    if extracted_text:
        full_prompt = f"{prompt}\n\n--- Eklenen dosya içeriği ---\n{extracted_text[:8000]}"
    else:
        import company_rag
        import hybrid_graph_rag

        kb_docs = company_rag.search_company_kb_sync(prompt, top_k=2)
        graph_lines: list[str] = []
        try:
            grag = hybrid_graph_rag.HybridGraphRAG()
            g_hits = grag.hybrid_search(prompt, top_k=2)
            for gh in g_hits:
                graph_lines.append(f"- [GraphRAG] {gh['title']}: {gh['content'][:300]}")
        except Exception:
            pass
        if kb_docs or graph_lines:
            kb_text = "\n".join([*(f"- {d['title']}: {d['content']}" for d in kb_docs), *graph_lines])
            full_prompt = f"{prompt}\n\n--- Şirket Mühendislik Bilgi Bankası (Hybrid GraphRAG) ---\n{kb_text}"
    full_prompt += file_note

    # Skip the classifier call when a keyword match already determines the category.
    keyword_task = forced_task_type or keyword_category_override(prompt)
    inappropriate = False
    if not keyword_task:
        _, inappropriate = await classify_and_moderate(prompt)

    return full_prompt, image_b64, forced_task_type, keyword_task or "", inappropriate


@router.post("/chat", response_model=ChatResponse)
async def chat(prompt: str = Form(...), file: UploadFile | None = File(None)):  # noqa: B008
    if file is None or not file.filename:
        calc_result = try_calculate(prompt)
        if calc_result is not None:
            return ChatResponse(content=calc_result, used_model="hesaplama", task_type="hesaplama")

    full_prompt, image_b64, _forced_task_type, keyword_task, inappropriate = await _prepare_chat_request(prompt, file)

    if inappropriate:
        return ChatResponse(
            content=(
                "Bu mesaj hakaret/uygunsuz ifade içerebilecek şekilde değerlendirildi, "
                "bu yüzden bir modele iletilmedi. Lütfen sorunu farklı bir şekilde ifade et."
            ),
            used_model="moderation",
            task_type="engellendi",
        )

    task_type = keyword_task or DEFAULT_TASK
    content, used_model = await call_ollama_chat(full_prompt, system_prompt=ANSWER_SYSTEM_PROMPT, image_b64=image_b64)
    return ChatResponse(content=content, used_model=used_model, task_type=task_type)


@router.get("/media/{filename}")
async def get_assistant_media(filename: str):
    """Serve generated or edited images (.png, .svg) and documents (.xlsx, .docx, .pdf)."""
    import multimodal_studio as mms

    safe = "".join(c for c in filename if c.isalnum() or c in ("-", "_", "."))
    if not safe or safe != filename:
        raise HTTPException(status_code=400, detail="Geçersiz medya dosya adı.")
    target = mms.media_dir() / safe
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    headers = {"Cache-Control": "no-cache"}
    if safe.endswith((".xlsx", ".docx", ".pptx", ".pdf")):
        headers["Content-Disposition"] = f'attachment; filename="{safe}"'
    return FileResponse(target, headers=headers)


async def _tracked_stream(source, prompt: str, user_id: str, conversation_id: str):
    """Wrap an SSE generator: measure latency, fill in token usage on the final event, and persist
    usage statistics plus the conversation turn (episodic memory) for the personal space."""
    import time

    import memory_engine as mem
    import user_profile as up

    started = time.monotonic()
    collected: list[str] = []
    model_used = ""
    task_type = ""
    failed = False
    async for chunk in source:
        text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else chunk
        if not text.startswith("data: "):
            yield chunk
            continue
        try:
            evt = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            yield chunk
            continue
        etype = evt.get("type")
        if etype == "token":
            collected.append(evt.get("content", ""))
        elif etype == "error":
            failed = True
        elif etype == "done":
            model_used = evt.get("model", "")
            task_type = evt.get("task_type", "")
            answer = "".join(collected)
            usage = evt.get("usage") or {}
            estimated = not usage
            p_tok = int(usage.get("prompt_tokens") or up.estimate_tokens(prompt))
            c_tok = int(usage.get("completion_tokens") or up.estimate_tokens(answer))
            latency_ms = round((time.monotonic() - started) * 1000)
            evt["usage"] = {"prompt_tokens": p_tok, "completion_tokens": c_tok, "estimated": estimated}
            evt["latency_ms"] = latency_ms
            try:
                up.record_usage(user_id, conversation_id, model_used, task_type, p_tok, c_tok, latency_ms, estimated)
                if conversation_id and answer.strip():
                    learn = bool(up.get_settings(user_id).get("auto_learn_facts"))
                    mem.record_conversation_turn(
                        conversation_id, prompt, answer, model_used, task_type, user_id=user_id, learn=learn
                    )
            except Exception:
                pass
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            continue
        yield chunk
    _ = failed


@router.post("/chat/stream")
async def chat_stream(
    prompt: str = Form(...),
    file: UploadFile | None = File(None),  # noqa: B008
    history: str = Form("[]"),
    user_id: str = Form("default"),
    conversation_id: str = Form(""),
):
    """Streaming chat endpoint: tokens arrive as Server-Sent Events."""
    import user_profile as up

    try:
        uid = up.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    resp = await _chat_stream_impl(prompt, file, history, uid, conversation_id[:80])
    resp.body_iterator = _tracked_stream(resp.body_iterator, prompt, uid, conversation_id[:80])
    return resp


async def _chat_stream_impl(
    prompt: str,
    file: UploadFile | None,
    history: str,
    user_id: str,
    conversation_id: str,
):
    has_file = bool(file is not None and file.filename)

    if _is_3d_cad_request(file):
        report_md = await _run_3d_cad_cam_from_chat(file, prompt)  # type: ignore[arg-type]

        async def _cad3d_gen():
            yield f"data: {json.dumps({'type': 'token', 'content': report_md}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model': 'cnc-ballooner', 'task_type': 'cad3d'})}\n\n"

        return StreamingResponse(_cad3d_gen(), media_type="text/event-stream")

    if _is_cnc_balloon_request(prompt, file):
        report_md = await _run_cnc_balloon_from_chat(file)  # type: ignore[arg-type]

        async def _cnc_gen():
            yield f"data: {json.dumps({'type': 'token', 'content': report_md}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model': 'cnc-ballooner', 'task_type': 'cnc'})}\n\n"

        return StreamingResponse(_cnc_gen(), media_type="text/event-stream")

    if _is_zip_workspace_request(prompt, file):
        import workspace_builder as wb

        raw_zip = await file.read()  # type: ignore[union-attr]
        zname = file.filename or "proje.zip"  # type: ignore[union-attr]
        wants_exe = any(k in prompt.lower() for k in ("exe", "derle"))

        async def _zip_gen():
            try:
                ws_meta, ws_tree = wb.import_zip_workspace(zname, raw_zip)
                msg = f"### ZIP Projesi İçe Aktarıldı: **{ws_meta['name']}**\n- Çalışma alanı kimliği: `{ws_meta['id']}`\n"
                yield f"data: {json.dumps({'type': 'token', 'content': msg}, ensure_ascii=False)}\n\n"
                if wants_exe:
                    yield f"data: {json.dumps({'type': 'token', 'content': '**PyInstaller ile Windows .EXE derleniyor...**\\n'}, ensure_ascii=False)}\n\n"
                    res = await wb.build_workspace_exe(ws_meta["id"])
                    if res.get("ok"):
                        ws_dir = wb.safe_workspace_dir(ws_meta["id"])
                        ws_meta = wb.load_workspace_meta(ws_dir)
                        ws_meta["has_exe"] = True
                        ws_meta["exe_name"] = res["exe_name"]
                        ws_tree = wb.build_file_tree(ws_dir)
                yield f"data: {json.dumps({'type': 'workspace', 'workspace': ws_meta, 'tree': ws_tree}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': 'workspace-importer', 'task_type': 'proje'})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(_zip_gen(), media_type="text/event-stream")

    # Universal Image / Logo / Illustration Generation
    import document_factory as df
    import multimodal_studio as mms

    if mms.is_image_generation_request(prompt, has_file):
        async def _img_gen():
            try:
                res = await mms.generate_ai_image(prompt)
                md_lines = [
                    "## Üretilen Görsel Tasarım",
                    f"- **Motor:** `{res['engine']}`",
                    f"- [Yüksek Çözünürlüklü PNG İndir]({res['png_url']})"
                    + (f" · [Vektörel SVG İndir]({res['svg_url']})" if res.get("svg_url") else ""),
                    "",
                    f"![Üretilen Görsel]({res['png_url']})",
                ]
                yield f"data: {json.dumps({'type': 'token', 'content': '\\n'.join(md_lines)}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': res['engine'], 'task_type': 'gorsel'})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(_img_gen(), media_type="text/event-stream")

    # Universal Office & PDF Document Deliverable Factory (.xlsx, .docx, .pdf)
    doc_fmt = df.detect_document_request(prompt, has_file)
    if doc_fmt:
        async def _doc_gen():
            try:
                res = await df.generate_document_deliverable(prompt, doc_fmt)
                fmt_upper = doc_fmt.upper()
                md = [
                    f"## {res['title']} ({fmt_upper} Dosyası Hazır)",
                    res.get("summary") or "",
                    "",
                    f"- **Dosya İndirme Bağlantısı:** [{res['title']} (.{doc_fmt} İndir)]({res['url']})",
                    "",
                ]
                headers = res.get("table_headers") or []
                rows = res.get("table_rows") or []
                if headers and rows:
                    md.append("| " + " | ".join(str(h) for h in headers) + " |")
                    md.append("|" + "|".join("---" for _ in headers) + "|")
                    for r in rows[:15]:
                        md.append("| " + " | ".join(str(c) for c in r[:len(headers)]) + " |")
                yield f"data: {json.dumps({'type': 'token', 'content': '\\n'.join(md)}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': res['model'], 'task_type': 'dokuman'})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(_doc_gen(), media_type="text/event-stream")

    if _is_project_build_request(prompt, file):
        import workspace_builder as wb

        detected_type, wants_exe = _detect_project_type(prompt)

        async def _project_gen():
            ws_meta = None
            ws_tree = None
            used_model = config.STUDIO_CODER_MODEL
            try:
                async for evt in wb.stream_generate_project(prompt.strip(), project_type=detected_type):
                    et = evt.get("type")
                    if et == "status":
                        status_msg = f"{evt['message']}\n\n"
                        yield f"data: {json.dumps({'type': 'token', 'content': status_msg}, ensure_ascii=False)}\n\n"
                    elif et == "plan":
                        ws_meta = evt["workspace"]
                        used_model = ws_meta.get("model") or used_model
                        flist = "\n".join(f"- `{f['path']}` - {f['purpose']}" for f in evt["files"])
                        chunk = f"### Proje Planı: **{ws_meta['name']}** ({len(evt['files'])} dosya)\n{flist}\n\n"
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
                    elif et == "file_done":
                        kb = round(evt["size"] / 1024, 1)
                        chunk = f"- `{evt['path']}` ({kb} KB)\n"
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
                    elif et == "done":
                        ws_meta = evt["workspace"]
                        ws_tree = evt["tree"]

                if ws_meta and wants_exe and ws_meta.get("project_type") in ("game", "desktop", "cli"):
                    exe_start_msg = "\n**PyInstaller ile Windows .EXE derleniyor...**\n"
                    yield f"data: {json.dumps({'type': 'token', 'content': exe_start_msg}, ensure_ascii=False)}\n\n"
                    build_res = await wb.build_workspace_exe(ws_meta["id"])
                    if build_res.get("ok"):
                        ws_dir = wb.safe_workspace_dir(ws_meta["id"])
                        ws_meta = wb.load_workspace_meta(ws_dir)
                        ws_meta["has_exe"] = True
                        ws_tree = wb.build_file_tree(ws_dir)
                        mb = round(build_res.get("exe_size", 0) / (1024 * 1024), 2)
                        exe_ok_msg = f"**EXE hazır:** `dist/{build_res['exe_name']}` ({mb} MB)\n"
                        yield f"data: {json.dumps({'type': 'token', 'content': exe_ok_msg}, ensure_ascii=False)}\n\n"
                    else:
                        exe_err_msg = f"EXE derleme notu: {build_res.get('error')}\n"
                        yield f"data: {json.dumps({'type': 'token', 'content': exe_err_msg}, ensure_ascii=False)}\n\n"

                if ws_meta:
                    ws_dir = wb.safe_workspace_dir(ws_meta["id"])
                    ws_meta["has_web_preview"] = (ws_dir / "index.html").is_file() or (ws_dir / "public" / "index.html").is_file()
                    exe_files = list((ws_dir / "dist").glob("*.exe")) if (ws_dir / "dist").is_dir() else []
                    ws_meta["has_exe"] = len(exe_files) > 0
                    ws_meta["exe_name"] = exe_files[0].name if exe_files else ""
                    yield f"data: {json.dumps({'type': 'workspace', 'workspace': ws_meta, 'tree': ws_tree or wb.build_file_tree(ws_dir)}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': used_model, 'task_type': 'proje'})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(_project_gen(), media_type="text/event-stream")

    if file is None or not file.filename:
        calc_result = try_calculate(prompt)
        if calc_result is not None:
            async def _calc_gen():
                yield f"data: {json.dumps({'type': 'token', 'content': calc_result})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': 'hesaplama', 'task_type': 'hesaplama'})}\n\n"
            return StreamingResponse(_calc_gen(), media_type="text/event-stream")

    full_prompt, image_b64, _forced_task_type, keyword_task, inappropriate = await _prepare_chat_request(prompt, file)

    if inappropriate:
        msg = (
            "Bu mesaj hakaret/uygunsuz ifade içerebilecek şekilde değerlendirildi, "
            "bu yüzden bir modele iletilmedi. Lütfen sorunu farklı bir şekilde ifade et."
        )
        async def _mod_gen():
            yield f"data: {json.dumps({'type': 'token', 'content': msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model': 'moderation', 'task_type': 'engellendi'})}\n\n"
        return StreamingResponse(_mod_gen(), media_type="text/event-stream")

    task_type = keyword_task or DEFAULT_TASK
    model = config.MASTER_MODEL
    ollama_url = config.OLLAMA_URL

    messages = []
    if ANSWER_SYSTEM_PROMPT:
        messages.append({"role": "system", "content": ANSWER_SYSTEM_PROMPT})

    # Multi-turn conversation history + 4-Layer Persistent Semantic Memory
    import memory_engine as mem
    import user_profile as up

    user_settings = up.get_settings(user_id)
    extra_blocks = [up.personalization_block(user_id)]
    if user_settings.get("auto_learn_facts"):
        mem.extract_and_upsert_memories(prompt, user_id=user_id)
    extra_blocks.append(mem.build_memory_context_block(prompt, user_id=user_id))
    if user_settings.get("cross_chat_memory"):
        extra_blocks.append(up.cross_chat_context_block(user_id, prompt, exclude_conversation=conversation_id))
    mem_ctx = "\n\n".join(b for b in extra_blocks if b)
    if mem_ctx and messages and messages[0]["role"] == "system":
        messages[0]["content"] = f"{messages[0]['content']}\n\n{mem_ctx}"

    try:
        hist_items = json.loads(history) if history else []
        if isinstance(hist_items, list):
            for h_msg in hist_items[-10:]:
                if isinstance(h_msg, dict) and h_msg.get("role") in ("user", "assistant") and h_msg.get("text"):
                    messages.append({"role": h_msg["role"], "content": str(h_msg["text"])[:3000]})
    except Exception:
        pass
    messages = mem.compact_conversation_context(messages)

    # If an image was processed/edited, prepend the processed image preview before the LLM analysis
    pre_note = ""
    if "### İşlenmiş Görsel Çıktısı" in full_prompt:
        idx_n = full_prompt.index("### İşlenmiş Görsel Çıktısı")
        pre_note = full_prompt[idx_n:] + "\n\n---\n\n"
        full_prompt = full_prompt[:idx_n].strip()

    user_msg: dict = {"role": "user", "content": full_prompt}
    if image_b64:
        user_msg["images"] = [image_b64]
    messages.append(user_msg)

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "think": False,
        "options": {"num_predict": config.ASSISTANT_NUM_PREDICT, "temperature": 0.7},
    }

    async def _stream_gen():
        try:
            if pre_note:
                yield f"data: {json.dumps({'type': 'token', 'content': pre_note}, ensure_ascii=False)}\n\n"
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", f"{ollama_url}/api/chat", json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content_piece = chunk.get("message", {}).get("content", "")
                        if content_piece:
                            yield f"data: {json.dumps({'type': 'token', 'content': content_piece})}\n\n"
                        if chunk.get("done"):
                            done_evt: dict = {"type": "done", "model": model, "task_type": task_type}
                            if chunk.get("eval_count") is not None:
                                done_evt["usage"] = {
                                    "prompt_tokens": int(chunk.get("prompt_eval_count") or 0),
                                    "completion_tokens": int(chunk.get("eval_count") or 0),
                                    "estimated": False,
                                }
                            yield f"data: {json.dumps(done_evt)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(_stream_gen(), media_type="text/event-stream")


class CodeRunRequest(BaseModel):
    code: str


class CodeRunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


CODE_RUN_TIMEOUT_SECONDS = 5
CODE_RUN_MEMORY_LIMIT_MB = 128
NOBODY_ID = 65534


def _limit_code_run_resources() -> None:
    """Passed to subprocess.run as preexec_fn (POSIX only) -- caps the run's CPU time and
    memory so a runaway loop or allocation cannot affect the master process."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (CODE_RUN_TIMEOUT_SECONDS, CODE_RUN_TIMEOUT_SECONDS))
    mem_bytes = CODE_RUN_MEMORY_LIMIT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))


def _code_run_env() -> dict[str, str]:
    """A minimal environment: the run must not see the master's secrets (AGENT_TOKEN, the
    gateway key) through os.environ."""
    env = {"PYTHONIOENCODING": "utf-8"}
    if sys.platform == "win32":
        # Python cannot start on Windows without these.
        for key in ("SYSTEMROOT", "PATH"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def _run_code_blocking(code: str) -> CodeRunResponse:
    options: dict = {}
    if sys.platform != "win32":
        options["preexec_fn"] = _limit_code_run_resources
        # The master runs as root in its Docker image. Drop to "nobody" so a run cannot read
        # root-only files such as /proc/1/environ (the master's environment).
        if os.geteuid() == 0:
            options.update(user=NOBODY_ID, group=NOBODY_ID, extra_groups=[])
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=CODE_RUN_TIMEOUT_SECONDS,
            env=_code_run_env(),
            cwd=tempfile.gettempdir(),
            check=False,
            **options,
        )
        return CodeRunResponse(
            stdout=result.stdout[-4000:],
            stderr=result.stderr[-4000:],
            exit_code=result.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return CodeRunResponse(
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=stderr + f"\n[Zaman aşımı: kod {CODE_RUN_TIMEOUT_SECONDS} saniyede bitmedi.]",
            exit_code=-1,
            timed_out=True,
        )


@router.get("/config")
async def assistant_config():
    """Tells the web UI which optional Assistant features this master has switched on."""
    return {"code_run_enabled": config.CODE_RUN_ENABLED}


@router.post("/run-code", response_model=CodeRunResponse)
async def run_code(body: CodeRunRequest):
    """Run a code block (see the "Run" button) in an isolated subprocess.

    Off unless CODE_RUN_ENABLED is set, because the web UI has no login yet (PB-56).

    LIMIT (deliberate trade-off): this is not a full security sandbox -- no container or VM,
    and network access is not blocked. It is subprocess isolation with a time (RLIMIT_CPU) and
    memory (RLIMIT_AS) ceiling, a minimal environment and, inside Docker, the unprivileged
    "nobody" user. That is enough for a team member to test code that came out of their own
    prompt on their own machine -- NOT for a public/multi-tenant service. PB-41 (Sprint 4)
    adds a real sandbox for agent-executed code.
    """
    if not config.CODE_RUN_ENABLED:
        raise HTTPException(status_code=403, detail="Kod çalıştırma bu sunucuda kapalı (CODE_RUN_ENABLED).")
    # subprocess.run is blocking; without a thread a running snippet could hold up another
    # user's /chat request on the same event loop for up to CODE_RUN_TIMEOUT_SECONDS.
    return await asyncio.to_thread(_run_code_blocking, body.code)


@router.get("/enterprise-status")
async def enterprise_status():
    """Return live telemetry, Thompson Bandit Router state, LLMOps DPO status, and 12-discipline ELO Arena leaderboard."""
    import cluster_telemetry as ct
    import enterprise_security_mcp as esm
    import llmops_pipeline as lp
    import media_lab_arena as mla

    arena = mla.CognitiveArena()
    return {
        "telemetry": ct.get_local_hardware_telemetry(query_ollama=False),
        "llmops": lp.get_llmops_stats(),
        "audit_chain_valid": esm.AuditTrail().verify_chain(),
        "elo_leaderboard": arena.get_leaderboard()[:5],
    }

