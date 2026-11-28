"""Torture of what leaves the application: exported CSV, Excel and PDF files, and dates across time zones."""

from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path
from typing import Any

import torture_probe as probe

Outcome = tuple["bool | None", str]
_RECORD = "İstanbul Iğdır şçöü"
_EXPORT = "button:visible, a:visible, input[type=button]:visible"
_EXPORT_WORDS = re.compile(r"csv|excel|xlsx|pdf|dışa aktar|indir|export|download", re.IGNORECASE)
_LEAP = "2028-02-29"
_SHIFTED = re.compile(r"\b28[./ -]0?2[./ -]2028\b|\b2028-02-28\b|\b0?2/28/2028\b|28 Şubat 2028|February 28, 2028")


def _text_of(data: bytes, name: str) -> str:
    """The text a reader of the file would see; ValueError when the file cannot be opened."""
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(data), read_only=True)
        return " ".join(str(cell) for sheet in book for row in sheet.iter_rows(values_only=True) for cell in row if cell is not None)
    if suffix == ".pdf":
        import pymupdf

        with pymupdf.open(stream=data, filetype="pdf") as document:
            return " ".join(page.get_text() for page in document)
    return data.decode("utf-8-sig")


def exports(session: probe.Session, _url: str) -> Outcome:
    """Every export button's file must open and carry a Turkish record exactly; a CSV needs its byte order mark for Excel."""
    page = session.page
    if not probe.usable(page):
        return None, "kayıt ekleyen alan yok"
    probe.add(page, _RECORD)
    buttons = [b for b in page.locator(_EXPORT).all() if _EXPORT_WORDS.search((b.inner_text() or b.get_attribute("value") or "") + " " + (b.get_attribute("download") or ""))]
    if not buttons:
        return None, "dışa aktarma düğmesi yok"
    problems, checked = [], []
    for button in buttons[:3]:
        label = (button.inner_text() or "dışa aktar").strip()[:30]
        try:
            with page.expect_download(timeout=6000) as waiting:
                button.click()
            download = waiting.value
            data = Path(download.path()).read_bytes()
            name = download.suggested_filename
            if _RECORD not in _text_of(data, name):
                problems.append(f"'{label}' dosyasında Türkçe kayıt bozuk ya da yok ({name})")
            elif name.lower().endswith(".csv") and not data.startswith(b"\xef\xbb\xbf"):
                problems.append(f"'{label}' CSV'sinde BOM yok: Excel Türkçe harfleri bozuk açar")
            checked.append(name)
        except UnicodeDecodeError:
            problems.append(f"'{label}' dosyası UTF-8 değil")
        except Exception as exc:  # noqa: BLE001, RUF100  # no download, or a file its reader cannot open
            problems.append(f"'{label}' açılabilir bir dosya vermedi ({type(exc).__name__})")
    return not problems, "; ".join(problems) if problems else f"doğrulanan dosyalar: {', '.join(checked)}"


def timezones(session: probe.Session, url: str) -> Outcome:
    """A date typed by a user west of Greenwich must not appear one day earlier."""
    if not probe.usable(session.page) or not session.page.locator("input[type=date]:visible").count():
        return None, "tarih alanı yok"
    context = session.context.browser.new_context(timezone_id="America/Los_Angeles")
    try:
        page = context.new_page()
        page.goto(url, timeout=20000)
        probe.add(page, "artık-yıl kaydı")
        body = page.inner_text("body")
        shifted = _SHIFTED.search(body)
        return not shifted, "" if not shifted else f"{_LEAP} girildi, batı saat diliminde '{shifted.group(0)}' gösteriliyor"
    finally:
        with contextlib.suppress(Exception):
            context.close()


CHECKS: dict[str, Any] = {"dışa aktarılan dosyalar": exports, "saat dilimi ve tarih": timezones}
