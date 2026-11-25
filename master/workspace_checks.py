"""Static checks for generated projects: JS syntax, DOM id contract between JS and HTML, Python undefined names."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from process_utils import run_process

_JS_ID_RE = re.compile(r"""getElementById\(\s*['"]([\w-]+)['"]\s*\)|querySelector(?:All)?\(\s*['"]#([\w-]+)['"]\s*\)""")
_HTML_ID_RE = re.compile(r"""\bid\s*=\s*["']([\w-]+)["']""")
_JS_MAKES_ID_RE = re.compile(r"""(?:\.id\s*=\s*|id\s*=\s*\?["']|setAttribute\(\s*['"]id['"]\s*,\s*)['"]?([\w-]+)""")
_SKIP = (".history", "node_modules", "dist", "build", "venv", ".venv")


def _files(ws_dir: Path, suffix: str) -> list[Path]:
    return [p for p in sorted(ws_dir.rglob(f"*{suffix}")) if not any(s in p.parts for s in _SKIP)]


def js_syntax_problem(ws_dir: Path) -> tuple[Path, str] | None:
    node = shutil.which("node")
    if node is None:
        return None
    for js in _files(ws_dir, ".js"):
        proc = run_process([node, "--check", str(js)], timeout_s=20, max_output_chars=1500)
        if proc.returncode != 0 and not proc.timed_out:
            first = next((ln for ln in proc.stderr.splitlines() if "Error" in ln), proc.stderr.strip()[:200])
            return js, f"{js.name} JavaScript sözdizimi hatası içeriyor: {first}"
    return None


def dom_id_problem(ws_dir: Path) -> tuple[Path, str] | None:
    """A script that looks up an id which no page (and no script) defines throws on load and breaks the whole app."""
    html_ids: set[str] = set()
    for page in _files(ws_dir, ".html"):
        html_ids.update(_HTML_ID_RE.findall(page.read_text(encoding="utf-8", errors="replace")))
    if not html_ids:
        return None
    scripts = [(js, js.read_text(encoding="utf-8", errors="replace")) for js in _files(ws_dir, ".js")]
    made = {m for _js, src in scripts for m in _JS_MAKES_ID_RE.findall(src)}
    for js, src in scripts:
        for a, b in _JS_ID_RE.findall(src):
            wanted = a or b
            if wanted not in html_ids and wanted not in made:
                return js, f"{js.name} dosyası HTML'de olmayan `{wanted}` id'sini arıyor. HTML'deki id'ler: {', '.join(sorted(html_ids))[:300]}. JS'teki id'leri bu listeye uyacak şekilde düzelt."
    return None


def python_name_problem(ws_dir: Path) -> tuple[Path, str] | None:
    proc = run_process([sys.executable, "-m", "ruff", "check", "--no-cache", "--isolated", "--select", "F821,F822,F823,F63,F7,E9", "--output-format", "concise", str(ws_dir)], timeout_s=30, max_output_chars=2000)
    if proc.returncode != 1:
        return None  # 0 = clean, anything else = ruff unavailable
    for line in proc.stdout.splitlines():
        m = re.match(r"(.+?):(\d+):\d+: (\w+) (.*)", line)
        if m and not any(s in m.group(1) for s in _SKIP):
            return Path(m.group(1)), f"{Path(m.group(1)).name} satır {m.group(2)}: {m.group(3)} {m.group(4)}"
    return None


_EVAL_RE = re.compile(r"(?<![\w.])eval\s*\(")


def eval_problem(ws_dir: Path) -> tuple[Path, str] | None:
    """eval() on user input is a code-injection hole; a small parser or Function-free arithmetic is required instead."""
    for js in _files(ws_dir, ".js"):
        if _EVAL_RE.search(js.read_text(encoding="utf-8", errors="replace")):
            return js, f"{js.name} dosyası eval() kullanıyor; bu güvenlik açığıdır. eval() yerine ifadeyi ayrıştıran güvenli bir fonksiyon yaz (ör. sayıları ve + - * / işleçlerini elle işle)."
    return None


def static_problem(ws_dir: Path) -> tuple[Path, str] | None:
    for check in (js_syntax_problem, eval_problem, dom_id_problem, python_name_problem):
        if (found := check(ws_dir)) is not None:
            return found
    return None
