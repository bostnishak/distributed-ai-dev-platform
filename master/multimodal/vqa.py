"""EPK-09: Local Multimodal VQA Feature Inspector, Video Keyframe Detector & Turkish ASR WER Benchmark."""

from __future__ import annotations

import base64
import importlib.util
import io
import math
from typing import Any

from fastapi import APIRouter, HTTPException
from PIL import Image, ImageStat
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/studios/media", tags=["multimodal-vqa"])


def _decode_pil(image_b64: str) -> Image.Image:
    try:
        return Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
    except (ValueError, OSError) as exc:
        raise ValueError(f"Geçersiz görsel verisi: {exc}") from exc


def analyze_image_vqa(image_b64: str, question: str) -> dict[str, Any]:
    """Extract deterministic visual attributes + OCR runtime status to ground VQA answers honestly."""
    im = _decode_pil(image_b64)
    stat = ImageStat.Stat(im)
    r_m, g_m, b_m = (round(v, 1) for v in stat.mean[:3])
    luma = round(0.299 * r_m + 0.587 * g_m + 0.114 * b_m, 1)
    std_c = round(sum(stat.stddev[:3]) / 3.0, 1)
    ocr_avail = importlib.util.find_spec("pytesseract") is not None
    tone = "açık" if luma >= 170 else ("koyu" if luma <= 80 else "orta")
    return {
        "ok": True,
        "question": question,
        "width": im.width,
        "height": im.height,
        "mean_rgb": [r_m, g_m, b_m],
        "luminance": luma,
        "contrast_std": std_c,
        "tone": tone,
        "ocr_engine_available": ocr_avail,
        "honest_note": "Yerel OCR kurulu." if ocr_avail else "Yerel pytesseract kurulu değil; yalnızca piksel istatistikleri raporlandı.",
    }


def analyze_video_keyframes(frames_b64: list[str], fps: float = 1.0, change_threshold: float = 18.0) -> dict[str, Any]:
    """Detect scene changes across sampled video frames via thumbnail L1 difference."""
    if not frames_b64:
        return {"ok": True, "frame_count": 0, "keyframes": []}
    keyframes: list[dict[str, Any]] = []
    prev_bytes: bytes | None = None
    safe_fps = max(0.1, float(fps))
    for idx, b64 in enumerate(frames_b64[:120]):
        im = _decode_pil(b64).convert("L").resize((32, 32))
        cur = im.tobytes()
        delta = 99.0 if prev_bytes is None else sum(abs(a - b) for a, b in zip(cur, prev_bytes, strict=True)) / len(cur)
        if prev_bytes is None or delta >= change_threshold:
            keyframes.append({"frame_index": idx, "timestamp_s": round(idx / safe_fps, 2), "scene_delta": round(delta, 2)})
        prev_bytes = cur
    return {"ok": True, "frame_count": len(frames_b64), "keyframe_count": len(keyframes), "keyframes": keyframes}


def compute_turkish_wer(reference: str, hypothesis: str) -> dict[str, Any]:
    """Compute Word Error Rate (WER) via Levenshtein edit distance on normalized Turkish words."""
    ref_w = [w for w in (reference or "").lower().split() if w]
    hyp_w = [w for w in (hypothesis or "").lower().split() if w]
    if not ref_w:
        return {"ok": True, "wer": 0.0 if not hyp_w else 1.0, "edits": len(hyp_w), "ref_words": 0}
    dp = list(range(len(hyp_w) + 1))
    for i, rw in enumerate(ref_w, start=1):
        prev = dp[0]
        dp[0] = i
        for j, hw in enumerate(hyp_w, start=1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (0 if rw == hw else 1))
            prev = cur
    edits = dp[-1]
    wer = round(edits / len(ref_w), 4)
    return {"ok": True, "wer": wer, "accuracy_pct": round(max(0.0, (1.0 - wer) * 100.0), 2), "edits": edits, "ref_words": len(ref_w), "hyp_words": len(hyp_w), "passes_target": math.isfinite(wer) and wer <= 0.15}


class VqaRequest(BaseModel):
    image_b64: str = Field(..., min_length=8)
    question: str = Field(default="Bu görselde ne var?", max_length=500)


class VideoAnalyzeRequest(BaseModel):
    frames_b64: list[str] = Field(default_factory=list)
    fps: float = Field(default=1.0, ge=0.1, le=60.0)
    change_threshold: float = Field(default=18.0, ge=1.0, le=200.0)


class AsrWerRequest(BaseModel):
    reference: str = Field(..., max_length=8000)
    hypothesis: str = Field(..., max_length=8000)


@router.post("/vqa")
async def api_vqa(body: VqaRequest):
    """Inspect image attributes and return grounded local VQA diagnostics."""
    try:
        return analyze_image_vqa(body.image_b64, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/video-analyze")
async def api_video_analyze(body: VideoAnalyzeRequest):
    """Detect keyframes and scene-change timestamps from sampled video frames."""
    try:
        return analyze_video_keyframes(body.frames_b64, fps=body.fps, change_threshold=body.change_threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/asr-wer")
async def api_asr_wer(body: AsrWerRequest):
    """Evaluate Turkish ASR transcription quality via Word Error Rate (WER)."""
    return compute_turkish_wer(body.reference, body.hypothesis)
