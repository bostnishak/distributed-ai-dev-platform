"""Render the same validated document blocks with Typst, for documents with equations or when the user asks for it.

All text is escaped, so a document can never run Typst code; compilation has no access outside its temporary folder.
"""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)
_ASKS_RE = re.compile(r"\btypst\b|\bdenklem\w*|\bformül\w*\s+(?:içeren|yoğun)|\bakademik\s+makale|\bequations?\b", re.IGNORECASE)
_SPECIAL = re.compile(r"([\\#$*_`<>@\[\]=~+\-/{}\"'])")


def wanted(prompt: str) -> bool:
    return bool(_ASKS_RE.search(prompt))


def escape(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", str(text)).replace("\n", " ")


def _block(block: dict[str, Any]) -> str:
    kind = block["type"]
    if kind == "heading":
        return f"{'=' * (block.get('level', 1))} {escape(block['text'])}"
    if kind == "para":
        return escape(block["text"])
    if kind in ("bullets", "numbered"):
        marker = "-" if kind == "bullets" or block.get("own_numbers") else "+"
        return "\n".join(f"{marker} {escape(item)}" for item in block["items"])
    if kind == "table":
        columns = len(block["headers"]) or 1
        cells = [f"[*{escape(h)}*]" for h in block["headers"]] + [f"[{escape(cell)}]" for row in block["rows"] for cell in row[:columns]]
        return f"#table(columns: {columns}, " + ", ".join(cells) + ")"
    if kind == "signature":
        return "#v(2em)\n#grid(columns: 2, gutter: 3em, " + ", ".join(f"[{escape(p)} \\ \\ ......................]" for p in block["parties"]) + ")"
    if kind == "chart":
        cells = [f"[{escape(label)}], [{escape(f'{value:,.2f}')}]" for label, value in zip(block["labels"], block["values"], strict=True)]
        return f"*{escape(block.get('title', ''))}*\n\n#table(columns: 2, " + ", ".join(cells) + ")"
    return ""


def source(spec: dict[str, Any]) -> str:
    head = ['#set page(paper: "a4", margin: 2.2cm, numbering: "1")', '#set text(size: 11pt, lang: "tr")', "#set par(justify: true)",
            f"#align(center)[#text(18pt)[*{escape(spec['title'])}*]]"]
    if spec.get("subtitle"):
        head.append(f"#align(center)[{escape(spec['subtitle'])}]")
    return "\n\n".join([*head, *[text for block in spec["blocks"] if (text := _block(block))]]) + "\n"


def build(out_path: Path, spec: dict[str, Any]) -> int:
    """Write the PDF and return its page count; RuntimeError when Typst cannot compile it."""
    import pymupdf
    import typst

    with tempfile.TemporaryDirectory(prefix="cm6453_typ_", ignore_cleanup_errors=True) as tmp:
        main = Path(tmp) / "main.typ"
        main.write_text(source(spec), encoding="utf-8")
        try:
            out_path.write_bytes(typst.compile(str(main), root=tmp))
        except Exception as exc:  # noqa: BLE001, RUF100  (the binding raises its own error types)
            _log.warning("typst failed: %s", exc)
            raise RuntimeError(f"Typst derlemesi başarısız: {exc}") from exc
    with pymupdf.open(out_path) as doc:
        return doc.page_count
