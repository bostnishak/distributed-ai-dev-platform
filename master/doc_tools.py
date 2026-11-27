"""Ways to move around an attached document, computed by code: contents, a page range, its tables, and whether a
quotation is really in it.

  içindekiler | sayfa 3-5 | tabloları çıkar | alıntıyı doğrula: "..."
"""

from __future__ import annotations

import io
import json
import logging
import re
from collections.abc import Callable
from typing import Any

import pymupdf
from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import doc_reader
import extract

_log = logging.getLogger(__name__)
_EXT = (".pdf", ".docx", ".md", ".txt")
_TOC_RE = re.compile(r"^\s*(?:içindekiler|içindekileri\s+(?:göster|listele|çıkar)|table\s+of\s+contents)\s*[.!?]?\s*$", re.IGNORECASE)
_PAGES_RE = re.compile(r"^\s*sayfa\s+(?P<a>\d{1,5})(?:\s*(?:-|ile|\u2013)\s*(?P<b>\d{1,5}))?\s*(?:arasını|arası|'?\w{0,4})?\s*(?:göster|oku|getir)?\s*[.!?]?\s*$", re.IGNORECASE)
_TABLES_RE = re.compile(r"^\s*(?:tabloları\s+(?:çıkar|göster|listele)|extract\s+tables)\s*[.!?]?\s*$", re.IGNORECASE)
_QUOTE_RE = re.compile(r"^\s*(?:alıntıyı|alıntı)\s+doğrula\s*:\s*[\"“”']?(?P<quote>.{10,600}?)[\"“”']?\s*$", re.IGNORECASE | re.DOTALL)
_LIMIT = 6000


def _markdown_table(rows: list[list[Any]]) -> str:
    cells = [[" ".join(str(c or "").split()).replace("|", "\\|") for c in row] for row in rows if row]
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    cells = [r + [""] * (width - len(r)) for r in cells]
    used = [i for i in range(width) if any(r[i] for r in cells)]
    if not used:
        return ""
    cells, width = [[r[i] for i in used] for r in cells], len(used)
    return "\n".join(["| " + " | ".join(cells[0]) + " |", "|" + "---|" * width, *("| " + " | ".join(r) + " |" for r in cells[1:])])


def contents(name: str, raw: bytes) -> str:
    """Headings with their page (PDF) or line (text); says so when the document declares none."""
    lower = name.lower()
    entries: list[str] = []
    if lower.endswith(".pdf"):
        with pymupdf.open(stream=raw, filetype="pdf") as doc:
            entries = [f"{'  ' * (level - 1)}- {title.strip()} (sayfa {page})" for level, title, page in doc.get_toc()]
    elif lower.endswith(".docx"):
        import docx

        for paragraph in docx.Document(io.BytesIO(raw)).paragraphs:
            if (match := re.match(r"(?:Heading|Başlık)\s*(\d)", paragraph.style.name)) and paragraph.text.strip():
                entries.append(f"{'  ' * (int(match[1]) - 1)}- {paragraph.text.strip()}")
    else:
        for number, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            if match := re.match(r"(#{1,4})\s+(.+)", line):
                entries.append(f"{'  ' * (len(match[1]) - 1)}- {match[2].strip()} (satır {number})")
    return "İçindekiler:\n" + "\n".join(entries[:150]) if entries else "Belgede tanımlı başlık ya da içindekiler yok."


def pages(name: str, raw: bytes, first: int, last: int) -> str:
    if not name.lower().endswith(".pdf"):
        return "Sayfa aralığı yalnız PDF'te var (diğer biçimlerde sayfa sınırı dosyada yazılı değil)."
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        if not 1 <= first <= last <= doc.page_count:
            return f"Belge {doc.page_count} sayfa; istenen aralık geçersiz."
        shown = [f"### Sayfa {n}\n{doc[n - 1].get_text('text').strip() or '(bu sayfada metin katmanı yok)'}" for n in range(first, min(last, first + 9) + 1)]
    text = "\n\n".join(shown)
    cut = len(text) > _LIMIT or last > first + 9
    return text[:_LIMIT] + ("\n\n_(Uzun olduğu için kesildi; daha dar bir aralık iste.)_" if cut else "")


def tables(name: str, raw: bytes) -> str:
    found: list[str] = []
    if name.lower().endswith(".pdf"):
        with pymupdf.open(stream=raw, filetype="pdf") as doc:
            for number, page in enumerate(doc, 1):
                found += [f"**Sayfa {number}**\n\n{_markdown_table(table.extract())}" for table in page.find_tables().tables]
                if len(found) >= 12:
                    break
    elif name.lower().endswith(".docx"):
        import docx

        found = [f"**Tablo {i}**\n\n{_markdown_table([[c.text for c in row.cells] for row in t.rows])}" for i, t in enumerate(docx.Document(io.BytesIO(raw)).tables, 1)]
    return "\n\n".join(found[:12]) if found else "Belgede çizgileriyle tanınabilen bir tablo bulunamadı."


def verify_quote(name: str, raw: bytes, quote: str) -> str:
    text = extract.extract_text(name, raw)
    where = doc_reader.place(text, doc_reader.pdf_pages(name, raw), quote)
    if where:
        return f"Alıntı belgede **birebir var**: {where}."
    words = set(re.findall(r"\w{4,}", quote.casefold()))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]
    best = max(sentences, key=lambda s: len(words & set(re.findall(r"\w{4,}", s.casefold()))), default="")
    close = len(words & set(re.findall(r"\w{4,}", best.casefold()))) >= max(2, len(words) // 2)
    return "Alıntı belgede **birebir yok**." + (f"\nEn yakın cümle ({doc_reader.place(text, doc_reader.pdf_pages(name, raw), best) or 'yeri belirsiz'}): \"{best[:300]}\"" if close else "")


def answer(prompt: str, name: str, raw: bytes) -> str:
    """The reply to a document command; "" for any other request."""
    actions: tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = (
        (_TOC_RE, lambda _m: contents(name, raw)),
        (_PAGES_RE, lambda m: pages(name, raw, int(m["a"]), int(m["b"] or m["a"]))),
        (_TABLES_RE, lambda _m: tables(name, raw)),
        (_QUOTE_RE, lambda m: verify_quote(name, raw, m["quote"])),
    )
    for pattern, run in actions:
        if match := pattern.match(prompt):
            try:
                return run(match)
            except (OSError, ValueError, KeyError, RuntimeError, extract.UnsupportedFileError, pymupdf.FileDataError) as exc:
                _log.warning("document command failed: %r", exc)
                return f"Belge okunamadı: {type(exc).__name__}"
    return ""


def fastpath(prompt: str, file: UploadFile) -> StreamingResponse | None:
    name = file.filename or ""
    if not name.lower().endswith(_EXT) or not any(p.match(prompt) for p in (_TOC_RE, _PAGES_RE, _TABLES_RE, _QUOTE_RE)):
        return None
    raw = file.file.read(20_000_000)
    file.file.seek(0)
    reply = answer(prompt, name, raw)

    def sse(payload: dict[str, str]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(iter([sse({"type": "token", "content": reply}), sse({"type": "done", "model": "doc-tools", "task_type": "dokuman"})]), media_type="text/event-stream")
