"""Random rapid clicking and hostile input on a generated page in a real headless browser, with the network blocked.

Uncaught errors are what is reported. The seed is fixed so a finding can be reproduced.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from prompt_loader import load_prompt

_log = logging.getLogger(__name__)
_SEEDS = (7, 1234)


def errors(page_file: Path) -> list[str] | None:
    """Distinct uncaught errors; None when no browser is available."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    found: list[str] = []
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                for seed in _SEEDS:
                    page = browser.new_page()
                    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:")) else route.abort())
                    page.on("pageerror", lambda exc: found.append(str(exc).splitlines()[0][:160]))
                    page.on("dialog", lambda dialog: dialog.dismiss())
                    page.goto(page_file.resolve().as_uri(), timeout=15000)
                    page.evaluate(load_prompt("ui_chaos.js.txt"), seed)
                    page.wait_for_timeout(500)
                    page.close()
            finally:
                browser.close()
    except PlaywrightError as exc:
        _log.warning("chaos test could not run: %s", exc)
        return None
    return sorted(set(found))


_UNREACHABLE_JS = """() => [...document.querySelectorAll('button, a[href], input, select, textarea, [onclick], [role=button]')]
  .filter(e => e.offsetParent !== null && !e.disabled)
  .filter(e => e.tabIndex < 0 || (!e.matches('button, a[href], input, select, textarea') && !e.hasAttribute('tabindex')))
  .map(e => (e.innerText || e.getAttribute('aria-label') || e.tagName).trim().slice(0, 30))"""
_ENTRIES = "li, tbody tr, article, .card, .item"


def _ergonomics(page: Any) -> list[str]:
    """Phone width, keyboard only, hurried double clicks and a blank submit."""
    found = []
    page.set_viewport_size({"width": 320, "height": 700})
    page.wait_for_timeout(200)
    if (width := page.evaluate("document.documentElement.scrollWidth")) > 322:
        found.append(f"320 px genişlikte yatay taşma ({width} px)")
    if unreachable := page.evaluate(_UNREACHABLE_JS):
        found.append("klavyeyle ulaşılamayan denetim: " + ", ".join(unreachable[:3]))
    field = page.locator("form input[type=text]:visible, form input:not([type]):visible, form textarea:visible").first
    submit = page.locator("form button:visible, form input[type=submit]:visible").first
    if field.count() and submit.count():
        before = page.locator(_ENTRIES).count()
        field.fill("   ")
        submit.click()
        page.wait_for_timeout(300)
        if page.locator(_ENTRIES).count() > before:
            found.append("yalnız boşlukla gönderim kayıt ekledi")
        before = page.locator(_ENTRIES).count()
        field.fill("çift tık denemesi")
        submit.dblclick()
        page.wait_for_timeout(400)
        if page.locator(_ENTRIES).count() > before + 1:
            found.append("çift tıklama aynı kaydı iki kez ekledi")
    return found


def ergonomics(page_file: Path) -> list[str] | None:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page()
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.goto(page_file.resolve().as_uri(), timeout=15000)
                return _ergonomics(page)
            finally:
                browser.close()
    except PlaywrightError as exc:
        _log.warning("ergonomics test could not run: %s", exc)
        return None


def report(ws_dir: Path) -> str | None:
    """"" when the page survived, a warning line when it threw, None when there is no page or no browser."""
    page = ws_dir / "index.html"
    if not page.is_file():
        return None
    found = errors(page)
    if found is None:
        return None
    lines = ["Rastgele tıklama testinde yakalanmamış hata: " + "; ".join(found[:3])] if found else []
    if rough := ergonomics(page):
        lines.append("Kullanım zorlama testi: " + "; ".join(rough[:4]))
    return " | ".join(lines)
