"""Plain-text extraction for uploaded documents (requirements documents and chat attachments).

Preserves Turkish characters cleanly (UTF-8-SIG, UTF-8, Windows-1254/CP1254, ISO-8859-9) and
uses PyMuPDF first for PDF text extraction with pypdf fallback.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from itertools import zip_longest
from typing import Any

import pymupdf as fitz
from docx import Document
from docx.opc.exceptions import OpcError
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pptx import Presentation
from pptx.exc import PythonPptxError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from safe_archive import UnsafeArchive, inspect_zip

log = logging.getLogger(__name__)

REQUIREMENT_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".tsv", ".txt", ".md", ".zip")

_ZIP_MAX_TOTAL_CHARS = 60_000
_ZIP_TREE_MAX_ENTRIES = 200
_ZIP_BINARY_SNIFF_BYTES = 1024


class UnsupportedFileError(ValueError):
    pass


def _decode_bytes(raw: bytes) -> str:
    """Decode text preserving Turkish characters (UTF-8 with BOM, UTF-8, Windows-1254, ISO-8859-9)."""
    for enc in ("utf-8-sig", "utf-8", "cp1254", "iso-8859-9"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_pdf_text(raw: bytes) -> str:
    """Extract PDF text using PyMuPDF (better Turkish Unicode/CID support), falling back to pypdf."""
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        try:
            pages = [str(page.get_text("text") or "") for page in doc]
        finally:
            doc.close()
        text = "\n".join(pages).strip()
        if text:
            return text
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
        log.debug("Recoverable error suppressed: %s", exc)
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(raw: bytes) -> str:
    doc = Document(io.BytesIO(raw))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # Requirements documents often keep details in tables; paragraphs alone would lose them.
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def _collect_pptx_table_lines(table: Any, lines: list[str]) -> None:
    if table is None:
        return
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        if any(cells):
            lines.append(" | ".join(cells))


def _collect_pptx_tf_lines(tf: Any, lines: list[str]) -> None:
    if tf is None:
        return
    for para in tf.paragraphs:
        ptxt = (para.text or "").strip()
        if ptxt:
            level = int(getattr(para, "level", 0) or 0)
            lines.append(f"{'  ' * level}- {ptxt}" if level > 0 else ptxt)


def _collect_pptx_shape_lines(shape: Any, title_id: int | None, lines: list[str]) -> None:
    if title_id is not None and getattr(shape, "shape_id", None) == title_id:
        return
    if getattr(shape, "has_table", False):
        _collect_pptx_table_lines(getattr(shape, "table", None), lines)
        return
    if getattr(shape, "has_text_frame", False):
        _collect_pptx_tf_lines(getattr(shape, "text_frame", None), lines)
        return
    for child in getattr(shape, "shapes", None) or ():
        _collect_pptx_shape_lines(child, title_id, lines)


def extract_pptx_text(raw: bytes) -> str:
    """Extract slide numbers, titles, body/bullets, tables, and speaker notes from a PPTX archive."""
    prs = Presentation(io.BytesIO(raw))
    parts: list[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        title_shape = getattr(slide.shapes, "title", None)
        title_id = getattr(title_shape, "shape_id", None) if title_shape is not None else None
        title_text = ""
        if title_shape is not None and getattr(title_shape, "has_text_frame", False):
            title_text = (getattr(title_shape, "text", "") or "").strip()
        header = f"--- Slayt {idx}: {title_text} ---" if title_text else f"--- Slayt {idx} ---"
        slide_lines: list[str] = [header]
        for shape in slide.shapes:
            _collect_pptx_shape_lines(shape, title_id, slide_lines)
        if getattr(slide, "has_notes_slide", False):
            notes_slide = getattr(slide, "notes_slide", None)
            notes_tf = getattr(notes_slide, "notes_text_frame", None) if notes_slide is not None else None
            notes_txt = (getattr(notes_tf, "text", "") or "").strip() if notes_tf is not None else ""
            if notes_txt:
                slide_lines.append(f"[Konuşmacı Notları]: {notes_txt}")
        if len(slide_lines) > 1 or title_text:
            parts.append("\n".join(slide_lines))
    return "\n\n".join(parts)


def extract_csv_text(raw: bytes, *, delimiter: str | None = None) -> str:
    text = _decode_bytes(raw)
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    if delimiter is None:
        tab_count = first_line.count("\t")
        semi_count = first_line.count(";")
        comma_count = first_line.count(",")
        if tab_count > 0 and tab_count >= semi_count and tab_count >= comma_count:
            delimiter = "\t"
        elif semi_count > comma_count:
            delimiter = ";"
        else:
            delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)


def extract_xlsx_text(raw: bytes) -> str:
    wb_val = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    wb_fml = None
    parts: list[str] = []
    try:
        wb_fml = load_workbook(io.BytesIO(raw), read_only=True, data_only=False)
        for sheet_val in wb_val.worksheets:
            parts.append(f"--- Sayfa: {sheet_val.title} ---")
            sheet_fml = wb_fml[sheet_val.title]
            for row_val, row_fml in zip_longest(
                sheet_val.iter_rows(values_only=True),
                sheet_fml.iter_rows(values_only=True),
                fillvalue=(),
            ):
                merged = [v if v is not None else f for v, f in zip_longest(row_val, row_fml, fillvalue=None)]
                if any(v is not None for v in merged):
                    parts.append(" | ".join("" if v is None else str(v) for v in merged))
    finally:
        wb_val.close()
        if wb_fml is not None:
            wb_fml.close()
    return "\n".join(parts)


_ZIP_SKIP_EXTS = (
    ".pyc", ".pyo", ".pyd", ".class", ".exe", ".dll", ".so", ".wasm", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".bmp", ".tiff", ".tif",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".woff", ".woff2", ".ttf", ".otf",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".db", ".sqlite", ".sqlite3",
    ".doc", ".xls",
)

_ZIP_RECOVERABLE_ERRORS = (
    zipfile.BadZipFile,
    csv.Error,
    PyPdfError,
    OpcError,
    PythonPptxError,
    InvalidFileException,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def _build_zip_tree(infos: list[zipfile.ZipInfo]) -> str:
    """Build a crisp indented directory tree summary of all folders and files in a ZIP."""
    dir_set: set[str] = set()
    file_sizes: dict[str, int] = {}
    for info in infos:
        norm = info.filename.replace("\\", "/").strip("/")
        if not norm:
            continue
        segs = [s for s in norm.split("/") if s]
        for depth in range(1, len(segs) + (1 if info.is_dir() else 0)):
            dir_set.add("/".join(segs[:depth]) + "/")
        if not info.is_dir():
            file_sizes["/".join(segs)] = info.file_size
    entries = sorted(dir_set | set(file_sizes.keys()), key=lambda p: p.rstrip("/").split("/"))
    lines = [f"=== ZIP Dizin Ağacı ({len(file_sizes)} dosya, {len(dir_set)} klasör) ==="]
    for path in entries[:_ZIP_TREE_MAX_ENTRIES]:
        is_dir = path.endswith("/")
        parts = path.rstrip("/").split("/")
        indent = "  " * (len(parts) - 1)
        if is_dir:
            lines.append(f"{indent}{parts[-1]}/")
        else:
            kb = round(file_sizes[path] / 1024, 1)
            lines.append(f"{indent}{parts[-1]} ({kb} KB)")
    if len(entries) > _ZIP_TREE_MAX_ENTRIES:
        lines.append(f"... (+{len(entries) - _ZIP_TREE_MAX_ENTRIES} öğe daha)")
    return "\n".join(lines)


_ZIP_DOC_EXTRACTORS = (
    (".pdf", extract_pdf_text),
    (".docx", extract_docx_text),
    (".pptx", extract_pptx_text),
    (".xlsx", extract_xlsx_text),
    (".xlsm", extract_xlsx_text),
)


def _extract_zip_stream_text(zf: zipfile.ZipFile, info: zipfile.ZipInfo, name: str, max_text_bytes: int) -> str | None:
    with zf.open(info) as stream:
        file_raw = stream.read(max(1024, max_text_bytes))
    if b"\x00" in file_raw[:_ZIP_BINARY_SNIFF_BYTES]:
        return None
    if name.endswith(".tsv"):
        return extract_csv_text(file_raw, delimiter="\t")
    if name.endswith(".csv"):
        return extract_csv_text(file_raw)
    return _decode_bytes(file_raw)


def _extract_zip_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, max_text_bytes: int) -> str | None:
    name = info.filename.lower()
    if info.is_dir() or any(name.endswith(ext) for ext in _ZIP_SKIP_EXTS):
        return None
    try:
        doc_fn = next((fn for ext, fn in _ZIP_DOC_EXTRACTORS if name.endswith(ext)), None)
        content = doc_fn(zf.read(info.filename)) if doc_fn is not None else _extract_zip_stream_text(zf, info, name, max_text_bytes)
        if not content or not content.strip():
            return None
        return f"=== {info.filename} ===\n{content.strip()}"
    except _ZIP_RECOVERABLE_ERRORS as exc:
        log.debug("Recoverable error skipped in loop: %s", exc)
        return None


def extract_zip_text(raw: bytes) -> str:
    """Extract a directory tree plus streaming-bounded text from readable files inside a ZIP archive."""
    try:
        inspect_zip(raw)  # SEC-07: bombs, zip-slip, links and deep nesting stop here
    except UnsafeArchive as exc:
        raise UnsupportedFileError(f"Güvensiz arşiv reddedildi: {exc}") from exc
    parts: list[str] = []
    tree_text = ""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            infos = zf.infolist()
            tree_text = _build_zip_tree(infos)
            budget = max(2000, _ZIP_MAX_TOTAL_CHARS - len(tree_text) - 2)
            used = 0
            for info in infos:
                remaining = budget - used
                if remaining <= 0:
                    parts.append(f"[... ZIP metin bütçesi ({_ZIP_MAX_TOTAL_CHARS} karakter) dolduğu için kalan dosyalar atlandı ...]")
                    break
                entry = _extract_zip_member(zf, info, max_text_bytes=remaining * 4)
                if not entry:
                    continue
                if len(entry) > remaining:
                    parts.append(entry[:remaining] + "\n[... kısaltıldı ...]")
                    used = budget
                    break
                parts.append(entry)
                used += len(entry) + 2
    except zipfile.BadZipFile as exc:
        raise UnsupportedFileError(f"Geçersiz ZIP dosyası: {exc}") from exc
    if not parts:
        raise UnsupportedFileError("ZIP içinde okunabilir metin bulunamadı.")
    return f"{tree_text}\n\n" + "\n\n".join(parts)


def extract_text(filename: str, raw: bytes) -> str:
    """Return the text of a PDF, DOCX, PPTX, XLSX, CSV, TSV, TXT, Markdown or ZIP file; raise UnsupportedFileError otherwise."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(raw)
    if name.endswith(".docx"):
        return extract_docx_text(raw)
    if name.endswith(".pptx"):
        return extract_pptx_text(raw)
    if name.endswith((".xlsx", ".xlsm")):
        return extract_xlsx_text(raw)
    if name.endswith(".tsv"):
        return extract_csv_text(raw, delimiter="\t")
    if name.endswith(".csv"):
        return extract_csv_text(raw)
    if name.endswith((".txt", ".md")):
        return _decode_bytes(raw)
    if name.endswith(".zip"):
        return extract_zip_text(raw)
    raise UnsupportedFileError(filename)


extract_text_from_bytes = extract_text
