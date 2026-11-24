"""EPK-19: Persistent SM-2 Spaced Repetition Flashcards & Rubric-Weighted Exam Autograder."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import dbconn
import user_profile

router = APIRouter(prefix="/api/education", tags=["education-sm2"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_education_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS edu_flashcards ("
            "card_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, topic TEXT NOT NULL, "
            "front TEXT NOT NULL, back TEXT NOT NULL, repetitions INTEGER NOT NULL DEFAULT 0, "
            "interval_days INTEGER NOT NULL DEFAULT 1, ease_factor REAL NOT NULL DEFAULT 2.5, "
            "next_review_at TEXT NOT NULL, created_at TEXT NOT NULL)"
        )


def sm2_schedule(quality: int, repetitions: int, interval_days: int, ease_factor: float) -> tuple[int, int, float]:
    """Exact SuperMemo-2 (SM-2) spaced repetition update for recall quality 0..5."""
    q = max(0, min(5, int(quality)))
    ef = max(1.3, ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    if q < 3:
        return 0, 1, round(ef, 3)
    new_reps = repetitions + 1
    new_interval = 1 if new_reps == 1 else (6 if new_reps == 2 else round(interval_days * ef))
    return new_reps, max(1, int(new_interval)), round(ef, 3)


def create_flashcard(user_id: str, topic: str, front: str, back: str) -> dict[str, Any]:
    init_education_db()
    uid = user_profile.valid_user_id(user_id)
    cid = f"card_{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO edu_flashcards "
            "(card_id, user_id, topic, front, back, repetitions, interval_days, ease_factor, next_review_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, 1, 2.5, ?, ?)",
            (cid, uid, topic.strip() or "Genel", front.strip(), back.strip(), now, now),
        )
    return {"ok": True, "card_id": cid, "user_id": uid, "topic": topic, "interval_days": 1, "ease_factor": 2.5}


def review_flashcard(card_id: str, user_id: str, quality: int) -> dict[str, Any]:
    init_education_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT repetitions, interval_days, ease_factor FROM edu_flashcards WHERE card_id = ? AND user_id = ?",
            (card_id, uid),
        ).fetchone()
        if not row:
            raise KeyError(f"Kart bulunamadı: {card_id}")
        reps, interval, ef = sm2_schedule(quality, int(row["repetitions"]), int(row["interval_days"]), float(row["ease_factor"]))
        next_due = (datetime.now(UTC) + timedelta(days=interval)).isoformat()
        conn.execute(
            "UPDATE edu_flashcards SET repetitions = ?, interval_days = ?, ease_factor = ?, next_review_at = ? "
            "WHERE card_id = ? AND user_id = ?",
            (reps, interval, ef, next_due, card_id, uid),
        )
    return {"ok": True, "card_id": card_id, "repetitions": reps, "interval_days": interval, "ease_factor": ef, "next_review_at": next_due}


def list_flashcards(user_id: str) -> list[dict[str, Any]]:
    init_education_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM edu_flashcards WHERE user_id = ? ORDER BY next_review_at ASC",
            (uid,),
        ).fetchall()
    return [dict(r) for r in rows]


def grade_exam_submission(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic rubric + answer-key autograder across multiple-choice and open-ended rubric items."""
    total_pts = 0.0
    earned_pts = 0.0
    details: list[dict[str, Any]] = []
    for idx, q in enumerate(questions, start=1):
        weight = float(q.get("points", 10.0))
        total_pts += weight
        ans = str(q.get("student_answer") or "").strip().lower()
        key = str(q.get("expected_key") or "").strip().lower()
        rubric = [str(r).strip().lower() for r in (q.get("rubric_keywords") or []) if str(r).strip()]
        if key:
            ratio = 1.0 if ans == key else 0.0
        elif rubric:
            matched = sum(1 for kw in rubric if kw in ans)
            ratio = matched / len(rubric)
        else:
            ratio = 0.0
        score = round(weight * ratio, 2)
        earned_pts += score
        details.append({"question": idx, "earned": score, "possible": weight, "pct": round(ratio * 100.0, 1)})
    pct = round((earned_pts / max(1e-9, total_pts)) * 100.0, 2) if total_pts > 0 else 0.0
    return {"ok": True, "earned_points": round(earned_pts, 2), "total_points": round(total_pts, 2), "score_pct": pct, "details": details}


class FlashcardCreateRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    topic: str = Field(default="Genel", max_length=80)
    front: str = Field(..., min_length=1, max_length=1000)
    back: str = Field(..., min_length=1, max_length=2000)


class FlashcardReviewRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    quality: int = Field(..., ge=0, le=5)


class ExamGradeRequest(BaseModel):
    questions: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/flashcards")
async def api_list_flashcards(user_id: str = Query(default="default")):
    """List user's SM-2 spaced-repetition flashcards ordered by next due review."""
    try:
        cards = list_flashcards(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "count": len(cards), "flashcards": cards}


@router.post("/flashcards")
async def api_create_flashcard(body: FlashcardCreateRequest):
    """Create a persistent SM-2 spaced-repetition flashcard."""
    try:
        return create_flashcard(body.user_id, body.topic, body.front, body.back)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/flashcards/{card_id}/review")
async def api_review_flashcard(card_id: str, body: FlashcardReviewRequest):
    """Apply SM-2 spaced-repetition scheduling update for recall quality 0..5."""
    try:
        return review_flashcard(card_id, body.user_id, body.quality)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/grade-exam")
async def api_grade_exam(body: ExamGradeRequest):
    """Grade multiple-choice and rubric-keyword exam questions deterministically."""
    return grade_exam_submission(body.questions)
