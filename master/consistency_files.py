"""The four deliverables of a consistency report, their independent readers and their PNG renderings."""

from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

import pymupdf
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

import consistency
import ligatures
import office_verify
from consistency import AVERAGE, LARGEST, SUBTOTAL, SUMMARY, TOTAL, VAT, Report
from prompt_loader import load_prompt

NAMES = {"excel": "hesap.xlsx", "sunum": "sunum.pptx", "pdf": "rapor.pdf", "web": "index.html"}
_MONEY_FORMAT = "#,##0.00"


def _workbook(report: Report, path: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Hesap"
    sheet.append(["Kalem", "Adet", "Birim fiyat", "Tutar"])
    for row, item in enumerate(report.items, 2):
        sheet.append([item.name, float(item.quantity), float(item.price), f"=ROUND(B{row}*C{row},2)"])
    last = len(report.items) + 1
    span = f"D2:D{last}"
    formulas = {SUBTOTAL: f"=SUM({span})", VAT: f"=ROUND(D{last + 2}*{report.vat}/100,2)", TOTAL: f"=D{last + 2}+D{last + 3}", AVERAGE: f"=ROUND(AVERAGE({span}),2)", LARGEST: f"=MAX({span})"}
    sheet.append([])
    for name, formula in formulas.items():
        sheet.append([name, None, None, formula])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = _MONEY_FORMAT
    sheet.column_dimensions["A"].width = max(28, max(len(item.name) for item in report.items) + 6)
    for letter in "BCD":
        sheet.column_dimensions[letter].width = 16
    book.save(path)


def _slides(report: Report, values: dict[str, Decimal], path: Path) -> None:
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    slide.shapes.title.text = report.title
    data = CategoryChartData(number_format=_MONEY_FORMAT)
    data.categories = [item.name for item in report.items]
    data.add_series("Tutar", [float(values[item.name]) for item in report.items])
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.7), Inches(7), Inches(5.2), data).chart
    chart.has_legend = False
    chart.plots[0].has_data_labels = True
    rows = [("Kalem", "Tutar (TL)")] + [(name, consistency.turkish(values[name])) for name in (*(item.name for item in report.items), *SUMMARY)]
    table = slide.shapes.add_table(len(rows), 2, Inches(7.9), Inches(1.7), Inches(4.9), Inches(0.36 * len(rows))).table
    for number, row in enumerate(rows):
        for column, text in enumerate(row):
            cell = table.cell(number, column)
            cell.text = text
            cell.text_frame.paragraphs[0].font.size = Pt(14)
    deck.save(path)


def _pdf(report: Report, values: dict[str, Decimal], path: Path) -> None:
    rows = "".join(f"<tr><td>{html.escape(item.name)}</td><td>{item.quantity}</td><td>{consistency.turkish(item.price)}</td><td>{consistency.turkish(values[item.name])}</td></tr>" for item in report.items)
    summary = "".join(f"<p>{name}: <b>{consistency.turkish(values[name])}</b> TL</p>" for name in SUMMARY)
    body = f"<h1>{html.escape(report.title)}</h1><table border='1'><tr><th>Kalem</th><th>Adet</th><th>Birim fiyat</th><th>Tutar</th></tr>{rows}</table>{summary}"
    story = pymupdf.Story(html=body, user_css="body{font-family:sans-serif;font-size:11px} td,th{padding:3px 8px;white-space:nowrap}")
    writer = pymupdf.DocumentWriter(str(path))
    more = 1
    while more:
        device = writer.begin_page(pymupdf.paper_rect("a4"))
        more, _filled = story.place(pymupdf.Rect(40, 40, 555, 800))
        story.draw(device)
        writer.end_page()
    writer.close()


def _web(report: Report, path: Path) -> None:
    data = {"title": report.title, "vat": report.vat, "items": [{"name": i.name, "quantity": str(i.quantity), "price": str(i.price)} for i in report.items]}
    path.write_text(load_prompt("consistency_dashboard.html.txt").replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")).replace("__TITLE__", html.escape(report.title)), encoding="utf-8")


def build(report: Report, values: dict[str, Decimal], folder: Path) -> dict[str, Path]:
    files = {kind: folder / name for kind, name in NAMES.items()}
    _workbook(report, files["excel"])
    _slides(report, values, files["sunum"])
    _pdf(report, values, files["pdf"])
    _web(report, files["web"])
    return files


def _read_excel(path: Path) -> dict[str, Decimal]:
    """The values LibreOffice computed from the formulas, not anything the platform wrote."""
    if not office_verify.soffice():
        return {}
    with tempfile.TemporaryDirectory(prefix="cm6453_cons_", ignore_cleanup_errors=True) as tmp:
        recalculated = office_verify._convert(path, "xlsx", Path(tmp))
        if recalculated is None:
            return {}
        book = load_workbook(recalculated, data_only=True)
        found = {str(row[0].value): Decimal(str(row[3].value)) for row in book.active.iter_rows(min_row=2) if row[0].value and isinstance(row[3].value, int | float)}
        book.close()
    return found


def _read_slides(path: Path) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """(the table, the chart) of the slide, read separately: either one can be wrong on its own."""
    table: dict[str, Decimal] = {}
    chart: dict[str, Decimal] = {}
    for shape in Presentation(path).slides[0].shapes:
        if shape.has_table:
            table = {row.cells[0].text: consistency.read_turkish(row.cells[1].text) for row in list(shape.table.rows)[1:]}
        if shape.has_chart:
            plot = shape.chart.plots[0]
            chart = {str(c): Decimal(str(v)) for c, v in zip(plot.categories, plot.series[0].values, strict=True)}
    return table, chart


def _read_pdf(report: Report, path: Path) -> dict[str, Decimal]:
    """The table and totals as the PDF's own text gives them; names may wrap over lines."""
    with pymupdf.open(path) as document:
        flat = ligatures.split(" ".join(" ".join(page.get_text().split()) for page in document))
    found: dict[str, Decimal] = {}
    for item in report.items:
        name = r"\s*".join(re.escape(word) for word in item.name.split())
        row = re.search(rf"(?<!\S){name}\s+{re.escape(str(item.quantity))}\s+[\d.,]+\s+([\d.]+,\d{{2}})", flat)
        if row:
            found[item.name] = consistency.read_turkish(row.group(1))
    for name in SUMMARY:
        total = re.search(rf"{r'\s*'.join(map(re.escape, name.split()))}:\s*([\d.]+,\d{{2}})", flat)
        if total:
            found[name] = consistency.read_turkish(total.group(1))
    return found


def _read_web(path: Path) -> dict[str, Decimal]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        try:
            page = browser.new_page()
            page.goto(path.resolve().as_uri())
            page.wait_for_selector("[data-figure]")
            pairs = page.eval_on_selector_all("[data-figure]", "nodes => nodes.map(n => [n.getAttribute('data-figure'), n.textContent])")
        finally:
            browser.close()
    return {name: consistency.read_turkish(text) for name, text in pairs}


def read_all(report: Report, files: dict[str, Path]) -> dict[str, dict[str, Decimal]]:
    table, chart = _read_slides(files["sunum"])
    return {"excel": _read_excel(files["excel"]), "sunum": table, consistency.CHART: chart, "pdf": _read_pdf(report, files["pdf"]), "web": _read_web(files["web"])}


def render_pngs(files: dict[str, Path], folder: Path) -> list[Path]:
    """A picture of every deliverable as a reader would see it (Office files through LibreOffice)."""
    from playwright.sync_api import sync_playwright

    folder.mkdir(parents=True, exist_ok=True)
    made = []
    with tempfile.TemporaryDirectory(prefix="cm6453_png_", ignore_cleanup_errors=True) as tmp:
        for kind in ("excel", "sunum", "pdf"):
            source = files[kind] if kind == "pdf" else (office_verify._convert(files[kind], "pdf", Path(tmp)) if office_verify.soffice() else None)
            if source is None:
                continue
            if kind != "pdf":
                shutil.copyfile(source, Path(tmp) / f"{kind}-shown.pdf")
                source = Path(tmp) / f"{kind}-shown.pdf"
            with pymupdf.open(source) as document:
                document[0].get_pixmap(dpi=90).save(folder / f"{kind}.png")
            made.append(folder / f"{kind}.png")
    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        try:
            page = browser.new_page(viewport={"width": 900, "height": 700})
            page.goto(files["web"].resolve().as_uri())
            page.screenshot(path=str(folder / "web.png"), full_page=True)
            made.append(folder / "web.png")
        finally:
            browser.close()
    return made
