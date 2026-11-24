"""Universal Office & Document Deliverable Factory (.xlsx, .docx, .pptx, .pdf).

Builds real, rich, Unicode/Turkish-safe corporate deliverables with embedded TrueType fonts in PDF,
auto-sized wrapped columns & charts in Excel, styled headings/tables in Word, and OpenXML slides in PPTX.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pymupdf as fitz
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import multimodal_studio as mms
from prompt_loader import load_prompt

DOC_BUILD_RE = re.compile(
    r"((excel|\.xlsx)\s*(tablo\w*|dosya\w*|rapor\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*)|"
    r"(word|\.docx)\s*(dosya\w*|belge\w*|rapor\w*|sözleşme\w*|dilekçe\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|ver\w*)|"
    r"(sunum\w*|powerpoint|slayt\w*|\.pptx)\s*(dosya\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*)|"
    r"(pdf|\.pdf)\s*(rapor\w*|dosya\w*|belge\w*|özet\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*))",
    re.IGNORECASE,
)

_UNICODE_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/calibri.ttf"),
    Path("C:/Windows/Fonts/tahoma.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)

_UNICODE_BOLD_CANDIDATES = (
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/calibrib.ttf"),
    Path("C:/Windows/Fonts/tahomabd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
)

DOC_ACTION_RE = re.compile(
    r"(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|uret\w*|çıkar\w*|cikar\w*|ver\w*|yaz\w*|indir\w*|dışa\s+aktar)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _DocContent:
    title: str
    summary: str
    sections: list[dict[str, Any]]
    headers: list[str]
    rows: list[list[Any]]


def _unpack_doc_content(args: tuple[Any, ...], kwargs: dict[str, Any]) -> _DocContent:
    if len(args) == 1 and isinstance(args[0], _DocContent):
        return args[0]
    title = str(args[0] if len(args) > 0 else kwargs.get("title", ""))
    summary = str(args[1] if len(args) > 1 else kwargs.get("summary", ""))
    sections = list(args[2] if len(args) > 2 else kwargs.get("sections", []))
    headers = list(args[3] if len(args) > 3 else kwargs.get("headers", []))
    rows = list(args[4] if len(args) > 4 else kwargs.get("rows", []))
    return _DocContent(title=title, summary=summary, sections=sections, headers=headers, rows=rows)


def _find_unicode_fonts() -> tuple[str | None, str | None]:
    reg = next((str(p) for p in _UNICODE_FONT_CANDIDATES if p.is_file()), None)
    bold = next((str(p) for p in _UNICODE_BOLD_CANDIDATES if p.is_file()), reg)
    return reg, bold


def _detect_requested_language(prompt: str) -> str:
    low = (prompt or "").lower()
    if any(k in low for k in ("ingilizce", "in english", "english report", "english pdf", "english excel")):
        return "English"
    if any(k in low for k in ("almanca", "auf deutsch", "german")):
        return "German"
    return "Türkçe"


def detect_document_request(prompt: str, has_file: bool) -> str | None:
    """Return 'xlsx' | 'docx' | 'pptx' | 'pdf' if the user is asking for a downloadable document file."""
    _ = has_file
    lower = prompt.lower()
    if any(k in lower for k in ("balonla", "teknik çizim", "web sitesi", "e-ticaret", "oyun", "exe")):
        return None
    has_doc_trigger = bool(DOC_BUILD_RE.search(lower)) or (
        bool(DOC_ACTION_RE.search(lower))
        and any(k in lower for k in ("word dosya", "word belge", ".docx", "excel dosya", "excel tablo", ".xlsx", "pdf dosya", "pdf rapor", ".pdf"))
    )
    if not has_doc_trigger:
        return None
    if "excel" in lower or ".xlsx" in lower:
        return "xlsx"
    if "word" in lower or ".docx" in lower:
        return "docx"
    if "sunum" in lower or "powerpoint" in lower or "slayt" in lower or ".pptx" in lower:
        return "pptx"
    if "pdf" in lower:
        return "pdf"
    return None


async def generate_document_deliverable(prompt: str, fmt: str, context_text: str = "") -> dict[str, Any]:
    """Use local LLM to structure content and compile a real .xlsx, .docx, .pptx, or .pdf file."""
    model = await mms.pick_best_model("deep")
    file_id = f"doc-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_dir = mms.media_dir()
    target_lang = _detect_requested_language(prompt)
    schema_prompt = load_prompt("b3_document_factory_schema.txt").replace("{target_lang}", target_lang)

    user_msg = prompt
    if context_text:
        user_msg += f"\n\nKaynak veri (sayıları buradan al, uydurma):\n{context_text[:10000]}"

    spec: dict[str, Any] = {
        "title": f"Kurumsal Rapor: {prompt[:60]}",
        "summary": prompt,
        "sections": [
            {"heading": "1. Yönetici Özeti ve Kapsam", "content": prompt},
            {"heading": "2. Teknik ve Operasyonel Değerlendirme", "content": "Veriler yerel motor tarafından yapılandırılmıştır."},
        ],
        "table_headers": ["No", "Kalem / Başlık", "Kategori", "Durum", "Değer"],
        "table_rows": [
            ["01", "Planlama ve Analiz", "Hazırlık", "Tamamlandı", 100],
            ["02", "Uygulama ve Doğrulama", "Operasyon", "Aktif", 250],
        ],
    }

    try:
        import gateway

        res = await gateway.default_client.chat(
            [
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            profile="factual",
            num_predict=3500,
            timeout_s=120.0,
            feature="document_factory",
            max_retries=0,
        )
        m = re.search(r"\{[\s\S]*\}", res.content)
        if m:
            cleaned_json = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, dict) and parsed.get("title"):
                spec.update(parsed)
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as _exc:
        import logging

        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", _exc)

    title = str(spec.get("title") or "Kurumsal Rapor")
    summary = str(spec.get("summary") or "")
    sections = spec.get("sections") or []
    headers = [str(h) for h in (spec.get("table_headers") or ["Kalem", "Açıklama", "Değer"])]
    rows = spec.get("table_rows") or []

    if fmt == "xlsx":
        out_path = out_dir / f"{file_id}.xlsx"
        _build_xlsx(out_path, title, summary, sections, headers, rows)
    elif fmt == "docx":
        out_path = out_dir / f"{file_id}.docx"
        _build_docx(out_path, title, summary, sections, headers, rows)
    elif fmt == "pptx":
        import deep_research as dr

        out_path = out_dir / f"{file_id}.pptx"
        slides = [
            {"title": str(s.get("heading") or "Bölüm"), "bullets": [b.strip() for b in str(s.get("content") or "").split(". ") if b.strip()]}
            for s in sections
            if isinstance(s, dict)
        ]
        if headers and rows:
            slides.append({
                "title": "Veri ve Özet Tablosu",
                "bullets": [" | ".join(str(c) for c in r[: len(headers)]) for r in rows[:8]],
            })
        dr.build_pptx_presentation(title=title, subtitle=summary[:180], slides=slides, out_path=out_path)
    else:
        out_path = out_dir / f"{file_id}.pdf"
        _build_pdf(out_path, title, summary, sections, headers, rows)

    return {
        "file_id": file_id,
        "format": fmt,
        "title": title,
        "summary": summary,
        "sections": sections,
        "table_headers": headers,
        "table_rows": rows,
        "model": model,
        "url": f"/api/assistant/media/{out_path.name}",
    }


def _xlsx_write_banner(ws: Any, content: _DocContent, border: Border) -> list[int]:
    navy = PatternFill("solid", fgColor="1E293B")
    accent = PatternFill("solid", fgColor="4F46E5")
    last_col = get_column_letter(max(3, len(content.headers)))
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].value = content.title
    ws["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws["A1"].fill = navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"].value = content.summary[:400]
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="334155")
    ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 28

    col_widths = [max(14, len(h) + 6) for h in content.headers]
    for ci, h in enumerate(content.headers, start=1):
        c = ws.cell(4, ci, h)
        c.font = Font(name="Calibri", bold=True, color="FFFFFF", size=10.5)
        c.fill = accent
        c.border = border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 26
    return col_widths


def _xlsx_write_data_rows(ws: Any, content: _DocContent, border: Border, col_widths: list[int]) -> set[int]:
    zebra = PatternFill("solid", fgColor="F8FAFC")
    numeric_cols: set[int] = set()
    for ri, rdata in enumerate(content.rows, start=5):
        for ci in range(1, len(content.headers) + 1):
            val = rdata[ci - 1] if ci - 1 < len(rdata) else ""
            if isinstance(val, (int, float)):
                numeric_cols.add(ci)
            c = ws.cell(ri, ci, val)
            c.font = Font(name="Calibri", size=10)
            c.border = border
            c.alignment = Alignment(vertical="center", wrap_text=True, horizontal="right" if isinstance(val, (int, float)) else "left")
            if isinstance(val, float):
                c.number_format = "#,##0.00"
            elif isinstance(val, int):
                c.number_format = "#,##0"
            if (ri - 4) % 2 == 0:
                c.fill = zebra
            col_widths[ci - 1] = min(48, max(col_widths[ci - 1], len(str(val)) + 4))
    return numeric_cols


def _xlsx_add_totals_and_chart(ws: Any, content: _DocContent, numeric_cols: set[int], border: Border) -> None:
    if not content.rows or not numeric_cols:
        return
    total_fill = PatternFill("solid", fgColor="E2E8F0")
    sum_r = 4 + len(content.rows) + 1
    avg_r = sum_r + 1
    ws.cell(sum_r, 1, "TOPLAM").font = Font(name="Calibri", bold=True)
    ws.cell(avg_r, 1, "ORTALAMA").font = Font(name="Calibri", bold=True)
    for ci in range(1, len(content.headers) + 1):
        ws.cell(sum_r, ci).fill = total_fill
        ws.cell(sum_r, ci).border = border
        ws.cell(avg_r, ci).border = border
    for ci in sorted(numeric_cols):
        col_let = get_column_letter(ci)
        sc = ws.cell(sum_r, ci, f"=SUM({col_let}5:{col_let}{sum_r - 1})")
        sc.font = Font(name="Calibri", bold=True, color="1E293B")
        sc.number_format = "#,##0.00"
        ac = ws.cell(avg_r, ci, f"=AVERAGE({col_let}5:{col_let}{sum_r - 1})")
        ac.font = Font(name="Calibri", italic=True, color="334155")
        ac.number_format = "#,##0.00"

    last_num_c = max(numeric_cols)
    if len(content.rows) >= 2 and last_num_c >= 2:
        chart = BarChart()
        chart.title = f"{content.headers[last_num_c - 1]} Dağılımı"
        chart.y_axis.title = content.headers[last_num_c - 1]
        data_ref = Reference(ws, min_col=last_num_c, min_row=4, max_row=4 + len(content.rows))
        cats_ref = Reference(ws, min_col=2 if len(content.headers) > 1 else 1, min_row=5, max_row=4 + len(content.rows))
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.width = 16
        chart.height = 9
        ws.add_chart(chart, f"A{avg_r + 2}")


def _xlsx_add_notes_sheet(wb: Workbook, content: _DocContent) -> None:
    if not content.sections:
        return
    ws2: Any = wb.create_sheet("Yönetici Özeti ve Notlar")
    ws2["A1"].value = content.title
    ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color="1E293B")
    r_cursor = 3
    for sec in content.sections:
        if not isinstance(sec, dict):
            continue
        ws2.cell(r_cursor, 1, str(sec.get("heading") or "")).font = Font(name="Calibri", bold=True, size=11)
        ws2.cell(r_cursor + 1, 1, str(sec.get("content") or "")).alignment = Alignment(wrap_text=True)
        r_cursor += 3
    ws2.column_dimensions["A"].width = 96


def _build_xlsx(out_path: Path, *args: Any, **kwargs: Any) -> None:
    content = _unpack_doc_content(args, kwargs)
    wb = Workbook()
    ws: Any = wb.active
    if ws is None:
        raise RuntimeError("Workbook active worksheet is unavailable")
    ws.title = "Veri ve Tablo"

    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    col_widths = _xlsx_write_banner(ws, content, border)
    numeric_cols = _xlsx_write_data_rows(ws, content, border, col_widths)
    _xlsx_add_totals_and_chart(ws, content, numeric_cols, border)

    for ci, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.freeze_panes = "A5"
    _xlsx_add_notes_sheet(wb, content)
    wb.save(str(out_path))


def _shade_docx_cell(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _style_docx_cell_runs(cell: Any, *, size_pt: float, bold: bool = False, rgb: RGBColor | None = None) -> None:
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.name = "Segoe UI"
            run.font.size = Pt(size_pt)
            if bold:
                run.bold = True
            if rgb is not None:
                run.font.color.rgb = rgb


def _docx_add_table(doc: Any, headers: list[str], rows: list[list[Any]]) -> None:
    doc.add_heading("Veri ve Özet Tablosu", level=1)
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        cell.text = h
        _shade_docx_cell(cell, "1E293B")
        _style_docx_cell_runs(cell, size_pt=9.5, bold=True, rgb=RGBColor(0xFF, 0xFF, 0xFF))
    for r_idx, rdata in enumerate(rows):
        rc = tbl.add_row().cells
        for i in range(len(headers)):
            rc[i].text = str(rdata[i]) if i < len(rdata) else ""
            if r_idx % 2 == 1:
                _shade_docx_cell(rc[i], "F8FAFC")
            _style_docx_cell_runs(rc[i], size_pt=9.0)


def _build_docx(out_path: Path, *args: Any, **kwargs: Any) -> None:
    content = _unpack_doc_content(args, kwargs)
    doc = Document()
    normal_style: Any = doc.styles["Normal"]
    normal_style.font.name = "Segoe UI"
    normal_style.font.size = Pt(10.5)

    h0 = doc.add_heading(content.title, level=0)
    for r in h0.runs:
        r.font.name = "Segoe UI"
        r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    if content.summary:
        p_sum = doc.add_paragraph(content.summary)
        for r in p_sum.runs:
            r.font.name = "Segoe UI"

    for sec in content.sections:
        if isinstance(sec, dict):
            h1 = doc.add_heading(str(sec.get("heading") or "Bölüm"), level=1)
            for r in h1.runs:
                r.font.name = "Segoe UI"
            doc.add_paragraph(str(sec.get("content") or ""))

    if content.headers and content.rows:
        _docx_add_table(doc, content.headers, content.rows)

    doc.save(str(out_path))


def _pdf_new_page(doc: fitz.Document, fonts: tuple[str | None, str | None, str, str]) -> fitz.Page:
    reg_font, bold_font, fn_reg, fn_bold = fonts
    page = doc.new_page(width=595, height=842)
    if reg_font:
        page.insert_font(fontname=fn_reg, fontfile=reg_font)
    if bold_font:
        page.insert_font(fontname=fn_bold, fontfile=bold_font)
    return page


def _pdf_draw_table_header(pg: fitz.Page, y_pos: float, headers: list[str], fn_bold: str) -> float:
    col_w = 523.0 / max(1, len(headers))
    pg.draw_rect(fitz.Rect(36, y_pos, 559, y_pos + 22), color=(0.31, 0.27, 0.9), fill=(0.31, 0.27, 0.9))
    for i, h in enumerate(headers):
        pg.insert_textbox(
            fitz.Rect(39 + i * col_w, y_pos + 4, 36 + (i + 1) * col_w - 3, y_pos + 20),
            h,
            fontname=fn_bold,
            fontsize=8.5,
            color=(1, 1, 1),
        )
    return y_pos + 24


def _pdf_render_table(
    doc: fitz.Document,
    page: fitz.Page,
    y: float,
    content: _DocContent,
    fonts: tuple[str | None, str | None, str, str],
) -> None:
    _reg, _bold, fn_reg, fn_bold = fonts
    if y > 700:
        page = _pdf_new_page(doc, fonts)
        y = 48.0
    col_w = 523.0 / max(1, len(content.headers))
    y = _pdf_draw_table_header(page, y, content.headers, fn_bold)
    for r_idx, rdata in enumerate(content.rows):
        row_h = 22.0
        if y + row_h > 800:
            page = _pdf_new_page(doc, fonts)
            y = _pdf_draw_table_header(page, 48.0, content.headers, fn_bold)
        if r_idx % 2 == 1:
            page.draw_rect(fitz.Rect(36, y, 559, y + row_h), color=(0.95, 0.96, 0.98), fill=(0.95, 0.96, 0.98))
        page.draw_rect(fitz.Rect(36, y, 559, y + row_h), color=(0.82, 0.85, 0.89), width=0.5)
        for i in range(len(content.headers)):
            val = str(rdata[i]) if i < len(rdata) else ""
            page.insert_textbox(
                fitz.Rect(39 + i * col_w, y + 4, 36 + (i + 1) * col_w - 3, y + row_h - 2),
                val,
                fontname=fn_reg,
                fontsize=8.5,
                color=(0.1, 0.12, 0.16),
            )
        y += row_h


def _build_pdf(out_path: Path, *args: Any, **kwargs: Any) -> None:
    """Build a multi-page Unicode/Turkish-safe PDF with embedded TrueType font (no broken ğ/ş/ı/İ)."""
    content = _unpack_doc_content(args, kwargs)
    reg_font, bold_font = _find_unicode_fonts()
    fn_reg = "tr_reg" if reg_font else "helv"
    fn_bold = "tr_bold" if bold_font else "hebo"
    fonts = (reg_font, bold_font, fn_reg, fn_bold)

    doc = fitz.open()
    page = _pdf_new_page(doc, fonts)
    page.draw_rect(fitz.Rect(0, 0, 595, 82), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
    page.insert_textbox(fitz.Rect(36, 20, 559, 76), content.title, fontname=fn_bold, fontsize=15, color=(1, 1, 1))

    y = 98.0
    if content.summary:
        est_h = max(46.0, min(140.0, (len(content.summary) / 72.0 + 1.5) * 14.5))
        page.insert_textbox(fitz.Rect(36, y, 559, y + est_h), content.summary, fontname=fn_reg, fontsize=10, color=(0.15, 0.2, 0.28))
        y += est_h + 10

    for sec in content.sections:
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading") or "")
        body = str(sec.get("content") or "")
        est_h = max(36.0, min(220.0, (len(body) / 76.0 + 1.5) * 14.0))
        if y + est_h + 30 > 795:
            page = _pdf_new_page(doc, fonts)
            y = 48.0
        page.insert_text((36, y), heading, fontname=fn_bold, fontsize=11.5, color=(0.12, 0.16, 0.23))
        y += 14
        page.insert_textbox(fitz.Rect(36, y, 559, y + est_h), body, fontname=fn_reg, fontsize=9.5, color=(0.2, 0.24, 0.3))
        y += est_h + 10

    if content.headers and content.rows:
        _pdf_render_table(doc, page, y, content, fonts)

    doc_pages: Any = doc
    total_pages = len(doc_pages)
    for idx, pg in enumerate(doc_pages, start=1):
        pg.insert_text((490, 824), f"Sayfa {idx} / {total_pages}", fontname=fn_reg, fontsize=8.5, color=(0.45, 0.5, 0.58))

    doc.save(str(out_path), deflate=True, garbage=3)
    doc.close()
