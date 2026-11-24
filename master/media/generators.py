"""EPK-22: Media Generators (SRT Subtitles, Three.js 3D Scene Spec & Honest Local Backend Probing)."""

from __future__ import annotations

import importlib.util
import os
import shutil
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/media", tags=["media-generators"])


def _fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, round(float(seconds) * 1000))
    hrs, rem = divmod(ms_total, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def generate_srt_subtitles(segments: list[dict[str, Any]]) -> dict[str, Any]:
    """Format timestamped speech segments into a standard SubRip (.srt) subtitle file."""
    blocks: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = _fmt_srt_time(float(seg.get("start_s", (idx - 1) * 3.0)))
        end = _fmt_srt_time(float(seg.get("end_s", idx * 3.0)))
        text = str(seg.get("text") or "").strip() or "..."
        blocks.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return {"ok": True, "cue_count": len(blocks), "srt": "\n".join(blocks)}


def generate_threejs_scene_spec(prompt: str) -> dict[str, Any]:
    """Generate a deterministic, self-contained Three.js 3D scene specification from a Turkish/English prompt."""
    low = (prompt or "").lower()
    geom = "torus" if ("halka" in low or "flanş" in low or "flans" in low) else (
        "cylinder" if ("mil" in low or "silindir" in low or "şaft" in low) else "box"
    )
    color = "#38bdf8" if "mavi" in low else ("#ef4444" if "kırmızı" in low or "kirmizi" in low else "#94a3b8")
    return {
        "ok": True,
        "engine": "threejs-spec-v1",
        "prompt": prompt,
        "camera": {"type": "PerspectiveCamera", "fov": 45, "position": [4.0, 3.0, 5.0]},
        "lights": [
            {"type": "AmbientLight", "intensity": 0.6},
            {"type": "DirectionalLight", "intensity": 1.2, "position": [5.0, 8.0, 4.0]},
        ],
        "meshes": [{"name": "primary_part", "geometry": geom, "material": {"type": "MeshStandardMaterial", "color": color, "metalness": 0.45, "roughness": 0.35}}],
    }


def probe_media_backends() -> dict[str, Any]:
    """Report honest availability of optional local media backends (ComfyUI, ffmpeg, Pillow, pyttsx3)."""
    comfy_url = os.environ.get("COMFYUI_URL", "").strip()
    return {
        "ok": True,
        "backends": {
            "pillow_image": {"available": importlib.util.find_spec("PIL") is not None},
            "ffmpeg_video": {"available": shutil.which("ffmpeg") is not None},
            "comfyui_sd": {"available": bool(comfy_url), "reason": "COMFYUI_URL tanımlı" if comfy_url else "COMFYUI_URL yapılandırılmadı (yerel SVG/Pillow yedek aktif)"},
            "local_tts": {"available": importlib.util.find_spec("pyttsx3") is not None, "fallback": "Web Speech API + SRT"},
        },
    }


class SrtRequest(BaseModel):
    segments: list[dict[str, Any]] = Field(default_factory=list)


class Scene3dRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=500)


@router.post("/srt")
async def api_generate_srt(body: SrtRequest):
    """Generate a standard SRT subtitle transcript from timestamped segments."""
    return generate_srt_subtitles(body.segments)


@router.post("/scene-3d")
async def api_generate_scene_3d(body: Scene3dRequest):
    """Generate a Three.js 3D scene specification JSON from a description."""
    return generate_threejs_scene_spec(body.prompt)


@router.get("/backends")
async def api_media_backends():
    """Return honest status of local image, audio, video, and 3D media backends."""
    return probe_media_backends()
