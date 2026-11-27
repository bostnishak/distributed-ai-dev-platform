"""Random rapid clicking and hostile input on a generated page in a real headless browser, with the network blocked.

Uncaught errors are what is reported. The seed is fixed so a finding can be reproduced.
"""

from __future__ import annotations

import logging
from pathlib import Path

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


def report(ws_dir: Path) -> str | None:
    """"" when the page survived, a warning line when it threw, None when there is no page or no browser."""
    page = ws_dir / "index.html"
    if not page.is_file():
        return None
    found = errors(page)
    if found is None:
        return None
    return "Rastgele tıklama testinde yakalanmamış hata: " + "; ".join(found[:3]) if found else ""
