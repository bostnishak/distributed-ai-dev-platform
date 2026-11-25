"""Chat-side handling of image requests: follow-up edits, honest capability notes, and the SSE stream.

The built-in image engine draws vector illustrations from templates. It cannot make photo-realistic pictures or place
arbitrary objects (animals, people) on request, so the reply must say so instead of implying otherwise.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi.responses import StreamingResponse

_SSE = "text/event-stream"
_MARKER_RE = re.compile(r"(Üretilen Görsel|/api/assistant/media/img-gen-)")
_FOLLOWUP_RE = re.compile(
    r"\b(gündüz\w*|gunduz\w*|gece\w*|daha\w*|farklı\w*|farkli\w*|başka\w*|baska\w*|değiştir\w*|degistir\w*|çevir\w*|cevir\w*|"
    r"dönüştür\w*|donustur\w*|olsun|ekle\w*|çıkar\w*|cikar\w*|renk\w*|büyüt\w*|küçült\w*|yeniden|tekrar|bunu|onu|andırıyor|andiriyor|hayvan\w*)\b",
    re.IGNORECASE,
)
_PHOTOREAL_RE = re.compile(r"\b(gerçekçi\w*|gercekci\w*|fotogerçekçi\w*|fotogercekci\w*|fotoğraf\w*|fotograf\w*|photo\w*|realistic|hyperrealistic|ultra\s*real\w*)\b", re.IGNORECASE)
_DAY_RE = re.compile(r"\b(gündüz\w*|gunduz\w*|güneşli|gunesli|day\w*)\b", re.IGNORECASE)


def parse_history(history: str) -> list[dict[str, Any]]:
    try:
        items = json.loads(history) if history else []
    except (json.JSONDecodeError, TypeError):
        return []
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def is_image_revision(prompt: str, history: list[dict[str, Any]]) -> bool:
    """True when the previous assistant turn was a generated image and this short message asks to change it."""
    if len(prompt) > 200 or not history:
        return False
    last_assistant = next((str(m.get("text") or "") for m in reversed(history) if m.get("role") == "assistant"), "")
    return bool(_MARKER_RE.search(last_assistant) and _FOLLOWUP_RE.search(prompt))


def photoreal_requested(prompt: str) -> bool:
    return bool(_PHOTOREAL_RE.search(prompt))


def wants_daylight(prompt: str) -> bool:
    return bool(_DAY_RE.search(prompt))


async def photoreal_backend_available() -> bool:
    """A real image model (Stable Diffusion web UI or ComfyUI) answering locally."""
    for url in ("http://127.0.0.1:7860/sdapi/v1/options", "http://127.0.0.1:8188/system_stats"):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                if (await client.get(url)).status_code == 200:
                    return True
        except (httpx.HTTPError, OSError):
            continue
    return False


NO_PHOTOREAL_MSG = (
    "Gerçekçi (fotoğraf gibi) bir görsel üretemiyorum: bu kurulumda bunu yapabilecek bir görsel yapay zeka modeli "
    "(Stable Diffusion ya da ComfyUI) çalışmıyor. Uydurma bir sonuç vermek istemedim.\n\n"
    "Şunları yapabilirim:\n"
    "1. **Vektörel illüstrasyon**: manzara, şehir, uzay ya da soyut bir sahne (şablon tabanlı, nesneleri tek tek çizemez).\n"
    "2. **Logo, poster, diyagram, infografik**.\n"
    "3. İstersen Stable Diffusion/ComfyUI'yi yerelde kurman için adımları anlatırım; çalışınca gerçekçi görseller de üretirim.\n\n"
    "Hangisini istersin? Örneğin: \"illüstrasyon olarak gündüz bir dağ manzarası üret\"."
)
TEMPLATE_NOTE = (
    "\n\n> **Not:** Bu görsel hazır sahne şablonundan çiziliyor (gökyüzü, dağlar, güneş/ay gibi). İstediğin hayvan, kişi ya da "
    "belirli nesneleri tek tek çizemez; yalnızca sahne türünü ve renk paletini isteğine göre seçer."
)


def build_image_gen_stream(prompt: str, history: str) -> StreamingResponse:
    import multimodal_studio as mms

    hist = parse_history(history)

    def _sse(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def _gen():
        try:
            if photoreal_requested(prompt) and not await photoreal_backend_available():
                yield _sse({"type": "token", "content": NO_PHOTOREAL_MSG})
                yield _sse({"type": "done", "model": "capability-check", "task_type": "gorsel"})
                return
            res = await mms.generate_ai_image(prompt, history=hist)
            preview_url = res.get("svg_url") or res["png_url"]
            meta = [f"**Motor:** `{res['engine']}`"]
            if res.get("brand_name"):
                meta.append(f"**Konsept:** {res['brand_name']}")
            if res.get("palette_name"):
                meta.append(f"**Palet:** {res['palette_name']}")
            svg_link = f" · [Vektörel SVG İndir]({res['svg_url']})" if res.get("svg_url") else ""
            md = f"## Üretilen Görsel Tasarım\n- {' · '.join(meta)}\n- [Yüksek Çözünürlüklü PNG İndir]({res['png_url']}){svg_link}\n\n![Üretilen Görsel]({preview_url})"
            if str(res.get("engine", "")).startswith("scene-procedural"):
                md += TEMPLATE_NOTE
            yield _sse({"type": "artifact", "kind": "image", "format": "png", "url": res["png_url"], "svg_url": res.get("svg_url")})
            yield _sse({"type": "token", "content": md})
            yield _sse({"type": "done", "model": res["engine"], "task_type": "gorsel"})
        except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
            yield _sse({"type": "error", "content": str(exc)})

    return StreamingResponse(_gen(), media_type=_SSE)
