"""Plain-text extraction for uploaded documents (requirements documents and chat attachments).

Preserves Turkish characters cleanly (UTF-8-SIG, UTF-8, Windows-1254/CP1254, ISO-8859-9) and
uses PyMuPDF first for PDF text extraction with pypdf fallback.
"""

import csv
import io
import zipfile

import pymupdf as fitz
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from safe_archive import UnsafeArchive, inspect_zip

REQUIREMENT_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".zip")


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
        pages = [page.get_text("text") or "" for page in doc]
        doc.close()
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)
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


def extract_csv_text(raw: bytes) -> str:
    text = _decode_bytes(raw)
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delim = ";" if first_line.count(";") > first_line.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)


def extract_xlsx_text(raw: bytes) -> str:
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    parts = []
    for sheet in workbook.worksheets:
        parts.append(f"--- Sayfa: {sheet.title} ---")
        for row in sheet.iter_rows(values_only=True):
            if any(v is not None for v in row):
                parts.append(" | ".join("" if v is None else str(v) for v in row))
    return "\n".join(parts)


def extract_zip_text(raw: bytes) -> str:
    """Extract and concatenate text from all readable files inside a ZIP archive."""
    parts = []
    try:
        inspect_zip(raw)  # SEC-07: bombs, zip-slip, links and deep nesting stop here
    except UnsafeArchive as exc:
        raise UnsupportedFileError(f"Güvensiz arşiv reddedildi: {exc}") from exc
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.lower()
                if any(name.endswith(ext) for ext in (
                    ".pyc", ".pyo", ".class", ".exe", ".dll", ".so", ".png",
                    ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".ttf",
                )):
                    continue
                try:
                    file_raw = zf.read(info.filename)
                    if name.endswith(".pdf"):
                        content = extract_pdf_text(file_raw)
                    elif name.endswith(".docx"):
                        content = extract_docx_text(file_raw)
                    elif name.endswith((".xlsx", ".xlsm")):
                        content = extract_xlsx_text(file_raw)
                    elif name.endswith((".csv", ".tsv")):
                        content = extract_csv_text(file_raw)
                    else:
                        content = _decode_bytes(file_raw)
                    if content.strip():
                        parts.append(f"=== {info.filename} ===\n{content.strip()}")
                except Exception as _exc:
                    import logging

                    logging.getLogger(__name__).debug("Recoverable error skipped in loop: %s", _exc)
                    continue
    except zipfile.BadZipFile as exc:
        raise UnsupportedFileError(f"Geçersiz ZIP dosyası: {exc}") from exc
    if not parts:
        raise UnsupportedFileError("ZIP içinde okunabilir metin bulunamadı.")
    return "\n\n".join(parts)


def extract_text(filename: str, raw: bytes) -> str:
    """Return the text of a PDF, DOCX, XLSX, CSV, TXT, Markdown or ZIP file; raise UnsupportedFileError otherwise."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(raw)
    if name.endswith(".docx"):
        return extract_docx_text(raw)
    if name.endswith((".xlsx", ".xlsm")):
        return extract_xlsx_text(raw)
    if name.endswith((".csv", ".tsv")):
        return extract_csv_text(raw)
    if name.endswith((".txt", ".md")):
        return _decode_bytes(raw)
    if name.endswith(".zip"):
        return extract_zip_text(raw)
    raise UnsupportedFileError(filename)
