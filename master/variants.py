"""Two designs of the same request, side by side: the chat builds both and shows both workspaces to choose from."""

from __future__ import annotations

import json
import logging
import re
import subprocess

import httpx
from fastapi.responses import StreamingResponse

import design_system

_log = logging.getLogger(__name__)
_TRIGGER_RE = re.compile(r"\b(?:(?:iki|2)\s+(?:farklı\s+)?(?:tasarım\s+)?(?:varyant\w*|alternatif\w*|seçenek\w*|versiyon\w*)|(?:two|2)\s+(?:design\s+)?variants?)\b", re.IGNORECASE)
_STYLES = (
    ("A", "sık ve sade: dar boşluklar, tablo ve liste ağırlıklı, tek sütunlu üst menü"),
    ("B", "ferah ve kart ağırlıklı: geniş boşluklar, sol yan menü, öne çıkan özet kartları"),
)


def parse(prompt: str) -> str:
    """The request without the 'two variants' wording, or '' when variants were not asked for."""
    if not _TRIGGER_RE.search(prompt):
        return ""
    cleaned = _TRIGGER_RE.sub(" ", prompt)
    return re.sub(r"\s+", " ", cleaned).strip(" ,.:;-") if len(cleaned.strip()) > 8 else ""


def requests_for(base: str) -> list[tuple[str, str]]:
    """(name, full request) per variant; different layout and, when the user chose no colours, a different palette."""
    out = []
    for name, style in _STYLES:
        colours = ""
        if design_system.brief(base):
            tokens = design_system.palette(f"{base} {name}", dark=name == "B")
            colours = "\nRenkler (CSS değişkeni olarak): " + "; ".join(f"{k}: {v}" for k, v in tokens.items())
        out.append((name, f"{base}\n\nTasarım yaklaşımı {name}: {style}. Tek HTML dosyası.{colours}"))
    return out


async def _stream(base: str):
    import assistant_stream_fastpaths as fp
    import project_flow
    import workspace_builder as wb

    built = 0
    for name, request in requests_for(base):
        yield fp.sse_event({"type": "token", "content": f"\n### Varyant {name} hazırlanıyor...\n"})
        try:
            async for evt in project_flow.stream_generate(request, project_type="web"):
                if evt["type"] == "done":
                    _failed, notes = fp._verdict(evt)
                    yield fp.sse_event({"type": "token", "content": "".join(notes)})
                    yield fp.sse_event(fp._attach_workspace_flags(wb, evt["workspace"], evt["tree"]))
                    built += 1
        except (httpx.HTTPError, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            _log.warning("variant %s failed: %r", name, exc)
            yield fp.sse_event({"type": "token", "content": f"Varyant {name} üretilemedi: {exc}\n"})
    yield fp.sse_event({"type": "token", "content": f"\n{built} varyant hazır. Beğendiğinin kartından devam edebilirsin.\n"})
    yield fp.sse_event({"type": "done", "model": "varyant", "task_type": "proje"})


def fastpath(prompt: str) -> StreamingResponse | None:
    base = parse(prompt)
    if not base or len(json.dumps(base)) > 6000:
        return None
    return StreamingResponse(_stream(base), media_type="text/event-stream")
