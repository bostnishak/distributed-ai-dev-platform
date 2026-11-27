"""Use a running web application the way a person would, and keep the evidence.

Fill the main form with a new value, submit it, see it appear; reload the page and see it still there; restart the
server and see it once more; submit an empty form and expect no new entry; delete the entry where there is a button
for it. Console errors, page errors and server errors fail the journey. Each step leaves a screenshot.
"""

from __future__ import annotations

import re
import time
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
    requests: list[dict[str, Any]] = field(default_factory=list)  # HTTP trace of the browser
    rows: dict[str, dict[str, int]] = field(default_factory=dict)  # database row counts at named moments
    shots: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.monotonic)

    def step(self, name: str, ok: bool, detail: str = "") -> bool:
        self.steps.append({"name": name, "ok": ok, "detail": detail[:200], "at_s": round(time.monotonic() - self.started, 2)})
        return ok

    @property
    def passed(self) -> bool:
        return bool(self.steps) and all(s["ok"] for s in self.steps) and not self.errors

    def summary(self) -> str:
        failed = [f"{s['name']}: {s['detail'] or 'başarısız'}" for s in self.steps if not s["ok"]]
        if failed or self.errors:
            return "; ".join(failed + list(dict.fromkeys(self.errors)))[:500]
        return "geçen adımlar: " + ", ".join(s["name"] for s in self.steps)


_ASSETS = ("stylesheet", "script", "image", "font", "document")


def _seen(response: Any, journey: Journey) -> None:
    request = response.request
    if len(journey.requests) < 200:
        journey.requests.append({"method": request.method, "url": response.url.split("//", 1)[-1].split("/", 1)[-1][:120], "status": response.status, "type": request.resource_type})
    name = response.url.rsplit("/", 1)[-1]
    if response.status >= 500:
        journey.errors.append(f"sunucu hatası {response.status}: {name}")
    elif response.status >= 400 and request.resource_type in _ASSETS and "favicon" not in name:
        journey.errors.append(f"yüklenemeyen varlık {response.status}: {name}")


def _created(journey: Journey, since: int) -> None:
    """The request that stored the entry must answer 201 Created (a classic form post may redirect instead)."""
    posts = [r for r in journey.requests[since:] if r["method"] == "POST"]
    if posts:
        status = posts[0]["status"]
        journey.step("kayıt isteği 201 döndü", status in (201, 302, 303), f"POST /{posts[0]['url']} {status} döndürdü (201 Created bekleniyor)")


def _row_step(journey: Journey, rows: Callable[[], dict[str, int]] | None, moment: str) -> None:
    if rows is None:
        return
    journey.rows[moment] = rows()
    if moment == "gönderim-sonrası" and journey.rows.get("önce") is not None and journey.rows[moment]:
        grown = sum(journey.rows[moment].values()) - sum(journey.rows["önce"].values())
        journey.step("veritabanında satır arttı", grown >= 1, f"satır farkı {grown}: kayıt veritabanına yazılmamış")
    if moment == "yeniden-başlatma-sonrası" and journey.rows.get("gönderim-sonrası"):
        same = sum(journey.rows[moment].values()) >= sum(journey.rows["gönderim-sonrası"].values())
        journey.step("satırlar yeniden başlatmadan sonra duruyor", same, str(journey.rows[moment]))


def _entry(page: Any, marker: str) -> Any:
    return page.locator("li, tr, article, .card, .item, .row, div").filter(has_text=marker).filter(has=page.locator("button, input[type=checkbox]")).last


def _toggle(page: Any, journey: Journey, marker: str) -> None:
    """Tick the entry's checkbox where there is one, and expect it still ticked after a reload."""
    box = _entry(page, marker).locator("input[type=checkbox]").first
    if not box.count():
        return
    wanted = not box.is_checked()
    box.click()
    page.wait_for_timeout(_WAIT_MS)
    page.reload()
    page.wait_for_timeout(_WAIT_MS)
    kept = _entry(page, marker).locator("input[type=checkbox]").first
    journey.step("durum değişikliği kalıcı", bool(kept.count()) and kept.is_checked() == wanted, "yenileyince eski durumuna döndü")


def _filter(page: Any, journey: Journey, marker: str) -> None:
    """Search for the entry and for nonsense, where the page offers a search box."""
    search = page.locator("input[type=search]:visible, input[placeholder*='ara' i]:visible, input[placeholder*='filtre' i]:visible, input[placeholder*='search' i]:visible").first
    if not search.count():
        return
    search.fill(marker)
    page.wait_for_timeout(_WAIT_MS)
    found = _shown(page, marker)
    search.fill("zzzz-olmayan-kayıt")
    page.wait_for_timeout(_WAIT_MS)
    hidden = not _shown(page, marker)
    search.fill("")
    page.wait_for_timeout(_WAIT_MS)
    journey.step("arama süzüyor", found and hidden, "eşleşen kayıt görünmüyor" if not found else "eşleşmeyen aramada kayıt hâlâ görünüyor")


def _watch(page: Any, journey: Journey, expected_errors: list[bool]) -> None:
    page.on("pageerror", lambda error: journey.errors.append(f"sayfa hatası: {str(error)[:120]}"))
    page.on("console", lambda m: journey.errors.append(f"konsol hatası: {m.text[:120]}") if m.type == "error" and "favicon" not in m.text and not expected_errors else None)
    page.on("response", lambda r: _seen(r, journey))
    page.on("requestfailed", lambda r: journey.errors.append(f"istek başarısız: {r.url.rsplit('/', 1)[-1]}") if r.resource_type in _ASSETS else None)


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


def _walk(page: Any, journey: Journey, url: str, server: tuple[Callable[[], None] | None, Callable[[], dict[str, int]] | None], hooks: tuple[Callable[[str], None], list[bool]]) -> None:
    shot, expected = hooks
    restart, rows = server
    page.goto(url, timeout=30000)
    page.wait_for_timeout(_WAIT_MS)
    shot("ilk-yükleme")
    journey.step("sayfa açıldı", bool(page.inner_text("body").strip()), "sayfa boş")
    marker = f"Kanıt {uuid.uuid4().hex[:6]} İğdır"
    button = _fill_form(page, marker)
    if not journey.step("form bulundu", button is not None, "yazı alanı ve gönder düğmesi olan bir form yok"):
        return
    shot("dolu-form")
    _row_step(journey, rows, "önce")
    sent = len(journey.requests)
    button.click()
    page.wait_for_timeout(_WAIT_MS)
    shot("gönderim-sonrası")
    _created(journey, sent)
    _row_step(journey, rows, "gönderim-sonrası")
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
        _row_step(journey, rows, "yeniden-başlatma-sonrası")
    _toggle(page, journey, marker)
    _filter(page, journey, marker)
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


def page_text(url: str) -> str:
    """What the page shows right now; ValueError when no browser can be used."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError("tarayıcı kurulu değil") from exc
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_timeout(_WAIT_MS)
                return str(page.inner_text("body"))
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise ValueError(f"sayfa okunamadı: {str(exc).splitlines()[0]}") from exc


def run(url: str, folder: Path, restart: Callable[[], None] | None = None, rows: Callable[[], dict[str, int]] | None = None) -> Journey:
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
                journey.shots.append(f"{count[0]:02d}-{name}.png")

            try:
                _walk(page, journey, url, (restart, rows), (shot, expected))
            finally:
                browser.close()
    except (PlaywrightError, OSError) as exc:
        journey.step("yolculuk tamamlanamadı", False, str(exc).splitlines()[0])
    return journey
