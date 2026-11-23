"""Cluster B (`[M33]`, Faz 9.1 & Faz 19.2): Headless Browser DOM-to-Markdown Converter & Set-of-Marks (SoM) Interactive Element Annotator.

Provides:
- `html_to_clean_markdown(html_text: str) -> dict`: strips scripts/styles, converts headings, links, paragraphs, lists, and HTML `<table>` elements into clean Markdown + structured `tables: list[list[list[str]]]`.
- `annotate_set_of_marks_dom(html_text: str) -> list[dict]`: extracts all interactive elements (`<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`) with sequential `[SOM-1]`, `[SOM-2]` IDs, tag, label, and CSS selector.
"""

from __future__ import annotations

import html
import re
from typing import Any

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript|svg|head)\b[^>]*>[\s\S]*?</\1>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
_TITLE_RE = re.compile(r"<title\b[^>]*>([\s\S]*?)</title>", re.IGNORECASE)
_TABLE_RE = re.compile(r"<table\b[^>]*>([\s\S]*?)</table>", re.IGNORECASE)
_TR_RE = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
_CELL_RE = re.compile(r"<t[dh]\b[^>]*>([\s\S]*?)</t[dh]>", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>([\s\S]*?)</h\1>", re.IGNORECASE)
_LINK_RE = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*['"]([^'"]+)['"][^>]*>([\s\S]*?)</a>""", re.IGNORECASE)
_LI_RE = re.compile(r"<li\b[^>]*>([\s\S]*?)</li>", re.IGNORECASE)
_BLOCK_RE = re.compile(r"</?(?:p|div|section|article|header|footer|main|br|hr|tr|ul|ol)\b[^>]*>", re.IGNORECASE)

_INTERACTIVE_RE = re.compile(
    r"<(a|button|input|select|textarea)\b([^>]*?)(?:>([\s\S]*?)</\1>|/?>)",
    re.IGNORECASE,
)
_ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:['"]([^'"]*)['"]|([^\s>]+))""")


def _clean_text(raw: str) -> str:
    no_tags = _TAG_STRIP_RE.sub(" ", raw or "")
    unescaped = html.unescape(no_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    norm_rows = [r + [""] * (col_count - len(r)) for r in rows]
    header = norm_rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in norm_rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def html_to_clean_markdown(html_text: str) -> dict[str, Any]:
    """Strip scripts/styles, extract structured tables, and convert HTML into clean Markdown."""
    raw = html_text or ""
    title_match = _TITLE_RE.search(raw)
    title = _clean_text(title_match.group(1)) if title_match else ""

    working = _COMMENT_RE.sub("", raw)
    working = _SCRIPT_STYLE_RE.sub("", working)

    tables: list[list[list[str]]] = []
    links: list[dict[str, str]] = []

    def _replace_table(match: re.Match[str]) -> str:
        t_html = match.group(1)
        parsed_rows: list[list[str]] = []
        for tr_m in _TR_RE.finditer(t_html):
            cells = [_clean_text(c.group(1)) for c in _CELL_RE.finditer(tr_m.group(1))]
            if any(cells):
                parsed_rows.append(cells)
        if parsed_rows:
            tables.append(parsed_rows)
            return "\n\n" + _table_to_markdown(parsed_rows) + "\n\n"
        return ""

    working = _TABLE_RE.sub(_replace_table, working)

    def _replace_heading(match: re.Match[str]) -> str:
        level = int(match.group(1))
        txt = _clean_text(match.group(2))
        return f"\n\n{'#' * level} {txt}\n\n" if txt else ""

    working = _HEADING_RE.sub(_replace_heading, working)

    def _replace_link(match: re.Match[str]) -> str:
        href = match.group(1).strip()
        label = _clean_text(match.group(2)) or href
        links.append({"href": href, "text": label})
        return f"[{label}]({href})"

    working = _LINK_RE.sub(_replace_link, working)
    working = _LI_RE.sub(lambda m: f"\n- {_clean_text(m.group(1))}", working)
    working = _BLOCK_RE.sub("\n", working)
    working = _TAG_STRIP_RE.sub("", working)
    working = html.unescape(working)

    cleaned_lines: list[str] = []
    for ln in working.splitlines():
        s = re.sub(r"[ \t]+", " ", ln).strip()
        if s:
            cleaned_lines.append(s)
        elif cleaned_lines and cleaned_lines[-1] != "":
            cleaned_lines.append("")

    markdown = "\n".join(cleaned_lines).strip()
    return {
        "title": title,
        "markdown": markdown,
        "tables": tables,
        "links": links,
    }


def _parse_attrs(attr_str: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_str or ""):
        key = m.group(1).lower()
        val = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        attrs[key] = html.unescape(val.strip())
    return attrs


def annotate_set_of_marks_dom(html_text: str) -> list[dict[str, Any]]:
    """Extract interactive DOM elements with sequential `[SOM-1]`, `[SOM-2]` IDs, tag, label, and CSS selector."""
    working = _COMMENT_RE.sub("", html_text or "")
    working = _SCRIPT_STYLE_RE.sub("", working)

    elements: list[dict[str, Any]] = []
    tag_counters: dict[str, int] = {}

    for idx, match in enumerate(_INTERACTIVE_RE.finditer(working), start=1):
        tag = match.group(1).lower()
        attrs = _parse_attrs(match.group(2) or "")
        inner_text = _clean_text(match.group(3) or "")

        tag_counters[tag] = tag_counters.get(tag, 0) + 1
        label = (
            inner_text
            or attrs.get("aria-label")
            or attrs.get("placeholder")
            or attrs.get("value")
            or attrs.get("name")
            or attrs.get("title")
            or attrs.get("id")
            or f"{tag}-{tag_counters[tag]}"
        )

        if attrs.get("id"):
            selector = f"#{attrs['id']}"
        elif attrs.get("name"):
            selector = f'{tag}[name="{attrs["name"]}"]'
        elif "href" in attrs and attrs["href"] and tag == "a":
            selector = f'a[href="{attrs["href"]}"]'
        else:
            selector = f"{tag}:nth-of-type({tag_counters[tag]})"

        som_id = f"[SOM-{idx}]"
        elements.append(
            {
                "som_id": som_id,
                "index": idx,
                "tag": tag,
                "type": attrs.get("type", tag),
                "label": label,
                "selector": selector,
                "attributes": attrs,
            }
        )

    return elements
