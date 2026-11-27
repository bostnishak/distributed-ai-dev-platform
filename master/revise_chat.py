"""'Fix this / make the buttons blue' typed in the chat edits the project built earlier in the same conversation.

Without this the message either started a brand new project or got a text answer, and the built app never changed.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from typing import Any

import httpx
from fastapi.responses import StreamingResponse

import checkpoint
import spec_contract
import tier0_edit

_RECENT_TURNS = 8
_MAX_CHARS = 1500
_CHANGE_RE = re.compile(
    r"\b(?:düzelt\w*|duzelt\w*|değiştir\w*|degistir\w*|geliştir\w*|gelistir\w*|güncelle\w*|guncelle\w*|düzenle\w*|duzenle\w*|"
    r"ekle|ekleyin|kaldır\w*|kaldir\w*|büyüt\w*|küçült\w*|çalışmıyor\w*|calismiyor\w*|olmamış|olmadı|beğenmedim|bozuk|hatalı|"
    r"fix|change|add|remove|update|improve|broken|doesn't work|not working)\b",
    re.IGNORECASE,
)
_UI_RE = re.compile(r"\b(?:buton|düğme|renk|rengi|sayfa|başlık|font|yazı|panel|menü|form|liste|kart|arka ?plan|tema|tasarım|button|colou?r|page|header|layout)\w*", re.IGNORECASE)
_MAKE_RE = re.compile(r"\b(?:yap|olsun|yapalım|make|should)\b", re.IGNORECASE)
_NOT_EDIT_RE = re.compile(
    r"\?\s*$|\b(?:nedir|neden|nasıl|nasil|açıkla|what|why|how|explain|yeni (?:bir )?(?:proje|uygulama|site|oyun)|başka bir|sıfırdan|new (?:app|project|site)|pdf|word|excel|sunum)\b",
    re.IGNORECASE,
)


def is_revision(prompt: str) -> bool:
    if len(prompt) > _MAX_CHARS or _NOT_EDIT_RE.search(prompt):
        return False
    return bool(tier0_edit.parse(prompt) or tier0_edit._LINT_RE.match(prompt) or _CHANGE_RE.search(prompt) or (_UI_RE.search(prompt) and _MAKE_RE.search(prompt)))


def last_workspace_id(history: str) -> str:
    """Id of the project shown in one of the latest replies of this conversation."""
    try:
        items = json.loads(history or "[]")
    except (json.JSONDecodeError, TypeError):
        return ""
    for item in reversed(items[-_RECENT_TURNS:] if isinstance(items, list) else []):
        box: Any = item.get("workspace") if isinstance(item, dict) else None
        if isinstance(box, dict):
            meta = box.get("workspace") if isinstance(box.get("workspace"), dict) else box
            return str(meta.get("id") or "")
    return ""


def fastpath(prompt: str, history: str, has_file: bool) -> StreamingResponse | None:
    if not has_file and (resumed := checkpoint.fastpath(prompt, history)) is not None:
        return resumed
    ws_id = "" if has_file or not is_revision(prompt) else last_workspace_id(history)
    if not ws_id:
        return None
    import workspace_builder as wb

    try:
        if not wb.safe_workspace_dir(ws_id).is_dir():
            return None
    except (ValueError, OSError):
        return None
    return StreamingResponse(_stream(ws_id, prompt), media_type="text/event-stream")


def _page_errors(ws_id: str, prompt: str) -> list[str]:
    """What the browser gate still finds wrong with the page (empty when it passes or cannot run here)."""
    import workspace_builder as wb
    import workspace_docker
    import workspace_web

    ws_dir = wb.safe_workspace_dir(ws_id)
    wanted = spec_contract.extract(prompt)
    absent = spec_contract.missing(ws_dir, {"colors": wanted["colors"][-1:], "labels": [], "sizes": []})
    gaps = [f"İstenen renk dosyalarda yok: {absent[0]}"] if absent else []
    if not workspace_web.has_page(ws_dir) or not workspace_docker.available():
        return gaps
    return gaps + [str(e)[:220] for e in (workspace_web.probe(ws_dir) or {}).get("errors", [])]


def _test_errors(ws_id: str, changed: list[str]) -> list[str]:
    """Run only the project tests that depend on the edited files."""
    import repo_map
    import workspace_builder as wb
    import workspace_docker
    import workspace_requirements

    ws_dir = wb.safe_workspace_dir(ws_id)
    only = repo_map.affected_tests(ws_dir, changed)
    if not only or not workspace_docker.available():
        return []
    log = workspace_docker.test_log(ws_dir, workspace_requirements.declared_packages(ws_dir), tuple(only))
    return [f"Etkilenen testler başarısız ({', '.join(only)}): {log.splitlines()[-1][:160]}"] if log else []


async def _stream(ws_id: str, prompt: str):
    import assistant_stream_fastpaths as fp
    import workspace_builder as wb

    yield fp.sse_event({"type": "token", "content": "Mevcut projede istediğin değişiklik yapılıyor...\n"})
    try:
        if quick := await asyncio.to_thread(tier0_edit.apply, wb.safe_workspace_dir(ws_id), prompt):
            yield fp.sse_event({"type": "token", "content": f"Model çağrılmadan birebir uygulandı: {', '.join(quick)}\n"})
            meta = wb.load_workspace_meta(wb.safe_workspace_dir(ws_id))
            yield fp.sse_event(fp._attach_workspace_flags(wb, meta, wb.build_file_tree(wb.safe_workspace_dir(ws_id))))
            yield fp.sse_event({"type": "done", "model": "tier0", "task_type": "proje"})
            return
        changed: list[str] = []
        async for evt in wb.stream_iterate_project(ws_id, prompt.strip()):
            if evt["type"] == "file_done":
                changed.append(evt["path"])
                yield fp.sse_event({"type": "token", "content": f"- `{evt['path']}` güncellendi\n"})
            elif evt["type"] == "done":
                yield fp.sse_event({"type": "token", "content": "\nDeğişiklik tarayıcı ortamında test ediliyor...\n"})
                broken = await asyncio.to_thread(_page_errors, ws_id, prompt) + await asyncio.to_thread(_test_errors, ws_id, changed)
                warnings = [*broken, *(str(w) for w in evt.get("warnings") or [])]
                note = "\n".join(f"> {w}" for w in warnings[:3])
                verdict = "Değişiklik yazıldı ama TEST GEÇMEDİ" if broken else "Değişiklik uygulandı"
                yield fp.sse_event({"type": "token", "content": f"\n{verdict} ({len(changed)} dosya). Önizlemeden kontrol et.\n{note}\n"})
                flagged = fp._attach_workspace_flags(wb, evt["workspace"], evt["tree"])
                yield fp.sse_event(flagged)
        yield fp.sse_event({"type": "done", "model": "proje-revizyon", "task_type": "proje"})
    except (httpx.HTTPError, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        yield fp.sse_event({"type": "error", "content": str(exc)})
