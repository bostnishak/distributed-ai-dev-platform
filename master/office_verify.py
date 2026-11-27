"""Open every delivered Office file in headless LibreOffice: formulas are recalculated, error cells and broken files reported."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import zipfile
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

import xlsx_checks
from process_utils import run_process

_log = logging.getLogger(__name__)
_BINARIES = (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe", "/usr/bin/soffice")
_ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:")


def soffice() -> str:
    return os.environ.get("SOFFICE_PATH") or next((p for p in _BINARIES if Path(p).is_file()), "")


def _convert(path: Path, target: str, out_dir: Path) -> Path | None:
    profile = (out_dir / "profile").as_uri()  # own profile: never collides with a LibreOffice the user has open
    run_process([soffice(), f"-env:UserInstallation={profile}", "--headless", "--norestore", "--convert-to", target, "--outdir", str(out_dir), str(path)], timeout_s=90)
    result = out_dir / f"{path.stem}.{target}"
    return result if result.is_file() else None


def _workbook_errors(path: Path, out_dir: Path) -> list[str]:
    (out_dir / "x").mkdir()
    recalculated = _convert(path, "xlsx", out_dir / "x")
    if recalculated is None:
        return ["LibreOffice dosyayı açamadı"]
    book = load_workbook(recalculated, data_only=True, read_only=True)
    try:
        found = [f"{sheet.title}!{cell.coordinate}: {cell.value}" for sheet in book for row in sheet.iter_rows() for cell in row
                 if isinstance(cell.value, str) and cell.value.startswith(_ERRORS)]
    finally:
        book.close()
    return (xlsx_checks.problems(path) + found)[:8]


def proof_page(page: Any, number: int, slide: bool) -> list[str]:
    """What a reader would see wrong on one rendered page or slide."""
    found = []
    blocks = [block for block in page.get_text("blocks") if block[4].strip()]
    if not blocks and not page.get_images() and not page.get_drawings():
        return [f"{number}. sayfa boş"]
    if any(block[2] > page.rect.width + 2 or block[3] > page.rect.height + 2 or block[0] < -2 for block in blocks):
        found.append(f"{number}. sayfada/slaytta yazı sınırın dışına taşıyor")
    lines = [line["bbox"] for block in page.get_text("dict")["blocks"] for line in block.get("lines", []) if "".join(s["text"] for s in line["spans"]).strip()]
    for i, first in enumerate(lines):
        for second in lines[i + 1 :]:
            width = min(first[2], second[2]) - max(first[0], second[0])
            height = min(first[3], second[3]) - max(first[1], second[1])
            smaller = min((first[2] - first[0]) * (first[3] - first[1]), (second[2] - second[0]) * (second[3] - second[1]))
            if width > 0 and height > 0 and width * height > 0.35 * smaller:
                found.append(f"{number}. sayfada/slaytta yazılar üst üste biniyor")
                break
        else:
            continue
        break
    floor = 14 if slide else 6
    sizes = [span["size"] for block in page.get_text("dict")["blocks"] for line in block.get("lines", []) for span in line["spans"] if len(span["text"].strip()) > 3]
    if sizes and min(sizes) < floor - 0.5:  # a renderer reports 14 pt as 13.9
        found.append(f"{number}. sayfada/slaytta {min(sizes):.0f} punto yazı var (okunmaz)")
    return found


def _body_lines(page: Any) -> list[tuple[float, str, float, bool]]:
    """(bottom, text, size, bold) of the lines between the running header and footer, top to bottom."""
    height = page.rect.height
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text and height * 0.04 < line["bbox"][1] and line["bbox"][3] < height * 0.945:
                first = line["spans"][0]
                out.append((line["bbox"][3], text, first["size"], bool(first["flags"] & 16) or "bold" in first["font"].lower()))
    return sorted(out)


def flow_problems(doc: Any) -> list[str]:
    """A heading left alone at the foot of a page, and a last page that carries nothing but its header and footer."""
    found = []
    pages = [_body_lines(page) for page in doc]
    sizes = sorted(size for lines in pages for _b, _t, size, _bold in lines)
    body = sizes[len(sizes) // 2] if sizes else 0.0
    for number, (page, lines) in enumerate(zip(doc, pages, strict=True), start=1):
        if number == len(pages):
            if number > 1 and not lines and not page.get_images():
                found.append(f"{number}. (son) sayfa boş: yalnız üst/alt bilgi var")
            continue
        if not lines or any(image["bbox"][3] > lines[-1][0] for image in page.get_image_info()):
            continue
        bottom, text, size, bold = lines[-1]
        if bottom > page.rect.height * 0.6 and len(text) < 90 and (size >= body + 1.4 or (bold and size > body + 0.4)) and not text.endswith((".", ":", ",")):
            found.append(f"{number}. sayfanın sonunda başlık tek kalmış: {text[:40]}")
    return found


def _page_problems(path: Path, out_dir: Path) -> list[str]:
    import pymupdf

    pdf = _convert(path, "pdf", out_dir)
    if pdf is None:
        return ["LibreOffice dosyayı açamadı"]
    with pymupdf.open(pdf) as doc:
        if doc.page_count == 0:
            return ["belge boş"]
        slide = path.suffix.lower() == ".pptx"
        found = [problem for number, page in enumerate(doc, start=1) for problem in proof_page(page, number, slide)]
        return (found + ([] if slide else flow_problems(doc)))[:8]


def check_pdf(path: Path) -> list[str]:
    """The same page-by-page proofing for a delivered PDF."""
    import pymupdf

    with pymupdf.open(path) as doc:
        return ([problem for number, page in enumerate(doc, start=1) for problem in proof_page(page, number, False)] + flow_problems(doc))[:8]


def check(path: Path) -> list[str] | None:
    """Problems found; None when LibreOffice is not installed or the format is not an Office document."""
    suffix = path.suffix.lower()
    if not soffice() or suffix not in (".xlsx", ".docx", ".pptx") or not path.is_file():
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="cm6453_off_", ignore_cleanup_errors=True) as tmp:
            return (_workbook_errors if suffix == ".xlsx" else _page_problems)(path, Path(tmp))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile, InvalidFileException) as exc:
        _log.warning("Office doğrulaması yapılamadı: %s", exc)
        return None


async def verified(producing: Awaitable[dict[str, Any]], fmt: str) -> dict[str, Any]:
    """The document result with the verification outcome added to its summary."""
    import multimodal_studio as mms

    result = await producing
    if fmt not in ("xlsx", "docx", "pptx", "pdf"):
        return result
    path = mms.media_dir() / str(result.get("url", "")).rsplit("/", 1)[-1]
    if fmt == "pdf":
        if path.suffix.lower() != ".pdf" or not path.is_file():
            return result
        import artifact_check  # imports this module

        problems = await asyncio.to_thread(artifact_check.problems, path) + await asyncio.to_thread(check_pdf, path)  # a second, independent reader
    else:
        problems = await asyncio.to_thread(check, path)
    if problems is None:
        return result
    name = "Sayfa denetimi" if fmt == "pdf" else "LibreOffice doğrulaması"
    note = f"{name}: sorun bulunmadı." if not problems else f"{name} SORUN buldu: " + "; ".join(problems[:4])
    return {**result, "summary": f"{result.get('summary') or ''}\n\n> {note}".strip()}
