"""Web pages are untrusted data: instructions aimed at a model are cut out before any model sees them.

Two deterministic steps. Hidden content (comments, display:none, zero-size and aria-hidden elements) is removed from
the HTML, because a reader never sees it. Then every visible paragraph that tries to command or address a model is
dropped, sentence by sentence. What is dropped cannot be quoted, so it cannot pass the citation gate either.
A page that needs JavaScript is rendered in the local browser, with every request checked against private addresses.
"""

from __future__ import annotations

import logging
import re

import injection
from rag.web import is_safe_public_url

_HIDDEN_STYLE_RE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d])|opacity\s*:\s*0(?![.\d])|(?:left|top|text-indent)\s*:\s*-\d{3,}", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_RENDER_MS = 15_000
_log = logging.getLogger(__name__)


def visible_html(raw: str) -> str:
    """The HTML without anything a person reading the page would not see."""
    import lxml.html
    from lxml import etree

    try:
        tree = lxml.html.fromstring(raw)
    except (etree.ParserError, ValueError):
        return raw
    for node in list(tree.iter()):
        parent = node.getparent()
        if parent is None:
            continue
        hidden = node.tag is etree.Comment or (
            isinstance(node.tag, str)
            and (node.get("hidden") is not None or node.get("aria-hidden") == "true" or node.tag in ("template", "noscript") or _HIDDEN_STYLE_RE.search(node.get("style") or ""))
        )
        if hidden:
            node.drop_tree() if isinstance(node.tag, str) else parent.remove(node)
    return lxml.html.tostring(tree, encoding="unicode")


def _hostile(text: str) -> bool:
    """Flagged as a whole, or it speaks to a model: a web page has no reason to do that. A lone "you must run" in a
    manual is not enough."""
    found = injection.detect_injection(text)
    return found["flagged"] or "addresses-the-model" in found["signals"]


def sanitize(text: str) -> tuple[str, list[str]]:
    """(the page text without instructions aimed at a model, the pieces removed)."""
    kept: list[str] = []
    removed: list[str] = []
    for paragraph in text.split("\n"):
        if not _hostile(paragraph):
            kept.append(paragraph)
            continue
        sentences = _SENTENCE_RE.split(paragraph)
        clean = [s for s in sentences if not _hostile(s)]
        if _hostile(" ".join(clean)):  # the attempt is spread over sentences: the whole paragraph goes
            clean = []
        removed += [s for s in sentences if s not in clean]
        if clean:
            kept.append(" ".join(clean))
    return "\n".join(kept), removed


def _guard_request(route) -> None:
    url = route.request.url
    if url.startswith(("data:", "blob:")) or is_safe_public_url(url)[0]:
        route.continue_()
    else:
        route.abort()


def rendered_html(url: str) -> str:
    """The page after its scripts ran; "" when it cannot be rendered. Private and local addresses are never requested."""
    if not is_safe_public_url(url)[0]:
        return ""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                context = browser.new_context(accept_downloads=False, service_workers="block")
                context.route("**/*", _guard_request)
                page = context.new_page()
                page.goto(url, timeout=_RENDER_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                final = page.url
                return page.content() if is_safe_public_url(final)[0] else ""
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001, RUF100  # a page that cannot be rendered is simply not read
        _log.warning("sayfa tarayıcıda açılamadı (%s): %s", url[:80], type(exc).__name__)
        return ""
