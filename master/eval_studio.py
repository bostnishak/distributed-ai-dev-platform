"""EPK-02: Labeled Turkish Evaluation Dataset Registry, Dual-Annotator Studio & Cohen's Kappa."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn

router = APIRouter(prefix="/api/eval-studio", tags=["eval-studio"])
EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_eval_studio_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS eval_datasets ("
            "dataset_id TEXT PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'tr', "
            "item_count INTEGER NOT NULL DEFAULT 0, version TEXT NOT NULL DEFAULT '1.0.0', created_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS eval_annotations ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id TEXT NOT NULL, item_id TEXT NOT NULL, "
            "annotator_id TEXT NOT NULL, label TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', "
            "created_at TEXT NOT NULL, UNIQUE(dataset_id, item_id, annotator_id))"
        )


def compute_cohens_kappa(labels_a: list[str], labels_b: list[str]) -> dict[str, Any]:
    """Compute exact dual-annotator Cohen's kappa inter-rater reliability score."""
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("Etiket listeleri boş olamaz ve aynı uzunlukta olmalıdır.")
    n = len(labels_a)
    agree = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b)
    p_o = agree / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    cats = set(ca.keys()) | set(cb.keys())
    p_e = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    kappa = 1.0 if p_e >= 1.0 else (p_o - p_e) / (1.0 - p_e)
    band = (
        "almost_perfect" if kappa >= 0.81 else
        "substantial" if kappa >= 0.61 else
        "moderate" if kappa >= 0.41 else
        "fair" if kappa >= 0.21 else "poor"
    )
    return {
        "n": n,
        "observed_agreement": round(p_o, 4),
        "expected_agreement": round(p_e, 4),
        "kappa": round(kappa, 4),
        "interpretation": band,
    }


def list_eval_datasets() -> list[dict[str, Any]]:
    """Discover all JSONL benchmark datasets under eval/ plus registered studio datasets."""
    init_eval_studio_db()
    found: list[dict[str, Any]] = []
    if EVAL_DIR.is_dir():
        for p in sorted(EVAL_DIR.rglob("*.jsonl")):
            lines = [ln for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
            found.append({
                "dataset_id": p.stem,
                "path": p.relative_to(EVAL_DIR.parent).as_posix(),
                "item_count": len(lines),
                "source": "jsonl",
            })
    with _connect() as conn:
        rows = conn.execute("SELECT dataset_id, name, language, item_count, version FROM eval_datasets").fetchall()
    for r in rows:
        found.append({**dict(r), "source": "studio_db"})
    return found


def record_annotation(dataset_id: str, item_id: str, annotator_id: str, label: str, notes: str = "") -> dict[str, Any]:
    init_eval_studio_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO eval_datasets (dataset_id, name, language, item_count, version, created_at) "
            "VALUES (?, ?, 'tr', 0, '1.0.0', ?)",
            (dataset_id, dataset_id, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO eval_annotations (dataset_id, item_id, annotator_id, label, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (dataset_id, item_id, annotator_id, label.strip(), notes.strip()[:500], now),
        )
        cnt = conn.execute(
            "SELECT COUNT(DISTINCT item_id) FROM eval_annotations WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()[0]
        conn.execute("UPDATE eval_datasets SET item_count = ? WHERE dataset_id = ?", (int(cnt), dataset_id))
    return {"ok": True, "dataset_id": dataset_id, "item_id": item_id, "annotator_id": annotator_id, "label": label.strip()}


def compute_dataset_kappa(dataset_id: str, annotator_a: str, annotator_b: str) -> dict[str, Any]:
    init_eval_studio_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT a.item_id, a.label AS la, b.label AS lb "
            "FROM eval_annotations a JOIN eval_annotations b "
            "ON a.dataset_id = b.dataset_id AND a.item_id = b.item_id "
            "WHERE a.dataset_id = ? AND a.annotator_id = ? AND b.annotator_id = ?",
            (dataset_id, annotator_a, annotator_b),
        ).fetchall()
    if not rows:
        raise ValueError("İki etiketleyici için ortak etiketlenmiş öğe bulunamadı.")
    return compute_cohens_kappa([str(r["la"]) for r in rows], [str(r["lb"]) for r in rows])


def load_jsonl_dataset(rel_path: str) -> list[dict[str, Any]]:
    target = (EVAL_DIR.parent / rel_path).resolve()
    if not target.is_file():
        raise FileNotFoundError(rel_path)
    return [json.loads(ln) for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]


class AnnotateRequest(BaseModel):
    dataset_id: str = Field(..., min_length=1, max_length=64)
    item_id: str = Field(..., min_length=1, max_length=64)
    annotator_id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=64)
    notes: str = Field(default="", max_length=500)


class KappaRequest(BaseModel):
    dataset_id: str | None = Field(default=None, max_length=64)
    annotator_a: str | None = Field(default=None, max_length=64)
    annotator_b: str | None = Field(default=None, max_length=64)
    labels_a: list[str] | None = None
    labels_b: list[str] | None = None


@router.get("/datasets")
async def api_list_datasets():
    """List labeled evaluation datasets on disk and in the annotation studio."""
    ds = list_eval_datasets()
    return {"ok": True, "count": len(ds), "datasets": ds}


@router.post("/annotate")
async def api_annotate_item(body: AnnotateRequest):
    """Record a human/expert annotation label for an evaluation sample."""
    return record_annotation(body.dataset_id, body.item_id, body.annotator_id, body.label, body.notes)


@router.post("/kappa")
async def api_compute_kappa(body: KappaRequest):
    """Compute Cohen's kappa inter-annotator agreement from dataset annotations or raw label lists."""
    try:
        if body.labels_a is not None and body.labels_b is not None:
            res = compute_cohens_kappa(body.labels_a, body.labels_b)
        elif body.dataset_id and body.annotator_a and body.annotator_b:
            res = compute_dataset_kappa(body.dataset_id, body.annotator_a, body.annotator_b)
        else:
            raise ValueError("labels_a/labels_b veya dataset_id + annotator_a/b sağlanmalıdır.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **res}
