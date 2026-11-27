"""Layout audit in a real headless browser: horizontal overflow, unreadable contrast, overlapping controls, broken images.

jsdom has no layout, so this uses the installed Edge/Chrome. The page is generated code, so it runs from a throw-away copy
with a no-network policy, a throw-away profile and the browser's own sandbox.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from process_utils import run_process
from prompt_loader import load_prompt

_BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)
VIEWPORTS = {"dar": "500,900", "geniş": "1440,900"}
_POLICY = '<meta http-equiv="Content-Security-Policy" content="default-src \'self\' \'unsafe-inline\' data: blob: file:; connect-src \'none\'; form-action \'none\'">'
_RESULT_RE = re.compile(r'<pre id="__audit">(.*?)</pre>', re.DOTALL)


def browser_path() -> str:
    found = os.environ.get("AUDIT_BROWSER") or next((p for p in _BROWSERS if Path(p).is_file()), "")
    return found or shutil.which("chromium") or shutil.which("google-chrome") or ""


def _prepare(ws_dir: Path, stage: Path) -> Path:
    shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", "node_modules", "dist"))
    page = stage / "index.html"
    text = page.read_text(encoding="utf-8", errors="replace")
    head = re.search(r"<head\b[^>]*>", text, re.IGNORECASE)
    text = text[: head.end()] + _POLICY + text[head.end() :] if head else _POLICY + text
    page.write_text(text + f"<script>{load_prompt('visual_audit.js.txt')}</script>", encoding="utf-8")
    return page


def _run(browser: str, page: Path, profile: Path, size: str) -> list[str] | None:
    args = [browser, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}", f"--window-size={size}",
            "--host-resolver-rules=MAP * ~NOTFOUND", "--virtual-time-budget=3000", "--dump-dom", page.as_uri()]
    proc = run_process(args, timeout_s=40, max_output_chars=400_000)
    match = _RESULT_RE.search(proc.stdout)
    return json.loads(html.unescape(match.group(1))) if match else None


def audit(ws_dir: Path) -> list[str] | None:
    """Problems per viewport; None when no browser is available or the page could not be measured."""
    browser = browser_path()
    if not browser or not (ws_dir / "index.html").is_file():
        return None
    found: list[str] = []
    measured = False
    try:
        with tempfile.TemporaryDirectory(prefix="cm6453_vis_", ignore_cleanup_errors=True) as tmp:
            page = _prepare(ws_dir, Path(tmp) / "ws")
            for label, size in VIEWPORTS.items():
                result = _run(browser, page, Path(tmp) / f"profile-{size.split(',')[0]}", size)
                measured = measured or result is not None
                found += [f"{label} ekran: {item}" for item in result or []]
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return found if measured else None


def report(ws_dir: Path, limit: int = 4) -> str:
    """One warning line for the chat, or an empty string."""
    found = audit(ws_dir)
    return f"Görsel denetim {len(found)} sorun: " + "; ".join(found[:limit]) if found else ""
