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


_NSFW_RE = re.compile(r"\b(?:çıplak\w*|ciplak\w*|nude\w*|naked|erotik\w*|erotic\w*|porn\w*|cinsel\w*|sexual\w*|nsfw|seks\w*)\b", re.IGNORECASE)
_SUBJECT_RE = re.compile(
    r"\b(?:kedi\w*|köpek\w*|kopek\w*|kuş\w*|kus\w*|at\b|atlar\w*|aslan\w*|balık\w*|balik\w*|tavşan\w*|ayı\w*|"
    r"insan\w*|kadın\w*|kadin\w*|erkek\w*|çocuk\w*|cocuk\w*|adam\w*|araba\w*|uçak\w*|ucak\w*|gemi\w*|bisiklet\w*|"
    r"cat\w*|dog\w*|bird\w*|horse\w*|lion\w*|fish\w*|person|people|man|woman|girl|boy|car\w*|plane\w*|ship\w*)\b",
    re.IGNORECASE,
)


def nsfw_requested(prompt: str) -> bool:
    return bool(_NSFW_RE.search(prompt))


def unsupported_subject(prompt: str) -> str | None:
    """The animal/person/vehicle the user wants drawn: the template engine cannot draw it."""
    from multimodal_studio import classify_image_mode

    m = _SUBJECT_RE.search(prompt)
    return m.group(0) if m and classify_image_mode(prompt) == "scene_illustration" else None


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


NSFW_MSG = "Cinsel içerikli ya da müstehcen görseller üretmiyorum. İstersen manzara, logo, poster, diyagram gibi başka bir görsel isteyebilirsin."
NO_SUBJECT_MSG = (
    "Bir **{subject}** çizemiyorum: bu kurulumdaki görsel motoru hazır sahne şablonlarıyla (manzara, şehir, uzay, soyut) çalışıyor; "
    "hayvan, kişi ya da araç gibi belirli nesneleri çizemez ve yanlış bir şey çizip \"çizdim\" demek istemem.\n\n"
    "Seçenekler:\n1. Manzara/şehir/uzay sahnesi: örneğin \"gündüz bir dağ manzarası çiz\".\n2. Logo, poster ya da diyagram.\n"
    "3. Gerçek bir resim için Stable Diffusion kurulmalı: `scripts/install_sd_webui.ps1` betiği bunu yapar."
)
NO_PHOTOREAL_MSG = (
    "Gerçekçi (fotoğraf gibi) bir görsel üretemiyorum: bu kurulumda bunu yapabilecek bir görsel yapay zeka modeli "
    "(Stable Diffusion ya da ComfyUI) çalışmıyor. Uydurma bir sonuç vermek istemedim.\n\n"
    "Şunları yapabilirim:\n"
    "1. **Vektörel illüstrasyon**: manzara, şehir, uzay ya da soyut bir sahne (şablon tabanlı, nesneleri tek tek çizemez).\n"
    "2. **Logo, poster, diyagram, infografik**.\n"
    "3. Gerçekçi görseller için Stable Diffusion kur: `scripts/install_sd_webui.ps1` betiğini çalıştır; açılınca platform otomatik algılar.\n\n"
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
            subject = None if is_image_revision(prompt, hist) else unsupported_subject(prompt)
            if nsfw_requested(prompt) or (subject and not await photoreal_backend_available()):
                yield _sse({"type": "token", "content": NSFW_MSG if nsfw_requested(prompt) else NO_SUBJECT_MSG.format(subject=subject)})
                yield _sse({"type": "done", "model": "capability-check", "task_type": "gorsel"})
                return
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
