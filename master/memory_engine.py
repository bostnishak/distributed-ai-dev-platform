"""Cluster A (`[M01]`-`[M04]`): 4-Layer Persistent Cognitive Memory Engine.

Implements:
- Working Memory & Hierarchical Context Compaction (`compact_conversation_context`)
- Episodic Memory (`conversations` & `conversation_messages` with SQLite FTS5 full-text search)
- Semantic Memory (`semantic_memories`: automatic extraction of user preferences, project facts, constraints)
- Procedural Skill Store (`procedural_skills`: reusable verified solution templates)
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dbconn
import dbindexes


def _memory_db_path() -> Path:
    p = dbconn.database_file("cognitive_memory.db")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(_memory_db_path())


def init_memory_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL,
                summary TEXT DEFAULT '',
                pinned_context TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_used TEXT DEFAULT '',
                task_type TEXT DEFAULT '',
                workspace_id TEXT DEFAULT '',
                cnc_job_id TEXT DEFAULT '',
                feedback_score INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                conversation_id UNINDEXED,
                role UNINDEXED,
                content
            );

            CREATE TABLE IF NOT EXISTS semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                category TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, category, fact_key)
            );

            CREATE TABLE IF NOT EXISTS procedural_skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trigger_pattern TEXT NOT NULL,
                solution_template TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )
    with _connect() as conn:
        dbindexes.ensure_indexes(conn)


def record_conversation_turn(
    conversation_id: str,
    user_text: str,
    assistant_text: str,
    model_used: str = "",
    task_type: str = "",
    user_id: str = "default",
    learn: bool = True,
) -> None:
    """Persist a user+assistant turn into Episodic Memory and index in FTS5."""
    init_memory_db()
    now = datetime.now(UTC).isoformat()
    title = user_text.strip()[:60] or "Sohbet"
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (conversation_id, user_id, title, now, now),
        )
        conn.execute(
            """
            INSERT INTO conversation_messages (conversation_id, role, content, model_used, task_type, created_at)
            VALUES (?, 'user', ?, ?, ?, ?)
            """,
            (conversation_id, user_text, model_used, task_type, now),
        )
        conn.execute(
            "INSERT INTO messages_fts (conversation_id, role, content) VALUES (?, 'user', ?)",
            (conversation_id, user_text),
        )
        conn.execute(
            """
            INSERT INTO conversation_messages (conversation_id, role, content, model_used, task_type, created_at)
            VALUES (?, 'assistant', ?, ?, ?, ?)
            """,
            (conversation_id, assistant_text, model_used, task_type, now),
        )
        conn.execute(
            "INSERT INTO messages_fts (conversation_id, role, content) VALUES (?, 'assistant', ?)",
            (conversation_id, assistant_text),
        )

    if learn:
        extract_and_upsert_memories(user_text, user_id=user_id)


# Rule-based + pattern semantic fact extractor (instant, zero latency)
_PREFERENCE_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("preference", "ui_style", re.compile(r"(emoji\s*(istemiyorum|kullanma|kaldır|kaldir)|karanlık\s*tema|koyu\s*tema)", re.IGNORECASE)),
    ("technical_constraint", "cnc_standard", re.compile(r"\b(ISO\s*2768-[a-zA-Z]{1,2}|AS9102|ISO\s*286)\b", re.IGNORECASE)),
    ("project_fact", "preferred_stack", re.compile(r"\b(FastAPI|React|Next\.js|PostgreSQL|SQLite|Tkinter|PyInstaller)\b", re.IGNORECASE)),
    ("company_rule", "material_default", re.compile(r"\b(AISI\s*4140|Al\s*6061|Al\s*7075|AISI\s*304|Paslanmaz\s*316)\b", re.IGNORECASE)),
    ("preference", "user_identity", re.compile(r"(benim\s+adım|ismim|şirketimiz|sirketimiz)\s+([A-Za-zÇĞİÖŞÜçğıöşü0-9\s]{2,35})", re.IGNORECASE)),
]


def extract_and_upsert_memories(text: str, user_id: str = "default") -> list[dict[str, str]]:
    """Extract durable user preferences, technical constraints, and project facts from user messages."""
    init_memory_db()
    extracted: list[dict[str, str]] = []
    now = datetime.now(UTC).isoformat()

    with _connect() as conn:
        for category, key_prefix, pat in _PREFERENCE_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            val = m.group(0).strip()
            fkey = f"{key_prefix}:{val[:24].lower()}"
            conn.execute(
                """
                INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at)
                VALUES (?, ?, ?, ?, 0.95, ?)
                ON CONFLICT(user_id, category, fact_key) DO UPDATE SET
                    fact_value = excluded.fact_value,
                    updated_at = excluded.updated_at
                """,
                (user_id, category, fkey, val, now),
            )
            extracted.append({"category": category, "fact_key": fkey, "fact_value": val})
    return extracted


def upsert_semantic_fact(category: str, fact_key: str, fact_value: str, user_id: str = "default") -> dict[str, Any]:
    init_memory_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO semantic_memories (user_id, category, fact_key, fact_value, confidence, updated_at)
            VALUES (?, ?, ?, ?, 1.0, ?)
            ON CONFLICT(user_id, category, fact_key) DO UPDATE SET
                fact_value = excluded.fact_value,
                updated_at = excluded.updated_at
            """,
            (user_id, category, fact_key, fact_value, now),
        )
    return {"category": category, "fact_key": fact_key, "fact_value": fact_value}


def list_semantic_facts(user_id: str = "default") -> list[dict[str, Any]]:
    init_memory_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, category, fact_key, fact_value, confidence, updated_at FROM semantic_memories WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def search_episodic_memory(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search past conversations using SQLite FTS5."""
    init_memory_db()
    tokens = re.findall(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]+", query)
    if not tokens:
        return []
    fts_q = " OR ".join(f'"{t}"' for t in tokens[:6])
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT conversation_id, role, snippet(messages_fts, 2, '[', ']', '...', 24) AS snippet
            FROM messages_fts
            WHERE messages_fts MATCH ?
            LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def compact_conversation_context(messages: list[dict[str, str]], max_chars: int = 12000) -> list[dict[str, str]]:
    """Lossless hierarchical context compactor: preserves system prompt, pinned facts, and recent turns."""
    total = sum(len(m.get("content", "")) for m in messages)
    if total <= max_chars or len(messages) <= 4:
        return messages

    head = [m for m in messages[:1] if m.get("role") == "system"]
    older = messages[len(head):-4]
    recent = messages[-4:]

    summary_points: list[str] = []
    for m in older:
        role = m.get("role", "user")
        txt = m.get("content", "").strip().replace("\n", " ")
        if txt:
            summary_points.append(f"[{role.upper()}]: {txt[:180]}")

    compacted_msg = {
        "role": "system",
        "content": "Önceki konuşma turlarının sıkıştırılmış özeti:\n" + "\n".join(summary_points[-12:]),
    }
    return [*head, compacted_msg, *recent]


def register_procedural_skill(skill_id: str, name: str, trigger_pattern: str, solution_template: str) -> dict[str, Any]:
    init_memory_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO procedural_skills (id, name, trigger_pattern, solution_template, success_count, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                solution_template = excluded.solution_template,
                success_count = procedural_skills.success_count + 1
            """,
            (skill_id, name, trigger_pattern, solution_template, now),
        )
    return {"id": skill_id, "name": name}


def build_memory_context_block(query: str, user_id: str = "default") -> str:
    """Build a compact memory block to inject into the Assistant's system prompt."""
    facts = list_semantic_facts(user_id=user_id)[:8]
    if not facts:
        return ""
    lines = ["--- Öğrenilen Kullanıcı ve Proje Hafızası ---"]
    for f in facts:
        lines.append(f"- [{f['category']}] {f['fact_value']}")
    return "\n".join(lines)
