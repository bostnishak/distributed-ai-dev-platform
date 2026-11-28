"""A follow-up change must not break what worked before it.

The page is opened in a real browser before and after the change: uncaught errors, adding a record and keeping it over
a reload. When something got worse the model gets the exact error twice (the second time from a clean context); if it
still fails, the previous files come back and the user is told that the change was not applied.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

import asset_vault
import atomic_io
import clean_slate
import patch_edit
import torture_probe as probe
from process_utils import run_process
from prompt_loader import load_prompt

REJECTED = ".ai-os/rejected_edit.html"
_RECORD = "bekçi-kaydı-71"
_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc=)(?![^>]*type=[\"'](?:module|application/json))[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```")
_ATTEMPTS = 2
_log = logging.getLogger(__name__)

Generate = Callable[[str, str], Awaitable[str]]


@dataclass(frozen=True)
class Health:
    errors: tuple[str, ...] = field(default_factory=tuple)
    adds: bool | None = None  # None: the page has nothing to add with
    persists: bool | None = None


def _drive(session: probe.Session) -> Health:
    page, adds, persists = session.page, None, None
    if probe.usable(page):
        probe.add(page, _RECORD)
        adds = probe.shown(page, _RECORD) > 0
        page.reload()
        page.wait_for_timeout(300)
        persists = probe.shown(page, _RECORD) > 0
    return Health(tuple(dict.fromkeys([*session.errors, *session.console])), adds, persists)


def health(ws_dir: Path) -> Health | None:
    """None when there is no page or no browser: then nothing can be judged."""
    index = ws_dir / "index.html"
    if not index.is_file():
        return None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                with probe.opened(browser, index.resolve().as_uri()) as session:
                    return _drive(session)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001, RUF100  # no usable browser, or the page cannot be driven
        _log.warning("düzenleme bekçisi sayfayı sınayamadı: %s", exc)
        return None


def _write_page(ws_dir: Path, page: str) -> None:
    atomic_io.write_text(ws_dir / "index.html", page)
    asset_vault.localize(ws_dir)  # a rewrite may bring CDN links back


def snapshot(ws_dir: Path) -> tuple[Health | None, str]:
    """Taken before a change: how the page behaves and what it says."""
    page = ws_dir / "index.html"
    return health(ws_dir), page.read_text(encoding="utf-8", errors="replace") if page.is_file() else ""


def worse(before: Health, after: Health) -> str:
    """What the change broke, "" when nothing got worse."""
    broken = []
    if after.errors and not before.errors:
        broken.append(f"JavaScript hatası: {after.errors[0]}")
    if before.adds and not after.adds:
        broken.append("kayıt ekleme artık çalışmıyor")
    if before.persists and not after.persists:
        broken.append("kayıtlar artık yenileyince kayboluyor")
    return "; ".join(broken)


def syntax_error(page: str) -> str:
    """Node's message with the offending line for the first inline script that does not parse; "" when all do."""
    if not shutil.which("node"):
        return ""
    for number, body in enumerate(_SCRIPT_RE.findall(page), 1):
        with tempfile.TemporaryDirectory(prefix="cm6453_js_") as folder:
            script = Path(folder) / f"betik{number}.js"
            script.write_text(body, encoding="utf-8")
            done = run_process(["node", "--check", str(script)], timeout_s=20)
        if done.returncode != 0:
            lines = [line for line in done.stderr.splitlines() if line.strip() and not line.startswith(("    at ", "Node.js"))]
            return "\n".join(lines[:6]).replace(str(script), f"<script {number}>")
    return ""


async def _repair(page: str, diagnosis: str, instruction: str, generate: Generate, banned: list[str]) -> str:
    ask = f"{load_prompt('edit_guard.txt')}{diagnosis}\n\nİSTENEN DEĞİŞİKLİK: {instruction}\n\nMEVCUT index.html:\n{page}"
    if banned:
        ask = clean_slate.prompt(f"İSTENEN DEĞİŞİKLİK: {instruction}", "index.html", page, diagnosis, banned)
    patched = None if banned else await patch_edit.try_patch(generate, ask, page)
    if patched is None:
        answer = await generate("Yalnız dosyanın eksiksiz yeni içeriğini ``` bloğunda döndür.", ask)
        patched = max(_BLOCK_RE.findall(answer), key=len, default="")
    return patched if "</html>" in patched.lower() else ""


async def settle(ws_dir: Path, request: str, generate: Generate) -> list[str]:
    """A freshly built page that logs errors in the browser is repaired with the exact message; what stays is reported."""
    index, banned = ws_dir / "index.html", []
    for attempt in range(_ATTEMPTS + 1):
        found = await asyncio.to_thread(health, ws_dir)
        if found is None or not found.errors:
            return ["Tarayıcı konsolundaki hata onarıldı."] if attempt else []
        if attempt == _ATTEMPTS:
            break
        page = index.read_text(encoding="utf-8")
        diagnosis = "\n".join(filter(None, (f"Tarayıcı hatası: {found.errors[0]}", await asyncio.to_thread(syntax_error, page))))
        candidate = await _repair(page, diagnosis, request, generate, banned)
        banned.append(clean_slate.failed_approach(page, candidate or page, diagnosis))
        if candidate:
            _write_page(ws_dir, candidate)
    return [f"Uyarı: sayfa tarayıcıda hata veriyor: {found.errors[0][:200]}"]


async def guard(ws_dir: Path, before: tuple[Health | None, str], instruction: str, generate: Generate) -> list[str]:
    """`before` is (health, index.html) from before the change. Returns the lines to tell the user."""
    old_health, old_page = before
    if old_health is None or not old_page:
        return []
    banned: list[str] = []
    for attempt in range(_ATTEMPTS + 1):
        after = await asyncio.to_thread(health, ws_dir)
        broken = worse(old_health, after) if after else ""
        if not broken:
            return ["Değişiklik sayfayı bozmuştu; onarıldı."] if attempt else []
        if attempt == _ATTEMPTS:
            break
        page = (ws_dir / "index.html").read_text(encoding="utf-8")
        diagnosis = "\n".join(filter(None, (broken, await asyncio.to_thread(syntax_error, page))))
        candidate = await _repair(page, diagnosis, instruction, generate, banned)
        banned.append(clean_slate.failed_approach(page, candidate or page, broken))
        if candidate:
            _write_page(ws_dir, candidate)
    (ws_dir / REJECTED).parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(ws_dir / REJECTED, (ws_dir / "index.html").read_text(encoding="utf-8"))  # kept so it can be looked at
    atomic_io.write_text(ws_dir / "index.html", old_page)
    return [f"Uyarı: bu değişiklik uygulanmadı çünkü sayfayı bozuyordu ({broken[:200]}). Önceki çalışan sürüm geri yüklendi."]
