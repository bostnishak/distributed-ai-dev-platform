"""Deterministic, zero-hallucination file error & quality inspector for uploaded files.

Runs real syntax parsers, JSON validators, HTML structure checks, Excel formula error scanners,
CSV schema/anomaly detectors, and SAST security checks on uploaded files BEFORE the LLM responds
so the assistant reports exact line numbers/cell coordinates and never hallucinates fake errors.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import re
import shutil
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

import automl_studio as aml
import extract
import process_utils
import safe_archive
import self_healing_runner as shr

_EXCEL_ERROR_TOKENS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!")
_MOJIBAKE_RE = re.compile(r"Ã[§¶¼Ÿ±]|Ä[Ÿ±°]|Å[Ÿž]")
_TEXT_EXTS = (".txt", ".md", ".py", ".js", ".html", ".css", ".csv", ".json")


def decode_text_turkish_safe(raw: bytes) -> tuple[str, str]:
    """Decode bytes cleanly preserving Turkish characters (UTF-8-SIG -> UTF-8 -> CP1254 -> Latin-1)."""
    for enc in ("utf-8-sig", "utf-8", "cp1254", "iso-8859-9"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


class _HTMLStructureChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, int]] = []
        self.issues: list[dict[str, Any]] = []
        self.ids: dict[str, int] = {}
        self.void_tags = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        line = self.getpos()[0]
        for k, v in attrs:
            if k.lower() == "id" and v:
                if v in self.ids:
                    self.issues.append({
                        "severity": "MEDIUM",
                        "line": line,
                        "type": "DUPLICATE_ID",
                        "message": f"Tekrarlanan HTML id='{v}' (ilk tanim satir {self.ids[v]}).",
                    })
                else:
                    self.ids[v] = line
        if t not in self.void_tags:
            self.stack.append((t, line))

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        line = self.getpos()[0]
        if t in self.void_tags:
            return
        if not self.stack:
            self.issues.append({
                "severity": "HIGH",
                "line": line,
                "type": "UNMATCHED_CLOSE_TAG",
                "message": f"Acilmamis kapanis etiketi </{t}>.",
            })
            return
        top_tag, _top_line = self.stack[-1]
        if top_tag == t:
            self.stack.pop()
        else:
            self.issues.append({
                "severity": "HIGH",
                "line": line,
                "type": "MISMATCHED_TAG",
                "message": f"Beklenen </{top_tag}>, bulunan </{t}>.",
            })


def _append_sast_issues(td: Path, issues: list[dict[str, Any]]) -> None:
    sec = shr.scan_code_security(td)
    for s in sec.get("issues", []):
        issues.append({
            "severity": s["severity"],
            "line": s["line"],
            "type": s["category"],
            "message": s["message"],
        })


def _inspect_python(name: str, raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    text, enc = decode_text_turkish_safe(raw)
    stats["encoding"] = enc
    stats["line_count"] = len(text.splitlines())
    try:
        tree = ast.parse(text, filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "severity": "MEDIUM",
                    "line": getattr(node, "lineno", 1),
                    "type": "BARE_EXCEPT",
                    "message": "Genel 'except:' kullanimi tum hatalari (KeyboardInterrupt dahil) yutar; spesifik istisna belirtin.",
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "severity": "MEDIUM",
                            "line": getattr(node, "lineno", 1),
                            "type": "MUTABLE_DEFAULT_ARG",
                            "message": f"'{node.name}' fonksiyonunda degistirilebilir varsayilan arguman (list/dict/set) kullanilmis.",
                        })
    except SyntaxError as exc:
        issues.append({
            "severity": "CRITICAL",
            "line": exc.lineno or 1,
            "type": "SYNTAX_ERROR",
            "message": f"Python sozdizimi hatasi (satir {exc.lineno}, sutun {exc.offset}): {exc.msg}",
        })
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / Path(name).name
        p.write_text(text, encoding="utf-8")
        _append_sast_issues(Path(td), issues)


def _inspect_json(raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    text, enc = decode_text_turkish_safe(raw)
    stats["encoding"] = enc
    try:
        parsed = json.loads(text)
        stats["json_type"] = type(parsed).__name__
    except json.JSONDecodeError as exc:
        issues.append({
            "severity": "CRITICAL",
            "line": exc.lineno,
            "type": "JSON_SYNTAX_ERROR",
            "message": f"Gecersiz JSON (satir {exc.lineno}, sutun {exc.colno}): {exc.msg}",
        })


def _inspect_js(name: str, raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    text, enc = decode_text_turkish_safe(raw)
    stats["encoding"] = enc
    stats["line_count"] = len(text.splitlines())
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / Path(name).name
        p.write_text(text, encoding="utf-8")
        node_bin = shutil.which("node")
        if node_bin:
            proc = process_utils.run_process([node_bin, "--check", str(p)], timeout_s=6.0)
            if proc.returncode != 0:
                err_txt = (proc.stderr or proc.stdout).strip().splitlines()[:4]
                issues.append({
                    "severity": "CRITICAL",
                    "line": 1,
                    "type": "JS_SYNTAX_ERROR",
                    "message": "JavaScript sozdizimi hatasi: " + " | ".join(err_txt),
                })
        _append_sast_issues(Path(td), issues)


def _inspect_html(raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    text, enc = decode_text_turkish_safe(raw)
    stats["encoding"] = enc
    if "charset" not in text.lower():
        issues.append({
            "severity": "MEDIUM",
            "line": 1,
            "type": "MISSING_CHARSET",
            "message": 'Turkce karakterlerin bozulmamasi icin <meta charset="UTF-8"> etiketi eklenmelidir.',
        })
    checker = _HTMLStructureChecker()
    checker.feed(text)
    issues.extend(checker.issues)
    for tag_name, line_no in checker.stack[:5]:
        issues.append({
            "severity": "HIGH",
            "line": line_no,
            "type": "UNCLOSED_TAG",
            "message": f"Kapatilmamis HTML etiketi <{tag_name}>.",
        })


def _inspect_csv(lower: str, raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    text, enc = decode_text_turkish_safe(raw)
    stats["encoding"] = enc
    first_lines = text.splitlines()[:1]
    delim = "\t" if lower.endswith(".tsv") else (";" if first_lines and first_lines[0].count(";") > first_lines[0].count(",") else ",")
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    stats["row_count"] = max(0, len(rows) - 1)
    if not rows:
        return
    expected_cols = len(rows[0])
    stats["column_count"] = expected_cols
    for idx, r in enumerate(rows[1:], start=2):
        if len(r) != expected_cols:
            issues.append({
                "severity": "HIGH",
                "line": idx,
                "type": "CSV_COLUMN_MISMATCH",
                "message": f"Satir {idx} sutun sayisi uyumsuz (beklenen {expected_cols}, bulunan {len(r)}).",
            })
    dict_rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    if not dict_rows:
        return
    prof = aml.profile_dataset(dict_rows)
    for col, mcnt in prof.get("missing_counts", {}).items():
        if mcnt > 0:
            issues.append({
                "severity": "MEDIUM",
                "line": 1,
                "type": "MISSING_VALUES",
                "message": f"'{col}' sutununda {mcnt} adet eksik/bos deger var.",
            })
    for anom in prof.get("anomalies", [])[:10]:
        issues.append({
            "severity": "MEDIUM",
            "line": anom["row_index"] + 2,
            "type": "DATA_ANOMALY",
            "message": f"Satir {anom['row_index'] + 2} aykiri deger: {', '.join(anom.get('reasons', []))}",
        })


def _inspect_excel(raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    wb = load_workbook(io.BytesIO(raw), data_only=False)
    try:
        stats["sheet_count"] = len(wb.worksheets)
        for ws in wb.worksheets:
            for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                for c_idx, val in enumerate(row, start=1):
                    if isinstance(val, str) and any(tok in val for tok in _EXCEL_ERROR_TOKENS):
                        issues.append({
                            "severity": "HIGH",
                            "line": r_idx,
                            "type": "EXCEL_FORMULA_ERROR",
                            "message": f"'{ws.title}' sayfasi satir {r_idx}, sutun {c_idx} icinde Excel formulu hatasi: {val}",
                        })
    finally:
        wb.close()


def _inspect_pdf(raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    txt = extract.extract_pdf_text(raw)
    stats["extracted_chars"] = len(txt.strip())
    if len(txt.strip()) < 20:
        issues.append({
            "severity": "MEDIUM",
            "line": 1,
            "type": "SCANNED_OR_EMPTY_PDF",
            "message": "PDF icinde secilebilir metin bulunamadi (taranmis goruntu PDF olabilir; gorsel/OCR veya CNC balonlama olarak inceleyin).",
        })


def _inspect_zip(raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    try:
        summary = safe_archive.inspect_zip(raw)
    except safe_archive.UnsafeArchive as exc:
        is_corrupt = isinstance(exc.__cause__, zipfile.BadZipFile)
        issues.append({
            "severity": "CRITICAL",
            "line": 1,
            "type": "CORRUPT_ZIP" if is_corrupt else "UNSAFE_ZIP",
            "message": "ZIP arsivi bozuk veya acilamiyor." if is_corrupt else f"Guvenli olmayan ZIP arsivi engellendi: {exc}",
        })
        return
    stats["archive_unpacked_bytes"] = summary.get("total_bytes", 0)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            file_names = [i.filename for i in zf.infolist() if not i.is_dir()]
            stats["archive_file_count"] = len(file_names)
            for fn in file_names[:25]:
                if fn.lower().endswith((".py", ".json", ".js", ".html", ".csv", ".tsv")):
                    sub = inspect_uploaded_file(fn, zf.read(fn))
                    for sub_iss in sub["issues"][:5]:
                        issues.append({**sub_iss, "message": f"[{fn}] {sub_iss['message']}"})
    except zipfile.BadZipFile:
        issues.append({
            "severity": "CRITICAL",
            "line": 1,
            "type": "CORRUPT_ZIP",
            "message": "ZIP arsivi bozuk veya acilamiyor.",
        })


def _dispatch_inspector(name: str, lower: str, raw: bytes, stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    handlers = (
        ((".py",), lambda: _inspect_python(name, raw, stats, issues)),
        ((".json",), lambda: _inspect_json(raw, stats, issues)),
        ((".js", ".mjs", ".cjs"), lambda: _inspect_js(name, raw, stats, issues)),
        ((".html", ".htm"), lambda: _inspect_html(raw, stats, issues)),
        ((".csv", ".tsv"), lambda: _inspect_csv(lower, raw, stats, issues)),
        ((".xlsx", ".xlsm"), lambda: _inspect_excel(raw, stats, issues)),
        ((".pdf",), lambda: _inspect_pdf(raw, stats, issues)),
        ((".zip",), lambda: _inspect_zip(raw, stats, issues)),
    )
    for exts, fn in handlers:
        if lower.endswith(exts):
            fn()
            return


def inspect_uploaded_file(filename: str, raw: bytes) -> dict[str, Any]:
    """Deterministically inspect an uploaded file and return exact verified findings."""
    name = (filename or "dosya").strip()
    lower = name.lower()
    issues: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"filename": name, "size_bytes": len(raw)}
    _dispatch_inspector(name, lower, raw, stats, issues)

    if lower.endswith(_TEXT_EXTS):
        txt_check, _ = decode_text_turkish_safe(raw)
        if "\ufffd" in txt_check or _MOJIBAKE_RE.search(txt_check):
            issues.append({
                "severity": "MEDIUM",
                "line": 1,
                "type": "TURKISH_ENCODING_ARTIFACT",
                "message": "Dosyada bozuk Turkce karakter kodlamasi (UTF-8/Windows-1254 uyumsuzlugu) izleri tespit edildi.",
            })

    return {
        "ok": not any(i["severity"] in ("CRITICAL", "HIGH") for i in issues),
        "issue_count": len(issues),
        "stats": stats,
        "issues": issues[:40],
    }


def format_inspection_markdown(report: dict[str, Any]) -> str:
    """Format deterministic file inspection findings into a concise block for prompt & user."""
    issues = report.get("issues") or []
    stats = report.get("stats") or {}
    lines = [
        f"### Deterministik Dosya Denetim Raporu ({stats.get('filename', 'dosya')})",
        f"- **Durum:** {'Temiz (0 kritik/yuksek hata)' if report.get('ok') else f'{len(issues)} bulgu tespit edildi'} | "
        f"**Boyut:** {stats.get('size_bytes', 0)} bayt"
        + (f" | **Kodlama:** `{stats['encoding']}`" if stats.get("encoding") else ""),
    ]
    if issues:
        lines.append("| Onem | Satir | Kategori | Kesin Bulgu |")
        lines.append("|---|---|---|---|")
        for i in issues[:20]:
            lines.append(f"| **{i['severity']}** | `{i['line']}` | `{i['type']}` | {i['message']} |")
    else:
        lines.append("- Sozdizimi, JSON/HTML yapisi, formuller ve temel guvenlik taramasinda hata bulunmadi.")
    return "\n".join(lines)
