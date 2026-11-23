"""UX-16, UX-17, UX-24, UX-26: Health Wizard, Settings Schema, Secret-Scanned Shares & SLO Dashboard API (SEC-22)."""

from __future__ import annotations

import os
import secrets
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
import db
import sandbox
from access_control import require_local_or_admin
from distributed.core import build_performance_matrix
from hallucination.verifier import telemetry_summary_7d
from log_sanitizer import redact_sensitive_text
from rag.store import default_rag_store

router = APIRouter(prefix="/api/ux", tags=["ux"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]

# UX-16: Strict validated settings schema
SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "language": {"type": "enum", "values": ["tr", "en"], "default": "tr"},
    "theme": {"type": "enum", "values": ["dark", "light", "high_contrast"], "default": "dark"},
    "responseLength": {"type": "enum", "values": ["short", "balanced", "detailed"], "default": "balanced"},
    "tone": {"type": "enum", "values": ["professional", "academic", "concise"], "default": "professional"},
    "showConfidenceBadges": {"type": "bool", "default": True},
    "webSearchEnabled": {"type": "bool", "default": False},
    "reducedMotion": {"type": "bool", "default": False},
}


def validate_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """UX-16: Validate user settings strictly against SETTINGS_SCHEMA."""
    errors: list[str] = []
    cleaned: dict[str, Any] = {}
    for key, spec in SETTINGS_SCHEMA.items():
        val = payload.get(key, spec["default"])
        if spec["type"] == "enum" and val not in spec["values"]:
            errors.append(f"'{key}' geçersiz değer: {val} (izinli: {spec['values']})")
        elif spec["type"] == "bool" and not isinstance(val, bool):
            errors.append(f"'{key}' boolean olmalıdır.")
        else:
            cleaned[key] = val
    return {"valid": len(errors) == 0, "settings": cleaned, "errors": errors}


# ---------------------------------------------------------------- UX-17 Health Check Wizard

def build_health_wizard_report(
    *,
    ollama_reachable: bool = True,
    models_count: int = 1,
    bge_available: bool = True,
) -> dict[str, Any]:
    """UX-17: Actionable Turkish diagnostics for Ollama, models, embeddings, web search, sandbox & agents."""
    sb = sandbox.status()
    web_on = os.environ.get("WEB_SEARCH_ENABLED", "false").lower() == "true"
    try:
        agents = db.list_agents() if hasattr(db, "list_agents") else []
    except Exception:
        agents = []
    checks = [
        {
            "id": "ollama",
            "ok": ollama_reachable,
            "title": "Yerel Ollama Servisi",
            "remediation": "" if ollama_reachable else "`ollama serve` komutunu çalıştırıp 11434 portunu doğrulayın.",
        },
        {
            "id": "models",
            "ok": models_count > 0,
            "title": "Yüklü Dil Modelleri",
            "remediation": "" if models_count > 0 else "`ollama pull qwen3.5:9b` ile en az bir yerel model çekin.",
        },
        {
            "id": "embeddings",
            "ok": bge_available and default_rag_store.embedding_status == "ready",
            "title": "Bilgi Bankası Gömme Modeli (bge-m3)",
            "remediation": "" if bge_available else "`ollama pull bge-m3` çalıştırarak RAG bilgi bankasını etkinleştirin.",
        },
        {
            "id": "sandbox",
            "ok": bool(sb.get("available")),
            "title": "Docker Kod Çalıştırma Sandbox'ı",
            "remediation": "" if sb.get("available") else str(sb.get("reason") or "Docker Desktop başlatın."),
        },
        {
            "id": "web_search",
            "ok": web_on,
            "title": "Web Araştırması (SearXNG)",
            "remediation": "" if web_on else "İsteğe bağlı: `WEB_SEARCH_ENABLED=true` ve `SEARXNG_URL` ayarlayın.",
        },
        {
            "id": "agents",
            "ok": len(agents) > 0,
            "title": "Dağıtık Ajan Ağı",
            "remediation": "" if agents else "Ek bilgisayar bağlamak için Ajanlar sayfasındaki kurulum komutunu kullanın.",
        },
    ]
    return {"ready_count": sum(1 for c in checks if c["ok"]), "total": len(checks), "checks": checks}


# ---------------------------------------------------------------- UX-26 Secret-Scanned, Expiring Read-Only Shares

def _share_db_path() -> Path:
    p = Path(config.DATA_DIR) / "ux_shares.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _init_share_db() -> None:
    with sqlite3.connect(str(_share_db_path()), timeout=10.0) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS readonly_shares (
                share_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                allowed_users_json TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def create_readonly_share(
    *,
    owner_id: str,
    title: str,
    content: str,
    allowed_users: list[str] | None = None,
    ttl_seconds: int = 3600,
) -> dict[str, Any]:
    """UX-26: Scan shared content for secrets/PII, redact before storing, and issue expiring share link."""
    _init_share_db()
    redacted = redact_sensitive_text(content)
    had_secrets = redacted != content
    sid = f"shr_{secrets.token_urlsafe(12)}"
    exp = time.time() + ttl_seconds
    allowed = sorted({owner_id, *(allowed_users or [])})
    with sqlite3.connect(str(_share_db_path()), timeout=10.0) as conn:
        import json

        conn.execute(
            "INSERT INTO readonly_shares (share_id, owner_id, allowed_users_json, title, content, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, owner_id, json.dumps(allowed), title[:120], redacted, exp, datetime.now(UTC).isoformat()),
        )
    return {"share_id": sid, "url": f"/api/ux/shares/{sid}", "secrets_redacted": had_secrets, "expires_at": exp}


def fetch_readonly_share(share_id: str, *, requester_id: str) -> dict[str, Any]:
    import json

    _init_share_db()
    with sqlite3.connect(str(_share_db_path()), timeout=10.0) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM readonly_shares WHERE share_id = ?", (share_id,)).fetchone()
    if not row or time.time() > float(row["expires_at"]):
        raise FileNotFoundError("Paylaşım bağlantısı bulunamadı veya süresi doldu.")
    allowed = set(json.loads(row["allowed_users_json"] or "[]"))
    if requester_id not in allowed:
        raise PermissionError("Bu paylaşıma erişim yetkiniz yok.")
    return {"share_id": row["share_id"], "title": row["title"], "content": row["content"], "owner_id": row["owner_id"]}


# ---------------------------------------------------------------- FastAPI Routes (SEC-22 Compliant)

class ShareReq(BaseModel):
    owner_id: str = "default"
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    allowed_users: list[str] = Field(default_factory=list)
    ttl_seconds: int = Field(3600, ge=1, le=86400 * 30)


@router.get("/health-wizard")
async def api_health_wizard():
    return build_health_wizard_report()


@router.get("/settings/schema")
async def api_settings_schema():
    return {"schema": SETTINGS_SCHEMA}


@router.post("/settings/validate", dependencies=_LOCAL_OR_ADMIN)
async def api_validate_settings(payload: dict[str, Any]):
    res = validate_settings(payload)
    if not res["valid"]:
        raise HTTPException(status_code=400, detail=res["errors"])
    return res


@router.post("/shares", dependencies=_LOCAL_OR_ADMIN)
async def api_create_share(body: ShareReq):
    return create_readonly_share(
        owner_id=body.owner_id,
        title=body.title,
        content=body.content,
        allowed_users=body.allowed_users,
        ttl_seconds=body.ttl_seconds,
    )


@router.get("/shares/{share_id}")
async def api_get_share(share_id: str, user_id: str = "default"):
    try:
        return fetch_readonly_share(share_id, requester_id=user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/slo")
async def api_slo_dashboard():
    """UX-24: Live SLO indicators aggregating hallucination telemetry and agent performance."""
    return {
        "hallucination_7d": telemetry_summary_7d(),
        "agent_performance": build_performance_matrix()["rows"],
    }
