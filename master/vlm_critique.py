"""Screenshot critique: a real browser renders the page (network blocked) and the local vision model reviews it.

Slow (the vision model has to take over the GPU), so it runs only for deep-mode requests.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, ValidationError

from gateway import local_gpu
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)


class Defect(BaseModel):
    element: str
    problem: str
    css_fix: str = ""


class Critique(BaseModel):
    defects: list[Defect] = Field(default_factory=list, max_length=4)


def screenshot(page_file: Path, width: int = 1280, height: int = 800) -> bytes:
    """PNG of the page; every request other than local files is aborted."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:")) else route.abort())
            page.goto(page_file.resolve().as_uri(), timeout=15000)
            page.wait_for_timeout(400)
            return page.screenshot()
        finally:
            browser.close()


async def review(ws_dir: Path, request: str) -> list[Defect] | None:
    """Visible defects, or None when the page cannot be rendered or the model is unavailable."""
    page = ws_dir / "index.html"
    if not page.is_file():
        return None
    try:
        png = await asyncio.to_thread(screenshot, page)
        ask = f"{load_prompt('agent_visual_critic.md')}\n\nKULLANICININ İSTEĞİ:\n{request[:800]}"
        return Critique.model_validate(json.loads(await local_gpu.look(ask, png, Critique.model_json_schema()))).defects
    except (ImportError, OSError, RuntimeError, httpx.HTTPError, ValueError, ValidationError) as exc:
        _log.warning("Görsel eleştiri yapılamadı: %s", exc)
        return None


async def report(ws_dir: Path, request: str) -> str:
    found = await review(ws_dir, request)
    return "Görsel model notları: " + "; ".join(f"{d.element}: {d.problem}" for d in found) if found else ""
