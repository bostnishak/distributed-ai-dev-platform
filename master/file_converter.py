"""Universal Bidirectional File Converter & ZIP Archive Manager.

Supports:
- Bidirectional conversion across PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JSON
  using official python-docx, python-pptx, openpyxl, and PyMuPDF with Turkish Unicode support.
- Packing uploaded files (or converted outputs) into a named folder inside a downloadable .zip archive.
- Safe ZIP extraction (zip-slip protected) exposing every extracted file via downloadable media links.
- Zipping existing Studio workspaces directly from chat.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf as fitz
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

import deep_research as dr
import document_factory as df
import multimodal_studio as mms

TARGET_FMT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("docx", ("docx", "word")),
    ("pptx", ("pptx", "powerpoint", "sunum", "slayt")),
    ("pdf", ("pdf",)),
    ("xlsx", ("xlsx", "excel")),
    ("csv", ("csv",)),
    ("txt", ("txt", "metin dosyası", "metin dosyasi")),
    ("md", ("markdown", ".md")),
    ("json", ("json",)),
]

CONVERT_VERBS = (
    "çevir",
    "cevir",
    "dönüştür",
    "donustur",
    "aktar",
    "yap",
    "haline getir",
    "convert",
    "export",
)

ZIP_PACK_CUES = (
    "ziple",
    "zip yap",
    "zip'le",
    "zipe al",
    "zip'e al",
    "zip oluştur",
    "zip olustur",
    "klasöre al",
    "klasore al",
    "klasörle",
    "klasorle",
    "sıkıştır",
    "sikistir",
    "arşivle",
    "arsivle",
)

ZIP_EXTRACT_CUES = (
    "zipi aç",
    "zip'i aç",
    "zipi ac",
    "zip'i ac",
    "içini aç",
    "icini ac",
    "içini çıkar",
    "icini cikar",
    "arşivi aç",
    "arsivi ac",
    "dosyaları çıkar",
    "dosyalari cikar",
    "unzip",
    "extract",
    "ayıkla",
    "ayikla",
)


def _safe_stem(name: str) -> str:
    stem = Path(name or "dosya").stem
    clean = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem).strip("_")
    return (clean or "dosya")[:48]


def _find_target_format(low: str, ext: str) -> str | None:
    if not any(v in low for v in CONVERT_VERBS):
        return None
    for fmt, cues in TARGET_FMT_PATTERNS:
        if fmt != ext and any(c in low for c in cues):
            return fmt
    return None


def detect_conversion_or_archive_action(prompt: str, filename: str | None) -> dict[str, Any] | None:
    """Detect whether the user wants file conversion, folder+ZIP packing, ZIP extraction, or project zipping."""
    low = (prompt or "").lower()
    if not filename:
        has_proj = any(k in low for k in ("proje", "çalışma alanı", "calisma alani", "workspace"))
        has_zip = any(z in low for z in ("ziple", "zip yap", "sıkıştır", "sikistir", "zip olarak", "zip indir"))
        return {"action": "zip_project"} if (has_proj and has_zip) else None

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "zip" and any(k in low for k in ZIP_EXTRACT_CUES):
        return {"action": "extract_zip"}

    wants_zip = any(k in low for k in ZIP_PACK_CUES)
    target_fmt = _find_target_format(low, ext)

    if target_fmt and wants_zip:
        return {"action": "convert_and_zip", "target_fmt": target_fmt}
    if target_fmt:
        return {"action": "convert", "target_fmt": target_fmt}
    if wants_zip:
        return {"action": "pack_zip"}
    return None


def _decode_text_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_pdf_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    doc: Any = fitz.open(stream=raw, filetype="pdf")
    sections: list[dict[str, str]] = []
    pages_text: list[str] = []
    for idx, pg in enumerate(doc, start=1):
        t = (pg.get_text("text") or "").strip()
        pages_text.append(t)
        if t:
            lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
            heading = lines[0][:90] if lines else f"Sayfa {idx}"
            body = "\n".join(lines[1:]) if len(lines) > 1 else t
            sections.append({"heading": f"Sayfa {idx}: {heading}", "content": body})
    doc.close()
    return sections, [], [], "\n\n".join(pages_text)


def _extract_docx_structured(raw: bytes, title: str) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    doc = Document(io.BytesIO(raw))
    sections: list[dict[str, str]] = []
    headers: list[str] = []
    rows: list[list[Any]] = []
    cur_heading = title
    cur_paras: list[str] = []
    all_lines: list[str] = []
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
    if doc.tables and doc.tables[0].rows:
        t0 = doc.tables[0]
        headers = [c.text.strip() for c in t0.rows[0].cells]
        rows = [[c.text.strip() for c in r.cells] for r in t0.rows[1:]]
    return sections, headers, rows, "\n".join(all_lines)


def _extract_pptx_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    prs = Presentation(io.BytesIO(raw))
    sections: list[dict[str, str]] = []
    all_lines: list[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        slide_texts: list[str] = []
        for shape in slide.shapes:
            tf = getattr(shape, "text_frame", None)
            if getattr(shape, "has_text_frame", False) and tf is not None:
                st = str(getattr(tf, "text", "") or "").strip()
                if st:
                    slide_texts.append(st)
        if slide_texts:
            heading = slide_texts[0].splitlines()[0][:100]
            body = "\n".join(slide_texts[1:]) if len(slide_texts) > 1 else slide_texts[0]
            sections.append({"heading": f"Slayt {idx}: {heading}", "content": body})
            all_lines.append(f"## Slayt {idx}: {heading}\n{body}")
    return sections, [], [], "\n\n".join(all_lines)


def _extract_xlsx_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    wb = load_workbook(io.BytesIO(raw), data_only=True)
    ws: Any = wb.active
    all_rows = [[c if c is not None else "" for c in r] for r in ws.iter_rows(values_only=True)] if ws is not None else []
    non_empty = [r for r in all_rows if any(str(c).strip() for c in r)]
    headers: list[str] = []
    rows: list[list[Any]] = []
    if non_empty:
        headers = [str(c).strip() or f"Sütun {i + 1}" for i, c in enumerate(non_empty[0])]
        rows = non_empty[1:200]
    raw_text = "\n".join(" | ".join(str(c) for c in r) for r in non_empty[:200])
    wb.close()
    return [], headers, rows, raw_text


def _extract_csv_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    txt = _decode_text_bytes(raw)
    delim = ";" if txt.count(";") > txt.count(",") else ","
    parsed = list(csv.reader(io.StringIO(txt), delimiter=delim))
    non_empty = [r for r in parsed if any(c.strip() for c in r)]
    headers: list[str] = []
    rows: list[list[Any]] = []
    if non_empty:
        headers = [c.strip() or f"Sütun {i + 1}" for i, c in enumerate(non_empty[0])]
        rows = non_empty[1:200]
    return [], headers, rows, txt


def _extract_plain_structured(raw: bytes) -> tuple[list[dict[str, str]], list[str], list[list[Any]], str]:
    raw_text = _decode_text_bytes(raw)
    sections: list[dict[str, str]] = []
    blocks = [b.strip() for b in re.split(r"\n{2,}", raw_text) if b.strip()]
    for idx, blk in enumerate(blocks[:30], start=1):
        lines = blk.splitlines()
        heading = lines[0].lstrip("# ").strip()[:90] if lines else f"Bölüm {idx}"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else blk
        sections.append({"heading": heading, "content": body})
    return sections, [], [], raw_text


def extract_structured_content(filename: str, raw: bytes) -> dict[str, Any]:
    """Extract normalized title, sections, tables, and raw text from PDF/DOCX/PPTX/XLSX/CSV/TXT/MD/JSON."""
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
    elif ext == "csv":
        sections, headers, rows, raw_text = _extract_csv_structured(raw)
    else:
        sections, headers, rows, raw_text = _extract_plain_structured(raw)

    if not sections and raw_text:
        sections.append({"heading": "İçerik Özeti", "content": raw_text[:4000]})

    summary = (raw_text[:320].replace("\n", " ").strip() + "...") if len(raw_text) > 320 else raw_text.replace("\n", " ").strip()
    return {
        "title": title,
        "summary": summary,
        "sections": sections,
        "headers": headers,
        "rows": rows,
        "raw_text": raw_text,
    }


def _write_pptx_output(out_path: Path, filename: str, data: dict[str, Any]) -> None:
    slides = []
    for idx, s in enumerate(data["sections"][:14], start=1):
        raw_lines = [ln.strip("•-* \t") for ln in re.split(r"[\n]+|(?<=\.)\s+", s["content"]) if ln.strip()]
        slides.append({
            "kicker": f"BÖLÜM {idx}",
            "title": s["heading"][:80],
            "bullets": raw_lines[:5] or [s["content"][:220]],
            "key_fact": raw_lines[0][:140] if raw_lines else "",
        })
    if data["headers"] and data["rows"]:
        slides.append({
            "kicker": "TABLO ÖZETİ",
            "title": "Veri Tablosu Özeti",
            "bullets": [" | ".join(str(c) for c in r[: len(data["headers"])]) for r in data["rows"][:6]],
        })
    dr.build_pptx_presentation(
        title=data["title"],
        subtitle=data["summary"][:160] or f"{filename} dosyasından dönüştürüldü",
        slides=slides,
        out_path=out_path,
    )


def _write_csv_output(out_path: Path, data: dict[str, Any]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if data["headers"]:
        writer.writerow(data["headers"])
        writer.writerows(data["rows"])
    else:
        writer.writerow(["Bölüm", "İçerik"])
        for s in data["sections"]:
            writer.writerow([s["heading"], s["content"]])
    out_path.write_text(buf.getvalue(), encoding="utf-8-sig")


def _write_md_output(out_path: Path, data: dict[str, Any]) -> None:
    md_lines = [f"# {data['title']}", ""]
    for s in data["sections"]:
        md_lines.extend([f"## {s['heading']}", "", s["content"], ""])
    out_path.write_text("\n".join(md_lines), encoding="utf-8")


def convert_uploaded_file(filename: str, raw: bytes, target_fmt: str) -> dict[str, Any]:
    """Convert an uploaded file to target_fmt (docx, pptx, pdf, xlsx, csv, txt, md, json)."""
    data = extract_structured_content(filename, raw)
    stem = _safe_stem(filename)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:5]
    out_name = f"conv-{stem}-{stamp}-{uid}.{target_fmt}"
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
        "source_filename": filename,
        "target_format": target_fmt,
        "output_filename": out_name,
        "output_path": out_path,
        "size_kb": round(out_path.stat().st_size / 1024, 1),
        "url": f"/api/assistant/media/{out_name}",
        "section_count": len(data["sections"]),
    }


def pack_files_to_folder_zip(
    folder_name: str,
    files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Place one or more files inside a named folder and compress into a downloadable .zip archive."""
    safe_folder = _safe_stem(folder_name)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:5]
    zip_name = f"arsiv-{safe_folder}-{stamp}-{uid}.zip"
    zip_path = mms.media_dir() / zip_name

    included: list[str] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files:
            safe_f = Path(fname).name or "dosya.bin"
            arcname = f"{safe_folder}/{safe_f}"
            zf.writestr(arcname, content)
            included.append(arcname)

    return {
        "zip_filename": zip_name,
        "folder_name": safe_folder,
        "included_files": included,
        "size_kb": round(zip_path.stat().st_size / 1024, 1),
        "url": f"/api/assistant/media/{zip_name}",
    }


def extract_zip_to_media(zip_filename: str, raw: bytes) -> dict[str, Any]:
    """Safely extract all files from a ZIP archive (zip-slip protected) and expose downloadable links."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:5]
    out_dir = mms.media_dir()
    extracted: list[dict[str, Any]] = []

    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        for info in zf.infolist()[:40]:
            if info.is_dir():
                continue
            orig_name = Path(info.filename).name
            if not orig_name or orig_name.startswith("."):
                continue
            safe_orig = re.sub(r"[^A-Za-z0-9._\-]+", "_", orig_name)
            flat_name = f"unz-{stamp}-{uid}-{safe_orig}"[:110]
            data = zf.read(info)
            target = out_dir / flat_name
            target.write_bytes(data)
            extracted.append({
                "original_path": info.filename,
                "filename": flat_name,
                "size_kb": round(len(data) / 1024, 1),
                "url": f"/api/assistant/media/{flat_name}",
            })

    return {
        "zip_filename": zip_filename,
        "file_count": len(extracted),
        "files": extracted,
    }
