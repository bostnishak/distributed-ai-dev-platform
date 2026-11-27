"""Two designs of the same request, side by side: the chat builds both and shows both workspaces to choose from."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path

import httpx
from fastapi.responses import StreamingResponse

import complexity_governor
import config
import design_system
import revise_chat

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


_WINNER_RE = re.compile(r"^\s*(?:varyant\s+)?(?P<name>[AB])\s*(?:varyantını|'?[yı]i)?\s+(?:ana\s+projeye\s+al|birleştir)\s*[.!]?\s*$", re.IGNORECASE)


def _record() -> Path:
    return config.data_dir() / "variants.json"


def remember(main: str, built: dict[str, str]) -> None:
    _record().parent.mkdir(parents=True, exist_ok=True)
    _record().write_text(json.dumps({"main": main, "variants": built}), encoding="utf-8")


def merge_winner(name: str) -> str:
    """Copy the chosen variant into the project that was open before the variants (a version is saved first)."""
    import workspace_builder as wb

    try:
        state = json.loads(_record().read_text(encoding="utf-8"))
        source = wb.safe_workspace_dir(state["variants"][name.upper()])
    except (OSError, ValueError, KeyError):
        return "Kayıtlı bir varyant yok. Önce `iki varyant ...` ile üretin."
    if not state.get("main"):
        return f"Varyantlardan önce açık bir ana proje yoktu; `{source.name}` kendisi ana proje olarak kullanılabilir."
    target = wb.safe_workspace_dir(state["main"])
    wb.create_snapshot(target, f"varyant {name.upper()} öncesi")
    for relative in wb.list_relative_files(source):
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target / relative)
    wb.create_snapshot(target, f"varyant {name.upper()} birleştirildi")
    return f"Varyant {name.upper()} ana projeye (`{target.name}`) alındı. Eski hali sürüm geçmişinde duruyor."


async def _build(request: str):
    """One variant, without product research: both variants are designs of the same words."""
    import project_flow

    with complexity_governor.without_research():
        async for event in project_flow.stream_generate(request, project_type="web"):
            yield event


async def _stream(base: str, main: str = ""):
    import assistant_stream_fastpaths as fp
    import workspace_builder as wb

    ids: dict[str, str] = {}
    built = 0
    for name, request in requests_for(base):
        yield fp.sse_event({"type": "token", "content": f"\n### Varyant {name} hazırlanıyor...\n"})
        started = time.monotonic()
        try:
            async for evt in _build(request):
                if evt["type"] == "done":
                    yield fp.sse_event({"type": "token", "content": f"Süre: {time.monotonic() - started:.0f} sn.\n"})
                    _failed, notes = fp._verdict(evt)
                    yield fp.sse_event({"type": "token", "content": "".join(notes)})
                    yield fp.sse_event(fp._attach_workspace_flags(wb, evt["workspace"], evt["tree"]))
                    ids[name] = str(evt["workspace"]["id"])
                    built += 1
        except (httpx.HTTPError, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            _log.warning("variant %s failed: %r", name, exc)
            yield fp.sse_event({"type": "token", "content": f"Varyant {name} üretilemedi: {exc}\n"})
    remember(main, ids)
    yield fp.sse_event({"type": "token", "content": f"\n{built} varyant hazır. Kazananı ana projeye almak için `A varyantını ana projeye al` yazabilirsin.\n"})
    yield fp.sse_event({"type": "done", "model": "varyant", "task_type": "proje"})


def fastpath(prompt: str, history: str = "") -> StreamingResponse | None:
    if match := _WINNER_RE.match(prompt):
        import assistant_stream_fastpaths as fp

        return fp.single_token_stream(merge_winner(match["name"]), "varyant", "proje")
    base = parse(prompt)
    if not base or len(json.dumps(base)) > 6000:
        return None
    return StreamingResponse(_stream(base, revise_chat.last_workspace_id(history)), media_type="text/event-stream")
