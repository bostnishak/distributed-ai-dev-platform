"""An agent that operates one website in a throw-away browser profile.

The page is read as a numbered list of controls, each action is checked for an effect, network access is limited to the
site the user named, page text is untrusted data, and a click that cannot be undone waits for the user's approval of
that exact button.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Literal
from urllib.parse import urlparse

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

import gateway
import injection
import policy
from prompt_loader import load_prompt
from rag.web import is_safe_public_url

_log = logging.getLogger(__name__)
_TRIGGER_RE = re.compile(r"^\s*@(?:tarayıcı|tarayici|browser)\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_APPROVE_RE = re.compile(r"\bonay\s*:\s*[\"“']?([^\"”'\n]{1,60}?)[\"”']?\s*(?:$|\n)", re.IGNORECASE)
_RISKY_RE = re.compile(r"\b(?:gönder|sil|kaldır|öde|satın\s*al|sipariş|onayla|yayınla|paylaş|iptal|send|submit|delete|remove|pay|buy|order|checkout|confirm|publish|post|share)", re.IGNORECASE)
_STEPS = 12

Chat = Callable[[str, str, dict], Awaitable[str]]


class Action(BaseModel):
    action: Literal["write", "click", "select", "done", "fail"]
    id: int = 0
    text: str = ""


async def _ask(system: str, user: str, schema: dict) -> str:
    res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b", profile="extract",
                                            format_schema=schema, num_predict=500, num_ctx=8192, timeout_s=240.0, feature="browser_agent", max_retries=0)
    return res.content


def risky(element: dict) -> bool:
    """Clicks that send, delete, buy or otherwise cannot be taken back."""
    clickable = element.get("tag") != "input" or element.get("type") in ("button", "submit")
    return bool(element.get("submits") or (clickable and _RISKY_RE.search(element.get("label", ""))))


def _writable(element: dict) -> bool:
    return element["tag"] == "textarea" or (element["tag"] == "input" and element["type"] not in ("button", "submit", "checkbox", "radio", "image", "file", "reset"))


def _listing(elements: list[dict]) -> str:
    return "\n".join(f"[{e['id']}] {'YAZI ALANI ' if _writable(e) else ''}{e['tag']}{'/' + e['type'] if e['type'] else ''} \"{e['label']}\"" + (f" = {e['value']!r}" if e["value"] else "") for e in elements)


async def _visible_text(page) -> str:
    """Text a person could read on the page; hidden text never reaches the model."""
    return await page.evaluate(load_prompt("page_visible_text.js.txt"))


async def _state(page) -> tuple[str, list[dict], str]:
    elements = await page.evaluate(load_prompt("page_elements.js.txt"))
    return page.url, elements, (await _visible_text(page))[:3000]


async def _perform(page, action: Action) -> None:
    target = page.locator(f'[data-agent-id="{action.id}"]')
    if action.action == "write":
        await target.fill(action.text, timeout=4000)
    elif action.action == "select":
        await target.select_option(label=action.text, timeout=4000)
    else:
        await target.click(timeout=4000)
    await page.wait_for_timeout(600)


class _Stop(Exception):
    """The run ends here with this message."""


def _check(action: Action, element: dict, approved: tuple[str, ...]) -> None:
    """Refuse secrets and unapproved irreversible clicks before anything touches the page."""
    name = element["label"] or element["tag"]
    if action.action == "write" and (element["type"] == "password" or policy.has_secret(action.text)):
        raise _Stop(f"'{name}' alanına parola ya da gizli değer yazmam; bunu siz girin.")
    if action.action == "click" and risky(element):
        decision = policy.check("browser_submit", integrity=policy.UNTRUSTED, approved=name.casefold() in {a.casefold() for a in approved})
        if not decision.allowed:
            raise _Stop(f'Durdum: "{name}" geri alınamayabilir. Onaylıyorsanız isteğinizi şu satırla yeniden gönderin:\nonay: {name}')


def _page_data(body: str) -> str:
    """Page text fenced as data. Lines that try to command a model are removed before the model sees them."""
    lines = body.replace("<<<", "").splitlines()
    kept = [line for line in lines if not injection.detect_injection(line)["flagged"]]
    note = ["(Sayfadan talimat içeren satırlar çıkarıldı.)"] if len(kept) < len(lines) else []
    return "\n".join([*note, "<<<VERİ BAŞI>>>", *kept, "<<<VERİ SONU>>>"])


async def _step(page, task: str, history: list[str], approved: tuple[str, ...], chat: Chat) -> str:
    """Choose and perform one action; returns its description ('' when nothing was done)."""
    where, elements, body = await _state(page)
    ask = (f"GÖREV: {task}\n\nADRES: {where}\nYAPILANLAR: {json.dumps(history[-6:], ensure_ascii=False)}\n\n"
           f"ÖĞELER:\n{_listing(elements)}\n\nSAYFA METNİ:\n{_page_data(body)}")
    try:
        action = Action.model_validate_json(await chat(load_prompt("agent_browser.md"), ask, Action.model_json_schema()))
    except (ValidationError, ValueError) as exc:
        history.append(f"geçersiz yanıt: {str(exc)[:80]}")
        return ""
    if action.action in ("done", "fail"):
        raise _Stop(("Tamamlandı: " if action.action == "done" else "Yapılamadı: ") + action.text)
    element = next((e for e in elements if e["id"] == action.id), None)
    if element is None or action.action not in ("click", "write", "select"):
        history.append(f"olmayan öğe ya da eylem: {action.action} {action.id}")
        return ""
    _check(action, element, approved)
    name = element["label"] or element["tag"]
    before = (where, body, json.dumps(elements, sort_keys=True))
    await _perform(page, action)
    after = await _state(page)
    changed = before != (after[0], after[2], json.dumps(after[1], sort_keys=True))
    typed = f" <- {action.text!r}" if action.action != "click" and action.text else ""
    history.append(f"{action.action} '{name}'{typed}" + ("" if changed else " (sayfada değişiklik olmadı)"))
    return history[-1]


async def _fence(context, host: str, blocked: set[str]) -> None:
    """Only the named site may receive requests; other hosts may only serve static assets."""

    async def guard(route):
        target = urlparse(route.request.url)
        asset = route.request.method == "GET" and route.request.resource_type in ("stylesheet", "script", "font", "image")
        if target.scheme in ("data", "blob") or target.netloc == host or asset:
            await route.continue_()
        else:
            blocked.add(target.netloc)
            await route.abort()

    await context.route("**/*", guard)


async def _drive(browser, task: str, url: str, approved: tuple[str, ...], chat: Chat) -> AsyncIterator[tuple[str, str]]:
    from playwright.async_api import Error as PlaywrightError

    blocked: set[str] = set()
    history: list[str] = []
    context = await browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=False)
    await _fence(context, urlparse(url).netloc, blocked)
    page = await context.new_page()
    page.on("dialog", lambda dialog: dialog.dismiss())
    await page.goto(url, timeout=20000)
    outcome = f"{_STEPS} adımda tamamlayamadım."
    for _round in range(_STEPS):
        try:
            if done := await _step(page, task, history, approved, chat):
                yield "step", done
        except _Stop as stop:
            outcome = str(stop)
            break
        except PlaywrightError as exc:
            history.append(f"eylem başarısız: {str(exc).splitlines()[0][:80]}")
    final = (await _visible_text(page))[:500].strip()
    note = f"\n\nEngellenen dış istekler: {', '.join(sorted(blocked))}" if blocked else ""
    yield "result", f"{outcome}\n\nSon adres: {page.url}\nSayfada görünen: {final}{note}"


async def run(task: str, url: str, approved: tuple[str, ...] = (), chat: Chat = _ask, allow_local: bool = False) -> AsyncIterator[tuple[str, str]]:
    """("step", description) per action, then ("result", text)."""
    if not allow_local and not is_safe_public_url(url)[0]:
        yield "result", "Bu adrese gidemem: yalnızca herkese açık web siteleri."
        return
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright

    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        try:
            async for event in _drive(browser, task, url, approved, chat):
                yield event
        except PlaywrightError as exc:
            yield "result", f"Tarayıcı hatası: {str(exc).splitlines()[0]}"
        finally:
            await browser.close()


def parse(prompt: str) -> tuple[str, str, tuple[str, ...]] | None:
    """(task, url, approved button labels) for "@tarayıcı <url> <task>" messages."""
    if not _TRIGGER_RE.match(prompt) or not (found := _URL_RE.search(prompt)):
        return None
    url = found.group(0).rstrip(".,)")
    approved = tuple(m.strip() for m in _APPROVE_RE.findall(prompt))
    task = _APPROVE_RE.sub("", _TRIGGER_RE.sub("", prompt).replace(found.group(0), " ")).strip()
    return (task, url, approved) if task else None


def fastpath(prompt: str, has_file: bool) -> StreamingResponse | None:
    parsed = None if has_file else parse(prompt)
    if parsed is None:
        return None
    task, url, approved = parsed

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def gen():
        yield sse({"type": "status", "message": f"Tarayıcı açılıyor: {url}"})
        try:
            async for kind, text in run(task, url, approved):
                yield sse({"type": "token", "content": f"- {text}\n" if kind == "step" else f"\n{text}\n"})
        except (ImportError, OSError, RuntimeError, NotImplementedError) as exc:
            _log.warning("browser agent failed: %r", exc)
            yield sse({"type": "error", "content": f"Tarayıcı ajanı çalışamadı: {exc!r}"})
        yield sse({"type": "done", "model": "browser-agent", "task_type": "genel"})

    return StreamingResponse(gen(), media_type="text/event-stream")
