"""Tier 0: edits that need no model, applied in milliseconds and exactly.

Only unambiguous requests are handled ("replace colour #A with #B", "h1 rengini #B yap", 'change the text "X" to "Y"'); anything else goes to
the model.
"""

from __future__ import annotations

import re
from pathlib import Path

_EXTS = (".html", ".css", ".js", ".py")
_HEX = r"(#[0-9a-fA-F]{6})"
_COLOR_RES = (
    re.compile(_HEX + r"(?:\s*rengini|\s*renk)?\s*(?:yerine|->|→)\s*" + _HEX, re.IGNORECASE),
    re.compile(r"(?:replace|change)\s+(?:colou?r\s+)?" + _HEX + r"\s+(?:with|to)\s+" + _HEX, re.IGNORECASE),
)
_TEXT_RE = re.compile(r"[\"“]([^\"“”\n]{2,60})[\"”]\s*(?:yazısını|metnini|yazısı|->|→)\s*[\"“]([^\"“”\n]{1,60})[\"”]", re.IGNORECASE)
_MAX_CHARS = 200
_PRIMARY_RE = re.compile(r"(?:ana|birincil|primary)\s+(?:buton|düğme|button)?\s*(?:rengi\w*|colou?r)", re.IGNORECASE)
_PRIMARY_VAR_RE = re.compile(r"(--(?:(?:btn|button)-?primary|primary(?:-?(?:color|btn|button|bg))?|color-primary|accent(?:-color)?|(?:btn|button)-(?:color|bg))\s*:\s*)(#[0-9a-fA-F]{3,8})", re.IGNORECASE)


_ELEMENT_RE = re.compile(
    r"^\s*(?P<selector>[.#][A-Za-z_][\w-]*|h[1-6]|body|button|label|header|footer|nav|li|td|th|p|a|sayfa(?:nın)?)"
    r"(?:['\u2019]?(?:n[iıuü]n|[iıuü]n))?(?:\s+(?:etiketinin|öğesinin|elemanının|sınıfının))?\s+(?P<background>arka\s*plan(?:ının)?\s+)?(?:yazı\s+)?(?:rengi(?:ni)?|renk)\s+"
    + _HEX + r"\s*(?:olarak\s+)?(?:yap|olsun|değiştir)\s*[.!]?\s*$", re.IGNORECASE)
_STYLE_BLOCK_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.DOTALL | re.IGNORECASE)


def element_colour(instruction: str) -> tuple[str, str, str] | None:
    """(selector, css property, colour) of "<element> rengini #X yap", else None."""
    match = _ELEMENT_RE.match(instruction) if len(instruction) <= _MAX_CHARS else None
    if not match:
        return None
    selector = match["selector"]
    if selector.casefold().startswith("sayfa"):
        if not match["background"]:
            return None  # "the page's colour" could mean text or background
        selector = "body"
    elif selector[0] not in ".#":
        selector = selector.lower()
    return selector, "background-color" if match["background"] else "color", match.group(3)


def _set_rule(css: str, selector: str, prop: str, colour: str) -> tuple[str, bool]:
    """Set the property in the last rule written for exactly this selector; (css, False) when there is no such rule."""
    rules = list(re.finditer(rf"(?:^|(?<=\}})|(?<=\*/)|(?<=\n))[ \t]*{re.escape(selector)}\s*\{{(?P<body>[^{{}}]*)\}}", css))
    if not rules:
        return css, False
    body = rules[-1]["body"]
    names = ("background-color", "background") if prop == "background-color" else ("color",)
    for name in names:
        found = list(re.finditer(rf"(?<![\w-]){name}\s*:\s*[^;{{}}]+", body))
        if found:
            body = body[: found[-1].start()] + f"{name}: {colour}" + body[found[-1].end() :]
            break
    else:
        body = f"{body.rstrip().rstrip(';')}; {prop}: {colour}; " if body.strip() else f" {prop}: {colour}; "
    start, end = rules[-1].span("body")
    return css[:start] + body + css[end:], True


def _set_in_page(html: str, selector: str, prop: str, colour: str) -> tuple[str, bool]:
    hit = False
    for match in reversed(list(_STYLE_BLOCK_RE.finditer(html))):
        css, found = _set_rule(match.group(2), selector, prop, colour)
        if found:
            html, hit = html[: match.start(2)] + css + html[match.end(2) :], True
    return html, hit


def _add_rule(ws_dir: Path, selector: str, prop: str, colour: str) -> list[str]:
    page = ws_dir / "index.html"
    if not page.is_file():
        return []
    html = page.read_text(encoding="utf-8", errors="replace")
    block = f"<style>{selector} {{ {prop}: {colour} !important; }}</style>\n"
    marker = next((m for m in ("</head>", "</body>") if m in html), "")
    page.write_text(html.replace(marker, block + marker, 1) if marker else html + "\n" + block, encoding="utf-8")
    return ["index.html"]


def apply_element_colour(ws_dir: Path, selector: str, prop: str, colour: str) -> list[str]:
    """Change the rule where it is written; when no rule exists, add one to the entry page."""
    changed = []
    for path in sorted(ws_dir.rglob("*")):
        if not path.is_file() or path.suffix not in (".css", ".html") or any(x.startswith(".") for x in path.relative_to(ws_dir).parts):
            continue
        write = _set_rule if path.suffix == ".css" else _set_in_page
        updated, hit = write(path.read_text(encoding="utf-8", errors="replace"), selector, prop, colour)
        if hit:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.relative_to(ws_dir).as_posix())
    return changed or _add_rule(ws_dir, selector, prop, colour)


def parse(instruction: str) -> tuple[str, str] | None:
    """(old, new) of an exact replacement, or None when the request needs a model."""
    if len(instruction) > _MAX_CHARS:
        return None
    for rx in (*_COLOR_RES, _TEXT_RE):
        if m := rx.search(instruction):
            return m.group(1), m.group(2)
    return None


def primary_colour(instruction: str) -> str:
    """The new colour of a 'make the primary button colour #X' request, else an empty string."""
    colours = re.findall(_HEX, instruction)
    return colours[0] if len(instruction) <= _MAX_CHARS and len(colours) == 1 and _PRIMARY_RE.search(instruction) else ""


def apply(ws_dir: Path, instruction: str) -> list[str]:
    """Files changed by the replacement (empty when not applicable or the old value is nowhere)."""
    if target := element_colour(instruction):
        return apply_element_colour(ws_dir, *target)
    pair = parse(instruction)
    if pair is not None:
        old, new = pair
        rx = re.compile(re.escape(old), re.IGNORECASE if old.startswith("#") else 0)
        replace = lambda _m: new  # noqa: E731
    elif colour := primary_colour(instruction):
        rx, replace = _PRIMARY_VAR_RE, lambda m: m.group(1) + colour
    else:
        return []
    changed = []
    for path in ws_dir.rglob("*"):
        if not path.is_file() or path.suffix not in _EXTS or any(p.startswith(".") for p in path.relative_to(ws_dir).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = rx.sub(replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.relative_to(ws_dir).as_posix())
    return changed
