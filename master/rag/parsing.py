"""RAG-02, RAG-03, RAG-04, RAG-16, RAG-24: Structure-Preserving Parsing, OCR, Chunking, Table QA & Ingest Security."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"disregard\s+safety\s+rules", re.IGNORECASE),
    re.compile(r"tüm\s+kuralları\s+yok\s+say", re.IGNORECASE),
    re.compile(r"<\s*script\b|javascript:", re.IGNORECASE),
)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")),
    ("tckn", re.compile(r"\b[1-9]\d{10}\b")),
    ("iban", re.compile(r"\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b")),
    ("api_key", re.compile(r"\b(?:sk-[a-zA-Z0-9]{16,}|ghp_[a-zA-Z0-9]{20,})\b")),
)


@dataclass
class ParsedTable:
    headers: list[str]
    rows: list[list[str]]
    page: int = 1
    section: str = ""


@dataclass
class ParsedPage:
    page_number: int
    markdown: str
    is_ocr: bool = False
    ocr_confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)


@dataclass
class ParsedDocument:
    title: str
    source_type: str
    pages: list[ParsedPage]
    tables: list[ParsedTable] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_ocr: bool = False


@dataclass
class ChunkRecord:
    chunk_index: int
    page: int
    section: str
    offset: int
    content: str
    content_hash: str
    is_table: bool = False
    is_ocr: bool = False
    quarantine: bool = False
    pii_tags: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------- RAG-24 Ingest Security Scanner

def scan_ingest_security(text: str) -> dict[str, Any]:
    """RAG-24: Detect prompt injection, active scripts, and PII before indexing."""
    injection_hits = [p.pattern for p in _INJECTION_PATTERNS if p.search(text or "")]
    pii_tags = [label for label, pat in _PII_PATTERNS if pat.search(text or "")]
    return {
        "quarantine": len(injection_hits) > 0,
        "injection_hits": injection_hits,
        "pii_tags": pii_tags,
    }


# ---------------------------------------------------------------- RAG-03 OCR Helper

def run_ocr_on_image_bytes(image_bytes: bytes) -> tuple[str, float, list[str]]:
    """RAG-03: Run Tesseract OCR (tur+eng) if installed; return clear DEF-15 message if unavailable."""
    try:
        import io

        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(img, lang="tur+eng", output_type=pytesseract.Output.DICT)
        words: list[str] = []
        confs: list[float] = []
        for txt, conf in zip(data.get("text", []), data.get("conf", []), strict=False):
            cleaned = str(txt or "").strip()
            if cleaned:
                words.append(cleaned)
                try:
                    c = float(conf)
                    if c >= 0:
                        confs.append(c / 100.0)
                except ValueError:
                    pass
        avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0
        warnings = ["Düşük OCR güveni: taranmış sayfa bulanık olabilir."] if avg_conf < 0.75 else []
        return " ".join(words), avg_conf, warnings
    except Exception as exc:
        return (
            "",
            0.0,
            [f"OCR motoru (Tesseract) kurulu değil veya çalıştırılamadı; taranmış sayfa okunamadı ({type(exc).__name__})."],
        )


# ---------------------------------------------------------------- RAG-02 Structure-Preserving Parsers

def _extract_markdown_tables(md: str, page: int = 1, section: str = "") -> list[ParsedTable]:
    tables: list[ParsedTable] = []
    lines = (md or "").splitlines()
    i = 0
    while i < len(lines) - 1:
        if "|" in lines[i] and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            headers = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            if headers and rows:
                tables.append(ParsedTable(headers=headers, rows=rows, page=page, section=section))
            continue
        i += 1
    return tables


def parse_document(file_path: Path | None = None, *, raw_text: str | None = None, title: str = "") -> ParsedDocument:
    """RAG-02 & RAG-03: Parse PDF (pymupdf4llm), DOCX, PPTX, XLSX, HTML, MD/TXT preserving structure."""
    if raw_text is not None:
        ext = Path(title).suffix.lower() if title else ".md"
        if ext in {".html", ".htm"}:
            clean = _html_to_markdown(raw_text)
            tabs = _extract_markdown_tables(clean, page=1)
            return ParsedDocument(title=title or "html_doc", source_type="html", pages=[ParsedPage(1, clean, tables=tabs)], tables=tabs)
        tabs = _extract_markdown_tables(raw_text, page=1)
        return ParsedDocument(title=title or "text_doc", source_type="markdown", pages=[ParsedPage(1, raw_text, tables=tabs)], tables=tabs)

    assert file_path is not None
    p = Path(file_path)
    ext = p.suffix.lower()
    doc_title = title or p.name

    if ext == ".pdf":
        return _parse_pdf(p, doc_title)
    if ext == ".docx":
        return _parse_docx(p, doc_title)
    if ext == ".pptx":
        return _parse_pptx(p, doc_title)
    if ext == ".xlsx":
        return _parse_xlsx(p, doc_title)
    if ext in {".html", ".htm"}:
        md = _html_to_markdown(p.read_text(encoding="utf-8", errors="ignore"))
        tabs = _extract_markdown_tables(md, page=1)
        return ParsedDocument(title=doc_title, source_type="html", pages=[ParsedPage(1, md, tables=tabs)], tables=tabs)
    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        text, conf, warns = run_ocr_on_image_bytes(p.read_bytes())
        return ParsedDocument(
            title=doc_title,
            source_type="image_ocr",
            pages=[ParsedPage(1, text, is_ocr=True, ocr_confidence=conf, warnings=warns)],
            warnings=warns,
            is_ocr=True,
        )
    text = p.read_text(encoding="utf-8", errors="ignore")
    tabs = _extract_markdown_tables(text, page=1)
    return ParsedDocument(title=doc_title, source_type="text", pages=[ParsedPage(1, text, tables=tabs)], tables=tabs)


def _parse_pdf(path: Path, title: str) -> ParsedDocument:
    import pymupdf
    import pymupdf4llm

    pages: list[ParsedPage] = []
    all_tables: list[ParsedTable] = []
    warnings: list[str] = []
    any_ocr = False

    chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True)
    doc = pymupdf.open(str(path))
    try:
        for idx, ch in enumerate(chunks, start=1):
            md = str(ch.get("text") or "").strip() if isinstance(ch, dict) else str(ch).strip()
            is_ocr = False
            ocr_conf = 1.0
            p_warns: list[str] = []
            if len(md) < 15 and idx - 1 < len(doc):
                # No text layer -> attempt OCR (RAG-03)
                pix = doc[idx - 1].get_pixmap(dpi=180)
                ocr_txt, ocr_conf, p_warns = run_ocr_on_image_bytes(pix.tobytes("png"))
                if ocr_txt:
                    md = f"[OCR]\n{ocr_txt}"
                is_ocr = True
                any_ocr = True
                warnings.extend(p_warns)
            tabs = _extract_markdown_tables(md, page=idx)
            all_tables.extend(tabs)
            pages.append(ParsedPage(idx, md, is_ocr=is_ocr, ocr_confidence=ocr_conf, warnings=p_warns, tables=tabs))
    finally:
        doc.close()

    return ParsedDocument(title=title, source_type="pdf", pages=pages, tables=all_tables, warnings=warnings, is_ocr=any_ocr)


def _parse_docx(path: Path, title: str) -> ParsedDocument:
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = []
    tables: list[ParsedTable] = []
    cur_sec = ""
    for para in doc.paragraphs:
        txt = para.text.strip()
        if not txt:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if "heading 1" in style:
            cur_sec = txt
            parts.append(f"# {txt}")
        elif "heading 2" in style:
            cur_sec = txt
            parts.append(f"## {txt}")
        elif "heading" in style:
            cur_sec = txt
            parts.append(f"### {txt}")
        else:
            parts.append(txt)
    for tbl in doc.tables:
        rows = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in tbl.rows]
        if rows:
            headers = rows[0]
            body = rows[1:]
            tables.append(ParsedTable(headers=headers, rows=body, page=1, section=cur_sec))
            md_tbl = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |",
                *["| " + " | ".join(r) + " |" for r in body],
            ]
            parts.append("\n".join(md_tbl))
    md = "\n\n".join(parts)
    return ParsedDocument(title=title, source_type="docx", pages=[ParsedPage(1, md, tables=tables)], tables=tables)


def _parse_pptx(path: Path, title: str) -> ParsedDocument:
    from pptx import Presentation

    prs = Presentation(str(path))
    pages: list[ParsedPage] = []
    for idx, slide in enumerate(prs.slides, start=1):
        lines: list[str] = []
        for shp in slide.shapes:
            if shp.has_text_frame:
                txt = shp.text_frame.text.strip()
                if txt:
                    if shp == slide.shapes.title:
                        lines.insert(0, f"## Slayt {idx}: {txt}")
                    else:
                        lines.append(txt)
        pages.append(ParsedPage(idx, "\n\n".join(lines)))
    return ParsedDocument(title=title, source_type="pptx", pages=pages)


def _parse_xlsx(path: Path, title: str) -> ParsedDocument:
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True)
    pages: list[ParsedPage] = []
    all_tables: list[ParsedTable] = []
    for idx, name in enumerate(wb.sheetnames, start=1):
        ws = wb[name]
        raw_rows = [[("" if v is None else str(v)) for v in row] for row in ws.iter_rows(values_only=True)]
        non_empty = [r for r in raw_rows if any(c.strip() for c in r)]
        if not non_empty:
            continue
        headers = non_empty[0]
        body = non_empty[1:]
        all_tables.append(ParsedTable(headers=headers, rows=body, page=idx, section=name))
        md_lines = [
            f"## {name}",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(r) + " |" for r in body],
        ]
        pages.append(ParsedPage(idx, "\n".join(md_lines), tables=[all_tables[-1]]))
    return ParsedDocument(title=title, source_type="xlsx", pages=pages, tables=all_tables)


def _html_to_markdown(raw_html: str) -> str:
    txt = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", raw_html, flags=re.IGNORECASE)
    txt = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"<(?:p|div|br|tr)[^>]*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


# ---------------------------------------------------------------- RAG-04 Structure-Aware Chunker

def _approx_tokens(text: str) -> int:
    return max(1, int(len((text or "").split()) * 1.3))


def _split_atomic_blocks(md: str) -> list[tuple[str, str]]:
    """Split markdown into atomic blocks: ('heading'|'code'|'table'|'para', content). Never breaks tables/code."""
    blocks: list[tuple[str, str]] = []
    lines = (md or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            buf = [line]
            i += 1
            while i < len(lines):
                buf.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            blocks.append(("code", "\n".join(buf)))
            continue
        if stripped.startswith("#"):
            blocks.append(("heading", stripped))
            i += 1
            continue
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            buf = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                buf.append(lines[i])
                i += 1
            blocks.append(("table", "\n".join(buf)))
            continue
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", "```")):
            if "|" in lines[i] and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
                break
            buf.append(lines[i])
            i += 1
        blocks.append(("para", "\n".join(buf)))
    return blocks


def chunk_document(parsed: ParsedDocument, *, min_tokens: int = 300, max_tokens: int = 750) -> list[ChunkRecord]:
    """RAG-04: Structure-aware chunking preserving heading breadcrumbs, whole tables, and whole code blocks."""
    chunks: list[ChunkRecord] = []
    heading_stack: list[tuple[int, str]] = []
    chunk_idx = 0
    global_offset = 0

    for page in parsed.pages:
        blocks = _split_atomic_blocks(page.markdown)
        cur_parts: list[str] = []
        cur_tokens = 0
        cur_has_table = False

        def _breadcrumb() -> str:
            return " > ".join(h for _, h in heading_stack)

        def _flush(page_num: int = page.page_number, page_is_ocr: bool = page.is_ocr) -> None:
            nonlocal chunk_idx, cur_parts, cur_tokens, cur_has_table, global_offset
            if not cur_parts:
                return
            sec = _breadcrumb()
            body = "\n\n".join(cur_parts).strip()
            full_text = f"[{sec}]\n{body}" if sec and not body.startswith("#") else body
            sec_scan = scan_ingest_security(full_text)
            h = hashlib.sha256(full_text.encode("utf-8")).hexdigest()[:24]
            chunks.append(
                ChunkRecord(
                    chunk_index=chunk_idx,
                    page=page_num,
                    section=sec,
                    offset=global_offset,
                    content=full_text,
                    content_hash=h,
                    is_table=cur_has_table,
                    is_ocr=page_is_ocr,
                    quarantine=sec_scan["quarantine"],
                    pii_tags=sec_scan["pii_tags"],
                )
            )
            chunk_idx += 1
            global_offset += len(full_text)
            cur_parts = []
            cur_tokens = 0
            cur_has_table = False

        for btype, btext in blocks:
            if btype == "heading":
                level = len(btext) - len(btext.lstrip("#"))
                title_txt = btext.lstrip("#").strip()
                if cur_tokens >= min_tokens // 2:
                    _flush()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title_txt))
                cur_parts.append(btext)
                cur_tokens += _approx_tokens(btext)
                continue

            btoks = _approx_tokens(btext)
            # Never split atomic tables or code blocks; flush before them if adding overflows max_tokens
            if cur_parts and cur_tokens + btoks > max_tokens:
                _flush()
            cur_parts.append(btext)
            cur_tokens += btoks
            if btype == "table":
                cur_has_table = True
            if cur_tokens >= max_tokens:
                _flush()

        _flush()
    return chunks


# ---------------------------------------------------------------- RAG-16 Deterministic Table QA

def query_table_numeric(table: ParsedTable, operation: str, column_name: str) -> dict[str, Any]:
    """RAG-16: Deterministic numeric aggregation (sum/avg/min/max/count) over structured table cells."""
    col_idx = -1
    target = column_name.strip().lower()
    for i, h in enumerate(table.headers):
        if target in h.strip().lower():
            col_idx = i
            break
    if col_idx < 0:
        raise ValueError(f"Sütun bulunamadı: {column_name}")

    vals: list[float] = []
    cell_refs: list[str] = []
    for r_idx, row in enumerate(table.rows, start=1):
        if col_idx >= len(row):
            continue
        raw = row[col_idx].replace(" ", "").replace("TL", "").replace("$", "").replace("%", "")
        # Handle Turkish decimal/thousand formatting cleanly
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        try:
            vals.append(float(raw))
            cell_refs.append(f"R{r_idx}C{col_idx + 1}")
        except ValueError:
            continue

    if not vals:
        raise ValueError(f"'{column_name}' sütununda sayısal değer bulunamadı.")

    op = operation.lower()
    if op == "sum":
        res = sum(vals)
    elif op in {"avg", "mean"}:
        res = sum(vals) / len(vals)
    elif op == "min":
        res = min(vals)
    elif op == "max":
        res = max(vals)
    elif op == "count":
        res = float(len(vals))
    else:
        raise ValueError(f"Desteklenmeyen tablo işlemi: {operation}")

    return {
        "operation": op,
        "column": table.headers[col_idx],
        "result": round(res, 6),
        "count": len(vals),
        "cell_range": f"{cell_refs[0]}:{cell_refs[-1]}",
        "page": table.page,
        "section": table.section,
    }
