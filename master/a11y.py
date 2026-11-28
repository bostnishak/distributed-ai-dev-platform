"""Accessibility on the real page: axe-core from the local vault, keyboard order and modal focus traps."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import config

_AXE = ("vendor", "lib", "axe-core", "axe.min.js")
_SERIOUS = ("critical", "serious")
_log = logging.getLogger(__name__)
_REACH_JS = """() => [...document.querySelectorAll('button, a[href], input:not([type=hidden]), select, textarea, [onclick], [role=button]')]
  .filter(e => e.offsetParent !== null && !e.disabled && (e.tabIndex < 0 || (!e.matches('button, a[href], input, select, textarea') && !e.hasAttribute('tabindex'))))
  .map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0, 30))"""
_DIALOG = "dialog[open], [role=dialog]:visible, [role=alertdialog]:visible, [aria-modal=true]:visible"
_OPENERS = "button:visible:has-text('aç'), button:visible:has-text('open'), [aria-haspopup=dialog]:visible"


def axe_script() -> Path:
    """The vault copy; the platform's own data directory first, then the repository's."""
    own = config.data_dir().joinpath(*_AXE)
    return own if own.is_file() else Path(__file__).resolve().parent.joinpath("data", *_AXE)


def _violations(page: Any) -> list[str]:
    if not axe_script().is_file():
        return []
    page.add_script_tag(path=str(axe_script()))
    found = page.evaluate("axe.run(document, {resultTypes: ['violations']}).then(r => r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help, count: v.nodes.length})))")
    return [f"{v['impact']}: {v['id']} ({v['count']} öğe) {v['help']}" for v in found if v["impact"] in _SERIOUS]


def _modal_trap(page: Any) -> list[str]:
    """Opens the first dialog it can and presses Tab: focus must stay inside, and Escape must close it."""
    opener = page.locator(_OPENERS)
    if opener.count():
        opener.first.click(timeout=2000)
        page.wait_for_timeout(200)
    dialog = page.locator(_DIALOG)
    if not dialog.count():
        return []
    found = []
    for _press in range(12):
        page.keyboard.press("Tab")
        if not dialog.first.evaluate("e => e.contains(document.activeElement) || document.activeElement === document.body"):
            found.append("pencere açıkken odak arkadaki sayfaya kaçıyor")
            break
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    if page.locator(_DIALOG).count():
        found.append("açılan pencere Escape ile kapanmıyor")
    return found


def audit(url: str) -> list[str] | None:
    """Serious and critical findings; None when no browser can be started."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                page = browser.new_page()
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.goto(url, timeout=20000)
                page.wait_for_timeout(300)
                found = _violations(page)
                if unreachable := page.evaluate(_REACH_JS):
                    found.append("klavye sırasına girmeyen denetim: " + ", ".join(unreachable[:3]))
                return found + _modal_trap(page)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001, RUF100  # no usable browser, or the page cannot be driven
        _log.warning("erişilebilirlik denetimi koşulamadı: %s", exc)
        return None


def report(ws_dir: Path) -> list[str]:
    index = ws_dir / "index.html"
    found = audit(index.resolve().as_uri()) if index.is_file() else None
    return [f"Erişilebilirlik: {line}" for line in (found or [])[:5]]
