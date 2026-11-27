"""A delivery is called finished only when four proofs exist: static, tests, running system, signed record.

The state machine has no way to reach COMPLETED while a proof is missing or failed; the user is told which one. The
record (.ai-os/proof.json, signed) holds what was checked, what was found and the hashes of the delivered files.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

import atomic_io
import code_audit
import flow_analysis
import js_mutation
import live_journey
import live_server
import mutation
import plan_matrix
import preview_server
import provenance
import security_scan
import shortcut_audit
import state_property
import workspace_builder as wb
import workspace_docker
import workspace_requirements
import workspace_smoke

_log = logging.getLogger(__name__)
STAGES = ("A", "B", "C", "D")
NAMES = {"A": "statik denetim", "B": "kod testleri", "C": "çalışan sistem", "D": "imzalı kayıt"}
PASSED, FAILED, MISSING = "geçti", "kaldı", "yapılamadı"
KILL_RATE = 0.8
RECORD = ".ai-os/proof.json"


@dataclass
class Delivery:
    """Proofs arrive in order; COMPLETED exists only behind four passed ones."""

    proofs: dict[str, tuple[str, str]] = field(default_factory=dict)

    def prove(self, stage: str, status: str, detail: str) -> None:
        if stage != STAGES[len(self.proofs)]:
            raise ValueError(f"sıra dışı kanıt: {stage}")
        self.proofs[stage] = (status, detail[:600])

    @property
    def state(self) -> str:
        if len(self.proofs) < len(STAGES):
            return "BUILDING"
        return "COMPLETED" if all(status == PASSED for status, _d in self.proofs.values()) else "INCOMPLETE_WITH_DIAGNOSTICS"

    def summary(self) -> str:
        marks = ", ".join(f"{s} {NAMES[s]}: {self.proofs[s][0]}" for s in STAGES if s in self.proofs)
        if self.state == "COMPLETED":
            return f"Teslim durumu: TAMAMLANDI — dört kanıt da geçti ({marks})."
        problems = " | ".join(f"{s}: {self.proofs[s][1]}" for s in STAGES if s in self.proofs and self.proofs[s][0] != PASSED)
        return f"Teslim durumu: EKSİK, tamamlandı sayılmaz ({marks}). {problems}"[:900]


def static_proof(ws_dir: Path) -> tuple[str, str]:
    problems = list(wb.verify_workspace_files(ws_dir))
    problems += shortcut_audit.findings(ws_dir)
    problems += code_audit.diagnostics(ws_dir)  # what a language server would underline
    problems += flow_analysis.tainted_flows(ws_dir)  # request data reaching a command, SQL or a path through other functions
    problems += [f"{f['file']}:{f['line']} {f['rule']}" for f in sorted(security_scan.scan(ws_dir), key=lambda f: not f["secret"])]
    for relative in wb.list_relative_files(ws_dir):
        if relative.endswith((".html", ".js", ".py", ".css")) and '<span class="hl-' in (ws_dir / relative).read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{relative}: renklendirme etiketleri koda sızmış")
    return (PASSED, "sözdizimi, derleyici tanıları, kaçamak, güvenlik ve gizli anahtar denetimi temiz") if not problems else (FAILED, "; ".join(problems[:5]))


def _has_tests(ws_dir: Path) -> bool:
    return any(Path(f).name.startswith("test_") and f.endswith(".py") for f in wb.list_relative_files(ws_dir))


def _javascript_test_proof(ws_dir: Path) -> tuple[str, str]:
    try:
        if failure := js_mutation.run_tests(ws_dir):
            return FAILED, f"JavaScript testleri geçmedi: {failure.strip().splitlines()[-1]}"
        tried, survived = js_mutation.run(ws_dir, limit=10)
    except OSError as exc:
        return MISSING, f"JavaScript testleri çalıştırılamadı: {exc}"
    if tried and (rate := 1 - len(survived) / tried) < KILL_RATE:
        return FAILED, f"testler geçti ama bilerek bozulan kodun yalnız %{rate * 100:.0f} kadarını yakaladı (en az %{KILL_RATE * 100:.0f})"
    return PASSED, f"JavaScript testleri geçti; bilerek yapılan {tried} bozmanın {tried - len(survived)} tanesi yakalandı"


def test_proof(ws_dir: Path) -> tuple[str, str]:
    if not _has_tests(ws_dir) and js_mutation.has_tests(ws_dir):
        return _javascript_test_proof(ws_dir)
    if not _has_tests(ws_dir):
        return MISSING, "projede çalıştırılabilir test yok"
    if not workspace_docker.available():
        return MISSING, "kod kutusu (Docker) kapalı"
    packages = workspace_requirements.declared_packages(ws_dir)
    if failure := workspace_docker.run_tests(ws_dir, packages):
        return FAILED, f"testler geçmedi: {failure}"
    tried, survived = mutation.run(ws_dir, lambda stage: not workspace_docker.run_tests(stage, packages), limit=10)
    if tried and (rate := 1 - len(survived) / tried) < KILL_RATE:
        return FAILED, f"testler geçti ama bilerek bozulan kodun yalnız %{rate * 100:.0f} kadarını yakaladı (en az %{KILL_RATE * 100:.0f})"
    return PASSED, f"testler geçti; bilerek yapılan {tried} bozmanın {tried - len(survived)} tanesi yakalandı"


def page_problems(url: str) -> tuple[str, str]:
    """Open the real page in a real browser: errors, failed requests and buttons nothing listens to."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return MISSING, "tarayıcı kurulu değil"
    problems: list[str] = []
    try:
        with sync_playwright() as driver:
            try:
                browser = driver.chromium.launch()
            except PlaywrightError as exc:  # no browser to test with says nothing about the page
                return MISSING, f"tarayıcı açılamadı: {str(exc).splitlines()[0][:120]}"
            page = browser.new_page()
            page.on("pageerror", lambda error: problems.append(f"sayfa hatası: {str(error)[:100]}"))
            page.on("console", lambda m: problems.append(f"konsol hatası: {m.text[:100]}") if m.type == "error" and "favicon" not in m.text else None)
            page.on("response", lambda r: problems.append(f"{r.status} {r.url.rsplit('/', 1)[-1]}") if r.status >= 400 and "favicon" not in r.url else None)
            page.goto(url, timeout=20000)
            page.wait_for_timeout(1200)
            problems += [f"hiçbir şeye bağlı olmayan düğme: {label}" for label in shortcut_audit.unwired(page)]
            text = page.inner_text("body").strip()
            browser.close()
    except PlaywrightError as exc:
        return FAILED, f"sayfa açılamadı: {str(exc).splitlines()[0][:150]}"
    if not text:
        problems.append("sayfa boş görünüyor")
    return (PASSED, "gerçek tarayıcıda hatasız açıldı, bağlanmamış düğme yok") if not problems else (FAILED, "; ".join(dict.fromkeys(problems))[:500])


_READY_LIMIT_S = 30
EVIDENCE = ".ai-os/evidence.json"


def _server_checks(ws_dir: Path, server: live_server.LiveServer) -> tuple[str, str]:
    """Health time, the user's journey when there is a page, then API contract and state checks."""
    if server.ready_s > _READY_LIMIT_S:
        return FAILED, f"sunucu {server.ready_s} sn'de hazır oldu (sınır {_READY_LIMIT_S} sn)"
    evidence: dict[str, Any] = {"ready_s": server.ready_s}
    has_page = "text/html" in httpx.get(server.url + "/", timeout=10).headers.get("content-type", "")
    if not has_page:
        server.restart()  # an API without a page: it must at least come back after a restart
        passed, detail = True, "sunucu gerçekten açıldı, yanıt verdi ve yeniden başlatılınca geri geldi"
    else:
        journey = live_journey.run(server.url, ws_dir / ".ai-os" / "filmstrip", server.restart, server.rows)
        passed, detail = journey.passed, journey.summary()
        evidence.update(steps=journey.steps, errors=journey.errors, requests=journey.requests, rows=journey.rows, screenshots=journey.shots)
    described = httpx.get(server.url + "/openapi.json", timeout=10)
    if described.status_code == 200 and (absent := plan_matrix.missing_endpoints(ws_dir, described.json())):
        return FAILED, f"istenen uç noktalar çalışan sunucuda yok: {', '.join(absent[:5])}"
    api = state_property.check(server.url, server.rows, (lambda: live_journey.page_text(server.url + "/")) if has_page else None)
    evidence["api"] = {"checked": api.checked, "problems": api.problems}
    atomic_io.write_text(ws_dir / EVIDENCE, json.dumps(evidence, ensure_ascii=False, indent=1))
    if api.problems:
        return FAILED, "; ".join(([] if passed else [detail]) + api.problems[:3])
    return (PASSED if passed else FAILED), detail + (f" | API denetimi: {len(api.checked)} kontrol geçti" if api.checked else "")


def server_proof(ws_dir: Path) -> tuple[str, str] | None:
    """Boot the project's own web server and use it; None when it is not a FastAPI or Flask project."""
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is None or not workspace_docker.available() or not any(w in entry.read_text(encoding="utf-8", errors="replace") for w in ("FastAPI", "Flask")):
        return None
    try:
        with live_server.serve(ws_dir) as server:
            return _server_checks(ws_dir, server)
    except (OSError, ValueError, KeyError, httpx.HTTPError) as exc:
        return FAILED, f"canlı sunucu denemesi başarısız: {exc}"[:500]


def live_proof(ws_dir: Path, warnings: list[str]) -> tuple[str, str]:
    failure = next((w for w in warnings if "Otomatik çalıştırma testi hata" in w), "")
    if failure:
        return FAILED, failure
    if (ws_dir / "index.html").is_file():
        preview_server.start_preview_server_background()
        url = f"{preview_server.get_preview_origin()}/preview/{ws_dir.name}/index.html"
        for _attempt in range(20):
            try:
                httpx.get(url, timeout=2)
                break
            except httpx.HTTPError:
                time.sleep(0.3)
        return page_problems(url)
    if (served := server_proof(ws_dir)) is not None:
        return served
    if any(f.endswith(".py") for f in wb.list_relative_files(ws_dir)):
        if any("çalıştırılamadı" in w for w in warnings) or not workspace_docker.available():
            return MISSING, "proje çalıştırılarak denenemedi"
        return PASSED, "proje yalıtılmış kutuda başlatıldı ve yanıt verdi"
    return MISSING, "çalıştırılacak bir giriş noktası yok"


def _evidence_hashes(ws_dir: Path) -> dict[str, str]:
    """Hashes of what the proof rests on: the evidence file and every screenshot."""
    found = [ws_dir / EVIDENCE, *sorted((ws_dir / ".ai-os" / "filmstrip").glob("*.png"))]
    return {p.relative_to(ws_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in found if p.is_file()}


def _record(ws_dir: Path, delivery: Delivery) -> tuple[str, str]:
    files = {f: hashlib.sha256((ws_dir / f).read_bytes()).hexdigest() for f in wb.list_relative_files(ws_dir)}
    body = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "proofs": {s: list(delivery.proofs[s]) for s in ("A", "B", "C")}, "files": files,
            "generation": provenance.generation(wb.load_workspace_meta(ws_dir)), "evidence": _evidence_hashes(ws_dir)}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
    try:
        atomic_io.write_text(ws_dir / RECORD, json.dumps({**body, **provenance.sign(payload.encode())}, ensure_ascii=False, indent=1))
    except OSError as exc:
        return FAILED, f"kayıt yazılamadı: {exc}"
    return PASSED, f"{len(files)} dosyanın özeti imzalandı"


def evaluate(ws_dir: Path, warnings: list[str]) -> Delivery:
    delivery = Delivery()
    for stage, proof in (("A", lambda: static_proof(ws_dir)), ("B", lambda: test_proof(ws_dir)), ("C", lambda: live_proof(ws_dir, warnings))):
        try:
            delivery.prove(stage, *proof())
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            _log.warning("kanıt %s çalışamadı: %r", stage, exc)
            delivery.prove(stage, MISSING, f"denetim çalışamadı: {exc}")
    delivery.prove("D", *_record(ws_dir, delivery))
    return delivery


async def apply(ws_dir: Path, done: dict[str, Any]) -> dict[str, Any]:
    """The finished event with the delivery state first among its warnings."""
    warnings = [str(w) for w in done.get("warnings") or []]
    delivery = await asyncio.to_thread(evaluate, ws_dir, warnings)
    return {**done, "warnings": [delivery.summary(), *warnings], "delivery": delivery.state}
