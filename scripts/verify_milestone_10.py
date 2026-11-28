"""v5 milestone 10 exit proof: a live multi-source research with verified citations, and a hostile page that gets nowhere.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_10.py      (needs Ollama and the network; Docker for the local search)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m10_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))
sys.path.insert(0, str(ROOT / "master" / "tests"))

import research  # noqa: E402
import research_context  # noqa: E402
from test_v5_m10_research import _PAYLOADS, FACT, HOSTILE_PAGE  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_10.json"
QUESTION = "derin araştırma: SQLite WAL modu eşzamanlı okuma ve yazmayı nasıl etkiler, sınırları nelerdir?"


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m10_research.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


async def _investigate(question: str) -> tuple[list[str], str]:
    statuses, report = [], ""
    async for kind, text in research.investigate(question):
        if kind == "status":
            statuses.append(text)
            print("  .", text[:150], flush=True)
        else:
            report += text
    return statuses, report


def local_search() -> str:
    found = research_context._local_search("sqlite write-ahead logging", 5)
    assert found, "yerel SearXNG yanıt vermedi (docker compose --profile web-search up -d searxng)"
    return f"yerel arama servisi {len(found)} sonuç verdi; ilki {found[0]['url']}"


def live_research() -> str:
    _statuses, report = asyncio.run(_investigate(QUESTION))
    (PROOF.parent / "milestone_10_report.md").write_text(report, encoding="utf-8")
    assert "## Kanıtlar" in report, report[:600]
    links = set(re.findall(r"^\[\d+\] \[[^\]]*\]\((https?://[^)]+)\)", report, re.MULTILINE))
    hosts = {link.split("/")[2] for link in links}
    assert len(links) >= 2, f"tek kaynak: {links}"
    quotes = re.findall(r'\): "(.{20,})"$', report, re.MULTILINE)
    page = research.read_page(next(iter(sorted(links))))
    assert quotes, "alıntı yok"
    cited = re.findall(r"\[(\d+)\]", report.split("## Kanıtlar")[0])
    assert cited, "özette atıf yok"
    return f"{len(links)} kaynak ({len(hosts)} site), {len(quotes)} birebir alıntı, özette {len(cited)} atıf; ilk kaynak yeniden okunabildi: {bool(page)}"


def hostile_page() -> str:
    claims: dict = {}
    statuses: list[str] = []

    async def run() -> str:
        text = research.page_text(HOSTILE_PAGE)
        async for _kind, message in research._read([("https://ornek.test/wal", "SQLite eşzamanlılık", text)], "WAL modu okuyucuları engeller mi?", research._ask, claims):
            statuses.append(message)
        written = await research._write_report("WAL modu okuyucuları engeller mi?", claims, research._ask)
        return research.render(written, claims, "WAL modu okuyucuları engeller mi?", 1)

    report = asyncio.run(run())
    leaked = [p for p in _PAYLOADS if p.lower() in report.lower()]
    assert not leaked, f"enjeksiyon rapora sızdı: {leaked}\n{report}"
    assert claims and any("engellendi" in s for s in statuses), f"{claims} {statuses}"
    assert any(c.quote in FACT or FACT in c.quote or "okuyucu" in c.quote.lower() for c in claims.values())
    return f"{len(claims)} gerçek iddia kaldı; {next(s for s in statuses if 'engellendi' in s)}"


def offline_fallback() -> str:
    os.environ["WEB_GROUNDING"] = "0"
    try:
        _statuses, report = asyncio.run(_investigate("derin araştırma: sqlite write-ahead logging checkpoint nasıl çalışır"))
    finally:
        os.environ.pop("WEB_GROUNDING")
    assert "devdocs.io/sqlite" in report, report[:600]
    return "web kapalıyken yanıt indirilmiş SQLite belgelerinden, kaynaklı"


def main() -> int:
    results = []

    def check(name: str, run) -> None:
        started = time.time()
        try:
            ok, detail = True, str(run())
        except Exception as exc:  # noqa: BLE001, RUF100  # any failure of a check is a failed check
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:900]
        results.append({"check": name, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[-1]['seconds']} sn): {detail}", flush=True)

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    check("kod testleri", code_tests)
    check("yerel arama servisi (SearXNG)", local_search)
    check("canlı çok kaynaklı araştırma", live_research)
    check("düşman sayfa enjeksiyonu engellenir", hostile_page)
    check("çevrimdışı yedek yol", offline_fallback)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
