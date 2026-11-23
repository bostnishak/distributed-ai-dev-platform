"""ORC-11..ORC-17, ORC-21..ORC-23: SSE Protocol, Jobs, Artifacts, Conversation State, Clarification, Memory & Runs."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config

SSE_EVENT_TYPES = frozenset({
    "meta",
    "route",
    "plan",
    "step_start",
    "step_end",
    "token",
    "citation",
    "artifact",
    "verification",
    "warning",
    "approval_required",
    "done",
    "error",
})


def make_sse_event(
    event_type: str,
    data: dict[str, Any],
    *,
    run_id: str,
    seq: int,
    schema_version: int = 1,
) -> dict[str, Any]:
    """ORC-11: Build a versioned, typed SSE event envelope."""
    if event_type not in SSE_EVENT_TYPES:
        raise ValueError(f"Desteklenmeyen SSE olay türü: {event_type}")
    return {
        "schema_version": schema_version,
        "run_id": run_id,
        "seq": seq,
        "type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": data,
    }


def format_sse_wire(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------- SQLite Persistence (ORC-12, 13, 14, 16, 22, 23)

def _db_path() -> Path:
    p = Path(config.DATA_DIR) / "gateway.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()), timeout=10.0)
    c.row_factory = sqlite3.Row
    return c


def init_orchestrator_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orchestrator_jobs (
                job_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orchestrator_artifacts (
                artifact_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT 'default',
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                sections_json TEXT NOT NULL DEFAULT '[]',
                content TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orchestrator_runs (
                run_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT 'default',
                prompt TEXT NOT NULL,
                intent TEXT NOT NULL,
                mode TEXT NOT NULL,
                tier TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                seed INTEGER,
                plan_json TEXT NOT NULL DEFAULT '{}',
                tools_json TEXT NOT NULL DEFAULT '[]',
                citations_json TEXT NOT NULL DEFAULT '[]',
                verification_json TEXT NOT NULL DEFAULT '{}',
                response_text TEXT NOT NULL DEFAULT '',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orchestrator_feedback (
                feedback_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'default',
                rating INTEGER NOT NULL,
                reason_tags_json TEXT NOT NULL DEFAULT '[]',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversation_states (
                chat_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                goals_json TEXT NOT NULL DEFAULT '[]',
                decisions_json TEXT NOT NULL DEFAULT '[]',
                open_questions_json TEXT NOT NULL DEFAULT '[]',
                artifact_ids_json TEXT NOT NULL DEFAULT '[]',
                active_mode TEXT NOT NULL DEFAULT 'general',
                turn_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """
        )


# ---------------------------------------------------------------- ORC-12 Jobs

def create_job(kind: str, *, user_id: str = "default", message: str = "Başlatıldı") -> dict[str, Any]:
    init_orchestrator_db()
    jid = f"job-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO orchestrator_jobs (job_id, user_id, kind, status, progress, message, result_json, created_at, updated_at)
            VALUES (?, ?, ?, 'queued', 0, ?, '{}', ?, ?)
            """,
            (jid, user_id, kind, message, now, now),
        )
    return get_job(jid) or {}


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    init_orchestrator_db()
    cur = get_job(job_id)
    if not cur:
        return None
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            UPDATE orchestrator_jobs
            SET status = ?, progress = ?, message = ?, result_json = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (
                status or cur["status"],
                cur["progress"] if progress is None else max(0, min(100, int(progress))),
                cur["message"] if message is None else message,
                json.dumps(cur["result"] if result is None else result, ensure_ascii=False),
                now,
                job_id,
            ),
        )
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any] | None:
    init_orchestrator_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orchestrator_jobs WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json") or "{}")
    return d


# ---------------------------------------------------------------- ORC-13 & ORC-16 Artifacts & Targeted Edit

def save_artifact(
    *,
    kind: str,
    title: str,
    sections: list[str] | None = None,
    content: str = "",
    chat_id: str = "",
    user_id: str = "default",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    init_orchestrator_db()
    aid = f"art-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    sec_list = sections if sections is not None else ([content] if content else [])
    merged = content or "\n\n".join(sec_list)
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO orchestrator_artifacts
                (artifact_id, chat_id, user_id, kind, title, version, sections_json, content, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                aid,
                chat_id,
                user_id,
                kind,
                title,
                json.dumps(sec_list, ensure_ascii=False),
                merged,
                json.dumps(metadata or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
    return get_artifact(aid) or {}


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    init_orchestrator_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orchestrator_artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["sections"] = json.loads(d.pop("sections_json") or "[]")
    d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
    return d


def list_artifacts(user_id: str = "default", chat_id: str | None = None) -> list[dict[str, Any]]:
    init_orchestrator_db()
    with _conn() as conn:
        if chat_id:
            rows = conn.execute(
                "SELECT * FROM orchestrator_artifacts WHERE user_id = ? AND chat_id = ? ORDER BY updated_at DESC",
                (user_id, chat_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM orchestrator_artifacts WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["sections"] = json.loads(d.pop("sections_json") or "[]")
        d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        out.append(d)
    return out


def apply_targeted_edit(artifact_id: str, section_index: int, new_section_content: str) -> dict[str, Any]:
    """ORC-16: Edit ONLY the target 0-based section of an artifact, keeping all other sections byte-identical."""
    art = get_artifact(artifact_id)
    if not art:
        raise KeyError(f"Artefakt bulunamadı: {artifact_id}")
    sections = list(art["sections"])
    if section_index < 0 or section_index >= len(sections):
        raise IndexError(f"Geçersiz bölüm indeksi: {section_index} (toplam {len(sections)} bölüm)")
    sections[section_index] = new_section_content
    new_ver = int(art["version"]) + 1
    merged = "\n\n".join(sections)
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            UPDATE orchestrator_artifacts
            SET version = ?, sections_json = ?, content = ?, updated_at = ?
            WHERE artifact_id = ?
            """,
            (new_ver, json.dumps(sections, ensure_ascii=False), merged, now, artifact_id),
        )
    return get_artifact(artifact_id) or {}


# ---------------------------------------------------------------- ORC-14 Conversation State Pinning

@dataclass
class ConversationState:
    chat_id: str
    user_id: str = "default"
    goals: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    active_mode: str = "general"
    turn_count: int = 0


def load_conversation_state(chat_id: str, user_id: str = "default") -> ConversationState:
    init_orchestrator_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM conversation_states WHERE chat_id = ?", (chat_id,)).fetchone()
    if not row:
        return ConversationState(chat_id=chat_id, user_id=user_id)
    return ConversationState(
        chat_id=row["chat_id"],
        user_id=row["user_id"],
        goals=json.loads(row["goals_json"] or "[]"),
        decisions=json.loads(row["decisions_json"] or "[]"),
        open_questions=json.loads(row["open_questions_json"] or "[]"),
        artifact_ids=json.loads(row["artifact_ids_json"] or "[]"),
        active_mode=row["active_mode"] or "general",
        turn_count=int(row["turn_count"] or 0),
    )


def save_conversation_state(state: ConversationState) -> None:
    init_orchestrator_db()
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO conversation_states
                (chat_id, user_id, goals_json, decisions_json, open_questions_json, artifact_ids_json, active_mode, turn_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                goals_json = excluded.goals_json,
                decisions_json = excluded.decisions_json,
                open_questions_json = excluded.open_questions_json,
                artifact_ids_json = excluded.artifact_ids_json,
                active_mode = excluded.active_mode,
                turn_count = excluded.turn_count,
                updated_at = excluded.updated_at
            """,
            (
                state.chat_id,
                state.user_id,
                json.dumps(state.goals[-10:], ensure_ascii=False),
                json.dumps(state.decisions[-15:], ensure_ascii=False),
                json.dumps(state.open_questions[-8:], ensure_ascii=False),
                json.dumps(state.artifact_ids[-20:], ensure_ascii=False),
                state.active_mode,
                int(state.turn_count),
                now,
            ),
        )


# ---------------------------------------------------------------- ORC-15 Clarification Gate

def check_clarification_needed(intent: str, user_text: str) -> list[str]:
    """ORC-15: Refuse fabricating critical numeric/domain inputs; return <= 3 focused questions."""
    low = (user_text or "").lower()
    nums = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", low)

    if intent == "finance_dcf":
        missing: list[str] = []
        if not any(k in low for k in ("nakit akışı", "cash flow", "fcf", "gelir")) or len(nums) < 2:
            missing.append("Yıllık beklenen serbest nakit akışları (FCF) veya başlangıç gelir tutarı nedir?")
        if not any(k in low for k in ("wacc", "iskonto", "discount", "%")):
            missing.append("Kullanılacak iskonto oranı (WACC, yüzde olarak) nedir?")
        if not any(k in low for k in ("büyüme", "growth", "terminal", "ufuk", "yıl")):
            missing.append("Projeksiyon süresi (yıl) ve terminal büyüme oranı nedir?")
        return missing[:3]

    if intent == "legal_info" and ("sözleşme" in low or "contract" in low or "nda" in low):
        if len(user_text.strip()) < 90:
            return [
                "İncelenecek sözleşme maddelerinin metnini paylaşabilir misin?",
                "Hangi ülke/hukuk sistemi (ör. Türkiye Cumhuriyeti kanunları) geçerlidir?",
            ]

    if intent == "cnc_engineering" and len(nums) == 0 and len(user_text.strip()) < 70:
        return [
            "Parçanın malzemesi (ör. Alüminyum 6061, Çelik 4140) ve nominal ölçü/tolerans sınıfı nedir?",
            "Teknik resim veya GD&T sembol bilgisini paylaşabilir misin?",
        ]

    return []


# ---------------------------------------------------------------- ORC-21 Memory Relevance Filtering

def filter_relevant_memories(
    query: str,
    memories: list[dict[str, Any] | str],
    *,
    threshold: float = 0.22,
    max_items: int = 5,
) -> list[dict[str, Any] | str]:
    """ORC-21: Inject only memories semantically/lexically relevant to the current query."""
    q_tokens = {w for w in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", (query or "").lower()) if len(w) >= 3}
    if not q_tokens or not memories:
        return []
    scored: list[tuple[float, dict[str, Any] | str]] = []
    for item in memories:
        txt = item.get("fact", "") if isinstance(item, dict) else str(item)
        m_tokens = {w for w in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", txt.lower()) if len(w) >= 3}
        if not m_tokens:
            continue
        overlap = len(q_tokens & m_tokens)
        score = overlap / max(1, min(len(q_tokens), len(m_tokens)))
        if score >= threshold:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:max_items]]


# ---------------------------------------------------------------- ORC-22 Feedback & ORC-23 Run Provenance

def save_run(record: dict[str, Any]) -> None:
    init_orchestrator_db()
    now = datetime.now(UTC).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO orchestrator_runs
                (run_id, chat_id, user_id, prompt, intent, mode, tier, model, provider, seed,
                 plan_json, tools_json, citations_json, verification_json, response_text, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["run_id"],
                record.get("chat_id", ""),
                record.get("user_id", "default"),
                record.get("prompt", ""),
                record.get("intent", "chat"),
                record.get("mode", "general"),
                record.get("tier", "standard"),
                record.get("model", ""),
                record.get("provider", ""),
                record.get("seed"),
                json.dumps(record.get("plan") or {}, ensure_ascii=False),
                json.dumps(record.get("tools_used") or [], ensure_ascii=False),
                json.dumps(record.get("citations") or [], ensure_ascii=False),
                json.dumps(record.get("verification") or {}, ensure_ascii=False),
                record.get("response_text", ""),
                int(record.get("latency_ms") or 0),
                now,
            ),
        )


def get_run(run_id: str) -> dict[str, Any] | None:
    init_orchestrator_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orchestrator_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["plan"] = json.loads(d.pop("plan_json") or "{}")
    d["tools_used"] = json.loads(d.pop("tools_json") or "[]")
    d["citations"] = json.loads(d.pop("citations_json") or "[]")
    d["verification"] = json.loads(d.pop("verification_json") or "{}")
    return d


def record_feedback(
    run_id: str,
    rating: int,
    *,
    reason_tags: list[str] | None = None,
    note: str = "",
    user_id: str = "default",
) -> dict[str, Any]:
    """ORC-22: Store run-linked feedback (+1/-1) with reason tags (yanlış, uzun, kaynak yok, ton)."""
    init_orchestrator_db()
    fid = f"fb-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    norm_rating = 1 if int(rating) > 0 else -1
    tags = [str(t).strip() for t in (reason_tags or []) if str(t).strip()]
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO orchestrator_feedback (feedback_id, run_id, user_id, rating, reason_tags_json, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fid, run_id, user_id, norm_rating, json.dumps(tags, ensure_ascii=False), note[:500], now),
        )
    return {"feedback_id": fid, "run_id": run_id, "rating": norm_rating, "reason_tags": tags, "created_at": now}


def feedback_summary() -> dict[str, Any]:
    init_orchestrator_db()
    with _conn() as conn:
        rows = conn.execute("SELECT rating, reason_tags_json FROM orchestrator_feedback").fetchall()
    up = sum(1 for r in rows if int(r["rating"]) > 0)
    down = sum(1 for r in rows if int(r["rating"]) < 0)
    tag_counts: dict[str, int] = {}
    for r in rows:
        for tag in json.loads(r["reason_tags_json"] or "[]"):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {"total": len(rows), "positive": up, "negative": down, "tags": tag_counts}
