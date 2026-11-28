"""The reality torture suite: what breaks real applications after the happy path works.

Triple clicks, parallel writes, a failing or vanished server, slow 3G, history and deep links, Turkish and hostile
text, exact money, an empty and a very full list, and growth over repeated use. Each check answers (passed, detail);
passed None means it does not apply to this application.
"""

from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

import leak_check
import torture_files
import torture_probe as probe
from process_utils import run_process
from prompt_loader import load_prompt

Outcome = tuple["bool | None", str]
_ERROR_WORDS = re.compile(r"hata|başarısız|olmadı|edilemedi|eklenemedi|bağlantı|error|failed|offline|çevrimdışı", re.IGNORECASE)
_BUSY_WORDS = re.compile(r"yükleniyor|kaydediliyor|ekleniyor|gönderiliyor|loading|saving", re.IGNORECASE)
_BROKEN_NUMBER = re.compile(r"\d\.\d{9,}|\bNaN\b|\bInfinity\b|\bundefined\b|\[object Object\]")
_HOSTILE = "<img src=x onerror=window.__xss=1> '\" & ; -- 🎉 مرحبا"
_SCALE = 1000
_SLOW_MS = 200
_SERVER_GROWTH_MIB = 30
_log = logging.getLogger(__name__)


def _double_submit(session: probe.Session, _url: str) -> Outcome:
    if not probe.usable(session.page):
        return None, "kayıt ekleyen alan yok"
    probe.add(session.page, "üçlü-tık-41", clicks=3)
    session.page.wait_for_timeout(700)
    count = probe.shown(session.page, "üçlü-tık-41")
    return count <= 1, "" if count <= 1 else f"üç hızlı tıklama {count} kayıt oluşturdu"


def _concurrent_writes(session: probe.Session, url: str) -> Outcome:
    if not probe.usable(session.page):
        return None, "kayıt ekleyen alan yok"
    probe.add(session.page, "eşzaman-0")
    seen = next((w for w in session.writes if "eşzaman-0" in w["body"] or "e%C5%9Fzaman-0" in w["body"]), None)
    if seen is None:
        return None, "sunucuya yazma isteği yok"

    def send(number: int) -> int:
        body = seen["body"].replace("eşzaman-0", f"eşzaman-{number}")
        headers = {"content-type": "application/json" if body.lstrip().startswith("{") else "application/x-www-form-urlencoded"}
        return httpx.request(seen["method"], seen["url"], content=body.encode("utf-8"), headers=headers, timeout=30).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(send, range(1, 11)))
    if any(code >= 500 for code in codes):
        return False, f"10 eşzamanlı yazmada sunucu hatası: {codes}"
    session.page.goto(url)
    session.page.wait_for_timeout(1200)
    missing = [n for n in range(1, 11) if not re.search(rf"eşzaman-{n}(?!\d)", session.page.inner_text("body"))]
    return not missing, "" if not missing else f"10 eşzamanlı yazmanın {len(missing)} tanesi kayboldu"


def _recoverable(session: probe.Session, label: str) -> Outcome:
    """After a write that could not reach the server: an error is shown, the typed text stays, nothing spins forever."""
    session.page.wait_for_timeout(2500)
    body = session.page.inner_text("body")
    field = probe.text_field(session.page)
    problems = []
    if not _ERROR_WORDS.search(body):
        problems.append("hata iletisi yok")
    if field is not None and "kayıp-olmasın" not in field.input_value() and "kayıp-olmasın" not in body:
        problems.append("yazılan metin sessizce silindi")
    if _BUSY_WORDS.search(body):
        problems.append("yükleniyor göstergesi takılı kaldı")
    problems += session.errors[:1]
    return not problems, "" if not problems else f"{label}: " + ", ".join(problems)


def _writes_to_server(session: probe.Session) -> bool:
    if not probe.usable(session.page):
        return False
    probe.add(session.page, "ağ-yoklaması")
    return bool(session.writes)


def _server_error(session: probe.Session, _url: str) -> Outcome:
    if not _writes_to_server(session):
        return None, "sunucuya yazma yok"
    session.page.route("**/*", lambda r: r.fulfill(status=503, body="down") if r.request.method != "GET" else r.continue_())
    probe.add(session.page, "kayıp-olmasın")
    return _recoverable(session, "sunucu 503 verince")


def _offline(session: probe.Session, _url: str) -> Outcome:
    if not _writes_to_server(session):
        return None, "sunucuya yazma yok"
    session.context.set_offline(True)
    probe.add(session.page, "kayıp-olmasın")
    return _recoverable(session, "bağlantı kesilince")


def _slow_network(session: probe.Session, _url: str) -> Outcome:
    if not _writes_to_server(session):
        return None, "sunucuya yazma yok"
    cdp = session.context.new_cdp_session(session.page)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 1500, "downloadThroughput": 50_000, "uploadThroughput": 50_000})
    probe.fill(session.page, "yavaş-ağ-7")
    button = probe.adder(session.page)
    button.click()
    session.page.wait_for_timeout(250)
    busy = not button.is_enabled() or bool(_BUSY_WORDS.search(session.page.inner_text("body")))
    session.page.wait_for_timeout(6000)
    if probe.shown(session.page, "yavaş-ağ-7") != 1:
        return False, "yavaş ağda kayıt görünmedi ya da çoğaldı"
    return busy, "" if busy else "yavaş ağda gönderim sürerken düğme kilitlenmiyor / yükleniyor yazmıyor"


def _history(session: probe.Session, url: str) -> Outcome:
    page = session.page
    page.goto(url + "?q=deneme&filtre=tümü")
    page.wait_for_timeout(300)
    page.goto(url + "#ikinci")
    page.go_back()
    page.wait_for_timeout(300)
    page.go_forward()
    page.wait_for_timeout(300)
    if session.errors:
        return False, f"geri/ileri ya da derin bağlantıda hata: {session.errors[0]}"
    if len(page.inner_text("body").strip()) < 3:
        return False, "geri/ileri sonrasında sayfa boş kaldı"
    search = probe.search_field(page)
    if search is None:
        return True, ""
    search.fill("abc")
    page.wait_for_timeout(300)
    if "abc" not in page.url:
        return True, ""
    page.reload()
    page.wait_for_timeout(400)
    kept = (probe.search_field(page) or search).input_value() == "abc"
    return kept, "" if kept else "süzgeç adreste duruyor ama yenileyince kutuya geri gelmiyor"


def _turkish_search(session: probe.Session, _url: str) -> Outcome:
    page = session.page
    if not probe.usable(page) or probe.search_field(page) is None:
        return None, "ekleme ya da arama alanı yok"
    probe.add(page, "İSTANBUL kaydı")
    probe.add(page, "Iğdır kaydı")
    missed = []
    for query, expected in (("istanbul", "İSTANBUL"), ("İstanbul", "İSTANBUL"), ("IĞDIR", "Iğdır"), ("ığdır", "Iğdır")):
        probe.search_field(page).fill(query)
        probe.search_field(page).dispatch_event("input")
        page.wait_for_timeout(400)
        if not probe.shown(page, expected):
            missed.append(f"'{query}' → '{expected}'")
    return not missed, "" if not missed else "Türkçe büyük/küçük harf araması bulamıyor: " + ", ".join(missed)


def _hostile_text(session: probe.Session, _url: str) -> Outcome:
    if not probe.usable(session.page):
        return None, "kayıt ekleyen alan yok"
    probe.add(session.page, _HOSTILE)
    if session.page.evaluate("window.__xss === 1"):
        return False, "girilen metin HTML olarak çalıştı (XSS)"
    literal = probe.shown(session.page, "<img src=x") and probe.shown(session.page, "🎉") and probe.shown(session.page, "مرحبا")
    return bool(literal) and not session.errors, "" if literal and not session.errors else "özel karakterli kayıt aynen görünmüyor"


def _exact_money(session: probe.Session, _url: str) -> Outcome:
    page = session.page
    if not probe.usable(page) or not page.locator("input[type=number]:visible").count():
        return None, "tutar alanı yok"
    probe.add(page, "kalem-bir", "0.1")
    probe.add(page, "kalem-iki", "0.2")
    found = _BROKEN_NUMBER.search(page.inner_text("body"))
    return not found, "" if not found else f"para hesabı kayan noktayla yapılıyor: {found.group(0)}"


def _empty_state(session: probe.Session, _url: str) -> Outcome:
    found = _BROKEN_NUMBER.search(session.page.inner_text("body"))
    return not found, "" if not found else f"kayıt yokken ekranda '{found.group(0)}' yazıyor"


def _scale(session: probe.Session, _url: str) -> Outcome:
    if not probe.usable(session.page):
        return None, "kayıt ekleyen alan yok"
    probe.add(session.page, "ilk-kayıt")
    if session.writes:
        return None, "sunucuya yazan uygulama; bin kayıt tarayıcıdan basılmaz"
    session.page.set_default_timeout(90000)
    measured = session.page.evaluate(load_prompt("torture_flood.js.txt"), [_SCALE])
    if session.errors:
        return False, f"{_SCALE} kayıtta hata: {session.errors[0]}"
    slow = measured["ms"] > _SLOW_MS
    return not slow, f"{_SCALE} kayıtta ekleme {measured['ms']:.0f} ms, {measured['nodes']} DOM öğesi" + (f" (sınır {_SLOW_MS} ms)" if slow else "")


def _boundaries(session: probe.Session, _url: str) -> Outcome:
    """One record, then negative, zero and enormous numbers and a leap-day date: nothing turns into NaN or Invalid Date."""
    page = session.page
    if not probe.usable(page):
        return None, "kayıt ekleyen alan yok"
    for number, label in (("0", "sıfır-kayıt"), ("-5", "eksi-kayıt"), ("999999999999", "dev-kayıt")):
        probe.add(page, label, number)
    body = page.inner_text("body")
    found = _BROKEN_NUMBER.search(body) or re.search("Invalid Date", body)
    if found or session.errors:
        return False, f"sınır değerlerde '{found.group(0)}' yazıyor" if found else f"sınır değerlerde hata: {session.errors[0]}"
    return bool(probe.shown(page, "sıfır-kayıt")), "" if probe.shown(page, "sıfır-kayıt") else "tutarı sıfır olan kayıt görünmüyor"


QUICK: dict[str, Callable[[probe.Session, str], Outcome]] = {
    "çift gönderim": _double_submit, "Türkçe arama": _turkish_search, "özel karakter ve XSS": _hostile_text, "para hesabı": _exact_money,
    "boş durum": _empty_state, "sayı ve tarih sınırları": _boundaries, **torture_files.CHECKS, "geri/ileri ve derin bağlantı": _history,
}
NETWORK: dict[str, Callable[[probe.Session, str], Outcome]] = {"sunucu hatası": _server_error, "çevrimdışı": _offline, "yavaş ağ": _slow_network, "10 eşzamanlı yazma": _concurrent_writes}
HEAVY: dict[str, Callable[[probe.Session, str], Outcome]] = {"1000 kayıt": _scale}


def _one(browser: Any, url: str, check: Callable[[probe.Session, str], Outcome]) -> Outcome:
    try:
        with probe.opened(browser, url) as session:
            return check(session, url)
    except Exception as exc:  # noqa: BLE001, RUF100  # any Playwright failure fails this one check
        return False, f"denetim yapılamadı: {type(exc).__name__}: {str(exc).splitlines()[0][:120] if str(exc) else ''}"


def run(url: str, checks: dict[str, Callable[[probe.Session, str], Outcome]]) -> dict[str, Outcome] | None:
    """Every check on its own fresh page; None when no browser can be started."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                return {name: _one(browser, url, check) for name, check in checks.items()}
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001, RUF100  # no usable browser on this machine
        _log.warning("zorlama testi koşulamadı: %s", exc)
        return None


def server_memory(container: str) -> float | None:
    """Resident memory of the application's container in MiB; None when Docker does not say."""
    done = run_process(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container], timeout_s=30)
    found = re.match(r"\s*([\d.]+)\s*([KMG]i?B)", done.stdout or "")
    return round(float(found[1]) * {"K": 1 / 1024, "M": 1, "G": 1024}[found[2][0]], 1) if found else None


def server_growth(url: str, container: str, write: Callable[[int], None], cycles: int = 50) -> Outcome:
    """The server's memory before and after fifty writes and reads."""
    write(0)
    httpx.get(url, timeout=30)
    before = server_memory(container)
    for number in range(1, cycles + 1):
        write(number)
        httpx.get(url, timeout=30)
    after = server_memory(container)
    if before is None or after is None:
        return None, "bellek okunamadı"
    return after - before < _SERVER_GROWTH_MIB, f"{cycles} yazma-okumada sunucu belleği {before} -> {after} MiB"


def leaks(url: str) -> Outcome:
    """Node, listener and heap growth over fifty repeated interactions."""
    started = time.time()
    try:
        grown = leak_check.measure(url).leaks()
    except ValueError as exc:
        return None, str(exc)
    return not grown, "; ".join(grown) if grown else f"50 tekrar, {time.time() - started:.0f} sn"


def failures(results: dict[str, Outcome]) -> list[str]:
    return [f"{name}: {detail}" for name, (passed, detail) in results.items() if passed is False]


ADVISORY = ("sunucu hatası", "çevrimdışı", "yavaş ağ")  # how it behaves when the network fails: told, not blocking


def judged(status_detail: tuple[str, str], results: dict[str, Outcome] | None, failed: str) -> tuple[str, str]:
    """A passed live proof that loses or corrupts data under torture is a failed one; network manners are warnings."""
    status, detail = status_detail
    broken = {name: outcome for name, outcome in (results or {}).items() if outcome[0] is False}
    if blocking := failures({n: o for n, o in broken.items() if n not in ADVISORY}):
        return failed, ("Zorlama testi: " + "; ".join(blocking[:4]))[:600]
    if broken:
        return status, f"{detail} | zorlama uyarısı: {'; '.join(failures(broken)[:3])}"[:600]
    return status, detail


def page_failures(ws_dir: Path) -> list[str]:
    """The quick set on a single-page project, for the delivery gate; [] when there is nothing to run it on."""
    index = ws_dir / "index.html"
    results = run(index.resolve().as_uri(), QUICK) if index.is_file() else None
    return failures(results) if results else []
