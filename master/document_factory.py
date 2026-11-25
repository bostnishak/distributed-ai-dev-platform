"""Universal Office & Document Deliverable Factory (.xlsx, .docx, .pptx, .pdf, .csv).

Unicode/Turkish-safe corporate deliverables: TrueType fonts & TOC in PDF, coerced numerics/formulas/
AutoFilter/conditional formatting/charts in Excel, Markdown-parsed Word docs, OpenXML PPTX, BOM-safe CSV.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pymupdf as fitz
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import multimodal_studio as mms
from document_chart import _coerce_excel_cell, _row_height, chart_series, format_cell, render_bar_chart_png
from document_chart import pdf_wrap_lines as _pdf_wrap_lines
from document_formulas import is_rate_column, row_total_formula
from prompt_loader import load_prompt

logger = logging.getLogger(__name__)

_DOC_BLOCK_RE = re.compile(r"(?:\bbalonla\w*|\bteknik\s+çizim\b|(?<!\w)(?:\.exe|exe)(?!\w)|\b(?:web\s+sitesi|e-ticaret\s+sitesi|oyun)\s+(?:yap|oluştur|olustur|kur|kodla|programla)\w*\b|nasıl\s+yapılır|nasil\s+yapilir|yaparken|nelere\s+dikkat|ipuçları|ipuclari|tavsiyeler|\bhow\s+to\b|\btips\s+for\b)", re.I)
DOC_ACTION_RE = re.compile(r"(?:hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|yap\w*|üret\w*|uret\w*|çıkar\w*|cikar\w*|ver\w*|yaz\w*|indir\w*|dışa\s+aktar\w*|disa\s+aktar\w*|derle\w*|kaydet\w*|\b(?:create|generate|make|build|produce|export|write|draft|prepare|compile|download|save|output)\w*\b)", re.I)
_FMT_MATCHERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("xlsx", re.compile(r"(?:\bexcel(?:['\u2019]?[a-zğüşöçı]+)?\b|\.xlsx\b|\bxlsx\b|\bspreadsheet\b)", re.I)),
    ("csv", re.compile(r"(?:\bcsv(?:['\u2019]?[a-zğüşöçı]+)?\b|\.csv\b)", re.I)),
    ("docx", re.compile(r"(?:\.docx\b|\bdocx\b|\b(?:ms|microsoft)\s+word\b|\bword(?:['\u2019](?:de|da|te|ta|e|a|ten|tan|den|dan)\b|\s+(?:dosya\w*|belge\w*|rapor\w*|sözleşme\w*|dilekçe\w*|olarak|ile|format\w*|çıktı\w*|doc\w*|file\w*|report\w*)))", re.I)),
    ("pptx", re.compile(r"(?:\bpowerpoint\b|\.pptx\b|\bpptx\b|\bsunum\w*\b|\bslayt\w*\b|\bpresentation\b|\bslide\s*deck\b)", re.I)),
    ("pdf", re.compile(r"(?:\bpdf(?:['\u2019]?[a-zğüşöçı]+)?\b|\.pdf\b)", re.I)),
)
DOC_BUILD_RE = re.compile("|".join(p.pattern for _, p in _FMT_MATCHERS), re.I)
_TR_CUES_RE = re.compile(r"\b(?:hazırla\w*|hazirla\w*|oluştur\w*|olustur\w*|rapor\w*|tablo\w*|dosya\w*|belge\w*|bütçe\w*|sözleşme\w*|için|olarak|lütfen|bana|hakkında|satış\w*|çıkar\w*|yaz\w*|ver\w*|özet\w*|sunum\w*|analiz\w*)\b", re.I)
_EN_CUES_RE = re.compile(r"\b(?:create|generate|make|build|export|write|draft|prepare|report|spreadsheet|document|summary|budget|analysis|table|sales|monthly|quarterly|annual|financial|please|executive|data|file|for|with|about|the|and|of|from)\b", re.I)
_MD_INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)")

_FONT_REG = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/freefont/FreeSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/Library/Fonts/Arial.ttf")
_FONT_BOLD = ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/tahomabd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf")
_LABEL_KEYS = ("sheet_data", "sheet_notes", "total", "average", "chart_suffix", "table_heading", "page_fmt", "section", "content", "report", "summary", "item", "value", "source_note")
_LABELS_RAW: dict[str, tuple[str, ...]] = {
    "English": ("Data", "Summary", "Total", "Average", "Distribution", "Data & Summary Table", "Page {page} / {total}", "Section", "Content", "Report", "Summary", "Item", "Value", "Source data (extract real numbers and facts strictly from here, do not fabricate):"),
    "German": ("Daten", "Zusammenfassung", "Summe", "Durchschnitt", "Verteilung", "Daten- und Übersichtstabelle", "Seite {page} / {total}", "Abschnitt", "Inhalt", "Bericht", "Zusammenfassung", "Position", "Wert", "Quelldaten (Zahlen und Fakten direkt hieraus übernehmen, nichts erfinden):"),
    "Türkçe": ("Veri ve Tablo", "Yönetici Özeti ve Notlar", "TOPLAM", "ORTALAMA", "Dağılımı", "Veri ve Özet Tablosu", "Sayfa {page} / {total}", "Bölüm", "İçerik", "Kurumsal Rapor", "Yönetici Özeti", "Kalem", "Değer", "Kaynak veri (sayıları ve olguları birebir buradan al, uydurma):"),
}


@dataclass(frozen=True)
class _DocContent:
    title: str
    summary: str
    sections: list[dict[str, Any]]
    headers: list[str]
    rows: list[list[Any]]
    lang: str = "Türkçe"


def _labels(lang: str) -> dict[str, str]:
    return dict(zip(_LABEL_KEYS, _LABELS_RAW.get(lang, _LABELS_RAW["Türkçe"]), strict=True))


def _unpack_doc_content(args: tuple[Any, ...], kwargs: dict[str, Any]) -> _DocContent:
    if len(args) == 1 and isinstance(args[0], _DocContent):
        return args[0]
    a = list(args)
    return _DocContent(str(a[0] if len(a) > 0 else kwargs.get("title", "")), str(a[1] if len(a) > 1 else kwargs.get("summary", "")), list(a[2] if len(a) > 2 else kwargs.get("sections", [])), list(a[3] if len(a) > 3 else kwargs.get("headers", [])), list(a[4] if len(a) > 4 else kwargs.get("rows", [])), str(a[5] if len(a) > 5 else kwargs.get("lang", "Türkçe")))


def _find_unicode_fonts() -> tuple[str | None, str | None]:
    reg = next((p for p in _FONT_REG if Path(p).is_file()), None)
    bold = next((p for p in _FONT_BOLD if Path(p).is_file()), None)
    if not reg and Path("/usr/share/fonts/truetype").is_dir():
        reg = next((str(c) for c in sorted(Path("/usr/share/fonts/truetype").rglob("*.ttf")) if "bold" not in c.name.lower() and "italic" not in c.name.lower()), None)
    return reg, bold or reg


def _detect_requested_language(prompt: str) -> str:
    low = (prompt or "").lower()
    for lang, cues in (("Türkçe", ("türkçe", "turkce", "in turkish")), ("English", ("ingilizce", "in english", "english report", "english pdf", "english excel", "english csv")), ("German", ("almanca", "auf deutsch", "in german", "german report"))):
        if any(k in low for k in cues):
            return lang
    has_tr = any(ch in prompt for ch in "çğıöşüÇĞİÖŞÜ")
    tr_hits, en_hits = len(_TR_CUES_RE.findall(low)) + (2 if has_tr else 0), len(_EN_CUES_RE.findall(low))
    return "English" if en_hits > 0 and (tr_hits == 0 or (en_hits > tr_hits and not has_tr)) else "Türkçe"


def detect_document_request(prompt: str, has_file: bool) -> str | None:
    """Return 'xlsx' | 'docx' | 'pptx' | 'pdf' | 'csv' if the user asks for a downloadable document."""
    _ = has_file
    text = prompt or ""
    if _DOC_BLOCK_RE.search(text) or not DOC_ACTION_RE.search(text) or not DOC_BUILD_RE.search(text):
        return None
    return next((fmt for fmt, pat in _FMT_MATCHERS if pat.search(text)), None)


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw or "", flags=re.I)
    dec = json.JSONDecoder()
    for candidate in (cleaned, re.sub(r",\s*([}\]])", r"\1", cleaned)):
        idx = 0
        while (start := candidate.find("{", idx)) != -1:
            try:
                obj, _ = dec.raw_decode(candidate, start)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            idx = start + 1
    return None


def _build_fallback_spec(prompt: str, context_text: str, lang: str) -> dict[str, Any]:
    lbl, topic, ctx = _labels(lang), re.sub(r"\s+", " ", (prompt or "").strip()), context_text.strip()
    headers, rows, sections = [], [], []
    if ctx:
        lines = [ln.strip() for ln in ctx.splitlines() if ln.strip()]
        for delim in ("\t", "|", ";", ","):
            split = [[c.strip() for c in ln.strip("|").split(delim)] for ln in lines if ln.count(delim) >= 1]
            split = [r for r in split if len(r) >= 2 and not all(set(c) <= {"-", ":"} for c in r if c)]
            if len(split) >= 2:
                w = len(split[0])
                headers, rows = split[0], [r[:w] + [""] * max(0, w - len(r)) for r in split[1:26]]
                break
        for i, blk in enumerate([b.strip() for b in re.split(r"\n{2,}", ctx) if b.strip()][:6], 1):
            bl = blk.splitlines()
            hd = bl[0].lstrip("#- ").strip()[:80] if len(bl) > 1 else f"{i}. {lbl['section']}"
            sections.append({"heading": hd, "content": ("\n".join(bl[1:]).strip() if len(bl) > 1 else blk)[:1200]})
    if not sections:
        parts = [p.strip() for p in re.split(r"[.;\n]+", topic) if p.strip()]
        sections.append({"heading": f"1. {lbl['summary']}", "content": topic})
        if len(parts) > 1:
            sections.append({"heading": f"2. {lbl['section']}", "content": "\n".join(f"- {p}" for p in parts[:8])})
    if not headers or not rows:
        headers, rows = [lbl["section"], lbl["content"]], [[s["heading"], s["content"][:240]] for s in sections]
    summary = ctx[:320].replace("\n", " ") if ctx else topic[:320]
    return {"title": topic[:72].rstrip(".,;:") or lbl["report"], "summary": summary, "sections": sections, "table_headers": headers, "table_rows": rows}


def _build_csv(out_path: Path, *args: Any, **kwargs: Any) -> None:
    content = _unpack_doc_content(args, kwargs)
    lbl, buf = _labels(content.lang), io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    if content.headers and content.rows:
        w = len(content.headers)
        writer.writerow(content.headers)
        writer.writerows([r[i] if i < len(r) else "" for i in range(w)] for r in content.rows)
    else:
        writer.writerow([lbl["section"], lbl["content"]])
        writer.writerows([str(s.get("heading") or ""), str(s.get("content") or "")] for s in content.sections if isinstance(s, dict))
    out_path.write_text(buf.getvalue(), encoding="utf-8-sig")


def _compile_deliverable_file(out_dir: Path, file_id: str, fmt: str, content: _DocContent) -> Path:
    builders = {"xlsx": _build_xlsx, "docx": _build_docx, "csv": _build_csv, "pdf": _build_pdf}
    if fmt == "pptx":
        import deep_research as dr

        lbl, out_path = _labels(content.lang), out_dir / f"{file_id}.pptx"
        slides = [{"title": str(s.get("heading") or lbl["section"]), "bullets": [b.strip() for b in str(s.get("content") or "").split(". ") if b.strip()]} for s in content.sections if isinstance(s, dict)]
        if content.headers and content.rows:
            slides.append({"title": lbl["table_heading"], "bullets": [" | ".join(str(c) for c in r[: len(content.headers)]) for r in content.rows[:8]]})
        dr.build_pptx_presentation(title=content.title, subtitle=content.summary[:180], slides=slides, out_path=out_path)
        return out_path
    ext = fmt if fmt in builders else "pdf"
    out_path = out_dir / f"{file_id}.{ext}"
    builders[ext](out_path, content)
    return out_path


_NO_CONTENT_MSG = "Dosyanın içeriğini üretemedim (model yanıt vermedi ya da geçerli bir içerik döndürmedi). İsteğini kopyalayan boş bir dosya vermemek için oluşturmadım; lütfen tekrar dener misin? Konuyu biraz daha açarsan sonuç daha iyi olur."


async def generate_document_deliverable(prompt: str, fmt: str, context_text: str = "") -> dict[str, Any]:
    """Use local LLM to structure content and compile a real .xlsx, .docx, .pptx, .pdf, or .csv file."""
    model = await mms.pick_best_model("deep")
    file_id = f"doc-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    target_lang = _detect_requested_language(prompt)
    lbl = _labels(target_lang)
    schema_prompt = load_prompt("b3_document_factory_schema.txt").replace("{target_lang}", target_lang)
    user_msg = f"{prompt}\n\n{lbl['source_note']}\n{context_text[:8000]}" if context_text else prompt
    if (pages := re.search(r"(\d{1,2})\s*(?:sayfa|page)", prompt, re.I)) and not context_text:
        user_msg += f"\n\n[Not: Belge yaklaşık {pages.group(1)} sayfa olmalı: toplam en az {int(pages.group(1)) * 380} kelime, bölümleri ayrıntılı ve dolu yaz.]"
    if re.search(r"(grafik|chart|diyagram)", prompt, re.I) and not context_text:
        user_msg += "\n\n[Not: Grafik isteniyor. Tabloda 1 kategori sütunu ve en az 1 sayısal sütun olsun; sayısal sütun başlığına (örnek değerler) yaz.]"
    spec = _build_fallback_spec(prompt, context_text, target_lang)
    try:
        import gateway

        res = await gateway.default_client.chat([{"role": "system", "content": schema_prompt}, {"role": "user", "content": user_msg}], model=model, profile="factual", num_predict=3500, timeout_s=120.0, feature="document_factory", max_retries=0)
        parsed = _extract_json_object(res.content)
        if parsed and parsed.get("title"):
            spec.update(parsed)
        elif not context_text.strip():
            raise RuntimeError(_NO_CONTENT_MSG)
        else:
            logger.warning("document_factory: invalid JSON from LLM; using the uploaded source data only")
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as exc:
        if not context_text.strip():
            raise RuntimeError(_NO_CONTENT_MSG) from exc
        logger.warning("document_factory: LLM call failed (%s); using the uploaded source data only", exc)
    content = _DocContent(str(spec.get("title") or lbl["report"]), str(spec.get("summary") or ""), list(spec.get("sections") or []), [str(h) for h in (spec.get("table_headers") or [lbl["item"], lbl["content"], lbl["value"]])], list(spec.get("table_rows") or []), target_lang)
    out_path = _compile_deliverable_file(mms.media_dir(), file_id, fmt, content)
    return {"file_id": file_id, "format": fmt, "title": content.title, "summary": content.summary, "sections": content.sections, "table_headers": content.headers, "table_rows": content.rows, "model": model, "url": f"/api/assistant/media/{out_path.name}"}


def _xlsx_write_table(ws: Any, content: _DocContent, border: Border) -> tuple[list[int], set[int]]:
    last_col = get_column_letter(max(3, len(content.headers)))
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].value, ws["A1"].fill = content.title, PatternFill("solid", fgColor="1E293B")
    ws["A1"].font, ws["A1"].alignment = Font(name="Calibri", size=13, bold=True, color="FFFFFF"), Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"].value, ws["A2"].font = content.summary[:400], Font(name="Calibri", size=10, italic=True, color="334155")
    ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height, ws.row_dimensions[2].height = 32, max(24.0, min(64.0, math.ceil(max(1, len(content.summary[:400])) / 90) * 15.0 + 8.0))
    accent, zebra = PatternFill("solid", fgColor="4F46E5"), PatternFill("solid", fgColor="F8FAFC")
    col_widths = [max(14, min(36, len(h) + 6)) for h in content.headers]
    for ci, h in enumerate(content.headers, start=1):
        c = ws.cell(4, ci, h)
        c.font, c.fill, c.border, c.alignment = Font(name="Calibri", bold=True, color="FFFFFF", size=10.5), accent, border, Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 26
    numeric_cols: set[int] = set()
    derived = row_total_formula(content.headers, content.rows)
    for ri, rdata in enumerate(content.rows, start=5):
        row_strs: list[str] = []
        for ci in range(1, len(content.headers) + 1):
            raw_val = rdata[ci - 1] if ci - 1 < len(rdata) else ""
            val, num_fmt, is_num = _coerce_excel_cell(raw_val)
            if derived and ci == derived[0]:
                val, num_fmt, is_num = f"={get_column_letter(derived[1])}{ri}*{get_column_letter(derived[2])}{ri}", "#,##0.00", True
            if is_num:
                numeric_cols.add(ci)
            c = ws.cell(ri, ci, val)
            c.font, c.border, c.alignment = Font(name="Calibri", size=10), border, Alignment(vertical="center", wrap_text=True, horizontal="right" if is_num else "left")
            if num_fmt:
                c.number_format = num_fmt
            if (ri - 4) % 2 == 0:
                c.fill = zebra
            txt = str(raw_val)
            row_strs.append(txt)
            col_widths[ci - 1] = min(48, max(col_widths[ci - 1], len(txt) + 4))
        ws.row_dimensions[ri].height = _row_height(row_strs, col_widths)
    return col_widths, numeric_cols


def _xlsx_add_totals_and_chart(ws: Any, content: _DocContent, numeric_cols: set[int], border: Border) -> None:
    formula_cols = sorted(ci for ci in numeric_cols if ci >= 2)
    if not content.rows or not formula_cols:
        return
    lbl, total_fill = _labels(content.lang), PatternFill("solid", fgColor="E2E8F0")
    last_r = 4 + len(content.rows)
    sum_r, avg_r = last_r + 1, last_r + 2
    ws.cell(sum_r, 1, lbl["total"]).font = Font(name="Calibri", bold=True, color="1E293B")
    ws.cell(avg_r, 1, lbl["average"]).font = Font(name="Calibri", bold=True, color="334155")
    for ci in range(1, len(content.headers) + 1):
        ws.cell(sum_r, ci).fill, ws.cell(sum_r, ci).border, ws.cell(avg_r, ci).border = total_fill, border, border
    for ci in formula_cols:
        col_let = get_column_letter(ci)
        if not is_rate_column(content.headers[ci - 1]):
            sc = ws.cell(sum_r, ci, f"=SUM({col_let}5:{col_let}{last_r})")
            sc.font, sc.number_format = Font(name="Calibri", bold=True, color="1E293B"), "#,##0.00"
        if is_rate_column(content.headers[ci - 1]) or not row_total_formula(content.headers, content.rows):
            ac = ws.cell(avg_r, ci, f"=AVERAGE({col_let}5:{col_let}{last_r})")
            ac.font, ac.number_format = Font(name="Calibri", italic=True, color="334155"), "#,##0.00"
    ws.row_dimensions[sum_r].height, ws.row_dimensions[avg_r].height = 22, 20
    last_c = max(formula_cols)
    if len(content.rows) >= 2:
        col_let = get_column_letter(last_c)
        ws.conditional_formatting.add(f"{col_let}5:{col_let}{last_r}", ColorScaleRule(start_type="min", start_color="F8FAFC", mid_type="percentile", mid_value=50, mid_color="E0E7FF", end_type="max", end_color="A5B4FC"))
        chart = BarChart()
        chart.style, chart.width, chart.height = 10, 16, 9
        chart.title, chart.y_axis.title = f"{content.headers[last_c - 1]} {lbl['chart_suffix']}", content.headers[last_c - 1]
        chart.add_data(Reference(ws, min_col=last_c, min_row=4, max_row=last_r), titles_from_data=True)
        chart.set_categories(Reference(ws, min_col=1, max_col=1, min_row=5, max_row=last_r))
        ws.add_chart(chart, f"A{avg_r + 2}")


def _build_xlsx(out_path: Path, *args: Any, **kwargs: Any) -> None:
    content = _unpack_doc_content(args, kwargs)
    wb = Workbook()
    ws: Any = wb.active
    if ws is None:
        raise RuntimeError("Workbook active worksheet is unavailable")
    ws.title = _labels(content.lang)["sheet_data"]
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    col_widths, numeric_cols = _xlsx_write_table(ws, content, border)
    if content.headers and content.rows:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(content.headers))}{4 + len(content.rows)}"
    _xlsx_add_totals_and_chart(ws, content, numeric_cols, border)
    for ci, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.freeze_panes = "A5"
    if content.sections:
        ws2: Any = wb.create_sheet(_labels(content.lang)["sheet_notes"])
        ws2["A1"].value, ws2["A1"].font, ws2.column_dimensions["A"].width = content.title, Font(name="Calibri", size=13, bold=True, color="1E293B"), 96
        for idx, sec in enumerate(s for s in content.sections if isinstance(s, dict)):
            r_cur, body = 3 + idx * 3, str(sec.get("content") or "")
            ws2.cell(r_cur, 1, str(sec.get("heading") or "")).font = Font(name="Calibri", bold=True, size=11, color="1E293B")
            ws2.cell(r_cur + 1, 1, body).alignment = Alignment(wrap_text=True, vertical="top")
            ws2.row_dimensions[r_cur + 1].height = _row_height([body], [96], base=24.0)
    wb.save(str(out_path))


def _xml_el(parent: Any, tag: str, text: str | None = None, **attrs: str) -> Any:
    el = OxmlElement(tag)
    for k, v in attrs.items():
        el.set(qn(k.replace("__", ":")), v)
    if text is not None:
        el.text = text
    parent.append(el)
    return el


def _set_docx_cell_xml(cell: Any, fill_hex: str | None = None, pad_lr: int = 110, pad_tb: int = 80) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    if fill_hex:
        _xml_el(tc_pr, "w:shd", w__val="clear", w__color="auto", w__fill=fill_hex)
    tc_mar = _xml_el(tc_pr, "w:tcMar")
    for side, val in (("top", pad_tb), ("bottom", pad_tb), ("left", pad_lr), ("right", pad_lr)):
        _xml_el(tc_mar, f"w:{side}", w__w=str(val), w__type="dxa")


def _docx_style_run(run: Any, **style: Any) -> None:
    size = float(style.get("size", 10.0))
    run.font.name, run.font.size = str(style.get("font", "Calibri")), Pt(size)
    run.bold, run.italic = bool(style.get("bold", False)) or run.bold, bool(style.get("italic", False)) or run.italic
    if (rgb := style.get("rgb")) is not None:
        run.font.color.rgb = rgb


def _docx_add_inline_runs(paragraph: Any, text: str, *, size_pt: float = 10.0, rgb: RGBColor | None = None, force_bold: bool = False) -> None:
    for tok in _MD_INLINE_RE.split(text):
        if not tok:
            continue
        is_b = tok.startswith("**") and tok.endswith("**") and len(tok) > 4
        is_i = (not is_b) and tok.startswith("*") and tok.endswith("*") and len(tok) > 2
        is_c = tok.startswith("`") and tok.endswith("`") and len(tok) > 2
        clean = tok[2:-2] if is_b else (tok[1:-1] if (is_i or is_c) else tok)
        _docx_style_run(paragraph.add_run(clean), size=size_pt - 0.5 if is_c else size_pt, bold=is_b or force_bold, italic=is_i, rgb=rgb, font="Consolas" if is_c else "Calibri")


_CHART_WORD = {"Türkçe": "Grafik", "English": "Chart", "German": "Diagramm"}


def _chart_title(content: _DocContent) -> str:
    return f"{content.title[:48]} - {_CHART_WORD.get(content.lang, 'Chart')}"


def _docx_col_widths(content: _DocContent) -> list[float]:
    lens = [max([len(str(h))] + [len(format_cell(r[i], str(h), content.lang)[0]) for r in content.rows if i < len(r)]) for i, h in enumerate(content.headers)]
    weights = [min(max(x, 5), 28) for x in lens]
    total = float(sum(weights)) or 1.0
    return [6.8 * w / total for w in weights]


def _docx_add_chart(doc: Any, content: _DocContent) -> None:
    from io import BytesIO

    png = render_bar_chart_png(content.headers, content.rows, _chart_title(content), _find_unicode_fonts())
    if png is None:
        return
    h = doc.add_heading(_CHART_WORD.get(content.lang, "Chart"), level=1)
    for r in h.runs:
        _docx_style_run(r, size=13.0, bold=True, rgb=RGBColor(0x1E, 0x29, 0x3B))
    doc.add_picture(BytesIO(png), width=Inches(6.6))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def _docx_add_table(doc: Any, content: _DocContent) -> None:
    h = doc.add_heading(_labels(content.lang)["table_heading"], level=1)
    for r in h.runs:
        _docx_style_run(r, size=13.0, bold=True, rgb=RGBColor(0x1E, 0x29, 0x3B))
    tbl = doc.add_table(rows=1, cols=len(content.headers))
    tbl.style, tbl.autofit, widths = "Table Grid", False, [Inches(w) for w in _docx_col_widths(content)]
    num_cols = {i for i, hd in enumerate(content.headers) if content.rows and all(format_cell(r[i], str(hd), content.lang)[1] for r in content.rows if i < len(r) and str(r[i]).strip())}
    tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
    _xml_el(tr_pr, "w:cantSplit")
    _xml_el(tr_pr, "w:tblHeader")
    for i, hdr in enumerate(content.headers):
        cell = tbl.rows[0].cells[i]
        cell.width, cell.paragraphs[0].text = widths[i], ""
        _set_docx_cell_xml(cell, fill_hex="1E293B")
        _docx_add_inline_runs(cell.paragraphs[0], str(hdr), size_pt=9.5, rgb=RGBColor(0xFF, 0xFF, 0xFF), force_bold=True)
        if i in num_cols:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r_idx, rdata in enumerate(content.rows):
        row = tbl.add_row()
        _xml_el(row._tr.get_or_add_trPr(), "w:cantSplit")
        for i in range(len(content.headers)):
            cell = row.cells[i]
            cell.width, cell.paragraphs[0].text = widths[i], ""
            _set_docx_cell_xml(cell, fill_hex="F8FAFC" if r_idx % 2 == 1 else None)
            text = format_cell(rdata[i], str(content.headers[i]), content.lang)[0] if i < len(rdata) else ""
            _docx_add_inline_runs(cell.paragraphs[0], text, size_pt=9.0, rgb=RGBColor(0x1E, 0x29, 0x3B))
            if i in num_cols:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if chart_series(content.headers, content.rows):
        _docx_add_chart(doc, content)


def _docx_add_header_footer(sec0: Any, content: _DocContent, muted: RGBColor) -> None:
    hp, fp = sec0.header.paragraphs[0], sec0.footer.paragraphs[0]
    hp.alignment = fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _docx_style_run(hp.add_run(content.title[:90]), size=8.5, rgb=muted)
    page_prefix = _labels(content.lang)["page_fmt"].split("{page}")[0]
    for txt, fld in ((page_prefix, "PAGE"), (" / ", "NUMPAGES")):
        _docx_style_run(fp.add_run(txt), size=8.5, rgb=muted)
        for kind, instr in (("begin", None), (None, f" {fld} "), ("separate", None), ("end", None)):
            run = fp.add_run()
            _docx_style_run(run, size=8.5, rgb=muted)
            _xml_el(run._r, "w:fldChar", w__fldCharType=kind) if kind else _xml_el(run._r, "w:instrText", text=instr, xml__space="preserve")


def _docx_add_section_body(doc: Any, body: str) -> None:
    for line in (ln.strip() for ln in body.splitlines() if ln.strip()):
        if m_bul := re.match(r"^(?:[-*\u2022])\s+(.+)$", line):
            _docx_add_inline_runs(doc.add_paragraph(style="List Bullet"), m_bul.group(1))
        elif m_num := re.match(r"^\d+[.)]\s+(.+)$", line):
            _docx_add_inline_runs(doc.add_paragraph(style="List Number"), m_num.group(1))
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(5)
            _docx_add_inline_runs(p, line)


def _build_docx(out_path: Path, *args: Any, **kwargs: Any) -> None:
    content = _unpack_doc_content(args, kwargs)
    doc = Document()
    normal_style: Any = doc.styles["Normal"]
    normal_style.font.name, normal_style.font.size = "Calibri", Pt(10.0)
    sec0, muted = doc.sections[0], RGBColor(0x64, 0x74, 0x8B)
    sec0.top_margin, sec0.bottom_margin, sec0.left_margin, sec0.right_margin = Inches(0.8), Inches(0.8), Inches(0.85), Inches(0.85)
    _docx_add_header_footer(sec0, content, muted)
    banner = doc.add_table(rows=1, cols=1)
    banner.autofit, bcell = False, banner.rows[0].cells[0]
    bcell.width = Inches(6.8)
    _set_docx_cell_xml(bcell, fill_hex="1E293B", pad_lr=180, pad_tb=160)
    bcell.paragraphs[0].paragraph_format.space_after = Pt(4)
    _docx_style_run(bcell.paragraphs[0].add_run(content.title), size=16.0, bold=True, rgb=RGBColor(0xFF, 0xFF, 0xFF))
    _docx_style_run(bcell.add_paragraph().add_run(datetime.now(UTC).strftime("%Y-%m-%d")), size=8.5, rgb=RGBColor(0xCB, 0xD5, 0xE1))
    if content.summary:
        p_sum = doc.add_paragraph()
        p_sum.paragraph_format.space_before, p_sum.paragraph_format.space_after = Pt(10), Pt(8)
        _docx_add_inline_runs(p_sum, content.summary, size_pt=10.5, rgb=RGBColor(0x33, 0x41, 0x55))
    lbl = _labels(content.lang)
    for sec in (s for s in content.sections if isinstance(s, dict)):
        for r in doc.add_heading(str(sec.get("heading") or lbl["section"]), level=1).runs:
            _docx_style_run(r, size=13.0, bold=True, rgb=RGBColor(0x1E, 0x29, 0x3B))
        _docx_add_section_body(doc, str(sec.get("content") or ""))
    if content.headers and content.rows:
        _docx_add_table(doc, content)
    doc.save(str(out_path))


def _pdf_new_page(doc: fitz.Document, fonts: tuple[str | None, str | None, str, str]) -> fitz.Page:
    reg_font, bold_font, fn_reg, fn_bold = fonts
    page = doc.new_page(width=595, height=842)
    if reg_font:
        page.insert_font(fontname=fn_reg, fontfile=reg_font)
    if bold_font:
        page.insert_font(fontname=fn_bold, fontfile=bold_font)
    return page


def _pdf_draw_lines(
    doc: fitz.Document, page: fitz.Page, y: float, lines: list[str], fonts: tuple[str | None, str | None, str, str],
    **style: Any,
) -> tuple[fitz.Page, float]:
    fontname, fontsize, line_h, color = str(style["fontname"]), float(style["fontsize"]), float(style["line_h"]), style["color"]
    for ln in lines:
        if y + line_h > 792:
            page, y = _pdf_new_page(doc, fonts), 48.0
        if ln:
            page.insert_text((36, y + fontsize), ln, fontname=fontname, fontsize=fontsize, color=color)
        y += line_h
    return page, y


def _pdf_render_table(
    doc: fitz.Document, page: fitz.Page, y: float, content: _DocContent,
    pdf_ctx: tuple[tuple[str | None, str | None, str, str], tuple[fitz.Font, fitz.Font], list[list[Any]]],
) -> tuple[fitz.Page, float]:
    fonts, measure, toc = pdf_ctx
    _reg, _bold, fn_reg, fn_bold = fonts
    f_reg, f_bold = measure
    col_w = 523.0 / max(1, len(content.headers))

    num_cols = {i for i, hd in enumerate(content.headers) if content.rows and all(format_cell(r[i], str(hd), content.lang)[1] for r in content.rows if i < len(r) and str(r[i]).strip())}

    def _draw_row(pg: fitz.Page, yp: float, cells: list[list[str]], *, is_hdr: bool = False, zebra: bool = False) -> float:
        rh = max(24.0 if is_hdr else 20.0, max(len(c) for c in cells) * 11.5 + 8.0)
        if is_hdr:
            pg.draw_rect(fitz.Rect(36, yp, 559, yp + rh), color=(0.31, 0.27, 0.9), fill=(0.31, 0.27, 0.9))
        else:
            if zebra:
                pg.draw_rect(fitz.Rect(36, yp, 559, yp + rh), color=(0.95, 0.96, 0.98), fill=(0.95, 0.96, 0.98))
            pg.draw_rect(fitz.Rect(36, yp, 559, yp + rh), color=(0.82, 0.85, 0.89), width=0.5)
        grid_c, txt_c, fn = ((0.45, 0.42, 0.95), (1, 1, 1), fn_bold) if is_hdr else ((0.82, 0.85, 0.89), (0.1, 0.12, 0.16), fn_reg)
        for i, lns in enumerate(cells):
            x0 = 36 + i * col_w
            if i > 0:
                pg.draw_line((x0, yp), (x0, yp + rh), color=grid_c, width=0.5)
            for li, ln in enumerate(lns):
                tx = x0 + col_w - 4 - (f_bold if is_hdr else f_reg).text_length(ln, fontsize=8.5) if i in num_cols else x0 + 4
                pg.insert_text((tx, yp + 12 + li * 11.5), ln, fontname=fn, fontsize=8.5, color=txt_c)
        return yp + rh

    if y > 700:
        page, y = _pdf_new_page(doc, fonts), 48.0
    tbl_title = _labels(content.lang)["table_heading"]
    toc.append([1, tbl_title, len(doc)])
    page.insert_text((36, y + 11.5), tbl_title, fontname=fn_bold, fontsize=11.5, color=(0.12, 0.16, 0.23))
    hdr_cells = [_pdf_wrap_lines(h, max(24.0, col_w - 8.0), f_bold, 8.5) for h in content.headers]
    y = _draw_row(page, y + 18.0, hdr_cells, is_hdr=True)
    for r_idx, rdata in enumerate(content.rows):
        cells = [_pdf_wrap_lines(format_cell(rdata[i], str(content.headers[i]), content.lang)[0] if i < len(rdata) else "", max(24.0, col_w - 8.0), f_reg, 8.5) for i in range(len(content.headers))]
        if y + max(20.0, max(len(c) for c in cells) * 11.5 + 8.0) > 792:
            page = _pdf_new_page(doc, fonts)
            y = _draw_row(page, 48.0, hdr_cells, is_hdr=True)
        y = _draw_row(page, y, cells, zebra=r_idx % 2 == 1)
    return page, y


def _pdf_add_chart(doc: fitz.Document, page: fitz.Page, y: float, content: _DocContent, ctx: tuple[tuple[str | None, str | None, str, str], list[list[Any]]]) -> None:
    fonts, toc = ctx
    reg_font, bold_font, _fn_reg, fn_bold = fonts
    png = render_bar_chart_png(content.headers, content.rows, _chart_title(content), (reg_font, bold_font))
    if png is None:
        return
    chart_h = 523.0 * 820 / 1600
    if y + chart_h + 30 > 792:
        page, y = _pdf_new_page(doc, fonts), 48.0
    word = _CHART_WORD.get(content.lang, "Chart")
    toc.append([1, word, len(doc)])
    page.insert_text((36, y + 24), word, fontname=fn_bold, fontsize=11.5, color=(0.12, 0.16, 0.23))
    page.insert_image(fitz.Rect(36, y + 32, 559, y + 32 + chart_h), stream=png)


def _build_pdf(out_path: Path, *args: Any, **kwargs: Any) -> None:
    """Build a multi-page Unicode/Turkish-safe PDF with embedded TrueType fonts, dynamic wrapping, and TOC."""
    content = _unpack_doc_content(args, kwargs)
    reg_font, bold_font = _find_unicode_fonts()
    fn_reg, fn_bold = ("tr_reg" if reg_font else "helv"), ("tr_bold" if bold_font else "hebo")
    fonts = (reg_font, bold_font, fn_reg, fn_bold)
    f_reg, f_bold = (fitz.Font(fontfile=reg_font) if reg_font else fitz.Font("helv")), (fitz.Font(fontfile=bold_font) if bold_font else fitz.Font("hebo"))
    doc = fitz.open()
    page, title_lines = _pdf_new_page(doc, fonts), _pdf_wrap_lines(content.title, 523.0, f_bold, 15.0)
    banner_h = max(68.0, 28.0 + len(title_lines) * 20.0)
    page.draw_rect(fitz.Rect(0, 0, 595, banner_h), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
    page.draw_rect(fitz.Rect(0, banner_h - 3, 595, banner_h), color=(0.31, 0.27, 0.9), fill=(0.31, 0.27, 0.9))
    for i, tl in enumerate(title_lines):
        page.insert_text((36, 30 + i * 20.0), tl, fontname=fn_bold, fontsize=15.0, color=(1, 1, 1))
    y, toc = banner_h + 16.0, []
    if content.summary:
        page, y = _pdf_draw_lines(doc, page, y, _pdf_wrap_lines(content.summary, 523.0, f_reg, 10.0), fonts, fontname=fn_reg, fontsize=10.0, line_h=14.5, color=(0.15, 0.2, 0.28))
        y += 8.0
    for sec in (s for s in content.sections if isinstance(s, dict)):
        heading, body = str(sec.get("heading") or ""), str(sec.get("content") or "")
        h_lines, b_lines = _pdf_wrap_lines(heading, 523.0, f_bold, 11.5), _pdf_wrap_lines(body, 523.0, f_reg, 9.5)
        if y + len(h_lines) * 16.0 + 34.0 > 792:
            page, y = _pdf_new_page(doc, fonts), 48.0
        if heading.strip():
            toc.append([1, heading.strip()[:120], len(doc)])
        page, y = _pdf_draw_lines(doc, page, y, h_lines, fonts, fontname=fn_bold, fontsize=11.5, line_h=16.0, color=(0.12, 0.16, 0.23))
        page.draw_line((36, y), (559, y), color=(0.82, 0.85, 0.89), width=0.5)
        page, y = _pdf_draw_lines(doc, page, y + 6.0, b_lines, fonts, fontname=fn_reg, fontsize=9.5, line_h=13.5, color=(0.2, 0.24, 0.3))
        y += 10.0
    if content.headers and content.rows:
        page, y = _pdf_render_table(doc, page, y, content, (fonts, (f_reg, f_bold), toc))
        _pdf_add_chart(doc, page, y, content, (fonts, toc))
    if toc:
        doc.set_toc(toc)
    lbl, doc_pages = _labels(content.lang), doc
    for idx, pg in enumerate(doc_pages, start=1):
        pg.draw_line((36, 808), (559, 808), color=(0.85, 0.88, 0.92), width=0.5)
        pg.insert_text((36, 824), content.title[:60], fontname=fn_reg, fontsize=8.0, color=(0.5, 0.55, 0.62))
        pg.insert_text((485, 824), lbl["page_fmt"].format(page=idx, total=len(doc_pages)), fontname=fn_reg, fontsize=8.5, color=(0.45, 0.5, 0.58))
    doc.save(str(out_path), deflate=True, garbage=3)
    doc.close()
