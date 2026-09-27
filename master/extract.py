"""Plain-text extraction for uploaded documents (requirements documents and chat attachments)."""

import io

from docx import Document
from pypdf import PdfReader

REQUIREMENT_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")


class UnsupportedFileError(ValueError):
    pass


def extract_pdf_text(raw: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(raw: bytes) -> str:
    doc = Document(io.BytesIO(raw))
    parts = [p.text for p in doc.paragraphs]
    # Requirements documents often keep details in tables; paragraphs alone would lose them.
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def extract_text(filename: str, raw: bytes) -> str:
    """Return the text of a PDF, DOCX, TXT or Markdown file; raise UnsupportedFileError otherwise."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(raw)
    if name.endswith(".docx"):
        return extract_docx_text(raw)
    if name.endswith((".txt", ".md")):
        return raw.decode("utf-8", errors="replace")
    raise UnsupportedFileError(filename)
