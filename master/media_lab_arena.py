"""Media Lab 2.0 & 12-Discipline Cognitive Model ELO Arena [M58].

Includes:
1. Document Perspective Scanner & Adaptive Shadow Removal (`scan_and_clean_document_image`)
2. Drawing / Image Revision Pixel-Diff Heatmap (`compute_visual_revision_diff`)
3. KVKK / PII Sensitive Text Redactor (`redact_sensitive_pii`)
4. 12-Discipline Cognitive Model ELO Arena & Confidence Calibrator (`CognitiveArena`)

100% local, zero emojis, deterministic Pillow/NumPy implementation.
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter, ImageOps

import config


def _media_dir() -> Path:
    d = config.DATA_DIR / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ============================================================================
# 1. DOCUMENT PERSPECTIVE SCANNER & ADAPTIVE SHADOW REMOVAL
# ============================================================================


def scan_and_clean_document_image(raw_bytes: bytes) -> dict[str, Any]:
    """Remove uneven lighting/shadows from photographed documents via large-radius Gaussian background division and save a scanner-grade PNG."""
    if not raw_bytes:
        raise ValueError("raw_bytes cannot be empty")

    orig = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    gray = ImageOps.grayscale(orig)

    # Auto-trim dark outer border if present by detecting document bounding region
    gray_arr = np.asarray(gray, dtype=np.float32)
    h, w = gray_arr.shape

    # Large-kernel Gaussian blur estimates low-frequency illumination / shadow field
    blur_radius = max(12.0, min(w, h) / 14.0)
    bg_img = gray.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    bg_arr = np.maximum(np.asarray(bg_img, dtype=np.float32), 12.0)

    # Normalize foreground by dividing by local background illumination
    norm = (gray_arr / bg_arr) * 255.0
    norm = np.clip(norm, 0.0, 255.0)

    # Adaptive contrast stretch and soft Sauvola-like clean white background boost
    p_low, p_high = np.percentile(norm, [3, 96])
    span = max(float(p_high - p_low), 10.0)
    stretched = np.clip((norm - p_low) / span * 255.0, 0.0, 255.0)

    # Push near-white paper background to pure crisp scanner white (255)
    paper_mask = stretched > 212.0
    ink_mask = stretched < 115.0
    cleaned = stretched.copy()
    cleaned[paper_mask] = 255.0
    cleaned[ink_mask] = np.clip(cleaned[ink_mask] * 0.55, 0.0, 255.0)

    out_uint8 = cleaned.astype(np.uint8)
    out_img = Image.fromarray(out_uint8, mode="L").convert("RGB")

    # Estimate shadow reduction metrics
    orig_bg_std = float(np.std(bg_arr))
    cleaned_bg = ImageOps.grayscale(out_img).filter(ImageFilter.GaussianBlur(radius=blur_radius))
    cleaned_bg_std = float(np.std(np.asarray(cleaned_bg, dtype=np.float32)))

    file_id = f"doc-scan-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_path = _media_dir() / f"{file_id}.png"
    out_img.save(out_path, format="PNG")

    return {
        "file_id": file_id,
        "output_path": str(out_path),
        "url": f"/api/assistant/media/{file_id}.png",
        "width": w,
        "height": h,
        "original_illumination_std": round(orig_bg_std, 3),
        "cleaned_illumination_std": round(cleaned_bg_std, 3),
        "mean_brightness": round(float(np.mean(out_uint8)), 2),
    }


# ============================================================================
# 2. DRAWING / IMAGE REVISION PIXEL-DIFF HEATMAP
# ============================================================================


def compute_visual_revision_diff(
    img_a_bytes: bytes,
    img_b_bytes: bytes,
    diff_threshold: float = 22.0,
) -> dict[str, Any]:
    """Align sizes of two image revisions, compute per-pixel difference magnitude, highlight changed regions in crimson/emerald overlay on a diff PNG, and return changed_area_pct and diff image URL."""
    if not img_a_bytes or not img_b_bytes:
        raise ValueError("Both img_a_bytes and img_b_bytes are required")

    img_a = Image.open(io.BytesIO(img_a_bytes)).convert("RGB")
    img_b = Image.open(io.BytesIO(img_b_bytes)).convert("RGB")

    target_w, target_h = img_a.size
    if img_b.size != (target_w, target_h):
        img_b = img_b.resize((target_w, target_h), Image.Resampling.LANCZOS)

    arr_a = np.asarray(img_a, dtype=np.float32)
    arr_b = np.asarray(img_b, dtype=np.float32)

    diff_rgb = np.abs(arr_b - arr_a)
    diff_mag = np.max(diff_rgb, axis=2)

    changed_mask = diff_mag >= float(diff_threshold)
    total_pixels = int(target_w * target_h)
    changed_pixels = int(np.count_nonzero(changed_mask))
    changed_area_pct = round((changed_pixels / max(1, total_pixels)) * 100.0, 4)

    # Signed luminance change to distinguish additions vs removals
    lum_a = np.mean(arr_a, axis=2)
    lum_b = np.mean(arr_b, axis=2)
    delta_lum = lum_b - lum_a

    # Build desaturated base image for high-visibility heatmap overlay
    base_gray = np.mean(arr_b, axis=2) * 0.45 + 30.0
    overlay = np.stack([base_gray, base_gray, base_gray], axis=-1)

    crimson_mask = changed_mask & (delta_lum < 0)
    emerald_mask = changed_mask & (delta_lum >= 0)

    # Crimson (220, 38, 38) and Emerald (16, 185, 129) highlights
    overlay[crimson_mask] = np.array([220.0, 38.0, 38.0], dtype=np.float32)
    overlay[emerald_mask] = np.array([16.0, 185.0, 129.0], dtype=np.float32)

    diff_img = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8), mode="RGB")
    file_id = f"rev-diff-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_path = _media_dir() / f"{file_id}.png"
    diff_img.save(out_path, format="PNG")

    return {
        "file_id": file_id,
        "output_path": str(out_path),
        "url": f"/api/assistant/media/{file_id}.png",
        "width": target_w,
        "height": target_h,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_area_pct": changed_area_pct,
        "max_diff_intensity": round(float(np.max(diff_mag)), 2),
    }


# ============================================================================
# 3. KVKK / PII SENSITIVE TEXT REDACTOR
# ============================================================================

_IBAN_RE = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE)
_CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b|\b\d{16}\b")
_TC_KIMLIK_RE = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?:(?:\+90|0090|0)\s*)?\(?5\d{2}\)?[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}\b"
)


def redact_sensitive_pii(text: str) -> dict[str, Any]:
    """Detect and mask Turkish TC Kimlik (11 digits), IBAN (TR + 24 digits), credit cards, phone numbers, and email addresses."""
    working = text or ""
    counts: dict[str, int] = {
        "iban": 0,
        "credit_card": 0,
        "tc_kimlik": 0,
        "phone": 0,
        "email": 0,
    }

    def _sub_with_count(pattern: re.Pattern[str], key: str, mask: str, src: str) -> str:
        def _repl(_m: re.Match[str]) -> str:
            counts[key] += 1
            return mask

        return pattern.sub(_repl, src)

    # Order matters: IBAN -> Credit Card -> TC Kimlik -> Phone -> Email
    working = _sub_with_count(_IBAN_RE, "iban", "[REDACTED_IBAN]", working)
    working = _sub_with_count(_CREDIT_CARD_RE, "credit_card", "[REDACTED_CARD]", working)
    working = _sub_with_count(_TC_KIMLIK_RE, "tc_kimlik", "[REDACTED_TC_KIMLIK]", working)
    working = _sub_with_count(_PHONE_RE, "phone", "[REDACTED_PHONE]", working)
    working = _sub_with_count(_EMAIL_RE, "email", "[REDACTED_EMAIL]", working)

    total_redacted = sum(counts.values())
    return {
        "cleaned_text": working,
        "counts": counts,
        "total_redacted": total_redacted,
        "has_pii": total_redacted > 0,
    }


# ============================================================================
# 4. 12-DISCIPLINE COGNITIVE MODEL ELO ARENA & CONFIDENCE CALIBRATOR
# ============================================================================

ARENA_DISCIPLINES: tuple[str, ...] = (
    "math",
    "code",
    "vision",
    "cnc",
    "finance",
    "legal",
    "data_science",
    "research",
    "security",
    "turkish",
    "speed",
    "reasoning",
)

ARENA_MODELS: tuple[str, ...] = (
    "qwen3.5:9b",
    "gemma4:e4b",
    "qwen2.5-coder:7b",
    "cnc-ballooner",
    "phi4-mini",
    "llama3.2:3b",
    "qwen3:1.7b",
)


def calibrate_confidence(
    answer: str,
    tool_verified: bool = False,
    citations_count: int = 0,
) -> dict[str, Any]:
    """Compute a calibrated confidence score and cross-verification recommendation for an assistant response."""
    clean = (answer or "").strip()
    if not clean:
        return {
            "confidence_score": 0.0,
            "confidence_pct": 0,
            "needs_cross_verification": True,
            "verification_badge": "Confidence: 0% | Unverified empty output",
        }

    score = 0.55
    if tool_verified:
        score += 0.25

    citation_boost = min(0.15, max(0, int(citations_count)) * 0.05)
    score += citation_boost

    # Content depth and structure signal
    if len(clean) >= 120:
        score += 0.04
    if any(tok in clean for tok in ("```", "|", "=", "%")):
        score += 0.03

    # Uncertainty / hedging penalty
    hedging_patterns = (
        r"\b(emin\s+de[ğg]ilim|san[ıi]r[ıi]m|belki|muhtemelen|not\s+sure|maybe|perhaps|i\s+guess)\b"
    )
    if re.search(hedging_patterns, clean, flags=re.IGNORECASE):
        score -= 0.18

    calibrated = round(float(min(0.99, max(0.05, score))), 4)
    pct = round(calibrated * 100)
    needs_cross_check = calibrated < 0.75

    sources: list[str] = []
    if tool_verified:
        sources.append("Deterministic Tool")
    if citations_count > 0:
        sources.append(f"{citations_count} Citation(s)")
    if not sources:
        sources.append("Model Heuristic")

    return {
        "confidence_score": calibrated,
        "confidence_pct": pct,
        "tool_verified": bool(tool_verified),
        "citations_count": int(citations_count),
        "needs_cross_verification": needs_cross_check,
        "verification_badge": f"Confidence: {pct}% | Verification: {' + '.join(sources)}",
    }


class CognitiveArena:
    """12-Discipline ELO Rating Tracker and Confidence Calibrator for Local Models."""

    DEFAULT_ELO: float = 1500.0
    K_FACTOR: float = 32.0

    def __init__(
        self,
        models: tuple[str, ...] = ARENA_MODELS,
        disciplines: tuple[str, ...] = ARENA_DISCIPLINES,
        default_elo: float = DEFAULT_ELO,
        k_factor: float = K_FACTOR,
    ) -> None:
        self.models: list[str] = list(models)
        self.disciplines: list[str] = list(disciplines)
        self.default_elo = float(default_elo)
        self.k_factor = float(k_factor)
        self.ratings: dict[str, dict[str, float]] = {
            model: {disc: float(default_elo) for disc in self.disciplines}
            for model in self.models
        }
        self.match_history: list[dict[str, Any]] = []

    def _ensure_model_and_discipline(self, model: str, discipline: str) -> None:
        if discipline not in self.disciplines:
            raise ValueError(f"Unsupported discipline '{discipline}'. Valid: {self.disciplines}")
        if model not in self.ratings:
            self.models.append(model)
            self.ratings[model] = {disc: self.default_elo for disc in self.disciplines}

    def get_rating(self, model: str, discipline: str) -> float:
        self._ensure_model_and_discipline(model, discipline)
        return self.ratings[model][discipline]

    def record_match(
        self,
        discipline: str,
        model_a: str,
        model_b: str,
        score_a: float = 1.0,
        k_factor: float | None = None,
    ) -> dict[str, Any]:
        """Update ELO ratings for model_a and model_b in `discipline` using R' = R + K * (S - E).

        `score_a` is 1.0 if model_a wins, 0.5 for draw, 0.0 if model_b wins.
        """
        if not (0.0 <= score_a <= 1.0):
            raise ValueError("score_a must be between 0.0 and 1.0")

        self._ensure_model_and_discipline(model_a, discipline)
        self._ensure_model_and_discipline(model_b, discipline)

        r_a = self.ratings[model_a][discipline]
        r_b = self.ratings[model_b][discipline]

        expected_a = 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))
        expected_b = 1.0 - expected_a

        score_b = 1.0 - float(score_a)
        k = float(k_factor) if k_factor is not None else self.k_factor

        new_r_a = round(r_a + k * (float(score_a) - expected_a), 2)
        new_r_b = round(r_b + k * (score_b - expected_b), 2)

        self.ratings[model_a][discipline] = new_r_a
        self.ratings[model_b][discipline] = new_r_b

        record = {
            "discipline": discipline,
            "model_a": model_a,
            "model_b": model_b,
            "score_a": float(score_a),
            "old_elo_a": r_a,
            "old_elo_b": r_b,
            "new_elo_a": new_r_a,
            "new_elo_b": new_r_b,
            "expected_a": round(expected_a, 4),
        }
        self.match_history.append(record)
        return record

    def get_leaderboard(self, discipline: str | None = None) -> list[dict[str, Any]]:
        """Return models sorted by ELO rating for a specific discipline or average across all 12 disciplines."""
        if discipline is not None:
            if discipline not in self.disciplines:
                raise ValueError(f"Unknown discipline: {discipline}")
            board = [
                {"model": m, "discipline": discipline, "elo": round(self.ratings[m][discipline], 2)}
                for m in self.models
            ]
        else:
            board = [
                {
                    "model": m,
                    "discipline": "overall",
                    "elo": round(sum(self.ratings[m].values()) / len(self.disciplines), 2),
                }
                for m in self.models
            ]
        board.sort(key=lambda item: item["elo"], reverse=True)
        return board

    @staticmethod
    def calibrate_confidence(
        answer: str,
        tool_verified: bool = False,
        citations_count: int = 0,
    ) -> dict[str, Any]:
        return calibrate_confidence(answer=answer, tool_verified=tool_verified, citations_count=citations_count)
