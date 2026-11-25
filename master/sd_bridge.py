"""Local Stable Diffusion (AUTOMATIC1111 API) for pictures of anything: animals, cars, people, places, photos.

The request is turned into an English diffusion prompt (the model understands that best), the 8 GB GPU is cleared of language
models first and the checkpoint is unloaded afterwards, so chat and image generation can share the same card.
Logos, posters and diagrams are NOT drawn here: diffusion models misspell text, those stay deterministic vectors.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from gateway.providers import unload_all_models

_LOG = logging.getLogger(__name__)
SD_URL = "http://127.0.0.1:7860"
_PHOTO_RE = re.compile(r"(gerçekçi|gercekci|fotoğraf|fotograf|photo|realistic)", re.IGNORECASE)
_WIDE_RE = re.compile(r"(manzara|panorama|landscape|şehir|sehir|deniz|dağ|dag|orman|sahil)", re.IGNORECASE)
_PORTRAIT_RE = re.compile(r"(portre|portrait|insan|kadın|kadin|erkek|çocuk|cocuk|kişi|kisi)", re.IGNORECASE)
_SYSTEM = (
    'Convert the user\'s image request into a Stable Diffusion prompt. Return ONLY JSON: {"prompt": "<English, concrete, comma separated: subject, '
    'setting, lighting, camera/style>"}. Keep every subject, colour and detail the user named; add nothing they did not ask for (no people, text or logos).'
)
_NEGATIVE = "lowres, blurry, deformed, disfigured, extra limbs, extra fingers, bad anatomy, text, watermark, signature, cropped, out of frame"
_LLM = Callable[[str, str], Awaitable[dict[str, Any] | None]]


def pick_size(prompt: str) -> tuple[int, int]:
    """SD 1.5 draws best around 512 px; choose the orientation from the subject."""
    if _PORTRAIT_RE.search(prompt) and not _WIDE_RE.search(prompt):
        return 512, 704
    return (768, 512) if _WIDE_RE.search(prompt) else (640, 512)


async def available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            return (await client.get(f"{SD_URL}/sdapi/v1/options")).status_code == 200
    except (httpx.HTTPError, OSError):
        return False


async def build_prompt(prompt: str, llm: _LLM) -> str:
    parsed = await llm(_SYSTEM, prompt) or {}
    text = str(parsed.get("prompt") or "").strip() or prompt
    style = ", photorealistic, natural lighting, sharp focus, highly detailed, 35mm photo" if _PHOTO_RE.search(prompt) else ", highly detailed, vivid colours, professional quality"
    style += ", the whole main subject fully visible in the frame, balanced composition"
    return text + style


async def generate(prompt: str, out_png: Path, llm: _LLM) -> bool:
    """True when a picture was written to `out_png`."""
    if not await available():
        return False
    english = await build_prompt(prompt, llm)
    width, height = pick_size(prompt)
    await unload_all_models()
    payload = {"prompt": english, "negative_prompt": _NEGATIVE, "steps": 28, "cfg_scale": 7, "width": width, "height": height, "sampler_name": "Euler a"}
    try:
        async with httpx.AsyncClient(timeout=420.0) as client:
            resp = await client.post(f"{SD_URL}/sdapi/v1/txt2img", json=payload)
            images = resp.json().get("images") if resp.status_code == 200 else None
            if images:
                await asyncio.to_thread(out_png.write_bytes, base64.b64decode(images[0]))
                await client.post(f"{SD_URL}/sdapi/v1/unload-checkpoint")  # hand the VRAM back to the language model
                return True
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        _LOG.warning("Stable Diffusion generation failed: %s", exc)
    return False
