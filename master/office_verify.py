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
    return found[:8]


def _page_problems(path: Path, out_dir: Path) -> list[str]:
    import pymupdf

    pdf = _convert(path, "pdf", out_dir)
    if pdf is None:
        return ["LibreOffice dosyayı açamadı"]
    with pymupdf.open(pdf) as doc:
        if doc.page_count == 0:
            return ["belge boş"]
        found = []
        for number, page in enumerate(doc, start=1):
            outside = any(b[2] > page.rect.width + 2 or b[3] > page.rect.height + 2 or b[0] < -2 for b in page.get_text("blocks"))
            if outside:
                found.append(f"{number}. sayfada/slaytta yazı sınırın dışına taşıyor")
    return found[:8]


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
    if fmt not in ("xlsx", "docx", "pptx"):
        return result
    problems = await asyncio.to_thread(check, mms.media_dir() / str(result.get("url", "")).rsplit("/", 1)[-1])
    if problems is None:
        return result
    note = "LibreOffice doğrulaması: sorun bulunmadı." if not problems else "LibreOffice doğrulaması SORUN buldu: " + "; ".join(problems[:4])
    return {**result, "summary": f"{result.get('summary') or ''}\n\n> {note}".strip()}
