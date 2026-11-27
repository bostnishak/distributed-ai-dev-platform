"""The machine check behind each ledger entry, run on the page that was really written, in a real browser.

A verdict is (passed, detail): True met, False not met, None undecidable here (left to a person, never counted as met).
"""

from __future__ import annotations

import contextlib
import html
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from prompt_loader import load_prompt
from req_ledger import Req

Verdict = tuple["bool | None", str]
_PROBE = "deneme-7Q"
_ADD_RE = re.compile(r"ekle|kaydet|oluştur|add|save|create", re.IGNORECASE)
_FILTER_RE = re.compile(r"tümü|hepsi|\ball\b|aktif|biten|tamamlanan|bekleyen|filtre|filter", re.IGNORECASE)
_BOUND_JS = ("(() => { const add = EventTarget.prototype.addEventListener; window.__bound = new WeakSet();"
             " EventTarget.prototype.addEventListener = function (type, ...rest) { if (type === 'click') window.__bound.add(this); return add.call(this, type, ...rest); }; })()")
_REMOVE_RE = re.compile(r"\bsil|temizle|kaldır|delete|remove|clear", re.IGNORECASE)
_EXTERNAL_TAG_RE = re.compile(r"""<(?:script|link|img|iframe)\b[^>]+(?:src|href)\s*=\s*["']https?://|@import\s+url\(["']?https?://""", re.IGNORECASE)
_DIALOG_CALL_RE = re.compile(r"(?<![\w.])(?:window\.)?(?:alert|confirm|prompt)\s*\(")
_HEAD = "header, [class*='header' i], [id*='header' i], [class*='topbar' i], [id*='topbar' i], [class*='navbar' i], [class*='ust' i]"
_SIDE = "aside, nav, [class*='sidebar' i], [id*='sidebar' i], [class*='side-' i], [class*='menu' i], [id*='menu' i]"
_FOOT = "footer, [class*='footer' i], [id*='footer' i], [class*='alt-' i], [class*='bottom' i]"
_MAIN = "main, [role=main], [class*='main' i], [id*='main' i], [class*='content' i], [id*='content' i]"
# a semantic tag or the usual class/id names: a visible div.header is a header
_REGIONS = (("üst", _HEAD), ("header", _HEAD), ("başlık", _HEAD), ("yan", _SIDE), ("sidebar", _SIDE), ("menü", _SIDE), ("alt", _FOOT), ("footer", _FOOT), ("ana", _MAIN), ("main", _MAIN))
_FOLD = str.maketrans("çğıöşü ", "cgiosu-")


def _source(ws_dir: Path) -> str:
    files = (p for p in ws_dir.rglob("*") if p.suffix in (".html", ".css", ".js", ".py") and p.is_file() and "vendor" not in p.parts and not any(x.startswith(".") for x in p.relative_to(ws_dir).parts))
    return html.unescape("\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files))


def _from_source(req: Req, source: str) -> Verdict | None:
    """The kinds the written files alone decide; None when the page has to be opened."""
    if req.kind in ("renk", "ölçü"):
        found = req.target.casefold() in source.casefold()
        return found, "" if found else f"{req.target} hiçbir dosyada yok"
    if req.kind == "dış kaynak yok":
        return not _EXTERNAL_TAG_RE.search(source), "dış adresten dosya yükleniyor" if _EXTERNAL_TAG_RE.search(source) else ""
    if req.kind == "açılır pencere yok":
        return not _DIALOG_CALL_RE.search(source), "alert/confirm/prompt çağrısı var" if _DIALOG_CALL_RE.search(source) else ""
    if req.kind == "uç nokta":
        method, path = req.target.split(" ", 1)
        declared = re.search(rf"\.{method.lower()}\(\s*[\"'`]{re.escape(path.rstrip('/'))}/?[\"'`]", source)
        return bool(declared), "" if declared else "kodda tanımlı değil"
    return (None, "makine denetimi yok") if req.kind == "elle" else None


def _fill(page: Any, value: str) -> None:
    for field in page.locator("input:visible, textarea:visible").all():
        kind = (field.get_attribute("type") or "text").lower()
        if kind in ("checkbox", "radio", "button", "submit", "file", "range", "color", "hidden"):
            continue
        with contextlib.suppress(Exception):
            field.fill({"number": "3" if value else "", "date": "2026-11-27" if value else "", "email": "a@b.co" if value else ""}.get(kind, value))


def _button(page: Any, label: str) -> Any:
    found = page.locator(f"button:has-text({label!r}), [role=button]:has-text({label!r}), input[type=button][value={label!r}], input[type=submit][value={label!r}], a:has-text({label!r})")
    return found.first if found.count() else None


def _adder(page: Any) -> Any:
    for candidate in page.locator("button, input[type=submit]").all():
        if _ADD_RE.search(candidate.inner_text() or candidate.get_attribute("value") or "") and candidate.is_visible():
            return candidate
    return None


def _add_record(page: Any) -> bool:
    adder = _adder(page)
    if adder is None:
        return False
    _fill(page, _PROBE)
    adder.click(timeout=2000)
    page.wait_for_timeout(150)
    return True


def _records(page: Any) -> int:
    return int(page.evaluate("document.querySelectorAll('li, tbody tr, .item, .card, [data-id]').length"))


def _check_button(page: Any, req: Req) -> Verdict:
    adds = bool(_ADD_RE.search(req.target))
    if not adds:
        _add_record(page)
    button = _button(page, req.target)
    if button is None:
        return False, "bu yazıyla bir düğme yok"
    before = page.evaluate("document.body.innerHTML + JSON.stringify(localStorage)")
    had = page.inner_text("body").count(_PROBE)
    if adds:
        _fill(page, _PROBE)
    if not button.is_enabled():
        return False, "düğme tıklanamıyor"
    button.click(timeout=2000)
    page.wait_for_timeout(200)
    shown = page.inner_text("body").count(_PROBE)
    if adds and shown <= had:
        return False, "tıklayınca yazılan metin sayfada görünmüyor"
    if _REMOVE_RE.search(req.target) and had and shown >= had:
        return False, "tıklayınca kayıt kaybolmuyor"
    changed = adds or page.evaluate("document.body.innerHTML + JSON.stringify(localStorage)") != before
    if not changed and _FILTER_RE.search(req.target):  # the filter that is already selected changes nothing; it must still be wired
        changed = bool(button.evaluate("e => window.__bound.has(e) || !!e.onclick || !!e.form"))
    return changed, "" if changed else "tıklayınca sayfada hiçbir şey değişmiyor"


def _check_region(page: Any, req: Req) -> Verdict:
    name = req.target.casefold()
    slug = re.sub(r"[^a-z0-9-]", "", name.translate(_FOLD))
    selectors = [selector for word, selector in _REGIONS if re.search(rf"\b{word}", name)] + [f"[id*='{part}' i], [class*='{part}' i]" for part in slug.split("-") if len(part) > 3]
    for selector in selectors:
        found = page.locator(selector)
        if found.count() and (box := found.first.bounding_box()) and box["width"] > 20 and box["height"] > 10:
            return True, ""
    return False, "bu bölgeye karşılık gelen görünür bir alan yok"


def _check_page(page: Any, req: Req) -> Verdict:
    if req.kind == "yazı":
        shown = page.evaluate("document.body.innerText + ' ' + [...document.querySelectorAll('input,textarea,[aria-label],[title]')].map(e => [e.placeholder, e.value, e.getAttribute('aria-label'), e.title].join(' ')).join(' ') + ' ' + document.title")
        found = req.target.casefold() in shown.casefold()
        return found, "" if found else "ekranda görünmüyor"
    if req.kind == "bölge":
        return _check_region(page, req)
    if req.kind == "düğme":
        return _check_button(page, req)
    if req.kind == "kalıcılık":
        if not _add_record(page):
            return False, "kayıt ekleyen bir düğme yok"
        page.reload()
        page.wait_for_timeout(250)
        kept = _PROBE in page.inner_text("body")
        return kept, "" if kept else "yenileyince eklenen kayıt kayboluyor"
    if req.kind == "boş girdi":
        _fill(page, "")
        adder = _adder(page)
        if adder is None:
            return False, "kayıt ekleyen bir düğme yok"
        before = _records(page)
        if adder.is_enabled():
            adder.click(timeout=2000)
            page.wait_for_timeout(150)
        return _records(page) <= before, "" if _records(page) <= before else "boş girdi kayıt ekledi"
    return _check_narrow(page)


def _check_narrow(page: Any) -> Verdict:
    """No sideways scrolling on a phone; the detail names what sticks out, so the repair knows where to look."""
    page.set_viewport_size({"width": 375, "height": 740})
    page.wait_for_timeout(150)
    wide = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    if wide <= 4:
        return True, ""
    culprits = page.evaluate(load_prompt("overflow_elements.js.txt"))
    return False, f"dar ekranda {wide} piksel yatay taşma; taşan öğeler: {', '.join(culprits)}. Genellikle sebep: box-sizing: border-box yok, sabit genişlik ya da margin+padding ile %100 aşımı."


@contextlib.contextmanager
def _browser() -> Iterator[Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        try:
            yield browser
        finally:
            browser.close()


def _on_fresh_page(browser: Any, url: str, req: Req) -> Verdict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    try:
        context.add_init_script(_BOUND_JS)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.goto(url, timeout=10000)
        page.wait_for_timeout(200)
        passed, detail = _check_page(page, req)
        if errors and req.kind in ("düğme", "kalıcılık", "boş girdi"):
            return False, f"sayfada JavaScript hatası: {errors[0][:120]}"
        return passed, detail
    finally:
        context.close()


def evaluate(ws_dir: Path, ledger: tuple[Req, ...]) -> dict[str, Verdict]:
    """One verdict per requirement; every browser check starts from an untouched page."""
    source = _source(ws_dir)
    verdicts = {r.id: verdict for r in ledger if (verdict := _from_source(r, source)) is not None}
    pending = [r for r in ledger if r.id not in verdicts]
    index = ws_dir / "index.html"
    if pending and not index.is_file():
        return {**verdicts, **{r.id: (None, "tek sayfa yok; canlı sunucu denetimine kaldı") for r in pending}}
    if not pending:
        return verdicts
    try:
        with _browser() as browser:
            for req in pending:
                try:
                    verdicts[req.id] = _on_fresh_page(browser, index.resolve().as_uri(), req)
                except Exception as exc:  # noqa: BLE001, RUF100  # any Playwright failure fails this one check
                    verdicts[req.id] = (False, f"denetim yapılamadı: {type(exc).__name__}")
    except Exception as exc:  # noqa: BLE001, RUF100  # no usable browser on this machine
        verdicts.update({r.id: (None, f"tarayıcı açılamadı: {type(exc).__name__}") for r in pending})
    return verdicts


def unmet(ledger: tuple[Req, ...], verdicts: dict[str, Verdict]) -> list[str]:
    return [f"{r.line()} -> {verdicts[r.id][1]}" for r in ledger if r.id in verdicts and verdicts[r.id][0] is False]


def score(verdicts: dict[str, Verdict]) -> tuple[int, int]:
    """(met, decidable)."""
    decided = [passed for passed, _ in verdicts.values() if passed is not None]
    return sum(decided), len(decided)
