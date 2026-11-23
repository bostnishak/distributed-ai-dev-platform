"""Cluster B (`[M25]`, Faz 6.3): Web UI Static/DOM Visual Verifier & Auto-Healer.

Provides:
- `verify_web_workspace_ui(ws_dir: Path) -> dict`: inspects all HTML/CSS/JS files in `ws_dir` for missing DOM IDs referenced by `getElementById`/`querySelector`, broken relative asset links, missing responsive viewport meta tags, and potential runtime JS errors.
- `auto_fix_web_ui_issues(ws_dir: Path) -> dict`: automatically repairs missing viewport meta tags, creates missing referenced local CSS/JS stubs, and injects missing placeholder DOM containers.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from code_graph import IGNORED_DIRS, parse_html_file

_GET_BY_ID_RE = re.compile(r"""document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)""")
_QUERY_ID_RE = re.compile(r"""document\.querySelector(?:All)?\(\s*['"]#([A-Za-z0-9_-]+)['"]\s*\)""")
_VIEWPORT_RE = re.compile(r"""<meta\b[^>]*name\s*=\s*['"]viewport['"]""", re.IGNORECASE)
_JS_SYNTAX_HAZARD_RE = re.compile(r"""\b(?:undefinedVariable|null\.[A-Za-z_]|NaN\s*===\s*NaN)\b""")


def _collect_web_files(ws_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
    html_files: list[Path] = []
    css_files: list[Path] = []
    js_files: list[Path] = []
    if not ws_dir.exists():
        return html_files, css_files, js_files

    for path in sorted(ws_dir.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts) or not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext == ".html":
            html_files.append(path)
        elif ext == ".css":
            css_files.append(path)
        elif ext in {".js", ".ts"}:
            js_files.append(path)
    return html_files, css_files, js_files


def verify_web_workspace_ui(ws_dir: Path) -> dict[str, Any]:
    """Inspect all HTML/CSS/JS files in `ws_dir` for DOM ID mismatches, broken asset links, missing viewport meta, and JS hazards."""
    ws_dir = Path(ws_dir).resolve()
    html_files, css_files, js_files = _collect_web_files(ws_dir)

    all_html_ids: set[str] = set()
    missing_viewport_files: list[str] = []
    broken_asset_links: list[dict[str, str]] = []
    missing_dom_ids: list[dict[str, str]] = []
    runtime_js_hazards: list[dict[str, Any]] = []

    for h_path in html_files:
        rel = h_path.relative_to(ws_dir).as_posix()
        source = h_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_html_file(source)
        all_html_ids.update(parsed["ids"])

        if not _VIEWPORT_RE.search(source):
            missing_viewport_files.append(rel)

        for ref in [*parsed["scripts"], *parsed["stylesheets"]]:
            cleaned = ref.split("?", 1)[0].split("#", 1)[0].strip()
            if not cleaned or cleaned.startswith(("http://", "https://", "//", "data:")):
                continue
            target = (ws_dir / cleaned.lstrip("/")) if cleaned.startswith("/") else (h_path.parent / cleaned)
            if not target.is_file():
                broken_asset_links.append({"file": rel, "asset": cleaned})

    for j_path in js_files:
        rel = j_path.relative_to(ws_dir).as_posix()
        source = j_path.read_text(encoding="utf-8", errors="replace")

        # Also collect any IDs dynamically assigned via `.id = "foo"` or `id="foo"` in JS templates
        for dyn_id in re.findall(r"""(?:\.id\s*=\s*['"]([^'"]+)['"]|\bid\s*=\s*['"]([^'"]+)['"])""", source):
            for candidate in dyn_id:
                if candidate:
                    all_html_ids.add(candidate)

        referenced_ids = set(_GET_BY_ID_RE.findall(source)) | set(_QUERY_ID_RE.findall(source))
        for ref_id in sorted(referenced_ids):
            if html_files and ref_id not in all_html_ids:
                missing_dom_ids.append({"js_file": rel, "id": ref_id})

        # Check balanced braces/parentheses and common runtime hazards
        if source.count("{") != source.count("}"):
            runtime_js_hazards.append(
                {
                    "file": rel,
                    "type": "unbalanced_braces",
                    "message": "Unbalanced curly braces `{}` in JavaScript file.",
                }
            )
        for m in _JS_SYNTAX_HAZARD_RE.finditer(source):
            line_no = source.count("\n", 0, m.start()) + 1
            runtime_js_hazards.append(
                {
                    "file": rel,
                    "line": line_no,
                    "type": "runtime_hazard",
                    "message": f"Potential runtime JS error near `{m.group(0)}`.",
                }
            )

    total_issues = (
        len(missing_viewport_files)
        + len(broken_asset_links)
        + len(missing_dom_ids)
        + len(runtime_js_hazards)
    )
    return {
        "workspace": str(ws_dir),
        "ok": total_issues == 0,
        "html_file_count": len(html_files),
        "css_file_count": len(css_files),
        "js_file_count": len(js_files),
        "missing_viewport_files": missing_viewport_files,
        "broken_asset_links": broken_asset_links,
        "missing_dom_ids": missing_dom_ids,
        "runtime_js_hazards": runtime_js_hazards,
        "total_issues": total_issues,
    }


def auto_fix_web_ui_issues(ws_dir: Path) -> dict[str, Any]:
    """Automatically fix missing viewport meta tags, broken local CSS/JS asset files, and missing DOM IDs in HTML."""
    ws_dir = Path(ws_dir).resolve()
    before = verify_web_workspace_ui(ws_dir)
    fixes_applied: list[str] = []

    html_files, _, _ = _collect_web_files(ws_dir)
    primary_html = html_files[0] if html_files else None

    # 1. Add missing viewport meta tag
    for rel_html in before["missing_viewport_files"]:
        h_path = ws_dir / rel_html
        if not h_path.is_file():
            continue
        content = h_path.read_text(encoding="utf-8", errors="replace")
        meta_tag = '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        if "<head>" in content:
            content = content.replace("<head>", "<head>\n" + meta_tag, 1)
        elif "<html" in content.lower():
            content = meta_tag + content
        else:
            content = f"<head>\n{meta_tag}</head>\n{content}"
        h_path.write_text(content, encoding="utf-8")
        fixes_applied.append(f"Injected responsive viewport meta into {rel_html}")

    # 2. Create stub files for broken local CSS/JS links
    for item in before["broken_asset_links"]:
        rel_html = item["file"]
        asset = item["asset"]
        h_path = ws_dir / rel_html
        target = (ws_dir / asset.lstrip("/")) if asset.startswith("/") else (h_path.parent / asset)
        target = target.resolve()
        if not target.is_relative_to(ws_dir):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".css":
            target.write_text("/* Auto-generated stylesheet stub */\nbody { margin: 0; }\n", encoding="utf-8")
            fixes_applied.append(f"Created missing stylesheet {asset}")
        elif target.suffix.lower() == ".js":
            target.write_text("// Auto-generated script stub\n", encoding="utf-8")
            fixes_applied.append(f"Created missing script {asset}")

    # 3. Inject missing DOM IDs into primary HTML file
    if primary_html is not None and before["missing_dom_ids"]:
        content = primary_html.read_text(encoding="utf-8", errors="replace")
        injected_elements: list[str] = []
        seen_ids: set[str] = set()
        for item in before["missing_dom_ids"]:
            dom_id = item["id"]
            if dom_id in seen_ids:
                continue
            seen_ids.add(dom_id)
            injected_elements.append(f'  <div id="{dom_id}"></div>')

        if injected_elements:
            block = "\n".join(injected_elements) + "\n"
            if "</body>" in content:
                content = content.replace("</body>", block + "</body>", 1)
            else:
                content = content + "\n" + block
            primary_html.write_text(content, encoding="utf-8")
            fixes_applied.append(f"Injected {len(seen_ids)} missing DOM ID container(s) into {primary_html.name}")

    after = verify_web_workspace_ui(ws_dir)
    return {
        "fixes_applied": fixes_applied,
        "before_issues": before["total_issues"],
        "after_issues": after["total_issues"],
        "verification": after,
    }
