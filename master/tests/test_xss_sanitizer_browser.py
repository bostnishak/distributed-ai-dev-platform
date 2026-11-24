"""XSS-01..39: run the real sanitizer in a real (headless) browser against the attack corpus."""

import functools
import http.server
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

ROOT = Path(__file__).resolve().parents[2]
CHROME = next(
    (
        c
        for c in (
            shutil.which("chrome"),
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("msedge"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        )
        if c and Path(c).exists()
    ),
    None,
)


@pytest.mark.skipif(CHROME is None, reason="no Chromium-based browser installed")
def test_xss_sanitizer_neutralises_every_payload_and_keeps_safe_markup():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None  # type: ignore[method-assign]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        out = subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--virtual-time-budget=8000",
                "--dump-dom",
                f"http://127.0.0.1:{port}/frontend/tests/xss_harness.html",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        ).stdout
    finally:
        server.shutdown()
    match = re.search(r"FAILS=(\d+)", out)
    assert match, out[-500:]
    assert match.group(1) == "0", out
    assert out.count("ok     ") >= 25
    assert out.count("keep   ") >= 4
