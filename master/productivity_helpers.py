"""Pure helper functions and static catalogs for `productivity_api.py`."""

from __future__ import annotations

import ast
import hashlib
import html
import math
import re
import shutil
import uuid
from collections import defaultdict
from typing import Any

from process_utils import run_process

TEMPLATE_GALLERY: tuple[dict[str, str], ...] = (
    {"id": "fastapi-rest", "name": "FastAPI REST API", "stack": "Python / FastAPI / SQLite"},
    {"id": "flask-notes", "name": "Flask Web Uygulaması", "stack": "Python / Flask / HTML"},
    {"id": "cli-tool", "name": "Python CLI Aracı", "stack": "Python / argparse / pytest"},
    {"id": "spa-vanilla", "name": "Çevrimdışı Vanilla JS SPA", "stack": "HTML / CSS / ES Modules"},
    {"id": "canvas-game", "name": "HTML5 Canvas 2B Oyun", "stack": "HTML5 Canvas / JS"},
    {"id": "data-dashboard", "name": "Veri Analizi Panosu", "stack": "HTML / SVG / CSV"},
    {"id": "rag-bot", "name": "Yerel RAG Asistanı", "stack": "Python / SQLite FTS5"},
    {"id": "automation-worker", "name": "Dağıtık İşçi Şablonu", "stack": "Python / httpx"},
)

SLIDE_ICONS: dict[str, str] = {
    "chart": '<svg viewBox="0 0 24 24" width="24" height="24"><rect x="3" y="12" width="4" height="9"/><rect x="10" y="7" width="4" height="14"/><rect x="17" y="3" width="4" height="18"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M12 2L4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3z"/></svg>',
    "cpu": '<svg viewBox="0 0 24 24" width="24" height="24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    "check": '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
}


def explain_python_code(source: str) -> dict[str, Any]:
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"valid": False, "error": f"Satır {exc.lineno}: {exc.msg}", "line_by_line": []}
    notes: dict[int, str] = {}
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.FunctionDef):
            notes[ln] = f"`{node.name}` fonksiyonunu tanımlar ({len(node.args.args)} parametre)."
        elif isinstance(node, ast.ClassDef):
            notes[ln] = f"`{node.name}` sınıfını tanımlar."
        elif isinstance(node, ast.Return):
            notes[ln] = "Fonksiyondan sonuç değeri döndürür."
        elif isinstance(node, ast.For):
            notes[ln] = "Koleksiyon üzerinde döngü başlatır."
        elif isinstance(node, ast.If):
            notes[ln] = "Koşullu dallanma kontrolü yapar."
    explained = [{"line": i + 1, "code": line, "explanation": notes.get(i + 1, "İfade / atama satırı.")} for i, line in enumerate(lines)]
    return {"valid": True, "line_by_line": explained}


def translate_python_to_js(code: str, source_lang: str, target_lang: str) -> str:
    out = code
    if source_lang.lower() == "python" and target_lang.lower() in ("js", "javascript"):
        out = re.sub(r"\bdef\s+(\w+)\(([^)]*)\):", r"function \1(\2) {", out)
        out = re.sub(r"\bTrue\b", "true", out)
        out = re.sub(r"\bFalse\b", "false", out)
        out = re.sub(r"\bNone\b", "null", out)
        out = re.sub(r"\bprint\(", "console.log(", out)
    return out


def read_workspace_git_log(ws_id: str, limit: int = 20) -> dict[str, Any]:
    import workspace_builder as wb

    ws_dir = wb.safe_workspace_dir(ws_id)
    if not (ws_dir / ".git").is_dir():
        return {"workspace_id": ws_id, "commits": [], "note": "Çalışma alanında henüz git geçmişi yok."}
    git_bin = shutil.which("git")
    if not git_bin:
        return {"workspace_id": ws_id, "commits": [], "note": "Git kurulu değil."}
    proc = run_process(
        [git_bin, "log", f"-n{max(1, min(limit, 50))}", "--pretty=format:%h|%an|%ad|%s", "--date=short"],
        cwd=ws_dir,
        timeout_s=8.0,
    )
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1], "date": parts[2], "message": parts[3]})
    return {"workspace_id": ws_id, "commits": commits}


def build_qrcode_svg(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    size = 21
    cells: list[str] = []
    for r in range(size):
        for c in range(size):
            finder = (r < 7 and c < 7) or (r < 7 and c >= size - 7) or (r >= size - 7 and c < 7)
            bit = (digest[(r * size + c) % len(digest)] >> ((r + c) % 8)) & 1
            if finder or bit:
                cells.append(f'<rect x="{(c + 2) * 8}" y="{(r + 2) * 8}" width="8" height="8" fill="#0f172a"/>')
    dim = (size + 4) * 8
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" width="{dim}" height="{dim}"><rect width="{dim}" height="{dim}" fill="#ffffff"/>{"".join(cells)}</svg>'


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r_km * math.asin(math.sqrt(min(1.0, a))), 3)


def clean_table_rows(rows: list[dict[str, Any]], fill_value: Any) -> dict[str, Any]:
    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        filled = {k: (fill_value if v is None or v == "" else v) for k, v in row.items()}
        sig = repr(sorted(filled.items()))
        if sig not in seen:
            seen.add(sig)
            cleaned.append(filled)
    return {"original_rows": len(rows), "cleaned_rows": len(cleaned), "dedupe_rows_removed": len(rows) - len(cleaned), "rows": cleaned}


def compute_pivot(rows: list[dict[str, Any]], row_key: str, col_key: str, value_key: str) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        rk = str(r.get(row_key, ""))
        ck = str(r.get(col_key, "Toplam")) if col_key else "Toplam"
        try:
            table[rk][ck] += float(r.get(value_key) or 0)
        except (TypeError, ValueError):
            continue
    return {k: dict(v) for k, v in table.items()}


def render_dashboard_html(rows: list[dict[str, Any]]) -> str:
    cols = list(rows[0].keys()) if rows else []
    head_html = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>"
        for r in rows[:100]
    )
    return f"<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'><title>Veri Panosu</title></head><body><h1>Veri Panosu ({len(rows)} kayıt)</h1><table border='1'><thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table></body></html>"


def build_ics_event(title: str, start_iso: str, end_iso: str, location: str, description: str) -> str:
    def _ics_ts(iso: str) -> str:
        return re.sub(r"[-:]", "", iso.replace("+00:00", "Z")).split(".")[0]

    uid = f"{uuid.uuid4().hex}@dadp.local"
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//DADP Platform//TR\r\n"
        f"BEGIN:VEVENT\r\nUID:{uid}\r\nSUMMARY:{title}\r\n"
        f"DTSTART:{_ics_ts(start_iso)}\r\nDTEND:{_ics_ts(end_iso)}\r\n"
        f"LOCATION:{location}\r\nDESCRIPTION:{description}\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )


def split_tweet_thread(text: str) -> list[str]:
    words = text.split()
    tweets: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) > 270:
            if cur:
                tweets.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        tweets.append(cur)
    return [f"{i + 1}/{len(tweets)} {t}" for i, t in enumerate(tweets)]
