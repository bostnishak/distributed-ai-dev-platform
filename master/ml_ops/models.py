"""ML-01..ML-13: Measured ML Classifiers, Isotonic Calibrator, Leakage-Free DPO, Canary Promotion & Drift Monitor."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

import config
from log_sanitizer import redact_sensitive_text
from rag.store import normalize_turkish_text


class ModelVersionMismatchError(ValueError):
    """ML-03: Raised when a calibrator trained for model A is invoked on scores from model B."""


# ---------------------------------------------------------------- ML-01 Embedding Intent Classifier (Pure NumPy)

def _text_feature_vec(text: str, vocab: dict[str, int]) -> np.ndarray:
    v = np.zeros(len(vocab), dtype=np.float32)
    for tok in normalize_turkish_text(text).split():
        idx = vocab.get(tok)
        if idx is not None:
            v[idx] += 1.0
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


class EmbeddingIntentClassifier:
    """ML-01: Versioned, explainable centroid/logistic intent classifier returning nearest training examples."""

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version
        self.vocab: dict[str, int] = {}
        self.centroids: dict[str, np.ndarray] = {}
        self.examples: list[tuple[str, str, np.ndarray]] = []  # (label, text, vec)

    def fit(self, samples: list[tuple[str, str]]) -> dict[str, Any]:
        """Train on list of (text, label) pairs."""
        tok_set: set[str] = set()
        for txt, _ in samples:
            tok_set.update(normalize_turkish_text(txt).split())
        self.vocab = {tok: i for i, tok in enumerate(sorted(tok_set))}
        grouped: dict[str, list[np.ndarray]] = {}
        self.examples = []
        for txt, label in samples:
            vec = _text_feature_vec(txt, self.vocab)
            grouped.setdefault(label, []).append(vec)
            self.examples.append((label, txt, vec))
        self.centroids = {}
        for label, vecs in grouped.items():
            c = np.mean(np.vstack(vecs), axis=0)
            n = float(np.linalg.norm(c))
            self.centroids[label] = c / n if n > 0 else c
        return {"version": self.version, "classes": len(self.centroids), "samples": len(samples)}

    def predict(self, text: str, *, uncertainty_threshold: float = 0.25) -> dict[str, Any]:
        if not self.centroids:
            return {"label": "unknown", "confidence": 0.0, "uncertain": True, "nearest_examples": []}
        q = _text_feature_vec(text, self.vocab)
        scores = {lbl: float(q @ c) for lbl, c in self.centroids.items()}
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_lbl, best_sc = ranked[0]
        second_sc = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_sc - second_sc
        nearest = sorted(
            ((float(q @ vec), lbl, ex_txt) for lbl, ex_txt, vec in self.examples),
            key=lambda x: x[0],
            reverse=True,
        )[:3]
        return {
            "label": best_lbl,
            "confidence": round(max(0.0, min(1.0, best_sc)), 4),
            "margin": round(margin, 4),
            "uncertain": best_sc < uncertainty_threshold or margin < 0.05,
            "nearest_examples": [{"label": lbl, "text": t, "sim": round(s, 3)} for s, lbl, t in nearest],
            "version": self.version,
        }

    def evaluate_macro_f1(self, test_samples: list[tuple[str, str]]) -> dict[str, Any]:
        tp: Counter[str] = Counter()
        fp: Counter[str] = Counter()
        fn: Counter[str] = Counter()
        labels: set[str] = set()
        for txt, true_lbl in test_samples:
            labels.add(true_lbl)
            pred = self.predict(txt)["label"]
            labels.add(pred)
            if pred == true_lbl:
                tp[true_lbl] += 1
            else:
                fp[pred] += 1
                fn[true_lbl] += 1
        per_class: dict[str, float] = {}
        for lbl in sorted(labels):
            p = tp[lbl] / max(1, tp[lbl] + fp[lbl])
            r = tp[lbl] / max(1, tp[lbl] + fn[lbl])
            per_class[lbl] = round((2 * p * r) / max(1e-9, p + r), 4) if (p + r) > 0 else 0.0
        macro = round(sum(per_class.values()) / max(1, len(per_class)), 4)
        return {"macro_f1": macro, "per_class_f1": per_class}


# ---------------------------------------------------------------- ML-02 Difficulty Estimator

class DifficultyEstimator:
    """ML-02: Classify prompts into easy/medium/hard for cost-quality tiering (ORC-19 & GW-19)."""

    _HARD_SIGNALS = ("dcf", "wacc", "karşılaştır", "mimari", "fullstack", "proje", "sözleşme", "kanun", "gd&t", "araştır", "kanıt")
    _EASY_SIGNALS = ("merhaba", "selam", "kısaca", "tek cümle", "çevir", "özetle", "nedir")

    def predict(self, prompt: str) -> dict[str, Any]:
        low = normalize_turkish_text(prompt)
        words = low.split()
        hard_hits = sum(1 for k in self._HARD_SIGNALS if k in low)
        easy_hits = sum(1 for k in self._EASY_SIGNALS if k in low)
        if hard_hits >= 1 or len(words) >= 24:
            return {"difficulty": "hard", "recommended_tier": "verified"}
        if easy_hits >= 1 and len(words) <= 10:
            return {"difficulty": "easy", "recommended_tier": "fast"}
        return {"difficulty": "medium", "recommended_tier": "standard"}


# ---------------------------------------------------------------- ML-03 Isotonic Confidence Calibrator

class ConfidenceCalibrator:
    """ML-03: Pool-Adjacent-Violators (PAV) isotonic calibrator with strict model-version guard."""

    def __init__(self, model_version: str) -> None:
        self.model_version = model_version
        self._x_knots: list[float] = []
        self._y_vals: list[float] = []

    def fit(self, raw_scores: list[float], labels: list[int]) -> dict[str, float]:
        pairs = sorted(zip(raw_scores, labels, strict=False), key=lambda p: p[0])
        # PAV algorithm for monotonic non-decreasing probability calibration
        blocks: list[list[float]] = []  # [sum_y, count, max_x]
        for x, y in pairs:
            blocks.append([float(y), 1.0, float(x)])
            while len(blocks) >= 2 and (blocks[-2][0] / blocks[-2][1]) > (blocks[-1][0] / blocks[-1][1]):
                b2 = blocks.pop()
                blocks[-1][0] += b2[0]
                blocks[-1][1] += b2[1]
                blocks[-1][2] = b2[2]
        self._x_knots = [b[2] for b in blocks]
        self._y_vals = [b[0] / b[1] for b in blocks]
        cal = [self.calibrate(s, model_version=self.model_version) for s in raw_scores]
        return {
            "ece_before": compute_ece(raw_scores, labels),
            "ece_after": compute_ece(cal, labels),
            "brier_before": compute_brier(raw_scores, labels),
            "brier_after": compute_brier(cal, labels),
        }

    def calibrate(self, score: float, *, model_version: str | None = None) -> float:
        if model_version is not None and model_version != self.model_version:
            raise ModelVersionMismatchError(
                f"Kalibratör sürüm uyuşmazlığı: beklenen={self.model_version}, gelen={model_version}"
            )
        if not self._x_knots:
            return round(max(0.0, min(1.0, float(score))), 4)
        for xk, yv in zip(self._x_knots, self._y_vals, strict=False):
            if score <= xk:
                return round(max(0.01, min(0.99, yv)), 4)
        return round(max(0.01, min(0.99, self._y_vals[-1])), 4)


def compute_ece(probs: list[float], labels: list[int], n_bins: int = 10) -> float:
    if not probs:
        return 0.0
    n = len(probs)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idxs = [i for i, p in enumerate(probs) if (lo <= p < hi) or (b == n_bins - 1 and p == 1.0)]
        if not idxs:
            continue
        avg_p = sum(probs[i] for i in idxs) / len(idxs)
        avg_y = sum(labels[i] for i in idxs) / len(idxs)
        ece += (len(idxs) / n) * abs(avg_p - avg_y)
    return round(ece, 4)


def compute_brier(probs: list[float], labels: list[int]) -> float:
    if not probs:
        return 0.0
    return round(sum((p - y) ** 2 for p, y in zip(probs, labels, strict=False)) / len(probs), 4)


# ---------------------------------------------------------------- ML-04, 05, 06 Eval-Gated Promotion Policy

def check_ml_promotion_gate(
    *,
    component: str,
    baseline_metric: float,
    candidate_metric: float,
    min_gain: float,
) -> dict[str, Any]:
    """ML-04/05/06/08: Never promote a fine-tuned reranker, NLI model, embedder, or LoRA without measured eval gain."""
    gain = round(candidate_metric - baseline_metric, 4)
    promote = gain >= min_gain
    return {
        "component": component,
        "promote": promote,
        "baseline": baseline_metric,
        "candidate": candidate_metric,
        "gain": gain,
        "required_gain": min_gain,
        "reason": "Eval kazancı doğrulandı; yayına uygun." if promote else "Yeterli eval kazancı yok; varsayılan kapalı kalır.",
    }


# ---------------------------------------------------------------- ML-07 Leakage-Free DPO Dataset Builder

def build_dpo_dataset(
    approved_corrections: list[dict[str, Any]],
    *,
    golden_prompts: set[str] | None = None,
) -> dict[str, Any]:
    """ML-07: Build PII-scrubbed, eval-leakage-checked DPO preference pairs with SHA-256 dataset hash."""
    blocked_norm = {normalize_turkish_text(p) for p in (golden_prompts or set())}
    pairs: list[dict[str, str]] = []
    rejected_leakage = 0

    for item in approved_corrections:
        if not item.get("approved"):
            continue
        prompt = redact_sensitive_text(str(item.get("prompt") or "")).strip()
        if not prompt:
            continue
        if normalize_turkish_text(prompt) in blocked_norm:
            rejected_leakage += 1
            continue
        pairs.append({
            "prompt": prompt,
            "chosen": redact_sensitive_text(str(item.get("corrected_answer") or "")).strip(),
            "rejected": redact_sensitive_text(str(item.get("bad_answer") or "")).strip(),
        })

    blob = "\n".join(json.dumps(p, ensure_ascii=False, sort_keys=True) for p in pairs)
    ds_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return {
        "count": len(pairs),
        "rejected_eval_leakage": rejected_leakage,
        "dataset_hash": ds_hash,
        "pairs": pairs,
    }


# ---------------------------------------------------------------- ML-08, 09, 10 Adapter Registry, Canary Rollback & Verified Synthetic Factory

def _ml_db_path() -> Path:
    p = Path(config.DATA_DIR) / "ml_ops.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _ml_conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_ml_db_path()), timeout=10.0)
    c.row_factory = sqlite3.Row
    return c


def init_ml_db() -> None:
    with _ml_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ml_model_registry (
                model_id TEXT PRIMARY KEY,
                base_model TEXT NOT NULL,
                adapter_name TEXT NOT NULL,
                dataset_hash TEXT NOT NULL,
                hyperparams_json TEXT NOT NULL,
                eval_report_path TEXT NOT NULL,
                eval_score REAL NOT NULL,
                baseline_score REAL NOT NULL,
                status TEXT NOT NULL,
                canary_traffic_pct INTEGER NOT NULL DEFAULT 0,
                owner TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS active_learning_queue (
                item_id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                predicted_intent TEXT NOT NULL,
                uncertainty REAL NOT NULL,
                priority_score REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                human_label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )


def register_and_gate_adapter(
    *,
    base_model: str,
    adapter_name: str,
    dataset_hash: str,
    hyperparams: dict[str, Any],
    eval_report_path: str,
    eval_score: float,
    baseline_score: float,
    owner: str = "system",
) -> dict[str, Any]:
    """ML-08 & ML-10: Register reproducible adapter metadata; promote to 10% canary ONLY if eval beats baseline."""
    init_ml_db()
    mid = f"mdl-{uuid.uuid4().hex[:10]}"
    promoted = eval_score > baseline_score
    status = "canary" if promoted else "rejected"
    canary_pct = 10 if promoted else 0
    now = datetime.now(UTC).isoformat()
    with _ml_conn() as conn:
        conn.execute(
            """
            INSERT INTO ml_model_registry
                (model_id, base_model, adapter_name, dataset_hash, hyperparams_json, eval_report_path,
                 eval_score, baseline_score, status, canary_traffic_pct, owner, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mid, base_model, adapter_name, dataset_hash, json.dumps(hyperparams, sort_keys=True),
                eval_report_path, float(eval_score), float(baseline_score), status, canary_pct, owner, now,
            ),
        )
    return {"model_id": mid, "status": status, "canary_traffic_pct": canary_pct, "promoted": promoted}


def evaluate_canary_health(model_id: str, *, canary_error_rate: float, baseline_error_rate: float) -> dict[str, Any]:
    """ML-08: Automatically roll back a canary adapter if error rate worsens relative to baseline."""
    init_ml_db()
    rollback = canary_error_rate > baseline_error_rate + 0.02
    new_status = "rolled_back" if rollback else "promoted"
    new_pct = 0 if rollback else 100
    with _ml_conn() as conn:
        conn.execute(
            "UPDATE ml_model_registry SET status = ?, canary_traffic_pct = ? WHERE model_id = ?",
            (new_status, new_pct, model_id),
        )
    return {"model_id": model_id, "rolled_back": rollback, "status": new_status, "canary_traffic_pct": new_pct}


def list_registered_models() -> list[dict[str, Any]]:
    init_ml_db()
    with _ml_conn() as conn:
        rows = conn.execute("SELECT * FROM ml_model_registry ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def build_verified_synthetic_dataset(candidates: list[dict[str, Any]], verifier_fn) -> dict[str, Any]:
    """ML-09: Keep ONLY 100% verifier-passing, deduplicated synthetic examples."""
    kept: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    duplicates = 0
    failed_verify = 0
    for item in candidates:
        if not verifier_fn(item):
            failed_verify += 1
            continue
        h = hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        if h in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(h)
        kept.append(item)
    return {
        "kept_count": len(kept),
        "failed_verify": failed_verify,
        "duplicates_removed": duplicates,
        "pass_rate": 1.0 if kept else 0.0,
        "items": kept,
    }


# ---------------------------------------------------------------- ML-11 Drift Monitor, ML-12 Active Learning, ML-13 Distillation

def detect_distribution_drift(baseline_counts: dict[str, int], current_counts: dict[str, int], *, psi_threshold: float = 0.20) -> dict[str, Any]:
    """ML-11: Population Stability Index (PSI) drift detector across intent/confidence buckets."""
    keys = sorted(set(baseline_counts) | set(current_counts))
    tot_b = max(1, sum(baseline_counts.values()))
    tot_c = max(1, sum(current_counts.values()))
    psi = 0.0
    for k in keys:
        pb = max(1e-4, baseline_counts.get(k, 0) / tot_b)
        pc = max(1e-4, current_counts.get(k, 0) / tot_c)
        psi += (pc - pb) * math.log(pc / pb)
    psi = round(psi, 4)
    return {
        "psi": psi,
        "drift_detected": psi >= psi_threshold,
        "recommendation": "Sınıflandırıcıyı yeniden eğitin ve eşikleri kalibre edin." if psi >= psi_threshold else "Dağılım kararlı.",
    }


def enqueue_active_learning(prompt: str, predicted_intent: str, *, uncertainty: float, user_corrected: bool = False) -> dict[str, Any]:
    """ML-12: Prioritize uncertain and user-corrected samples for human labeling."""
    init_ml_db()
    iid = f"alq-{uuid.uuid4().hex[:10]}"
    priority = round(min(1.0, float(uncertainty) + (0.35 if user_corrected else 0.0)), 4)
    now = datetime.now(UTC).isoformat()
    with _ml_conn() as conn:
        conn.execute(
            """
            INSERT INTO active_learning_queue (item_id, prompt, predicted_intent, uncertainty, priority_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (iid, prompt[:500], predicted_intent, float(uncertainty), priority, now),
        )
    return {"item_id": iid, "priority_score": priority}


def list_active_learning_queue(limit: int = 20) -> list[dict[str, Any]]:
    init_ml_db()
    with _ml_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM active_learning_queue WHERE status = 'pending' ORDER BY priority_score DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


_ALLOWED_TEACHER_LICENSES = frozenset({"apache-2.0", "mit", "bsd-3-clause", "local-self-9b"})


def check_distillation_policy(teacher_license: str, student_score: float, teacher_score: float) -> dict[str, Any]:
    """ML-13: Enforce open/permitted teacher license and >= 90% teacher retention gate."""
    lic_ok = teacher_license.strip().lower() in _ALLOWED_TEACHER_LICENSES
    ratio = round(student_score / max(1e-6, teacher_score), 4)
    return {
        "license_ok": lic_ok,
        "retention_ratio": ratio,
        "approved": lic_ok and ratio >= 0.90,
    }
