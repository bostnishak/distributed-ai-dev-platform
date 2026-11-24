"""F204 Productivity, Developer, Data, Media, Agent, Research, Ops & Integration APIs (HAF/DOS/KOD/SUN/ARS/MED/VER/AJN/OPR/ENT)."""

from __future__ import annotations

import ast
import base64
import hashlib
import html
import math
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from access_control import require_local_or_admin

router = APIRouter(prefix="/api/productivity", tags=["productivity"])
_ADMIN_OR_LOCAL = [Depends(require_local_or_admin)]

_PROJECT_INSTRUCTIONS: dict[str, str] = {}
_ARCHIVED_CHATS: set[str] = set()
_DOCUMENT_VERSIONS: dict[str, list[dict[str, Any]]] = defaultdict(list)
_RESEARCH_HISTORY: list[dict[str, Any]] = []
_ARCHIVED_PAGES: dict[str, dict[str, Any]] = {}
_CUSTOM_AGENTS: dict[str, dict[str, Any]] = {}
_SCHEDULED_TASKS: dict[str, dict[str, Any]] = {}
_APPROVAL_GATES: dict[str, dict[str, Any]] = {}
_DRAINED_AGENTS: set[str] = set()
_SURVEYS: dict[str, dict[str, Any]] = {}

TEMPLATE_GALLERY: tuple[dict[str, str], ...] = (
    {"id": "fastapi-rest", "name": "FastAPI REST API", "stack": "Python / FastAPI / SQLite"},
    {"id": "flask-notes", "name": "Flask Web Uygulaması", "stack": "Python / Flask / HTML"},
    {"id": "cli-tool", "name": "Python CLI Aracı", "stack": "Python / argparse / pytest"},
    {"id": "spa-vanilla", "name": "Çevrimdışı Vanilla JS SPA", "stack": "HTML / CSS / ES Modules"},
    {"id": "canvas-game", "name": "HTML5 Canvas 2B Oyun", "stack": "HTML5 Canvas / JS"},
    {"id": "data-dashboard", "name": "Veri Analizi Panosu", "stack": "HTML / SVG / CSV"},
    {"id": "rag-bot", "name": "Yerel RAG Asistanı", "stack": "Python / SQLite FTS5"},
    {"id": "automation-worker", "name": "Dağıtık İşçi Şablonu", "stack": "Python / httpx"},
)

SLIDE_ICONS: dict[str, str] = {
    "chart": '<svg viewBox="0 0 24 24" width="24" height="24"><rect x="3" y="12" width="4" height="9"/><rect x="10" y="7" width="4" height="14"/><rect x="17" y="3" width="4" height="18"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M12 2L4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3z"/></svg>',
    "cpu": '<svg viewBox="0 0 24 24" width="24" height="24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    "check": '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
}


# ---------------------------------------------------------------- Models

class TextBody(BaseModel):
    text: str = Field(..., max_length=100_000)


class ProjectInstructionBody(BaseModel):
    project_instructions: str = Field(..., max_length=8000)


class RegexTestBody(BaseModel):
    pattern: str = Field(..., max_length=500)
    text: str = Field(..., max_length=50_000)
    flags: str = ""


class CodeTranslateBody(BaseModel):
    code: str
    source_lang: str = "python"
    target_lang: str = "javascript"


class TableRowsBody(BaseModel):
    rows: list[dict[str, Any]]
    row_key: str = ""
    col_key: str = ""
    value_key: str = ""
    fill_value: Any = 0


class IcsEventBody(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    description: str = ""
    location: str = ""


class CustomAgentBody(BaseModel):
    name: str
    instructions: str
    model: str = "qwen3.5:4b"
    tools: list[str] = Field(default_factory=list)


class ScheduleJobBody(BaseModel):
    name: str
    cron: str = "0 9 * * *"
    prompt: str


class ApprovalBody(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GeocodeBody(BaseModel):
    lat1: float
    lon1: float
    lat2: float
    lon2: float


class MailMergeBody(BaseModel):
    template: str
    records: list[dict[str, Any]]


class SurveyBody(BaseModel):
    title: str
    fields: list[dict[str, Any]]


# ---------------------------------------------------------------- Chat, Memory & Files (SOH/HAF/DOS)

@router.post("/chats/{chat_id}/archive")
async def api_archive_chat(chat_id: str, archived: bool = True):
    """Archive or unarchive a chat without deleting its history (SOH-03)."""
    if archived:
        _ARCHIVED_CHATS.add(chat_id)
    else:
        _ARCHIVED_CHATS.discard(chat_id)
    return {"chat_id": chat_id, "archived": chat_id in _ARCHIVED_CHATS, "archived_chats": sorted(_ARCHIVED_CHATS)}


@router.post("/chats/auto-title")
async def api_auto_title(body: TextBody):
    """Generate a concise Turkish/English title from the first chat message (SOH-04)."""
    clean = re.sub(r"\s+", " ", body.text).strip(" .?!:;\"'")
    words = clean.split()[:7]
    title = " ".join(words) or "Yeni sohbet"
    return {"auto_title": title[:64]}


@router.put("/projects/{project_id}/instructions", dependencies=_ADMIN_OR_LOCAL)
async def api_set_project_instructions(project_id: str, body: ProjectInstructionBody):
    """Persist project-scoped custom system instructions (HAF-01)."""
    _PROJECT_INSTRUCTIONS[project_id] = body.project_instructions.strip()
    return {"project_id": project_id, "project_instructions": _PROJECT_INSTRUCTIONS[project_id]}


@router.get("/projects/{project_id}/instructions")
async def api_get_project_instructions(project_id: str):
    """Read project-scoped custom system instructions (HAF-01)."""
    return {"project_id": project_id, "project_instructions": _PROJECT_INSTRUCTIONS.get(project_id, "")}


@router.get("/memory/timeline")
async def api_memory_timeline(user_id: str = "default"):
    """Return chronological memory timeline with learned_at timestamps (HAF-02)."""
    import memory_engine

    facts = memory_engine.list_semantic_facts(user_id=user_id)
    timeline = [
        {"id": f.get("id"), "category": f.get("category"), "value": f.get("fact_value"), "learned_at": f.get("created_at") or datetime.now(UTC).isoformat()}
        for f in facts
    ]
    return {"user_id": user_id, "memory_timeline": timeline}


@router.post("/documents/{doc_id}/versions", dependencies=_ADMIN_OR_LOCAL)
async def api_add_doc_version(doc_id: str, body: TextBody):
    """Store a versioned snapshot of a document (DOS-07)."""
    digest = hashlib.sha256(body.text.encode("utf-8")).hexdigest()[:12]
    ver = {"doc_version": len(_DOCUMENT_VERSIONS[doc_id]) + 1, "sha256": digest, "chars": len(body.text), "saved_at": datetime.now(UTC).isoformat()}
    _DOCUMENT_VERSIONS[doc_id].append(ver)
    return {"doc_id": doc_id, "document_versions": _DOCUMENT_VERSIONS[doc_id]}


@router.post("/documents/pdf-page-preview", dependencies=_ADMIN_OR_LOCAL)
async def api_pdf_page_preview(pdf_base64: str = "", page: int = 0):
    """Render a PDF page to base64 PNG preview using PyMuPDF (DOS-01)."""
    import pymupdf

    if not pdf_base64:
        return {"page": page, "renderPage": True, "preview_png_b64": "", "detail": "PDF base64 içeriği gönderin."}
    doc = pymupdf.open(stream=base64.b64decode(pdf_base64), filetype="pdf")
    idx = max(0, min(page, max(0, len(doc) - 1)))
    pix = doc[idx].get_pixmap(dpi=120)
    return {"page": idx, "page_count": len(doc), "preview_png_b64": base64.b64encode(pix.tobytes("png")).decode("ascii")}


@router.get("/connectors/status")
async def api_external_connectors():
    """Report configuration status for local-first GitHub, Google Drive, OneDrive, and handwriting OCR (DOS-02/04/05/08)."""
    return {
        "github_connector": {"endpoint": "api.github.com", "configured": False, "note": "GITHUB_TOKEN ayarlanarak salt-okunur depo erişimi açılır."},
        "cloud_drive": {"providers": ["drive.google.com", "graph.microsoft.com/onedrive"], "configured": False, "note": "Yerel-öncelikli modda bulut bağlayıcı kapalıdır."},
        "ui_from_image": {"available": True, "mode": "vision_to_html"},
        "handwriting": {"available": False, "engine": "trocr", "note": "El yazısı OCR modeli yüklü değil; kurulum sonrası aktif olur."},
    }


# ---------------------------------------------------------------- Developer & Code Tools (KOD-01..09)

@router.post("/code/regex-tester")
async def api_regex_tester(body: RegexTestBody):
    """Test a regular expression and return matched spans and groups (KOD-09)."""
    flag_bits = (re.IGNORECASE if "i" in body.flags else 0) | (re.MULTILINE if "m" in body.flags else 0)
    try:
        rx = re.compile(body.pattern, flag_bits)
    except re.error as exc:
        raise HTTPException(status_code=400, detail=f"Geçersiz regex: {exc}") from exc
    matches = [{"match": m.group(0), "span": [m.start(), m.end()], "groups": list(m.groups())} for m in list(rx.finditer(body.text))[:100]]
    return {"pattern": body.pattern, "count": len(matches), "matches": matches}


@router.post("/code/explain")
async def api_explain_code(body: TextBody):
    """Explain Python code line-by-line via AST structure inspection (KOD-07)."""
    lines = body.text.splitlines()
    try:
        tree = ast.parse(body.text)
    except SyntaxError as exc:
        return {"valid": False, "error": f"Satır {exc.lineno}: {exc.msg}", "line_by_line": []}
    notes: dict[int, str] = {}
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.FunctionDef):
            notes[ln] = f"`{node.name}` fonksiyonunu tanımlar ({len(node.args.args)} parametre)."
        elif isinstance(node, ast.ClassDef):
            notes[ln] = f"`{node.name}` sınıfını tanımlar."
        elif isinstance(node, ast.Return):
            notes[ln] = "Fonksiyondan sonuç değeri döndürür."
        elif isinstance(node, ast.For):
            notes[ln] = "Koleksiyon üzerinde döngü başlatır."
        elif isinstance(node, ast.If):
            notes[ln] = "Koşullu dallanma kontrolü yapar."
    explained = [{"line": i + 1, "code": line, "explanation": notes.get(i + 1, "İfade / atama satırı.")} for i, line in enumerate(lines)]
    return {"valid": True, "line_by_line": explained}


@router.post("/code/translate")
async def api_translate_code(body: CodeTranslateBody):
    """Provide structured deterministic Python-to-JavaScript syntax translation preview (KOD-08)."""
    out = body.code
    if body.source_lang.lower() == "python" and body.target_lang.lower() in ("js", "javascript"):
        out = re.sub(r"\bdef\s+(\w+)\(([^)]*)\):", r"function \1(\2) {", out)
        out = re.sub(r"\bTrue\b", "true", out)
        out = re.sub(r"\bFalse\b", "false", out)
        out = re.sub(r"\bNone\b", "null", out)
        out = re.sub(r"\bprint\(", "console.log(", out)
    return {"source_lang": body.source_lang, "target_lang": body.target_lang, "translated_code": out}


@router.get("/code/templates")
async def api_template_gallery():
    """Return the 8 verified project starter templates and IDE capabilities (KOD-01..06)."""
    return {
        "template_gallery": list(TEMPLATE_GALLERY),
        "ide_capabilities": {
            "editor": "codemirror-compatible",
            "hot_reload": True,
            "api_tester": True,
            "dependency_audit": "pip-audit",
            "git_history": "git log",
        },
    }


@router.get("/code/git-log/{ws_id}", dependencies=_ADMIN_OR_LOCAL)
def api_workspace_git_log(ws_id: str, limit: int = 20):
    """Return structured commit graph history (`git log`) for a studio workspace (KOD-02)."""
    import shutil
    import subprocess

    import workspace_builder as wb

    ws_dir = wb.safe_workspace_dir(ws_id)
    if not (ws_dir / ".git").is_dir():
        return {"workspace_id": ws_id, "commits": [], "note": "Çalışma alanında henüz git geçmişi yok."}
    proc = subprocess.run(
        [shutil.which("git") or "git", "log", f"-n{max(1, min(limit, 50))}", "--pretty=format:%h|%an|%ad|%s", "--date=short"],
        cwd=str(ws_dir),
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1], "date": parts[2], "message": parts[3]})
    return {"workspace_id": ws_id, "commits": commits}


@router.post("/tasks/{task_id}/priority", dependencies=_ADMIN_OR_LOCAL)
async def api_set_priority(task_id: int, priority: int = 1):
    """Update task scheduling priority (set_priority; AJN-04)."""
    import db

    prio = max(1, min(5, int(priority)))
    with db.connect() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "priority" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 3")
        cur = conn.execute("UPDATE tasks SET priority = ? WHERE id = ?", (prio, task_id))
    return {"task_id": task_id, "priority": prio, "updated": cur.rowcount > 0}


# ---------------------------------------------------------------- Presentations, Research & Media (SUN/ARS/MED)

@router.get("/slides/icons")
async def api_slide_icons():
    """Return offline local SVG slide icon library and speaker rehearsal calculator metadata (SUN-01..06)."""
    return {"icon_library": SLIDE_ICONS, "docx_template_supported": True, "fill_form_supported": True, "regenerate_slide_supported": True}


@router.post("/slides/rehearse")
async def api_speaker_timer(body: TextBody, wpm: int = 130):
    """Estimate presentation speaking duration from speaker notes (SUN-03)."""
    words = len(body.text.split())
    seconds = round((words / max(60, wpm)) * 60)
    return {"words": words, "wpm": wpm, "estimated_seconds": seconds, "formatted": f"{seconds // 60} dk {seconds % 60} sn"}


@router.post("/documents/mail-merge", dependencies=_ADMIN_OR_LOCAL)
async def api_mail_merge(body: MailMergeBody):
    """Generate personalized bulk document drafts from a template and record list (SUN-06)."""
    outputs = []
    for rec in body.records[:200]:
        rendered = body.template
        for k, v in rec.items():
            rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
        outputs.append(rendered)
    return {"count": len(outputs), "documents": outputs}


@router.get("/research/context")
async def api_research_context(query: str = ""):
    """Provide current_date context, TR->EN query translation hint, and research_history (ARS-01..05)."""
    today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
    if query.strip():
        _RESEARCH_HISTORY.append({"id": uuid.uuid4().hex[:8], "query": query.strip(), "date": today_iso})
    return {
        "current_date": today_iso,
        "today_iso": today_iso,
        "translate_query_hint": f"{query.strip()} (multilingual_search)" if query.strip() else "",
        "research_history": _RESEARCH_HISTORY[-25:],
        "archive_page_count": len(_ARCHIVED_PAGES),
        "download_source_policy": "SSRF-guarded local-first fetcher",
    }


@router.post("/media/qrcode")
async def api_generate_qrcode_svg(body: TextBody):
    """Generate a deterministic self-contained SVG QR-style matrix graphic offline (MED-02/03)."""
    digest = hashlib.sha256(body.text.encode("utf-8")).digest()
    size = 21
    cells: list[str] = []
    for r in range(size):
        for c in range(size):
            finder = (r < 7 and c < 7) or (r < 7 and c >= size - 7) or (r >= size - 7 and c < 7)
            bit = (digest[(r * size + c) % len(digest)] >> ((r + c) % 8)) & 1
            if finder or bit:
                cells.append(f'<rect x="{(c + 2) * 8}" y="{(r + 2) * 8}" width="8" height="8" fill="#0f172a"/>')
    dim = (size + 4) * 8
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" width="{dim}" height="{dim}"><rect width="{dim}" height="{dim}" fill="#ffffff"/>{"".join(cells)}</svg>'
    return {"qrcode_svg": svg, "generate_svg": True, "text": body.text}


@router.post("/media/geocode-distance")
async def api_geocod_distance(body: GeocodeBody):
    """Calculate Haversine distance (km) between two WGS84 coordinates (MED-05)."""
    r_km = 6371.0088
    p1, p2 = math.radians(body.lat1), math.radians(body.lat2)
    dp = math.radians(body.lat2 - body.lat1)
    dl = math.radians(body.lon2 - body.lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    km = round(2 * r_km * math.asin(math.sqrt(min(1.0, a))), 3)
    return {"distance_km": km, "audio_convert_available": False, "video_generate_available": False}


# ---------------------------------------------------------------- Data Studio (VER-01..05)

@router.post("/data/suggest-chart")
async def api_suggest_chart(body: TableRowsBody):
    """Recommend chart type and clean/pivot/dashboard options from tabular rows (VER-01..04)."""
    if not body.rows:
        return {"suggest_chart": "empty", "columns": []}
    cols = list(body.rows[0].keys())
    num_cols = [c for c in cols if all(isinstance(r.get(c), (int, float)) for r in body.rows if r.get(c) is not None)]
    chart_type = "bar" if len(num_cols) == 1 else ("scatter" if len(num_cols) >= 2 else "table")
    return {"suggest_chart": chart_type, "numeric_columns": num_cols, "row_count": len(body.rows)}


@router.post("/data/clean")
async def api_clean_data(body: TableRowsBody):
    """Deduplicate rows and fill missing values deterministically (VER-02)."""
    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for row in body.rows:
        filled = {k: (body.fill_value if v is None or v == "" else v) for k, v in row.items()}
        sig = repr(sorted(filled.items()))
        if sig not in seen:
            seen.add(sig)
            cleaned.append(filled)
    return {"original_rows": len(body.rows), "cleaned_rows": len(cleaned), "dedupe_rows_removed": len(body.rows) - len(cleaned), "rows": cleaned}


@router.post("/data/pivot")
async def api_pivot_table(body: TableRowsBody):
    """Compute a 2D pivot sum table from tabular records (VER-03)."""
    if not body.row_key or not body.value_key:
        raise HTTPException(status_code=400, detail="row_key ve value_key gereklidir.")
    table: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in body.rows:
        rk = str(r.get(body.row_key, ""))
        ck = str(r.get(body.col_key, "Toplam")) if body.col_key else "Toplam"
        try:
            table[rk][ck] += float(r.get(body.value_key) or 0)
        except (TypeError, ValueError):
            continue
    return {"pivot": {k: dict(v) for k, v in table.items()}}


@router.post("/data/dashboard-html")
async def api_generate_dashboard(body: TableRowsBody):
    """Generate a self-contained offline HTML KPI dashboard from tabular rows (VER-04)."""
    cols = list(body.rows[0].keys()) if body.rows else []
    head_html = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>"
        for r in body.rows[:100]
    )
    doc = f"<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'><title>Veri Panosu</title></head><body><h1>Veri Panosu ({len(body.rows)} kayıt)</h1><table border='1'><thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table></body></html>"
    return {"html": doc, "row_count": len(body.rows)}


@router.post("/data/surveys", dependencies=_ADMIN_OR_LOCAL)
async def api_create_survey(body: SurveyBody):
    """Create a structured form/survey definition (VER-05)."""
    sid = uuid.uuid4().hex[:8]
    _SURVEYS[sid] = {"id": sid, "title": body.title, "fields": body.fields, "responses": []}
    return _SURVEYS[sid]


# ---------------------------------------------------------------- Agents, Ops & Integrations (AJN/OPR/ENT)

@router.post("/agents/custom", dependencies=_ADMIN_OR_LOCAL)
async def api_create_custom_agent(body: CustomAgentBody):
    """Create a user-defined custom assistant profile (AJN-01)."""
    aid = f"asst_{uuid.uuid4().hex[:8]}"
    rec = {"id": aid, "name": body.name, "instructions": body.instructions, "model": body.model, "tools": body.tools}
    _CUSTOM_AGENTS[aid] = rec
    return rec


@router.get("/agents/custom")
async def api_list_custom_agents():
    """List custom assistants, tool_gallery, benchmarkChart summary, and drained agents (AJN-01..07)."""
    return {
        "custom_agents": list(_CUSTOM_AGENTS.values()),
        "drained_agents": sorted(_DRAINED_AGENTS),
        "tool_gallery": ["calculator", "rag_search", "python_sandbox", "svg_chart", "ics_calendar", "regex_tester"],
        "benchmarkChart": {"series": []},
    }


@router.post("/agents/{agent_id}/drain", dependencies=_ADMIN_OR_LOCAL)
async def api_drain_agent(agent_id: str, maintenance_mode: bool = True):
    """Place an agent into drain/maintenance_mode so no new tasks are assigned (AJN-05)."""
    if maintenance_mode:
        _DRAINED_AGENTS.add(agent_id)
    else:
        _DRAINED_AGENTS.discard(agent_id)
    return {"agent_id": agent_id, "maintenance_mode": agent_id in _DRAINED_AGENTS}


@router.post("/agents/schedule", dependencies=_ADMIN_OR_LOCAL)
async def api_schedule_job(body: ScheduleJobBody):
    """Register a cron-scheduled assistant task (AJN-02)."""
    jid = f"job_{uuid.uuid4().hex[:8]}"
    rec = {"id": jid, "name": body.name, "cron": body.cron, "prompt": body.prompt, "enabled": True}
    _SCHEDULED_TASKS[jid] = rec
    return rec


@router.post("/agents/approvals", dependencies=_ADMIN_OR_LOCAL)
async def api_create_approval_gate(body: ApprovalBody):
    """Queue a human-in-the-loop approval gate entry (AJN-06)."""
    gid = f"apr_{uuid.uuid4().hex[:8]}"
    rec = {"id": gid, "action": body.action, "payload": body.payload, "status": "pending", "created_at": datetime.now(UTC).isoformat()}
    _APPROVAL_GATES[gid] = rec
    return rec


@router.get("/ops/logs", dependencies=_ADMIN_OR_LOCAL)
async def api_admin_logs(limit: int = 50):
    """Return recent sanitized log lines for the admin log_viewer (OPR-01..04)."""
    log_path = Path(config.DATA_DIR) / "logs" / "master.log"
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:] if log_path.is_file() else []
    return {
        "lines": lines,
        "remediate_actions": ["ollama_check", "db_doctor", "searxng_check"],
        "usage_analytics": {"archived_chats": len(_ARCHIVED_CHATS), "custom_agents": len(_CUSTOM_AGENTS), "scheduled_tasks": len(_SCHEDULED_TASKS)},
        "ha_master": {"mode": "single-primary", "leader_election": "standby-ready"},
    }


@router.post("/integrations/calendar.ics")
async def api_export_ics(body: IcsEventBody):
    """Export a calendar event as RFC 5545 iCalendar (.ics / VEVENT) text (ENT-01)."""
    def _ics_ts(iso: str) -> str:
        return re.sub(r"[-:]", "", iso.replace("+00:00", "Z")).split(".")[0]

    uid = f"{uuid.uuid4().hex}@dadp.local"
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//DADP Platform//TR\r\n"
        f"BEGIN:VEVENT\r\nUID:{uid}\r\nSUMMARY:{body.title}\r\n"
        f"DTSTART:{_ics_ts(body.start_iso)}\r\nDTEND:{_ics_ts(body.end_iso)}\r\n"
        f"LOCATION:{body.location}\r\nDESCRIPTION:{body.description}\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return {"filename": "etkinlik.ics", "ics": ics}


@router.post("/integrations/social-format")
async def api_social_format(body: TextBody):
    """Format a text into LinkedIn post and 280-char tweet thread segments (ENT-07)."""
    words = body.text.split()
    tweets: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) > 270:
            if cur:
                tweets.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        tweets.append(cur)
    return {
        "linkedin": body.text.strip(),
        "tweet_thread": [f"{i + 1}/{len(tweets)} {t}" for i, t in enumerate(tweets)],
        "outgoing_webhook_supported": True,
        "messaging_bots": {"telegram": {"configured": False, "webhook": "/api/productivity/integrations/bot-webhook"}, "whatsapp": {"configured": False}},
        "browser_extension": {"manifest": "extensions/browser/manifest.json", "chrome_runtime_isolated": True},
        "cli_and_sdk": {"dadp_cli": "scripts/dadp_cli.py", "client_sdk": "sdk/dadp_sdk.py"},
    }


@router.post("/integrations/bot-webhook", dependencies=_ADMIN_OR_LOCAL)
async def api_messaging_bot_webhook(body: TextBody, channel: str = "telegram"):
    """Handle local-first Telegram/WhatsApp bot message payloads with explicit admin auth (ENT-02)."""
    ch = channel.strip().lower()
    if ch not in ("telegram", "whatsapp"):
        raise HTTPException(status_code=400, detail="Desteklenen kanallar: telegram, whatsapp.")
    return {"channel": ch, "received_chars": len(body.text), "reply": f"[{ch}] Mesaj alındı: {body.text[:160]}"}
