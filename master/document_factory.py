"""Universal Office & Document Deliverable Factory (.xlsx, .docx, .pdf).

When a user asks the AI in any domain (finance, law, marketing, science, education, project management)
to create an Excel spreadsheet, Word document, or PDF report, this module asks the local LLM for a
structured document specification and builds a real, downloadable corporate file.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pymupdf as fitz
from docx import Document
from docx.shared import Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import config
import multimodal_studio as mms

DOC_BUILD_RE = re.compile(
    r"((excel|\.xlsx)\s*(tablo\w*|dosya\w*|rapor\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*)|"
    r"(word|\.docx)\s*(dosya\w*|belge\w*|rapor\w*|sözleşme\w*|dilekçe\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|ver\w*)|"
    r"(sunum\w*|powerpoint|slayt\w*|\.pptx)\s*(dosya\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*)|"
    r"(pdf|\.pdf)\s*(rapor\w*|dosya\w*|belge\w*|özet\w*)?\s*(hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|çıkar\w*|ver\w*))",
    re.IGNORECASE,
)


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
    """Use local LLM to structure content and compile a real .xlsx, .docx, or .pdf file."""
    model = await mms.pick_best_model("deep")
    file_id = f"doc-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_dir = mms.media_dir()

    schema_prompt = (
        "Kullanıcının istediği kurumsal dokümanı/tabloyu eksiksiz hazırlamak için SADECE geçerli bir JSON objesi döndür:\n"
        "{\n"
        '  "title": "Doküman Başlığı",\n'
        '  "summary": "Yönetici özeti ve açıklama paragrafı",\n'
        '  "sections": [\n'
        '    {"heading": "1. Bölüm Başlığı", "content": "Detaylı içerik paragrafı"}\n'
        "  ],\n"
        '  "table_headers": ["Sütun 1", "Sütun 2", "Sütun 3", "Sayısal Değer"],\n'
        '  "table_rows": [\n'
        '    ["Kalem A", "Açıklama", "Kategori", 1250],\n'
        '    ["Kalem B", "Açıklama", "Kategori", 3400]\n'
        "  ]\n"
        "}\n"
        "Kurallar: Asla emoji kullanma. Gerçekçi, kapsamlı ve profesyonel veriler üret."
    )
    user_msg = prompt
    if context_text:
        user_msg += f"\n\nKaynak veri:\n{context_text[:6000]}"

    spec: dict[str, Any] = {
        "title": "Kurumsal Rapor ve Veri Tablosu",
        "summary": prompt,
        "sections": [{"heading": "1. Genel Değerlendirme", "content": prompt}],
        "table_headers": ["No", "Kalem / Başlık", "Açıklama", "Değer"],
        "table_rows": [["1", "Örnek Kalem 1", "Detay", 100], ["2", "Örnek Kalem 2", "Detay", 250]],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": schema_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.25, "num_predict": 3072},
                },
            )
            if resp.status_code == 200:
                raw = resp.json().get("message", {}).get("content", "")
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    parsed = json.loads(m.group(0))
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
        _build_xlsx(out_path, title, summary, headers, rows)
    elif fmt == "docx":
        out_path = out_dir / f"{file_id}.docx"
        _build_docx(out_path, title, summary, sections, headers, rows)
    elif fmt == "pptx":
        import deep_research as dr

        out_path = out_dir / f"{file_id}.pptx"
        slides = [
            {"title": str(s.get("heading") or "Bölüm"), "bullets": str(s.get("content") or "").split(". ")}
            for s in sections
            if isinstance(s, dict)
        ]
        dr.build_pptx_presentation(title=title, subtitle=summary[:160], slides=slides, out_path=out_path)
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


def _build_xlsx(out_path: Path, title: str, summary: str, headers: list[str], rows: list[list[Any]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Rapor ve Tablo"

    navy = PatternFill("solid", fgColor="1E293B")
    accent = PatternFill("solid", fgColor="4F46E5")
    zebra = PatternFill("solid", fgColor="F8FAFC")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    col_count = max(3, len(headers))
    last_col = get_column_letter(col_count)
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = title.upper()
    ws["A1"].font = Font(size=13, bold=True, color="FFFFFF")
    ws["A1"].fill = navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = summary[:240]
    ws["A2"].font = Font(size=10, italic=True, color="334155")
    ws.row_dimensions[2].height = 22

    start_r = 4
    for ci, h in enumerate(headers, start=1):
        c = ws.cell(start_r, ci, h)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = accent
        c.border = border
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[start_r].height = 24

    for ri, rdata in enumerate(rows, start=start_r + 1):
        for ci in range(1, len(headers) + 1):
            val = rdata[ci - 1] if ci - 1 < len(rdata) else ""
            c = ws.cell(ri, ci, val)
            c.border = border
            if (ri - start_r) % 2 == 0:
                c.fill = zebra

    # Add automatic SUM row if last column has numbers
    if rows and any(isinstance(r[-1], (int, float)) for r in rows if r):
        sum_r = start_r + len(rows) + 1
        ws.cell(sum_r, 1, "TOPLAM").font = Font(bold=True)
        last_c = len(headers)
        col_let = get_column_letter(last_c)
        sc = ws.cell(sum_r, last_c, f"=SUM({col_let}{start_r + 1}:{col_let}{sum_r - 1})")
        sc.font = Font(bold=True, color="1E293B")
        sc.border = border

    for ci in range(1, col_count + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 24

    wb.save(str(out_path))


def _build_docx(
    out_path: Path,
    title: str,
    summary: str,
    sections: list[dict[str, Any]],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    doc = Document()
    h0 = doc.add_heading(title, level=0)
    for r in h0.runs:
        r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    if summary:
        doc.add_paragraph(summary)

    for sec in sections:
        if isinstance(sec, dict):
            doc.add_heading(str(sec.get("heading") or "Bölüm"), level=1)
            doc.add_paragraph(str(sec.get("content") or ""))

    if headers and rows:
        doc.add_heading("Veri ve Özet Tablosu", level=1)
        tbl = doc.add_table(rows=1, cols=len(headers))
        tbl.style = "Table Grid"
        for i, h in enumerate(headers):
            tbl.rows[0].cells[i].text = str(h)
            for p in tbl.rows[0].cells[i].paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(9.5)
        for rdata in rows:
            rc = tbl.add_row().cells
            for i in range(len(headers)):
                rc[i].text = str(rdata[i]) if i < len(rdata) else ""

    doc.save(str(out_path))


def _build_pdf(
    out_path: Path,
    title: str,
    summary: str,
    sections: list[dict[str, Any]],
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(0, 0, 595, 76), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
    page.insert_text((36, 46), title[:62], fontsize=15, color=(1, 1, 1))

    y = 104
    if summary:
        page.insert_textbox(fitz.Rect(36, y, 559, y + 70), summary[:450], fontsize=10, color=(0.15, 0.2, 0.28))
        y += 78

    for sec in sections[:6]:
        if not isinstance(sec, dict):
            continue
        if y > 720:
            page = doc.new_page(width=595, height=842)
            y = 48
        page.insert_text((36, y), str(sec.get("heading") or ""), fontsize=12, color=(0.12, 0.16, 0.23))
        y += 16
        content = str(sec.get("content") or "")
        page.insert_textbox(fitz.Rect(36, y, 559, y + 85), content[:520], fontsize=9.5, color=(0.2, 0.24, 0.3))
        y += 92

    if headers and rows:
        if y > 640:
            page = doc.new_page(width=595, height=842)
            y = 48
        col_w = 520 / max(1, len(headers))
        page.draw_rect(fitz.Rect(36, y - 12, 559, y + 6), color=(0.31, 0.27, 0.9), fill=(0.31, 0.27, 0.9))
        for i, h in enumerate(headers):
            page.insert_text((40 + i * col_w, y), str(h)[:18], fontsize=8.5, color=(1, 1, 1))
        y += 18
        for rdata in rows[:18]:
            if y > 790:
                break
            for i in range(len(headers)):
                val = str(rdata[i])[:20] if i < len(rdata) else ""
                page.insert_text((40 + i * col_w, y), val, fontsize=8.5, color=(0.1, 0.12, 0.16))
            y += 16

    doc.save(str(out_path))
    doc.close()
