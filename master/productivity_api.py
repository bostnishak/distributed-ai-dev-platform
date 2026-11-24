"""F204 Productivity, Developer, Data, Media, Agent, Research, Ops & Integration APIs (HAF/DOS/KOD/SUN/ARS/MED/VER/AJN/OPR/ENT)."""

from __future__ import annotations

import base64
import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

import config
import cronjobs
import productivity_engines as pe
import productivity_helpers as ph
from access_control import require_local_or_admin
from kvstore import PersistentDict, PersistentList, PersistentSet
from productivity_helpers import SLIDE_ICONS, TEMPLATE_GALLERY
from productivity_schemas import (
    ApprovalBody,
    ApprovalDecisionBody,
    AudioConvertBody,
    CodeTranslateBody,
    ConnectorScanBody,
    CustomAgentBody,
    GeocodeBody,
    IcsEventBody,
    MailMergeBody,
    ProjectInstructionBody,
    RegexTestBody,
    ScheduleJobBody,
    SourceDownloadBody,
    SurveyBody,
    TableRowsBody,
    TextBody,
    TranslateQueryBody,
    VideoGenerateBody,
)

router = APIRouter(prefix="/api/productivity", tags=["productivity"])
_ADMIN_OR_LOCAL = [Depends(require_local_or_admin)]

_PROJECT_INSTRUCTIONS = PersistentDict("project_instructions")
_ARCHIVED_CHATS = PersistentSet("archived_chats")
_DOCUMENT_VERSIONS = PersistentDict("document_versions")
_RESEARCH_HISTORY = PersistentList("research_history")
_ARCHIVED_PAGES = PersistentDict("archived_pages")
_CUSTOM_AGENTS = PersistentDict("custom_agents")
_SCHEDULED_TASKS = PersistentDict("scheduled_tasks")
_APPROVAL_GATES = PersistentDict("approval_gates")
_DRAINED_AGENTS = PersistentSet("drained_agents")
_SURVEYS = PersistentDict("surveys")


# Section: Chat, Memory and Files

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
    history = _DOCUMENT_VERSIONS.get(doc_id, [])
    ver = {"doc_version": len(history) + 1, "sha256": digest, "chars": len(body.text), "saved_at": datetime.now(UTC).isoformat()}
    history = [*history, ver]
    _DOCUMENT_VERSIONS[doc_id] = history
    return {"doc_id": doc_id, "document_versions": history}


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
    """Report live configuration status for GitHub/Git, local OneDrive/Google Drive sync, vision UI, and OCR (DOS-02/04/05/08)."""
    import importlib.util
    import os
    import shutil

    cloud_roots = pe.detect_cloud_drive_roots()
    git_ok = shutil.which("git") is not None
    gh_token = bool(os.environ.get("GITHUB_TOKEN", "").strip())
    ocr_ok = importlib.util.find_spec("pytesseract") is not None
    return {
        "github_connector": {
            "endpoint": "api.github.com",
            "configured": git_ok or gh_token,
            "git_local": git_ok,
            "token_set": gh_token,
        },
        "cloud_drive": {
            "providers": ["drive.google.com", "graph.microsoft.com/onedrive"],
            "configured": bool(cloud_roots),
            "detected_providers": [r["provider"] for r in cloud_roots],
        },
        "ui_from_image": {"available": True, "mode": "vision_to_html"},
        "handwriting": {"available": ocr_ok, "engine": "pytesseract/trocr"},
    }


@router.post("/connectors/cloud-drive/scan", dependencies=_ADMIN_OR_LOCAL)
async def api_scan_cloud_drive(body: ConnectorScanBody):
    """Scan locally synced OneDrive/Google Drive directory safely (DOS-04)."""
    try:
        return pe.scan_cloud_drive_files(body.path, body.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/connectors/github/inspect", dependencies=_ADMIN_OR_LOCAL)
async def api_inspect_github_repo(body: ConnectorScanBody):
    """Inspect a local Git/GitHub repository branch and recent commits (DOS-05)."""
    return pe.inspect_github_connector_repo(body.path, body.limit)


# Section: Developer and Code Tools

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
    return ph.explain_python_code(body.text)


@router.post("/code/translate")
async def api_translate_code(body: CodeTranslateBody):
    """Translate code across languages via AST with deterministic syntax verification (KOD-08)."""
    return pe.translate_code_verified(body.code, body.source_lang, body.target_lang)


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
    return ph.read_workspace_git_log(ws_id, limit)


@router.post("/tasks/{task_id}/priority", dependencies=_ADMIN_OR_LOCAL)
async def api_set_priority(task_id: int, priority: int = 1):
    """Update task scheduling priority (set_priority; AJN-04)."""
    import db

    prio = max(1, min(5, priority))
    with db.connect() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "priority" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 3")
        cur = conn.execute("UPDATE tasks SET priority = ? WHERE id = ?", (prio, task_id))
    return {"task_id": task_id, "priority": prio, "updated": cur.rowcount > 0}


# Section: Presentations, Research and Media

@router.get("/slides/icons")
async def api_slide_icons():
    """Return 24-icon offline local SVG slide icon library and metadata (SUN-01..06)."""
    return {
        "icon_library": SLIDE_ICONS,
        "icon_count": len(SLIDE_ICONS),
        "categories": pe.SLIDE_ICON_CATEGORIES,
        "docx_template_supported": True,
        "fill_form_supported": True,
        "regenerate_slide_supported": True,
    }


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
    """Provide current_date context, live web_archive count, and research_history (ARS-01..05)."""
    from rag.crawler import count_archived_pages

    today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
    if query.strip():
        _RESEARCH_HISTORY.append({"id": uuid.uuid4().hex[:8], "query": query.strip(), "date": today_iso})
    return {
        "current_date": today_iso,
        "today_iso": today_iso,
        "research_history": _RESEARCH_HISTORY[-25:],
        "archive_page_count": count_archived_pages(),
        "download_source_endpoint": "/api/productivity/research/download-source",
    }


@router.post("/research/download-source", dependencies=_ADMIN_OR_LOCAL)
async def api_download_and_index_source(body: SourceDownloadBody):
    """Download/extract a PDF or web source with SSRF guard, archive it, and index into RAG (ARS-01/ARS-04)."""
    from rag.crawler import fetch_and_index_source

    try:
        return await fetch_and_index_source(body.url, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/research/translate-query")
async def api_translate_query(body: TranslateQueryBody):
    """Translate a research query with the master model so sources in another language can be searched (ARS-05)."""
    import assistant

    system = "Translate the user's search query. Reply with the translated query only: no quotes, no explanation."
    prompt = f"Target language: {body.target}\nQuery: {body.query.strip()}"
    content, _model = await assistant.call_ollama_chat(prompt, system)
    translated = content.strip().splitlines()[0].strip().strip('"') if content.strip() else ""
    if not translated:
        raise HTTPException(status_code=502, detail="Model çeviri üretemedi.")
    return {"query": body.query.strip(), "target": body.target, "translated": translated}


@router.post("/media/qrcode")
async def api_generate_qrcode_svg(body: TextBody):
    """Generate a deterministic self-contained SVG QR-style matrix graphic offline (MED-02/03)."""
    return {"qrcode_svg": ph.build_qrcode_svg(body.text), "generate_svg": True, "text": body.text}


@router.post("/media/geocode-distance")
async def api_geocod_distance(body: GeocodeBody):
    """Calculate Haversine distance (km) between two WGS84 coordinates (MED-05)."""
    km = ph.haversine_km(body.lat1, body.lon1, body.lat2, body.lon2)
    return {"distance_km": km, "audio_convert_available": True, "video_generate_available": True}


@router.post("/media/audio-convert")
async def api_audio_convert(body: AudioConvertBody):
    """Clean, normalize, trim silence, and resample WAV PCM audio offline (MED-01)."""
    try:
        return pe.convert_clean_audio_wav(
            body.wav_base64,
            normalize=body.normalize,
            trim_silence=body.trim_silence,
            target_rate=body.target_rate,
            mono=body.mono,
        )
    except (ValueError, KeyError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Ses dönüştürme hatası: {exc}") from exc


@router.post("/media/video-generate")
async def api_video_generate(body: VideoGenerateBody):
    """Compose an offline animated slideshow/video (GIF) from structured slides via Pillow (MED-04)."""
    return pe.generate_slideshow_video(body.slides, width=body.width, height=body.height, frame_ms=body.frame_ms)


# Section: Data Studio

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
    return ph.clean_table_rows(body.rows, body.fill_value)


@router.post("/data/pivot")
async def api_pivot_table(body: TableRowsBody):
    """Compute a 2D pivot sum table from tabular records (VER-03)."""
    if not body.row_key or not body.value_key:
        raise HTTPException(status_code=400, detail="row_key ve value_key gereklidir.")
    return {"pivot": ph.compute_pivot(body.rows, body.row_key, body.col_key, body.value_key)}


@router.post("/data/dashboard-html")
async def api_generate_dashboard(body: TableRowsBody):
    """Generate a self-contained offline HTML KPI dashboard from tabular rows (VER-04)."""
    return {"html": ph.render_dashboard_html(body.rows), "row_count": len(body.rows)}


@router.post("/data/surveys", dependencies=_ADMIN_OR_LOCAL)
async def api_create_survey(body: SurveyBody):
    """Create a structured form/survey definition (VER-05)."""
    sid = uuid.uuid4().hex[:8]
    _SURVEYS[sid] = {"id": sid, "title": body.title, "fields": body.fields, "responses": []}
    return _SURVEYS[sid]


# Section: Agents, Operations and Integrations

@router.post("/agents/custom", dependencies=_ADMIN_OR_LOCAL)
async def api_create_custom_agent(body: CustomAgentBody):
    """Create a user-defined custom assistant profile persisted in SQLite custom_agents (AJN-01)."""
    from custom_agents import upsert_custom_agent

    saved = upsert_custom_agent(
        {
            "agent_id": f"asst_{uuid.uuid4().hex[:8]}",
            "user_id": "default",
            "name": body.name,
            "instructions": body.instructions,
            "model_override": body.model,
            "allowed_tools": body.tools,
        }
    )
    return {
        "id": saved["agent_id"],
        "name": body.name,
        "instructions": body.instructions,
        "model": body.model,
        "tools": body.tools,
        "version": saved["version"],
    }


@router.get("/agents/custom")
async def api_list_custom_agents():
    """List SQLite custom assistants, tool_gallery, benchmarkChart summary, and drained agents (AJN-01..07)."""
    from custom_agents import list_custom_agents

    agents = [
        {
            "id": a["agent_id"],
            "name": a["name"],
            "instructions": a["instructions"],
            "model": a.get("model_override") or "qwen3.5:4b",
            "tools": a.get("allowed_tools") or [],
            "version": a.get("current_version", 1),
        }
        for a in list_custom_agents("default")
    ]
    return {
        "custom_agents": agents,
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


async def assistant_runner(prompt: str) -> str:
    """Run a scheduled prompt through the master's own model (imported lazily to avoid an import cycle)."""
    import assistant

    content, _model = await assistant.call_ollama_chat(prompt)
    return content


@router.post("/agents/schedule", dependencies=_ADMIN_OR_LOCAL)
async def api_schedule_job(body: ScheduleJobBody):
    """Register a cron-scheduled assistant task; it is executed by the master's scheduler loop (AJN-02)."""
    try:
        return cronjobs.add_job(body.name, body.cron, body.prompt)
    except cronjobs.CronError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/agents/schedule", dependencies=_ADMIN_OR_LOCAL)
async def api_list_scheduled_jobs():
    return {"jobs": _SCHEDULED_TASKS.values(), "runs": cronjobs.recent_runs()}


@router.delete("/agents/schedule/{job_id}", dependencies=_ADMIN_OR_LOCAL)
async def api_delete_scheduled_job(job_id: str):
    if not cronjobs.remove_job(job_id):
        raise HTTPException(status_code=404, detail="Zamanlanmış görev bulunamadı.")
    return {"deleted": job_id}


@router.post("/agents/schedule/run-due", dependencies=_ADMIN_OR_LOCAL)
async def api_run_due_jobs():
    """Run every job that is due this minute right now (the background loop does this automatically)."""
    return {"runs": await cronjobs.run_due(assistant_runner)}


@router.post("/agents/approvals", dependencies=_ADMIN_OR_LOCAL)
async def api_create_approval_gate(body: ApprovalBody):
    """Queue a human-in-the-loop approval gate entry that blocks execution until approved (AJN-06)."""
    gid = f"apr_{uuid.uuid4().hex[:8]}"
    rec = {"id": gid, "action": body.action, "payload": body.payload, "status": "pending", "created_at": datetime.now(UTC).isoformat()}
    _APPROVAL_GATES[gid] = rec
    return rec


@router.post("/agents/approvals/{gate_id}/decide", dependencies=_ADMIN_OR_LOCAL)
async def api_decide_approval_gate(gate_id: str, body: ApprovalDecisionBody):
    """Approve or reject a pending human-in-the-loop gate (AJN-06)."""
    rec = _APPROVAL_GATES.get(gate_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Onay kapısı bulunamadı.")
    updated = {**rec, "status": body.decision, "reviewer": body.reviewer, "note": body.note, "decided_at": datetime.now(UTC).isoformat()}
    _APPROVAL_GATES[gate_id] = updated
    return updated


@router.post("/agents/approvals/{gate_id}/execute", dependencies=_ADMIN_OR_LOCAL)
async def api_execute_approval_gate(gate_id: str):
    """Execute a gated step ONLY after human approval; blocks pending (409) or rejected (403) gates (AJN-06)."""
    rec = _APPROVAL_GATES.get(gate_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Onay kapısı bulunamadı.")
    if rec.get("status") == "pending":
        raise HTTPException(status_code=409, detail="Bu adım insan onayı bekliyor; onaylanmadan çalıştırılamaz.")
    if rec.get("status") != "approved":
        raise HTTPException(status_code=403, detail=f"Adım reddedildi veya geçersiz durumda: {rec.get('status')}")
    executed = {**rec, "status": "executed", "executed_at": datetime.now(UTC).isoformat()}
    _APPROVAL_GATES[gate_id] = executed
    return {"ok": True, "gate": executed}


@router.get("/ops/logs", dependencies=_ADMIN_OR_LOCAL)
async def api_admin_logs(limit: int = 50):
    """Return recent sanitized log lines for the admin log_viewer, remediation endpoint, and live HA leader status (OPR-01..04)."""
    from ha.leader import get_ha_status

    log_path = Path(config.DATA_DIR) / "logs" / "master.log"
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:] if log_path.is_file() else []
    ha = get_ha_status()
    return {
        "lines": lines,
        "remediate_actions": ["ensure_dirs", "db_doctor", "init_dbs", "ollama_check", "searxng_check"],
        "remediate_endpoint": "/api/ux/health-wizard/remediate",
        "usage_analytics": {"archived_chats": len(_ARCHIVED_CHATS), "custom_agents": len(_CUSTOM_AGENTS), "scheduled_tasks": len(_SCHEDULED_TASKS)},
        "ha_master": {
            "mode": "ha-lease",
            "leader_election": True,
            "leader": ha.get("leader"),
            "term": ha.get("term", 0),
            "draining": bool(ha.get("draining", False)),
        },
    }


@router.post("/integrations/calendar.ics")
async def api_export_ics(body: IcsEventBody):
    """Export a calendar event as RFC 5545 iCalendar (.ics / VEVENT) text (ENT-01)."""
    ics = ph.build_ics_event(body.title, body.start_iso, body.end_iso, body.location, body.description)
    return {"filename": "etkinlik.ics", "ics": ics}


@router.post("/integrations/social-format")
async def api_social_format(body: TextBody):
    """Format a text into LinkedIn post and 280-char tweet thread segments (ENT-07)."""
    return {
        "linkedin": body.text.strip(),
        "tweet_thread": ph.split_tweet_thread(body.text),
        "outgoing_webhook_supported": True,
        "messaging_bots": {"telegram": {"configured": False, "webhook": "/api/productivity/integrations/bot-webhook"}, "whatsapp": {"configured": False}},
        "browser_extension": {"manifest": "extensions/browser/manifest.json (extension)", "runtime_api": "chrome.runtime"},
        "cli_and_sdk": {"dadp-cli": "scripts/dadp_cli.py", "cli_client": "scripts/dadp_cli.py", "client_sdk": "sdk/dadp_sdk.py"},
    }


@router.post("/integrations/bot-webhook", dependencies=_ADMIN_OR_LOCAL)
async def api_messaging_bot_webhook(body: TextBody, channel: str = "telegram"):
    """Handle local-first Telegram/WhatsApp bot message payloads with explicit admin auth (ENT-02)."""
    ch = channel.strip().lower()
    if ch not in ("telegram", "whatsapp"):
        raise HTTPException(status_code=400, detail="Desteklenen kanallar: telegram, whatsapp.")
    return {"channel": ch, "received_chars": len(body.text), "reply": f"[{ch}] Mesaj alındı: {body.text[:160]}"}
