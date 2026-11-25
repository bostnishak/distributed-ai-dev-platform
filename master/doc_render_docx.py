"""Render a validated block spec (doc_spec.parse) as a clean Word document."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import doc_tables
from document_chart import render_bar_chart_png, to_number

INK, MUTED, ACCENT = RGBColor(0x1E, 0x29, 0x3B), RGBColor(0x64, 0x74, 0x8B), "1E293B"


def _shade(cell: Any, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def _borders(table: Any, color: str = "CBD5E1") -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def _run(paragraph: Any, text: str, **style: Any) -> None:
    """Add a run; style keys: size, bold, italic, color."""
    r = paragraph.add_run(text)
    r.font.name, r.font.size = "Calibri", Pt(style.get("size", 10.5))
    r.font.bold, r.font.italic = style.get("bold", False), style.get("italic", False)
    if style.get("color") is not None:
        r.font.color.rgb = style["color"]


def _page_number(paragraph: Any) -> None:
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        run = paragraph.add_run()
        run.font.size = Pt(8)
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


def _title(doc: Any, spec: dict[str, Any]) -> None:
    banner = doc.add_table(rows=1, cols=1)
    cell = banner.rows[0].cells[0]
    _shade(cell, ACCENT)
    cell.paragraphs[0].paragraph_format.space_before = Pt(8)
    _run(cell.paragraphs[0], spec["title"], size=17, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    sub = cell.add_paragraph()
    sub.paragraph_format.space_after = Pt(8)
    _run(sub, " · ".join(x for x in (spec["subtitle"], datetime.now(UTC).strftime("%d.%m.%Y")) if x), size=9, color=RGBColor(0xCB, 0xD5, 0xE1))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _table(doc: Any, block: dict[str, Any]) -> None:
    headers, rows = block["headers"], block["rows"]
    if block.get("caption"):
        _run(doc.add_paragraph(), block["caption"], size=9.5, italic=True, color=MUTED)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(table)
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        _shade(cell, "4F46E5")
        _run(cell.paragraphs[0], h, size=10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            numeric = to_number(val) is not None
            _run(cells[i].paragraphs[0], val, size=10, bold=doc_tables.is_total_row(row))
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT if numeric else WD_ALIGN_PARAGRAPH.LEFT
            if ri % 2:
                _shade(cells[i], "F1F5F9")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _signature(doc: Any, parties: list[str]) -> None:
    table = doc.add_table(rows=1, cols=len(parties))
    for i, party in enumerate(parties):
        p = table.rows[0].cells[i].paragraphs[0]
        p.paragraph_format.space_before = Pt(36)
        _run(p, "______________________\n", size=10)
        _run(p, party + "\n", size=10, bold=True)
        _run(p, "İmza / Tarih", size=9, color=MUTED)


def _chart(doc: Any, block: dict[str, Any], fonts: tuple[str | None, str | None]) -> None:
    png = render_bar_chart_png(["", block["title"] or "Değer"], [[lab, v] for lab, v in zip(block["labels"], block["values"], strict=True)], block["title"], fonts)
    if png:
        doc.add_picture(BytesIO(png), width=Cm(15))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def build(out_path: Path, spec: dict[str, Any], fonts: tuple[str | None, str | None]) -> None:
    doc = Document()
    normal: Any = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10.5)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(footer, spec["title"][:60] + " · Sayfa ", size=8, color=MUTED)
    _page_number(footer)
    _title(doc, spec)
    for b in spec["blocks"]:
        kind = b["type"]
        if kind == "heading":
            h = doc.add_heading(level=b["level"])
            _run(h, b["text"], size=14 if b["level"] == 1 else 12, bold=True, color=INK)
        elif kind == "para":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(6)
            _run(p, b["text"])
        elif kind in ("numbered", "bullets"):
            for i, item in enumerate(b["items"], 1):
                p = doc.add_paragraph(style="List Bullet" if kind == "bullets" else None)
                p.paragraph_format.space_after = Pt(4)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                _run(p, item if kind == "bullets" or b.get("own_numbers") else f"{i}. {item}")
        elif kind == "table":
            _table(doc, b)
        elif kind == "signature":
            _signature(doc, b["parties"])
        elif kind == "chart":
            _chart(doc, b, fonts)
    doc.save(str(out_path))
