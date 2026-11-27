"""Does a page keep growing while it is used? Repeat its own controls and count what stays behind.

After a warm-up, the same buttons are clicked many times. DOM nodes, event listeners and the JavaScript heap are read
from the browser (after forcing garbage collection) before and after; growth with every repetition is a leak. The
same numbers also serve as a before/after measurement of an optimisation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_CYCLES = 50
_WARMUP = 5
_NODES_PER_CYCLE = 2.0
_LISTENERS_PER_CYCLE = 0.5
_HEAP_KB_PER_CYCLE = 60.0
_CONTROLS = "button:visible:not([type=submit]), [role=tab]:visible, summary:visible, input[type=checkbox]:visible"


@dataclass(frozen=True)
class Reading:
    nodes: int
    listeners: int
    heap_kb: int


@dataclass(frozen=True)
class Result:
    before: Reading
    after: Reading
    cycles: int
    load_ms: int

    def leaks(self) -> list[str]:
        found = []
        for label, grown, limit in (("DOM öğesi", self.after.nodes - self.before.nodes, _NODES_PER_CYCLE),
                                    ("olay dinleyicisi", self.after.listeners - self.before.listeners, _LISTENERS_PER_CYCLE),
                                    ("KB JavaScript belleği", self.after.heap_kb - self.before.heap_kb, _HEAP_KB_PER_CYCLE)):
            if grown / self.cycles > limit:
                found.append(f"{self.cycles} tekrarda {grown} {label} birikti (tekrar başına {grown / self.cycles:.1f})")
        return found

    def as_dict(self) -> dict[str, Any]:
        return {"before": asdict(self.before), "after": asdict(self.after), "cycles": self.cycles, "load_ms": self.load_ms}


def _read(session: Any) -> Reading:
    session.send("HeapProfiler.collectGarbage")
    metrics = {m["name"]: m["value"] for m in session.send("Performance.getMetrics")["metrics"]}
    return Reading(int(metrics.get("Nodes", 0)), int(metrics.get("JSEventListeners", 0)), int(metrics.get("JSHeapUsedSize", 0) // 1024))


def _use(page: Any, times: int) -> None:
    controls = page.locator(_CONTROLS)
    count = min(controls.count(), 6)
    for turn in range(times):
        if count:
            control = controls.nth(turn % count)
            if control.is_visible() and control.is_enabled():
                control.click(timeout=1000, no_wait_after=True)
        page.wait_for_timeout(15)


def measure(url: str, cycles: int = _CYCLES) -> Result:
    """ValueError when no browser is available or the page cannot be driven."""
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
                page.on("dialog", lambda dialog: dialog.dismiss())
                session = page.context.new_cdp_session(page)
                session.send("Performance.enable")
                page.goto(url, timeout=30000)
                load_ms = int(page.evaluate("performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd"))
                _use(page, _WARMUP)
                before = _read(session)
                _use(page, cycles)
                return Result(before, _read(session), cycles, load_ms)
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise ValueError(f"sayfa sınanamadı: {str(exc).splitlines()[0][:150]}") from exc


def compare(before: Result, after: Result) -> str:
    """What an optimisation changed, in measured numbers."""
    rows = (("açılış (ms)", before.load_ms, after.load_ms), ("DOM öğesi", before.after.nodes, after.after.nodes),
            ("dinleyici", before.after.listeners, after.after.listeners), ("bellek (KB)", before.after.heap_kb, after.after.heap_kb))
    lines = [f"| {name} | {old} | {new} | {new - old:+d} |" for name, old, new in rows]
    return "\n".join(["| Ölçü | Önce | Sonra | Fark |", "|---|---|---|---|", *lines])


def _preview_url(ws_dir: Path) -> str:
    """The project's page on the isolated preview origin; "" when it does not answer."""
    import time

    import httpx

    import preview_server

    preview_server.start_preview_server_background()
    url = f"{preview_server.get_preview_origin()}/preview/{ws_dir.name}/index.html"
    for _attempt in range(10):
        try:
            return url if httpx.get(url, timeout=2).status_code == 200 else ""
        except httpx.HTTPError:
            time.sleep(0.3)
    return ""


def report(ws_dir: Path) -> str:
    """One chat line when the page leaks; the readings are kept so the next version can be compared with this one."""
    import json

    import atomic_io

    url = _preview_url(ws_dir) if (ws_dir / "index.html").is_file() else ""
    if not url:
        return ""
    try:
        result = measure(url)
    except ValueError:
        return ""
    record = ws_dir / ".ai-os" / "performance.json"
    try:
        previous = json.loads(record.read_text(encoding="utf-8"))
        old = Result(Reading(**previous["before"]), Reading(**previous["after"]), previous["cycles"], previous["load_ms"])
    except (OSError, ValueError, KeyError, TypeError):
        old = None
    record.parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(record, json.dumps(result.as_dict()))
    if old is not None:
        atomic_io.write_text(ws_dir / ".ai-os" / "performance.md", compare(old, result) + "\n")
    leaks = result.leaks()
    return "Sızıntı denetimi: " + "; ".join(leaks) if leaks else ""
