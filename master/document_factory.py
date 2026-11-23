"""Universal Office & Document Deliverable Factory (.xlsx, .docx, .pptx, .pdf).

Builds real, rich, Unicode/Turkish-safe corporate deliverables with embedded TrueType fonts in PDF,
auto-sized wrapped columns & charts in Excel, styled headings/tables in Word, and OpenXML slides in PPTX.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    lower = prompt.lower()
    if any(k in lower for k in ("balonla", "teknik çizim", "web sitesi", "e-ticaret", "oyun", "exe")):
        return None
    if not DOC_BUILD_RE.search(lower):
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

    schema_prompt = (
        f"Kullanıcının istediği kurumsal dokümanı/tabloyu SADECE {target_lang} dilinde ve kusursuz Türkçe/Unicode karakterlerle "
        "(Ç, Ğ, İ, Ö, Ş, Ü, ç, ğ, ı, ö, ş, ü bozulmadan) eksiksiz hazırlamak için SADECE geçerli bir JSON objesi döndür:\n"
        "{\n"
        '  "title": "Doküman Başlığı",\n'
        '  "summary": "Kapsamlı yönetici özeti paragrafı",\n'
        '  "sections": [\n'
        '    {"heading": "1. Bölüm Başlığı", "content": "Detaylı ve gerçekçi içerik paragrafı"},\n'
        '    {"heading": "2. Bölüm Başlığı", "content": "Detaylı analiz ve bulgular"},\n'
        '    {"heading": "3. Bölüm Başlığı", "content": "Uygulama planı ve öneriler"}\n'
        "  ],\n"
        '  "table_headers": ["Kod / No", "Kalem / Açıklama", "Kategori", "Birim / Durum", "Sayısal Değer"],\n'
        '  "table_rows": [\n'
        '    ["01", "Somut Kalem 1", "Kategori A", "Aktif", 12500],\n'
        '    ["02", "Somut Kalem 2", "Kategori B", "Aktif", 24800]\n'
        "  ]\n"
        "}\n"
        "KESİN KURALLAR:\n"
        f"- Tüm başlıklar, metinler ve tablo hücreleri kesinlikle {target_lang} dilinde olsun; başka dilden kelimeler karıştırma.\n"
        "- Tabloda en az 8 adet dolu, tutarlı ve gerçekçi satır üret; 'Örnek Kalem' gibi boş yer tutucu yazma.\n"
        "- Asla emoji kullanma. Kaynak veri verildiyse sayıları uydurma, birebir kaynak veriden al."
    )
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
        raw = res.content
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            cleaned_json = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, dict) and parsed.get("title"):
                spec.update(parsed)
    except Exception:
        pass

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
                "bullets": [" | ".join(str(c) for c in r[:len(headers)]) for r in rows[:8]],
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


def _build_xlsx(
    out_path: Path,
    title: str,
    summary: str,
    sections: list[dict[str, Any]],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Veri ve Tablo"

    navy = PatternFill("solid", fgColor="1E293B")
    accent = PatternFill("solid", fgColor="4F46E5")
    zebra = PatternFill("solid", fgColor="F8FAFC")
    total_fill = PatternFill("solid", fgColor="E2E8F0")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    col_count = max(3, len(headers))
    last_col = get_column_letter(col_count)
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = title
    ws["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws["A1"].fill = navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30

    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = summary[:400]
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="334155")
    ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 28

    start_r = 4
    col_widths = [max(14, len(str(h)) + 6) for h in headers]
    for ci, h in enumerate(headers, start=1):
        c = ws.cell(start_r, ci, h)
        c.font = Font(name="Calibri", bold=True, color="FFFFFF", size=10.5)
        c.fill = accent
        c.border = border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[start_r].height = 26

    numeric_cols: set[int] = set()
    for ri, rdata in enumerate(rows, start=start_r + 1):
        for ci in range(1, len(headers) + 1):
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
            if (ri - start_r) % 2 == 0:
                c.fill = zebra
            col_widths[ci - 1] = min(48, max(col_widths[ci - 1], len(str(val)) + 4))

    # Add automatic SUM and AVERAGE rows for all numeric columns
    if rows and numeric_cols:
        sum_r = start_r + len(rows) + 1
        avg_r = sum_r + 1
        ws.cell(sum_r, 1, "TOPLAM").font = Font(name="Calibri", bold=True)
        ws.cell(avg_r, 1, "ORTALAMA").font = Font(name="Calibri", bold=True)
        for ci in range(1, len(headers) + 1):
            ws.cell(sum_r, ci).fill = total_fill
            ws.cell(sum_r, ci).border = border
            ws.cell(avg_r, ci).border = border
        for ci in sorted(numeric_cols):
            col_let = get_column_letter(ci)
            sc = ws.cell(sum_r, ci, f"=SUM({col_let}{start_r + 1}:{col_let}{sum_r - 1})")
            sc.font = Font(name="Calibri", bold=True, color="1E293B")
            sc.number_format = "#,##0.00"
            ac = ws.cell(avg_r, ci, f"=AVERAGE({col_let}{start_r + 1}:{col_let}{sum_r - 1})")
            ac.font = Font(name="Calibri", italic=True, color="334155")
            ac.number_format = "#,##0.00"

        # Add embedded BarChart for the last numeric column
        last_num_c = max(numeric_cols)
        if len(rows) >= 2 and last_num_c >= 2:
            chart = BarChart()
            chart.title = f"{headers[last_num_c - 1]} Dağılımı"
            chart.y_axis.title = headers[last_num_c - 1]
            data_ref = Reference(ws, min_col=last_num_c, min_row=start_r, max_row=start_r + len(rows))
            cats_ref = Reference(ws, min_col=2 if len(headers) > 1 else 1, min_row=start_r + 1, max_row=start_r + len(rows))
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            chart.width = 16
            chart.height = 9
            ws.add_chart(chart, f"A{avg_r + 2}")

    for ci, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.freeze_panes = f"A{start_r + 1}"

    if sections:
        ws2 = wb.create_sheet("Yönetici Özeti ve Notlar")
        ws2["A1"] = title
        ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color="1E293B")
        r_cursor = 3
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            ws2.cell(r_cursor, 1, str(sec.get("heading") or "")).font = Font(name="Calibri", bold=True, size=11)
            ws2.cell(r_cursor + 1, 1, str(sec.get("content") or "")).alignment = Alignment(wrap_text=True)
            r_cursor += 3
        ws2.column_dimensions["A"].width = 96

    wb.save(str(out_path))


def _shade_docx_cell(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _build_docx(
    out_path: Path,
    title: str,
    summary: str,
    sections: list[dict[str, Any]],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    doc = Document()
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Segoe UI"
    normal_style.font.size = Pt(10.5)

    h0 = doc.add_heading(title, level=0)
    for r in h0.runs:
        r.font.name = "Segoe UI"
        r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    if summary:
        p_sum = doc.add_paragraph(summary)
        for r in p_sum.runs:
            r.font.name = "Segoe UI"

    for sec in sections:
        if isinstance(sec, dict):
            h1 = doc.add_heading(str(sec.get("heading") or "Bölüm"), level=1)
            for r in h1.runs:
                r.font.name = "Segoe UI"
            doc.add_paragraph(str(sec.get("content") or ""))

    if headers and rows:
        doc.add_heading("Veri ve Özet Tablosu", level=1)
        tbl = doc.add_table(rows=1, cols=len(headers))
        tbl.style = "Table Grid"
        for i, h in enumerate(headers):
            cell = tbl.rows[0].cells[i]
            cell.text = str(h)
            _shade_docx_cell(cell, "1E293B")
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.name = "Segoe UI"
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for r_idx, rdata in enumerate(rows):
            rc = tbl.add_row().cells
            for i in range(len(headers)):
                rc[i].text = str(rdata[i]) if i < len(rdata) else ""
                if r_idx % 2 == 1:
                    _shade_docx_cell(rc[i], "F8FAFC")
                for p in rc[i].paragraphs:
                    for run in p.runs:
                        run.font.name = "Segoe UI"
                        run.font.size = Pt(9.0)

    doc.save(str(out_path))


def _build_pdf(
    out_path: Path,
    title: str,
    summary: str,
    sections: list[dict[str, Any]],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    """Build a multi-page Unicode/Turkish-safe PDF with embedded TrueType font (no broken ğ/ş/ı/İ)."""
    reg_font, bold_font = _find_unicode_fonts()
    fn_reg = "tr_reg" if reg_font else "helv"
    fn_bold = "tr_bold" if bold_font else "hebo"

    doc = fitz.open()

    def _new_page() -> fitz.Page:
        p = doc.new_page(width=595, height=842)
        if reg_font:
            p.insert_font(fontname=fn_reg, fontfile=reg_font)
        if bold_font:
            p.insert_font(fontname=fn_bold, fontfile=bold_font)
        return p

    page = _new_page()
    page.draw_rect(fitz.Rect(0, 0, 595, 82), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
    page.insert_textbox(
        fitz.Rect(36, 20, 559, 76),
        title,
        fontname=fn_bold,
        fontsize=15,
        color=(1, 1, 1),
    )

    y = 98.0
    if summary:
        est_h = max(46.0, min(140.0, (len(summary) / 72.0 + 1.5) * 14.5))
        page.insert_textbox(
            fitz.Rect(36, y, 559, y + est_h),
            summary,
            fontname=fn_reg,
            fontsize=10,
            color=(0.15, 0.2, 0.28),
        )
        y += est_h + 10

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading") or "")
        content = str(sec.get("content") or "")
        est_h = max(36.0, min(220.0, (len(content) / 76.0 + 1.5) * 14.0))
        if y + est_h + 30 > 795:
            page = _new_page()
            y = 48.0
        page.insert_text((36, y), heading, fontname=fn_bold, fontsize=11.5, color=(0.12, 0.16, 0.23))
        y += 14
        page.insert_textbox(
            fitz.Rect(36, y, 559, y + est_h),
            content,
            fontname=fn_reg,
            fontsize=9.5,
            color=(0.2, 0.24, 0.3),
        )
        y += est_h + 10

    if headers and rows:
        if y > 700:
            page = _new_page()
            y = 48.0
        col_w = 523.0 / max(1, len(headers))

        def _draw_table_header(pg: fitz.Page, y_pos: float) -> float:
            pg.draw_rect(fitz.Rect(36, y_pos, 559, y_pos + 22), color=(0.31, 0.27, 0.9), fill=(0.31, 0.27, 0.9))
            for i, h in enumerate(headers):
                pg.insert_textbox(
                    fitz.Rect(39 + i * col_w, y_pos + 4, 36 + (i + 1) * col_w - 3, y_pos + 20),
                    str(h),
                    fontname=fn_bold,
                    fontsize=8.5,
                    color=(1, 1, 1),
                )
            return y_pos + 24

        y = _draw_table_header(page, y)
        for r_idx, rdata in enumerate(rows):
            row_h = 22.0
            if y + row_h > 800:
                page = _new_page()
                y = _draw_table_header(page, 48.0)
            if r_idx % 2 == 1:
                page.draw_rect(fitz.Rect(36, y, 559, y + row_h), color=(0.95, 0.96, 0.98), fill=(0.95, 0.96, 0.98))
            page.draw_rect(fitz.Rect(36, y, 559, y + row_h), color=(0.82, 0.85, 0.89), width=0.5)
            for i in range(len(headers)):
                val = str(rdata[i]) if i < len(rdata) else ""
                page.insert_textbox(
                    fitz.Rect(39 + i * col_w, y + 4, 36 + (i + 1) * col_w - 3, y + row_h - 2),
                    val,
                    fontname=fn_reg,
                    fontsize=8.5,
                    color=(0.1, 0.12, 0.16),
                )
            y += row_h

    # Page numbers footer
    total_pages = len(doc)
    for idx, pg in enumerate(doc, start=1):
        pg.insert_text(
            (490, 824),
            f"Sayfa {idx} / {total_pages}",
            fontname=fn_reg,
            fontsize=8.5,
            color=(0.45, 0.5, 0.58),
        )

    doc.save(str(out_path), deflate=True, garbage=3)
    doc.close()
