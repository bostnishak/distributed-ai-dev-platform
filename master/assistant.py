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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
import db
from extract import extract_csv_text, extract_docx_text, extract_pdf_text, extract_xlsx_text

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

        if content_type.startswith("image/"):
            image_b64 = base64.b64encode(raw).decode()
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
        elif name.endswith(".csv"):
            extracted_text = extract_csv_text(raw)
            forced_task_type = "analiz"
        elif name.endswith((".txt", ".md")) or content_type.startswith("text/"):
            extracted_text = raw.decode("utf-8", errors="ignore")
            forced_task_type = "analiz"
        else:
            file_note = f"\n\n[Not: '{file.filename}' desteklenmeyen bir dosya türü.]"

    full_prompt = prompt
    if extracted_text:
        full_prompt = f"{prompt}\n\n--- Eklenen dosya içeriği ---\n{extracted_text[:8000]}"
    else:
        import company_rag

        kb_docs = company_rag.search_company_kb_sync(prompt, top_k=2)
        if kb_docs:
            kb_text = "\n".join(f"- {d['title']}: {d['content']}" for d in kb_docs)
            full_prompt = f"{prompt}\n\n--- Şirket Mühendislik Bilgi Bankası (RAG) ---\n{kb_text}"
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


@router.post("/chat/stream")
async def chat_stream(prompt: str = Form(...), file: UploadFile | None = File(None)):  # noqa: B008
    """Streaming chat endpoint: tokens arrive as Server-Sent Events."""
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
                            yield f"data: {json.dumps({'type': 'done', 'model': model, 'task_type': task_type})}\n\n"
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
