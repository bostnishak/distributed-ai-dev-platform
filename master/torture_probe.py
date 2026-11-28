"""What the torture checks need to drive any generated page: find the add form and the search box, count what shows."""

from __future__ import annotations

import contextlib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import req_checks

_SEARCH_WORDS = re.compile(r"search|\bara\b|\barama|\bara:|filtre|filter|süz", re.IGNORECASE)
_SEARCH = "input[type=search]:visible, input[placeholder*='ara' i]:visible, input[placeholder*='search' i]:visible, input[aria-label*='ara' i]:visible"
_TEXT_FIELDS = "input:visible:not([type=search]):not([type=number]):not([type=date]):not([type=checkbox]):not([type=radio]):not([type=submit]):not([type=button]), textarea:visible"


@dataclass
class Session:
    """One fresh browser page on the application, with its errors and the writes it sent."""

    page: Any
    context: Any
    errors: list[str]
    writes: list[dict[str, str]]
    console: list[str]  # console.error lines the page logged itself (failed downloads are not counted)


def _logged(session: Session, message: Any) -> None:
    if message.type == "error" and "Failed to load resource" not in message.text:
        session.console.append(message.text.splitlines()[0][:200])


@contextlib.contextmanager
def opened(browser: Any, url: str) -> Iterator[Session]:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    try:
        context.add_init_script(req_checks._BOUND_JS)
        page = context.new_page()
        session = Session(page, context, [], [], [])
        page.on("console", lambda message: _logged(session, message))
        page.on("pageerror", lambda error: session.errors.append(str(error).splitlines()[0][:160]))
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.on("request", lambda r: session.writes.append({"method": r.method, "url": r.url, "body": r.post_data or ""}) if r.method in ("POST", "PUT", "PATCH") else None)
        page.goto(url, timeout=20000)
        page.wait_for_timeout(300)
        yield session
    finally:
        context.close()


def _is_search(field: Any) -> bool:
    """A search box written as a plain text input is still a search box."""
    label = field.evaluate("e => [e.id, e.name, e.placeholder, e.getAttribute('aria-label'), ...[...(e.labels || [])].map(l => l.innerText)].join(' ')")
    return bool(_SEARCH_WORDS.search(label or ""))


def text_field(page: Any) -> Any:
    """The field a record is typed into: the first text field that is not a search or filter box."""
    found = page.locator(_TEXT_FIELDS).all()
    return next((field for field in found if not _is_search(field)), found[0] if found else None)


def search_field(page: Any) -> Any:
    found = page.locator(_SEARCH)
    return found.first if found.count() else None


def adder(page: Any) -> Any:
    return req_checks._adder(page)


def usable(page: Any) -> bool:
    """The page has something that adds a record from a text field."""
    return text_field(page) is not None and adder(page) is not None


def fill(page: Any, text: str, number: str = "3") -> None:
    for field in page.locator("input:visible, textarea:visible, select:visible").all():
        kind = (field.get_attribute("type") or "text").lower()
        if kind in ("checkbox", "radio", "button", "submit", "file", "range", "color", "hidden", "search"):
            continue
        with contextlib.suppress(Exception):
            if field.evaluate("e => e.tagName") == "SELECT":
                field.select_option(index=min(1, field.locator("option").count() - 1))
            else:
                field.fill({"number": number, "date": "2028-02-29", "email": "a@b.co", "time": "23:30"}.get(kind, text))


def add(page: Any, text: str, number: str = "3", clicks: int = 1) -> None:
    fill(page, text, number)
    adder(page).click(click_count=clicks, timeout=3000)
    page.wait_for_timeout(500)


def shown(page: Any, text: str) -> int:
    """How many times the text appears on the page itself (field values do not count)."""
    return page.inner_text("body").count(text)
