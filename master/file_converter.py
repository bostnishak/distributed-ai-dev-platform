"""Universal Bidirectional File Converter & ZIP Archive Manager.

Supports bidirectional conversion across PDF, DOCX, PPTX, XLSX, CSV, TSV, TXT, MD, JSON,
multi-folder ZIP creation (preserving relative paths + empty dirs), SEC-07 safe ZIP extraction,
and existing-workspace zipping without hijacking new-project creation prompts.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
import zipfile
from collections import Counter
from datetime import UTC, datetime
from itertools import zip_longest
from pathlib import Path
from typing import Any

import pymupdf as fitz
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

import deep_research as dr
import document_factory as df
import multimodal_studio as mms
import safe_archive

TARGET_FMT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("docx", ("docx", "word")), ("pptx", ("pptx", "powerpoint", "sunum", "slayt")),
    ("pdf", ("pdf",)), ("xlsx", ("xlsx", "excel")), ("csv", ("csv",)),
    ("txt", ("txt", "metin dosyası", "metin dosyasi")), ("md", ("markdown", ".md", "md")), ("json", ("json",)),
]

_TARGET_FMT_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    ("docx", re.compile(r"\b(?:docx(?:'?(?:y?[ae]|e|a))?|word(?:'?[ae]|a|e)?)\b")),
    ("pptx", re.compile(r"\b(?:pptx(?:'?(?:y?[ae]|e|a))?|powerpoint(?:'?[ae])?|sunum(?:a|u|la|lar|luk)?|slayt(?:a|lar|ı|i)?)\b")),
    ("pdf", re.compile(r"\bpdf(?:'?(?:y?[ae]|e|a))?\b")),
    ("xlsx", re.compile(r"\b(?:xlsx(?:'?(?:y?[ae]|e|a))?|excel(?:'?[ae]|e|a)?)\b")),
    ("csv", re.compile(r"\bcsv(?:'?(?:y?[ae]|e|a))?\b")),
    ("txt", re.compile(r"\b(?:txt(?:'?(?:y?[ae]|e|a))?|metin\s+dosyas[ıi]\w*)\b")),
    ("md", re.compile(r"(?<!\w)(?:\.md|markdown(?:'?[ae])?|md(?:'?(?:ye|e|a))?)\b")),
    ("json", re.compile(r"\bjson(?:'?[ae]|a|e)?\b")),
]

CONVERT_VERBS = ("çevir", "cevir", "dönüştür", "donustur", "aktar", "yap", "haline getir", "convert", "export")
_STRONG_VERB_RE = re.compile(
    r"\b(?:çevir\w*|cevir\w*|dönüştür\w*|donustur\w*|aktar\w*|haline\s+getir\w*|convert\w*|export\w*)\b"
)
_TO_PREPOSITION_RE = re.compile(r"\b(?:to|into)\b")
_YAP_VERB_RE = re.compile(r"\byap(?:ıp|ip|alım|alim|ar|sın|sin|tır|tir)?\b")
_ANALYSIS_BEFORE_YAP_RE = re.compile(
    r"\b(?:özet|ozet|analiz|inceleme|kontrol|yorum|hesap|değerlendirme|degerlendirme|karşılaştırma|karsilastirma|tarama|test)\s+yap\w*\b"
)
_FOR_CLAUSE_RE = re.compile(r"^\s*(?:için|icin|adına|adina|amacıyla|amac[ıi]yla)\b")
_PROJECT_CREATE_VERB_RE = re.compile(
    r"\b(?:oluştur(?!duğ|dug)\w*|olustur(?!duğ|dug)\w*|kur(?!duğ|dug)\w*|yaz(?!dığ|dig)\w*"
    r"|tasarla(?!dığ|dig)\w*|geliştir\w*|gelistir\w*|üret\w*|uret\w*|kodla\w*|hazırla(?!dığ|dig)\w*"
    r"|hazirla(?!dığ|dig)\w*|yap(?!tığ|tig)(?:ıp|ip|alım|alim|sın|sin|ar)?|build\w*|create\w*|generate\w*|scaffold\w*|make)\b"
)
_PROJECT_SPEC_RE = re.compile(
    r"(?:\b(?:docs|src|tests|app|public|assets|components|scripts)/|\b(?:proje\s+klasör\w*|klasör\w*\s+oluştur"
    r"|yeni\s+(?:bir\s+)?proje|sıfırdan|sifirdan|web\s+sitesi|website|uygulama|oyun|game|backend|frontend"
    r"|fastapi|flask|django|react|dashboard|landing\s+page|içinde\s+\w+/|icinde\s+\w+/)\b)"
)

ZIP_PACK_CUES = (
    "ziple", "zip yap", "zip'le", "zipe al", "zip'e al", "zip oluştur", "zip olustur",
    "klasöre al", "klasore al", "klasörle", "klasorle", "sıkıştır", "sikistir", "arşivle", "arsivle",
)
ZIP_EXTRACT_CUES = (
    "zipi aç", "zip'i aç", "zipi ac", "zip'i ac", "içini aç", "icini ac", "içini çıkar", "icini cikar",
    "arşivi aç", "arsivi ac", "dosyaları çıkar", "dosyalari cikar", "unzip", "extract", "ayıkla", "ayikla",
)
_MAX_TABLE_ROWS = 1000
_MAX_ZIP_EXTRACT_FILES = 100


def _safe_stem(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_\-]+", "_", Path(name or "dosya").stem).strip("_")
    return (clean or "dosya")[:48]


def _collect_format_mentions(low: str, ext: str) -> list[tuple[str, int, int]]:
    mentions: list[tuple[str, int, int]] = []
    for fmt, pattern in _TARGET_FMT_REGEXES:
        if fmt == ext:
            continue
        for match in pattern.finditer(low):
            if not _FOR_CLAUSE_RE.match(low[match.end() :]):
                mentions.append((fmt, match.start(), match.end()))
    return mentions


def _find_target_format(low: str, ext: str) -> str | None:
    mentions = _collect_format_mentions(low, ext)
    if not mentions:
        return None
    strong_verbs = list(_STRONG_VERB_RE.finditer(low))
    if strong_verbs:
        to_matches = list(_TO_PREPOSITION_RE.finditer(low))
        after_to = [
            (m_start - tm.end(), fmt)
            for tm in to_matches
            for fmt, m_start, _ in mentions
            if 0 <= m_start - tm.end() <= 24
        ]
        if after_to:
            return min(after_to, key=lambda item: item[0])[1]
        scored = [
            (
                max(0, min(v.start() - m_end if m_end <= v.start() else (m_start - v.end()) + 12 for v in strong_verbs)),
                fmt,
            )
            for fmt, m_start, m_end in mentions
        ]
        return min(scored, key=lambda item: item[0])[1]

    yap_matches = list(_YAP_VERB_RE.finditer(_ANALYSIS_BEFORE_YAP_RE.sub(" ", low)))
    if not yap_matches:
        return None
    adj = [
        (ym.start() - m_end, fmt)
        for fmt, _, m_end in mentions
        for ym in yap_matches
        if 0 <= ym.start() - m_end <= 22
        and low[m_end : ym.start()].strip() in ("", "dosyası", "dosyasi", "belgesi", "olarak", "tablosu", "formatı", "formati")
    ]
    return min(adj, key=lambda item: item[0])[1] if adj else None


def _is_existing_project_zip_request(low: str) -> bool:
    has_proj = any(k in low for k in ("proje", "çalışma alanı", "calisma alani", "workspace"))
    has_zip = any(z in low for z in ("ziple", "zip'le", "zip yap", "sıkıştır", "sikistir", "zip olarak", "zip indir", "arşivle", "arsivle"))
    if not (has_proj and has_zip):
        return False
    without_zip_yap = re.sub(r"\b(?:zip|arşiv|arsiv)\s+yap\w*\b", " ", low)
    return not (_PROJECT_CREATE_VERB_RE.search(without_zip_yap) or _PROJECT_SPEC_RE.search(low))


def detect_conversion_or_archive_action(prompt: str, filename: str | None) -> dict[str, Any] | None:
    """Detect whether the user wants file conversion, folder+ZIP packing, ZIP extraction, or project zipping."""
    low = (prompt or "").lower()
    if not filename:
        return {"action": "zip_project"} if _is_existing_project_zip_request(low) else None

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "zip" and any(k in low for k in ZIP_EXTRACT_CUES):
        return {"action": "extract_zip"}

    wants_zip = ext != "zip" and any(k in low for k in ZIP_PACK_CUES)
    target_fmt = _find_target_format(low, ext)
    if target_fmt and wants_zip:
        return {"action": "convert_and_zip", "target_fmt": target_fmt}
    if target_fmt:
        return {"action": "convert", "target_fmt": target_fmt}
    return {"action": "pack_zip"} if wants_zip else None


def _decode_text_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_pdf_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    doc: Any = fitz.open(stream=raw, filetype="pdf")
    sections, pages_text = [], []
    try:
        for idx, pg in enumerate(doc, start=1):
            t = (pg.get_text("text") or "").strip()
            pages_text.append(t)
            if t:
                lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
                sections.append({"heading": f"Sayfa {idx}: {lines[0][:90] if lines else f'Sayfa {idx}'}", "content": "\n".join(lines[1:]) if len(lines) > 1 else t})
    finally:
        doc.close()
    return sections, [], [], "\n\n".join(pages_text)


def _extract_docx_structured(raw: bytes, title: str) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    doc = Document(io.BytesIO(raw))
    sections, headers, rows, all_lines = [], [], [], []
    cur_heading, cur_paras = title, []
    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        all_lines.append(txt)
        style_name = (p.style.name or "").lower() if p.style else ""
        if "heading" in style_name or "title" in style_name:
            if cur_paras:
                sections.append({"heading": cur_heading, "content": "\n".join(cur_paras)})
                cur_paras = []
            cur_heading = txt[:100]
        else:
            cur_paras.append(txt)
    if cur_paras:
        sections.append({"heading": cur_heading, "content": "\n".join(cur_paras)})
    for t_idx, table in enumerate(doc.tables, start=1):
        t_rows = [r for r in ([c.text.strip().replace("\n", " ") for c in row.cells] for row in table.rows) if any(r)]
        if not t_rows:
            continue
        table_lines = [" | ".join(r) for r in t_rows]
        all_lines.extend(table_lines)
        if not headers:
            headers = [c or f"Sütun {i + 1}" for i, c in enumerate(t_rows[0])]
            rows = t_rows[1:_MAX_TABLE_ROWS]
        else:
            sections.append({"heading": f"Tablo {t_idx}", "content": "\n".join(table_lines)})
    return sections, headers, rows, "\n".join(all_lines)


def _collect_slide_texts(slide: Any, headers: list[str], rows: list[list[Any]]) -> tuple[list[str], list[str], list[list[Any]]]:
    slide_texts: list[str] = []
    for shape in slide.shapes:
        if getattr(shape, "has_table", False) and (tbl := getattr(shape, "table", None)) is not None:
            t_rows = [r for r in ([c.text.strip().replace("\n", " ") for c in row.cells] for row in tbl.rows) if any(r)]
            if t_rows:
                slide_texts.extend(" | ".join(r) for r in t_rows)
                if not headers:
                    headers = [c or f"Sütun {i + 1}" for i, c in enumerate(t_rows[0])]
                    rows = t_rows[1:_MAX_TABLE_ROWS]
        elif getattr(shape, "has_text_frame", False) and (tf := getattr(shape, "text_frame", None)) is not None:
            if (st := (getattr(tf, "text", "") or "").strip()):
                slide_texts.append(st)
    if getattr(slide, "has_notes_slide", False):
        ntf = getattr(getattr(slide, "notes_slide", None), "notes_text_frame", None)
        if ntf is not None and (notes_txt := (getattr(ntf, "text", "") or "").strip()):
            slide_texts.append(f"Konuşmacı Notları: {notes_txt}")
    return slide_texts, headers, rows


def _extract_pptx_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    prs = Presentation(io.BytesIO(raw))
    sections, headers, rows, all_lines = [], [], [], []
    for idx, slide in enumerate(prs.slides, start=1):
        slide_texts, headers, rows = _collect_slide_texts(slide, headers, rows)
        if slide_texts:
            heading = slide_texts[0].splitlines()[0][:100]
            body = "\n".join(slide_texts[1:]) if len(slide_texts) > 1 else slide_texts[0]
            sections.append({"heading": f"Slayt {idx}: {heading}", "content": body})
            all_lines.append(f"## Slayt {idx}: {heading}\n{body}")
    return sections, headers, rows, "\n\n".join(all_lines)


def _extract_xlsx_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    wb_val = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    wb_fml = None
    sections, headers, rows, raw_blocks = [], [], [], []
    try:
        wb_fml = load_workbook(io.BytesIO(raw), read_only=True, data_only=False)
        multi_sheet = len(wb_val.worksheets) > 1
        for sheet_val in wb_val.worksheets:
            sheet_fml = wb_fml[sheet_val.title]
            non_empty: list[list[Any]] = []
            for row_val, row_fml in zip_longest(
                sheet_val.iter_rows(values_only=True), sheet_fml.iter_rows(values_only=True), fillvalue=()
            ):
                merged = [v if v is not None else (f if f is not None else "") for v, f in zip_longest(row_val, row_fml, fillvalue=None)]
                if any(str(c).strip() for c in merged):
                    non_empty.append(merged)
                    if len(non_empty) > _MAX_TABLE_ROWS:
                        break
            if not non_empty:
                continue
            sheet_lines = [" | ".join(str(c) for c in r) for r in non_empty]
            raw_blocks.append(f"--- Sayfa: {sheet_val.title} ---\n" + "\n".join(sheet_lines))
            if not headers:
                headers = [str(c).strip() or f"Sütun {i + 1}" for i, c in enumerate(non_empty[0])]
                rows = non_empty[1 : _MAX_TABLE_ROWS + 1]
            if multi_sheet:
                sections.append({"heading": f"Sayfa: {sheet_val.title}", "content": "\n".join(sheet_lines[:200])})
    finally:
        wb_val.close()
        if wb_fml is not None:
            wb_fml.close()
    return sections, headers, rows, "\n\n".join(raw_blocks)


def _extract_csv_structured(raw: bytes, *, is_tsv: bool = False) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    txt = _decode_text_bytes(raw)
    first_line = txt.splitlines()[0] if txt.splitlines() else ""
    if is_tsv:
        delim = "\t"
    else:
        tab_c, semi_c, comma_c = first_line.count("\t"), first_line.count(";"), first_line.count(",")
        delim = "\t" if (tab_c > 0 and tab_c >= semi_c and tab_c >= comma_c) else (";" if semi_c > comma_c else ",")
    non_empty = [r for r in csv.reader(io.StringIO(txt), delimiter=delim) if any(c.strip() for c in r)]
    headers = [c.strip() or f"Sütun {i + 1}" for i, c in enumerate(non_empty[0])] if non_empty else []
    rows = non_empty[1 : _MAX_TABLE_ROWS + 1] if non_empty else []
    return [], headers, rows, txt


def _json_cell(val: Any) -> str:
    if val is None:
        return ""
    return json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)


def _parse_json_structured(raw_text: str) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str] | None:
    if not raw_text.lstrip().startswith(("{", "[")):
        return None
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
    sections, headers, rows = [], [], []
    if isinstance(parsed, list) and parsed and all(isinstance(item, dict) for item in parsed):
        keys: list[str] = []
        for item in parsed[:_MAX_TABLE_ROWS]:
            keys.extend(str(k) for k in item if str(k) not in keys)
        headers = keys
        rows = [[_json_cell(item.get(k)) for k in keys] for item in parsed[:_MAX_TABLE_ROWS]]
        sections.append({"heading": f"JSON Kayıtları ({len(parsed)} öğe)", "content": "\n".join(" | ".join(r) for r in rows[:40])})
    elif isinstance(parsed, dict):
        for k, v in list(parsed.items())[:40]:
            val_txt = json.dumps(v, ensure_ascii=False, indent=2) if isinstance(v, (dict, list)) else str(v)
            sections.append({"heading": str(k)[:90], "content": val_txt[:2000]})
        headers = ["Anahtar", "Değer"]
        rows = [[str(k), _json_cell(v)] for k, v in list(parsed.items())[:_MAX_TABLE_ROWS]]
    elif isinstance(parsed, list):
        headers = ["Değer"]
        rows = [[_json_cell(x)] for x in parsed[:_MAX_TABLE_ROWS]]
        sections.append({"heading": f"JSON Liste ({len(parsed)} öğe)", "content": "\n".join(f"- {r[0]}" for r in rows[:50])})
    return sections, headers, rows, pretty


def _extract_plain_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    raw_text = _decode_text_bytes(raw)
    if (json_parsed := _parse_json_structured(raw_text)) is not None:
        return json_parsed
    sections: list[dict[str, str]] = []
    for idx, blk in enumerate([b.strip() for b in re.split(r"\n{2,}", raw_text) if b.strip()][:30], start=1):
        lines = blk.splitlines()
        heading = lines[0].lstrip("# ").strip()[:90] if lines else f"Bölüm {idx}"
        sections.append({"heading": heading, "content": "\n".join(lines[1:]).strip() if len(lines) > 1 else blk})
    return sections, [], [], raw_text


def extract_structured_content(filename: str, raw: bytes) -> dict[str, Any]:
    """Extract normalized title, sections, tables, and raw text from PDF/DOCX/PPTX/XLSX/CSV/TSV/TXT/MD/JSON."""
    ext = Path(filename).suffix.lower().lstrip(".")
    title = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Dönüştürülen Belge"
    if ext == "pdf":
        sections, headers, rows, raw_text = _extract_pdf_structured(raw)
    elif ext == "docx":
        sections, headers, rows, raw_text = _extract_docx_structured(raw, title)
    elif ext == "pptx":
        sections, headers, rows, raw_text = _extract_pptx_structured(raw)
    elif ext in ("xlsx", "xlsm"):
        sections, headers, rows, raw_text = _extract_xlsx_structured(raw)
    elif ext in ("csv", "tsv"):
        sections, headers, rows, raw_text = _extract_csv_structured(raw, is_tsv=(ext == "tsv"))
    else:
        sections, headers, rows, raw_text = _extract_plain_structured(raw)
    if not sections and raw_text:
        sections.append({"heading": "İçerik Özeti", "content": raw_text[:4000]})
    summary = (raw_text[:320].replace("\n", " ").strip() + "...") if len(raw_text) > 320 else raw_text.replace("\n", " ").strip()
    return {"title": title, "summary": summary, "sections": sections, "headers": headers, "rows": rows, "raw_text": raw_text}


def _write_pptx_output(out_path: Path, filename: str, data: dict[str, Any]) -> None:
    slides = []
    for idx, s in enumerate(data["sections"][:14], start=1):
        raw_lines = [ln.strip("•-* \t") for ln in re.split(r"[\n]+|(?<=\.)\s+", s["content"]) if ln.strip()]
        slides.append({
            "kicker": f"BÖLÜM {idx}", "title": s["heading"][:80],
            "bullets": raw_lines[:5] or [s["content"][:220]], "key_fact": raw_lines[0][:140] if raw_lines else "",
        })
    if data["headers"] and data["rows"]:
        slides.append({
            "kicker": "TABLO ÖZETİ", "title": "Veri Tablosu Özeti",
            "bullets": [" | ".join(str(c) for c in r[: len(data["headers"])]) for r in data["rows"][:6]],
        })
    dr.build_pptx_presentation(
        title=data["title"], subtitle=data["summary"][:160] or f"{filename} dosyasından dönüştürüldü",
        slides=slides, out_path=out_path,
    )


def _write_csv_output(out_path: Path, data: dict[str, Any]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if data["headers"]:
        writer.writerow(data["headers"])
        writer.writerows(data["rows"])
    else:
        writer.writerow(["Bölüm", "İçerik"])
        writer.writerows([s["heading"], s["content"]] for s in data["sections"])
    out_path.write_text(buf.getvalue(), encoding="utf-8-sig")


def _write_md_output(out_path: Path, data: dict[str, Any]) -> None:
    esc = lambda v: str("" if v is None else v).replace("|", "\\|").replace("\n", " ").strip()  # noqa: E731
    md_lines = [f"# {data['title']}", ""]
    for s in data["sections"]:
        md_lines.extend([f"## {s['heading']}", "", s["content"], ""])
    headers, rows = data.get("headers") or [], data.get("rows") or []
    if headers and rows:
        md_lines.extend([
            "## Veri Tablosu", "",
            "| " + " | ".join(esc(h) for h in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ])
        col_count = len(headers)
        for row in rows:
            padded = list(row[:col_count]) + [""] * max(0, col_count - len(row))
            md_lines.append("| " + " | ".join(esc(c) for c in padded) + " |")
        md_lines.append("")
    out_path.write_text("\n".join(md_lines), encoding="utf-8")


def convert_uploaded_file(filename: str, raw: bytes, target_fmt: str) -> dict[str, Any]:
    """Convert an uploaded file to target_fmt (docx, pptx, pdf, xlsx, csv, txt, md, json)."""
    data = extract_structured_content(filename, raw)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_name = f"conv-{_safe_stem(filename)}-{stamp}-{uuid.uuid4().hex[:5]}.{target_fmt}"
    out_path = mms.media_dir() / out_name
    if target_fmt == "docx":
        df._build_docx(out_path, data["title"], data["summary"], data["sections"], data["headers"], data["rows"])
    elif target_fmt == "pdf":
        df._build_pdf(out_path, data["title"], data["summary"], data["sections"], data["headers"], data["rows"])
    elif target_fmt == "xlsx":
        hdrs = data["headers"] or ["Bölüm", "İçerik"]
        rws = data["rows"] or [[s["heading"], s["content"][:500]] for s in data["sections"]]
        df._build_xlsx(out_path, data["title"], data["summary"], data["sections"], hdrs, rws)
    elif target_fmt == "pptx":
        _write_pptx_output(out_path, filename, data)
    elif target_fmt == "csv":
        _write_csv_output(out_path, data)
    elif target_fmt == "json":
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif target_fmt == "md":
        _write_md_output(out_path, data)
    else:
        out_path.write_text(data["raw_text"] or data["summary"], encoding="utf-8")
    return {
        "source_filename": filename, "target_format": target_fmt, "output_filename": out_name,
        "output_path": out_path, "size_kb": round(out_path.stat().st_size / 1024, 1),
        "url": f"/api/assistant/media/{out_name}", "section_count": len(data["sections"]),
    }


def _sanitize_rel_path(raw_path: str, *, fallback: str = "") -> str:
    norm = (raw_path or "").replace("\\", "/").strip()
    if not norm:
        return fallback
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
        clean = re.sub(r"[\x00-\x1f<>:\"|?*]+", "_", Path(norm).name).strip()
        return clean if clean and clean not in (".", "..") else fallback
    segs = [c for p in norm.split("/") if (c := re.sub(r"[\x00-\x1f<>:\"|?*]+", "_", p).strip()) and c not in (".", "..")]
    return "/".join(segs) if segs else fallback


def pack_files_to_folder_zip(
    folder_name: str, files: list[tuple[str, bytes]], empty_dirs: list[str] | None = None
) -> dict[str, Any]:
    """Pack files (preserving safe nested relative paths) and optional empty dirs into a downloadable .zip archive."""
    safe_folder = _safe_stem(folder_name)
    zip_name = f"arsiv-{safe_folder}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:5]}.zip"
    zip_path = mms.media_dir() / zip_name
    included, included_dirs, written_dirs = [], [], set()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_dir in empty_dirs or []:
            if (rel_dir := _sanitize_rel_path(raw_dir)):
                dir_arc = f"{safe_folder}/{rel_dir.rstrip('/')}/"
                if dir_arc not in written_dirs:
                    zf.writestr(dir_arc, b"")
                    written_dirs.add(dir_arc)
                    included_dirs.append(dir_arc)
        for fname, content in files:
            arcname = f"{safe_folder}/{_sanitize_rel_path(fname, fallback='dosya.bin')}"
            zf.writestr(arcname, content)
            included.append(arcname)
    return {
        "zip_filename": zip_name, "folder_name": safe_folder, "included_files": included,
        "included_dirs": included_dirs, "size_kb": round(zip_path.stat().st_size / 1024, 1),
        "url": f"/api/assistant/media/{zip_name}",
    }


def _build_unique_media_name(stamp: str, uid: str, orig_path: str, is_duplicate: bool, used_names: set[str]) -> str:
    parts = [re.sub(r"[^A-Za-z0-9._\-]+", "_", p) for p in orig_path.replace("\\", "/").split("/") if p and p not in (".", "..")]
    candidate = "__".join(parts) if (is_duplicate and len(parts) > 1) else (parts[-1] if parts else "dosya.bin")
    p = Path(candidate)
    suffix = p.suffix if (p.suffix and len(p.suffix) <= 16 and p.stem) else ""
    prefix = f"unz-{stamp}-{uid}-"
    max_stem = max(1, min(95, 120 - len(prefix) - len(suffix)))
    stem = (p.stem if suffix else candidate)[:max_stem]
    flat_name, counter = f"{prefix}{stem}{suffix}", 2
    while flat_name.lower() in used_names:
        tag = f"_{counter}"
        flat_name = f"{prefix}{stem[: max(1, max_stem - len(tag))]}{tag}{suffix}"
        counter += 1
    used_names.add(flat_name.lower())
    return flat_name


def extract_zip_to_media(zip_filename: str, raw: bytes) -> dict[str, Any]:
    """Safely extract files from a ZIP archive (SEC-07 verified) and expose downloadable media links."""
    safe_archive.inspect_zip(raw)
    stamp, uid, out_dir = datetime.now(UTC).strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:5], mms.media_dir()
    extracted, used_names = [], set()
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        valid_infos = [
            info for info in zf.infolist()
            if not info.is_dir() and Path(info.filename).name and not Path(info.filename).name.startswith(".")
        ]
        total_files = len(valid_infos)
        truncated = total_files > _MAX_ZIP_EXTRACT_FILES
        selected = valid_infos[:_MAX_ZIP_EXTRACT_FILES]
        base_counts = Counter(re.sub(r"[^A-Za-z0-9._\-]+", "_", Path(i.filename).name).lower() for i in selected)
        for info in selected:
            base_key = re.sub(r"[^A-Za-z0-9._\-]+", "_", Path(info.filename).name).lower()
            flat_name = _build_unique_media_name(stamp, uid, info.filename, base_counts[base_key] > 1, used_names)
            data = zf.read(info)
            (out_dir / flat_name).write_bytes(data)
            extracted.append({
                "original_path": info.filename, "filename": flat_name,
                "size_kb": round(len(data) / 1024, 1), "url": f"/api/assistant/media/{flat_name}",
            })
    return {
        "zip_filename": zip_filename, "file_count": len(extracted), "total_file_count": total_files,
        "truncated": truncated,
        "truncation_note": f"Arşivde {total_files} dosya bulundu; ilk {_MAX_ZIP_EXTRACT_FILES} dosya çıkarıldı." if truncated else "",
        "files": extracted,
    }
