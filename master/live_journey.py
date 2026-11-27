"""Use a running web application the way a person would, and keep the evidence.

Fill the main form with a new value, submit it, see it appear; reload the page and see it still there; restart the
server and see it once more; submit an empty form and expect no new entry; delete the entry where there is a button
for it. Console errors, page errors and server errors fail the journey. Each step leaves a screenshot.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DELETE_RE = re.compile(r"^\s*(?:sil|kaldır|delete|remove|00d7|2715|2716|0001F5D1FE0F?)\s*$", re.IGNORECASE)
_FILL = {"number": "7", "date": "2027-03-14", "email": "deneme@example.com", "tel": "5550000000", "url": "https://example.com", "time": "10:30"}
_WAIT_MS = 900


@dataclass
class Journey:
    steps: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def step(self, name: str, ok: bool, detail: str = "") -> bool:
        self.steps.append({"name": name, "ok": ok, "detail": detail[:200]})
        return ok

    @property
    def passed(self) -> bool:
        return bool(self.steps) and all(s["ok"] for s in self.steps) and not self.errors

    def summary(self) -> str:
        failed = [f"{s['name']}: {s['detail'] or 'başarısız'}" for s in self.steps if not s["ok"]]
        if failed or self.errors:
            return "; ".join(failed + list(dict.fromkeys(self.errors)))[:500]
        return "geçen adımlar: " + ", ".join(s["name"] for s in self.steps)


def _watch(page: Any, journey: Journey, expected_errors: list[bool]) -> None:
    page.on("pageerror", lambda error: journey.errors.append(f"sayfa hatası: {str(error)[:120]}"))
    page.on("console", lambda m: journey.errors.append(f"konsol hatası: {m.text[:120]}") if m.type == "error" and "favicon" not in m.text and not expected_errors else None)
    page.on("response", lambda r: journey.errors.append(f"sunucu hatası {r.status}: {r.url.rsplit('/', 1)[-1]}") if r.status >= 500 else None)


def _fill_form(page: Any, marker: str) -> Any:
    """The first form (or the page itself) with a visible text field; returns its submit control or None."""
    form = page.locator("form").filter(has=page.locator("input:visible, textarea:visible")).first
    scope = form if form.count() else page.locator("body")
    fields = scope.locator("input:visible, textarea:visible, select:visible")
    wrote = False
    for index in range(fields.count()):
        item = fields.nth(index)
        tag = item.evaluate("e => e.tagName.toLowerCase()")
        kind = (item.get_attribute("type") or "text").lower()
        if tag == "select":
            values = item.evaluate("e => [...e.options].map(o => o.value).filter(Boolean)")
            if values:
                item.select_option(values[0])
        elif kind in ("checkbox", "radio", "hidden", "submit", "button", "file", "range", "color", "search"):
            continue
        elif kind in _FILL:
            item.fill(_FILL[kind])
        else:
            item.fill(marker if not wrote else f"{marker} not")
            wrote = True
    button = scope.locator("button[type=submit], input[type=submit], button:not([type])").first
    if not button.count():
        button = scope.locator("button:visible").first
    return button if wrote and button.count() else None


def _shown(page: Any, marker: str) -> bool:
    return marker in page.inner_text("body")


def _delete(page: Any, marker: str) -> bool | None:
    """Delete the entry that holds the marker; None when the page offers no delete control for it."""
    container = page.locator("li, tr, article, .card, .item, .row, div").filter(has_text=marker).filter(has=page.locator("button")).last
    if not container.count():
        return None
    buttons = container.locator("button")
    for index in range(buttons.count()):
        button = buttons.nth(index)
        label = f"{button.inner_text()} {button.get_attribute('aria-label') or ''} {button.get_attribute('title') or ''}".strip()
        if any(_DELETE_RE.match(part) for part in (button.inner_text(), button.get_attribute("aria-label") or "", button.get_attribute("title") or "")) or "sil" in label.lower():
            button.click()
            page.wait_for_timeout(_WAIT_MS)
            return not _shown(page, marker)
    return None


def _walk(page: Any, journey: Journey, url: str, restart: Callable[[], None] | None, hooks: tuple[Callable[[str], None], list[bool]]) -> None:
    shot, expected = hooks
    page.goto(url, timeout=30000)
    page.wait_for_timeout(_WAIT_MS)
    shot("ilk-yükleme")
    journey.step("sayfa açıldı", bool(page.inner_text("body").strip()), "sayfa boş")
    marker = f"Kanıt {uuid.uuid4().hex[:6]} İğdır"
    button = _fill_form(page, marker)
    if not journey.step("form bulundu", button is not None, "yazı alanı ve gönder düğmesi olan bir form yok"):
        return
    shot("dolu-form")
    button.click()
    page.wait_for_timeout(_WAIT_MS)
    shot("gönderim-sonrası")
    if not journey.step("kayıt listede göründü", _shown(page, marker), f"{marker!r} görünmüyor"):
        return
    page.reload()
    page.wait_for_timeout(_WAIT_MS)
    shot("yenileme-sonrası")
    journey.step("sayfa yenilenince duruyor", _shown(page, marker), "kayıt yalnız tarayıcı belleğindeymiş")
    if restart:
        restart()
        page.reload()
        page.wait_for_timeout(_WAIT_MS)
        shot("sunucu-yeniden-başladı")
        journey.step("sunucu yeniden başlayınca duruyor", _shown(page, marker), "kayıt diske yazılmamış")
    entries = "li, tbody tr, article, .card, .item"  # a validation message is not a new entry
    before = page.locator(entries).count()
    expected.append(True)  # a refused empty submission may log a 4xx in the console: that is correct behaviour
    empty = page.locator("form button, button[type=submit], input[type=submit]").first
    if empty.count():
        empty.click()
        page.wait_for_timeout(_WAIT_MS)
        grown = page.locator(entries).count() - before
        journey.step("boş gönderim kayıt eklemedi", grown <= 0, f"{grown} boş kayıt eklendi")
        shot("boş-gönderim")
    expected.clear()
    removed = _delete(page, marker)
    if removed is not None:
        journey.step("silme çalışıyor", removed, "silinen kayıt hâlâ görünüyor")
        page.reload()
        page.wait_for_timeout(_WAIT_MS)
        journey.step("silme kalıcı", not _shown(page, marker), "yenileyince geri geldi")
        shot("silme-sonrası")


def run(url: str, folder: Path, restart: Callable[[], None] | None = None) -> Journey:
    """ValueError when no browser is available; otherwise the journey with its steps and screenshots in `folder`."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError("tarayıcı kurulu değil") from exc
    journey = Journey()
    expected: list[bool] = []
    folder.mkdir(parents=True, exist_ok=True)
    count = [0]
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1100, "height": 800})
            _watch(page, journey, expected)

            def shot(name: str) -> None:
                count[0] += 1
                page.screenshot(path=str(folder / f"{count[0]:02d}-{name}.png"))

            try:
                _walk(page, journey, url, restart, (shot, expected))
            finally:
                browser.close()
    except (PlaywrightError, OSError) as exc:
        journey.step("yolculuk tamamlanamadı", False, str(exc).splitlines()[0])
    return journey
