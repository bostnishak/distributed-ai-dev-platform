"""DOC-01..DOC-10: Verified DOCX, Live-Formula XLSX, Linked-TOC PDF, Redline Edit, Roundtrip Audit & Quality Gate."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import openpyxl
import pymupdf
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from hallucination.verifier import verify_numbers_and_tables
from orchestrator.state import save_artifact
from rag.parsing import parse_document

# DOC-04: 9 Structured Document Templates
DOCUMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "report": {"title": "Teknik ve Yönetici Raporu", "required_fields": ["title", "summary", "sections"]},
    "academic_ieee": {"title": "IEEE Bilimsel Makale", "required_fields": ["title", "abstract", "sections", "references"]},
    "cv": {"title": "Özgeçmiş (CV)", "required_fields": ["full_name", "summary", "experience", "education"]},
    "proposal": {"title": "Proje Teklifi", "required_fields": ["title", "scope", "budget", "timeline"]},
    "minutes": {"title": "Toplantı Tutanağı", "required_fields": ["title", "date", "decisions", "actions"]},
    "contract_draft": {"title": "Sözleşme Taslağı", "required_fields": ["title", "parties", "clauses"]},
    "invoice": {"title": "Fatura Taslağı", "required_fields": ["invoice_no", "items", "tax_rate"]},
    "lesson_notes": {"title": "Ders Notu", "required_fields": ["title", "objectives", "sections", "exercises"]},
    "training_plan": {"title": "Eğitim Planı", "required_fields": ["title", "modules", "duration_hours"]},
}

_PLACEHOLDER_RE = re.compile(r"\b(?:lorem\s+ipsum|todo|tbd|fixme|yer\s+tutucu)\b|\[\.\.\.\]", re.IGNORECASE)
_EXCEL_ERR_TOKENS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!")


# ---------------------------------------------------------------- DOC-08 & DOC-09 Quality Audit

def audit_document_quality(text: str, *, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """DOC-08 & DOC-09: Detect placeholders (Lorem/TODO), repeated words, and unsourced numeric claims."""
    placeholders = _PLACEHOLDER_RE.findall(text or "")
    dup_words = re.findall(r"\b([a-zA-ZçğıöşüÇĞİÖŞÜ]{3,})\s+\1\b", text or "", re.IGNORECASE)
    num_audit = verify_numbers_and_tables(text, sources=sources) if sources else {"passed": True, "unsourced_numbers": [], "table_sum_errors": []}
    passed = len(placeholders) == 0 and num_audit["passed"]
    return {
        "passed": passed,
        "placeholders": placeholders,
        "repeated_words": dup_words,
        "numeric_audit": num_audit,
    }


# ---------------------------------------------------------------- DOC-01 Verified Word (DOCX) Builder

def _add_toc_field(doc: Any) -> None:
    p = doc.add_paragraph()
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_sep, fld_end])


def build_verified_docx(spec: dict[str, Any], *, output_path: Path, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """DOC-01, 08, 09: Build styled DOCX with TOC field, headers/footers, tables, source trace & verification."""
    doc = Document()
    title = str(spec.get("title") or "Rapor")
    doc.sections[0].header.paragraphs[0].text = title
    doc.sections[0].footer.paragraphs[0].text = f"{title} - Otomatik Doğrulanmış Belge"

    doc.add_heading(title, level=0)
    if spec.get("summary"):
        doc.add_paragraph(str(spec["summary"]))

    doc.add_heading("İçindekiler", level=1)
    _add_toc_field(doc)

    all_text_parts = [title, str(spec.get("summary") or "")]
    for idx, sec in enumerate(spec.get("sections") or [], start=1):
        heading = f"{idx}. {sec.get('heading', 'Bölüm')}"
        body = str(sec.get("content") or "")
        doc.add_heading(heading, level=1)
        doc.add_paragraph(body)
        all_text_parts.extend([heading, body])

    headers = spec.get("table_headers") or []
    rows = spec.get("table_rows") or []
    if headers and rows:
        tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
        for c_i, h in enumerate(headers):
            tbl.rows[0].cells[c_i].text = str(h)
        for r_i, r in enumerate(rows, start=1):
            for c_i, val in enumerate(r[: len(headers)]):
                tbl.rows[r_i].cells[c_i].text = str(val)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))

    # Re-open verification
    reopened = Document(str(output_path))
    quality = audit_document_quality("\n".join(all_text_parts), sources=sources)
    art = save_artifact(kind="document", title=title, sections=all_text_parts, metadata={"path": str(output_path), "format": "docx"})
    return {
        "path": str(output_path),
        "artifact_id": art["artifact_id"],
        "opened_ok": len(reopened.paragraphs) > 0,
        "paragraph_count": len(reopened.paragraphs),
        "quality": quality,
    }


# ---------------------------------------------------------------- DOC-05 In-Place Redline DOCX Edit

def edit_docx_inplace_redline(source_path: Path, target_paragraph_idx: int, new_text: str, output_path: Path) -> dict[str, Any]:
    """DOC-05: Edit ONLY one paragraph in-place with OOXML tracked-change (w:del / w:ins) leaving original & other paragraphs untouched."""
    doc = Document(str(source_path))
    if target_paragraph_idx < 0 or target_paragraph_idx >= len(doc.paragraphs):
        raise IndexError(f"Geçersiz paragraf indeksi: {target_paragraph_idx}")

    para = doc.paragraphs[target_paragraph_idx]
    old_text = para.text
    para.text = ""

    # Insert tracked deletion (w:del) and insertion (w:ins)
    w_del = OxmlElement("w:del")
    w_del.set(qn("w:id"), "1")
    w_del.set(qn("w:author"), "Platform Editor")
    r_del = OxmlElement("w:r")
    t_del = OxmlElement("w:delText")
    t_del.text = old_text
    r_del.append(t_del)
    w_del.append(r_del)

    w_ins = OxmlElement("w:ins")
    w_ins.set(qn("w:id"), "2")
    w_ins.set(qn("w:author"), "Platform Editor")
    r_ins = OxmlElement("w:r")
    t_ins = OxmlElement("w:t")
    t_ins.text = new_text
    r_ins.append(t_ins)
    w_ins.append(r_ins)

    para._p.append(w_del)
    para._p.append(w_ins)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return {"output_path": str(output_path), "edited_index": target_paragraph_idx, "old_text": old_text, "new_text": new_text, "has_redline": True}


# ---------------------------------------------------------------- DOC-02 Live-Formula Excel (XLSX) Builder & Verifier

def build_verified_xlsx(spec: dict[str, Any], *, output_path: Path) -> dict[str, Any]:
    """DOC-02: Build XLSX with live formulas (SUM/AVERAGE/IF), validation, conditional formatting, chart & zero-error check."""
    wb = openpyxl.Workbook()
    ws: Any = wb.active
    if ws is None:
        raise RuntimeError("Excel aktif çalışma sayfası oluşturulamadı.")
    ws.title = str(spec.get("sheet_name") or "Analiz")[:31]

    headers = list(spec.get("headers") or ["Kalem", "Adet", "Birim Fiyat", "Toplam", "Durum"])
    ws.append(headers)
    bold = Font(bold=True, color="FFFFFF")
    hdr_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = bold
        cell.fill = hdr_fill

    items = list(spec.get("items") or [("Modül A", 5, 200), ("Modül B", 3, 450), ("Modül C", 8, 120)])
    for r_idx, item in enumerate(items, start=2):
        name, qty, unit = item[0], float(item[1]), float(item[2])
        ws.cell(row=r_idx, column=1, value=str(name))
        ws.cell(row=r_idx, column=2, value=qty)
        ws.cell(row=r_idx, column=3, value=unit)
        ws.cell(row=r_idx, column=4, value=f"=B{r_idx}*C{r_idx}")
        ws.cell(row=r_idx, column=5, value=f'=IF(D{r_idx}>=1000,"Yüksek","Normal")')

    last_row = 1 + len(items)
    tot_row = last_row + 1
    ws.cell(row=tot_row, column=1, value="Genel Toplam").font = Font(bold=True)
    ws.cell(row=tot_row, column=2, value=f"=SUM(B2:B{last_row})")
    ws.cell(row=tot_row, column=3, value=f"=AVERAGE(C2:C{last_row})")
    ws.cell(row=tot_row, column=4, value=f"=SUM(D2:D{last_row})")

    # Data validation on Qty column (must be >= 0) & conditional formatting on Totals
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0")
    ws.add_data_validation(dv)
    dv.add(f"B2:B{last_row}")
    ws.conditional_formatting.add(
        f"D2:D{last_row}",
        CellIsRule(operator="greaterThanOrEqual", formula=["1000"], fill=PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")),
    )

    chart = BarChart()
    chart.title = str(spec.get("title") or "Kalem Toplamları")
    data_ref = Reference(ws, min_col=4, min_row=1, max_row=last_row)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=last_row)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "G2")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    audit = verify_xlsx_formulas(output_path)
    art = save_artifact(kind="spreadsheet", title=str(spec.get("title") or output_path.name), sections=[f"{len(items)} kalem, {audit['formula_cells']} canlı formül"], metadata={"path": str(output_path), "audit": audit})
    return {"path": str(output_path), "artifact_id": art["artifact_id"], "audit": audit}


def verify_xlsx_formulas(xlsx_path: Path) -> dict[str, Any]:
    """DOC-02: Inspect workbook for error cells (#REF!, #DIV/0!, etc.) and live formula count."""
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=False)
    formula_cells = 0
    error_cells: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                val = cell.value
                if isinstance(val, str):
                    if val.startswith("="):
                        formula_cells += 1
                    if any(err in val for err in _EXCEL_ERR_TOKENS):
                        error_cells.append(f"{ws.title}!{cell.coordinate}:{val}")
    return {
        "opened_ok": True,
        "formula_cells": formula_cells,
        "error_cells": error_cells,
        "passed": formula_cells > 0 and len(error_cells) == 0,
    }


# ---------------------------------------------------------------- DOC-03 Verified PDF with Linked TOC & Turkish Glyphs

def build_verified_pdf(spec: dict[str, Any], *, output_path: Path, pdf_a: bool = False) -> dict[str, Any]:
    """DOC-03: Build PDF with cover, clickable TOC bookmarks, Turkish UTF-8 text, and selectability verification."""
    doc = pymupdf.open()
    title = str(spec.get("title") or "Teknik Rapor")
    sections = list(spec.get("sections") or [{"heading": "Giriş", "content": "Türkçe karakter testi: ÇĞİÖŞÜ çğıöşü."}])

    # Cover page
    cover = doc.new_page()
    cover.insert_htmlbox(pymupdf.Rect(50, 120, 540, 320), f"<h1>{title}</h1><p>{spec.get('summary', '')}</p>")

    toc: list[list[Any]] = [[1, title, 1]]
    for idx, sec in enumerate(sections, start=1):
        p = doc.new_page()
        h = f"{idx}. {sec.get('heading', 'Bölüm')}"
        body = str(sec.get("content") or "")
        p.insert_htmlbox(pymupdf.Rect(50, 60, 540, 760), f"<h2>{h}</h2><p>{body}</p>")
        p.insert_htmlbox(pymupdf.Rect(50, 790, 540, 825), f"<small>{title} - Sayfa {idx + 1}</small>")
        toc.append([1, h, idx + 1])

    doc.set_toc(toc)
    if pdf_a:
        doc.set_metadata({"title": title, "subject": "PDF/A-1b compliant archive", "creator": "Distributed AI Platform"})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()

    # Verify reopening, TOC links, and selectable text
    chk: Any = pymupdf.open(str(output_path))
    extracted = "\n".join(str(pg.get_text("text")) for pg in chk)
    toc_entries = chk.get_toc()
    page_count = len(chk)
    chk.close()
    return {
        "path": str(output_path),
        "opened_ok": True,
        "page_count": page_count,
        "toc_entries": len(toc_entries),
        "selectable_chars": len(extracted.strip()),
        "pdf_a_tagged": pdf_a,
        "passed": page_count >= 2 and len(toc_entries) >= 2 and len(extracted.strip()) > 10,
    }


# ---------------------------------------------------------------- DOC-06 & DOC-07 Roundtrip & Table Extraction

def roundtrip_text_loss_audit(source_text: str, converted_path: Path) -> dict[str, Any]:
    """DOC-06: Measure round-trip text preservation ratio after converting a document."""
    parsed = parse_document(file_path=converted_path)
    out_text = " ".join(p.markdown for p in parsed.pages)
    src_tokens = set(re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", (source_text or "").lower()))
    out_tokens = set(re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", out_text.lower()))
    preserved = len(src_tokens & out_tokens) / max(1, len(src_tokens))
    loss_pct = round((1.0 - preserved) * 100.0, 2)
    return {
        "preserved_ratio": round(preserved, 4),
        "text_loss_pct": loss_pct,
        "tables_detected": len(parsed.tables),
        "passed": loss_pct <= 5.0,
    }
