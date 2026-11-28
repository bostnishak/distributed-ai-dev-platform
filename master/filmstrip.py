"""A short film of what a page does: first load, a filled form, after submitting, after a reload, the empty case."""

from __future__ import annotations

import contextlib
import logging
import shutil
from pathlib import Path

import torture_probe as probe

FOLDER = ".ai-os/filmstrip"
_RECORD = "film kaydı"
_log = logging.getLogger(__name__)


def names(ws_dir: Path) -> list[str]:
    return sorted(p.name for p in (ws_dir / FOLDER).glob("*.png"))


def _frames(session: probe.Session, folder: Path) -> None:
    page = session.page

    def shot(name: str) -> None:
        page.screenshot(path=str(folder / f"{name}.png"))

    shot("1-ilk-acilis")
    if not probe.usable(page):
        return
    probe.fill(page, _RECORD)
    shot("2-dolu-form")
    probe.adder(page).click()
    page.wait_for_timeout(500)
    shot("3-gonderim-sonrasi")
    page.reload()
    page.wait_for_timeout(400)
    shot("4-yenileme-sonrasi")
    with contextlib.suppress(Exception):
        probe.add(page, "   ")
        shot("5-bos-girdi")


def capture(url: str, ws_dir: Path) -> list[str]:
    """The screenshots taken; [] when no browser can be used (the proof itself does not depend on them)."""
    folder = ws_dir / FOLDER
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                with probe.opened(browser, url) as session:
                    _frames(session, folder)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001, RUF100  # screenshots are extra evidence, never a reason to fail
        _log.warning("film şeridi alınamadı: %s", exc)
    return names(ws_dir)
