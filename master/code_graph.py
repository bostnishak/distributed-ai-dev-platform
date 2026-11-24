from __future__ import annotations

from pathlib import Path
from typing import Any

from code_graph_analysis import (
    COMMON_THIRD_PARTY_MODULES,
    STDLIB_MODULES,
    parse_css_file,
    parse_html_file,
    parse_js_ts_file,
    parse_python_file,
    parse_sql_file,
)

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
}

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".html", ".css", ".sql"}

__all__ = [
    "COMMON_THIRD_PARTY_MODULES",
    "IGNORED_DIRS",
    "STDLIB_MODULES",
    "SUPPORTED_EXTENSIONS",
    "build_workspace_code_graph",
    "get_file_context_contract",
    "parse_css_file",
    "parse_html_file",
    "parse_js_ts_file",
    "parse_python_file",
    "parse_sql_file",
]


def _resolve_relative_asset(ws_dir: Path, source_rel_path: str, ref_url: str) -> str | None:
    cleaned = ref_url.split("?", 1)[0].split("#", 1)[0].strip()
    if not cleaned or cleaned.startswith(("http://", "https://", "//", "data:", "mailto:", "javascript:")):
        return None
    source_parent = (ws_dir / source_rel_path).parent
    candidate = (ws_dir / cleaned.lstrip("/")).resolve() if cleaned.startswith("/") else (source_parent / cleaned).resolve()
    try:
        return candidate.relative_to(ws_dir.resolve()).as_posix()
    except ValueError:
        return cleaned


def _resolve_relative_python_import(
    ws_dir: Path,
    source_dir: Path,
    module_name: str,
    names: list[str],
    level: int,
) -> tuple[str | None, bool]:
    base_dir = source_dir
    for _ in range(level - 1):
        base_dir = base_dir.parent
    ws_root = ws_dir.resolve()
    if module_name:
        target_base = base_dir.joinpath(*module_name.split("."))
        for cand in (target_base.with_suffix(".py"), target_base / "__init__.py"):
            if cand.is_file():
                return cand.resolve().relative_to(ws_root).as_posix(), False
        return module_name, True
    for name in names:
        for cand in (base_dir / f"{name}.py", base_dir / name / "__init__.py"):
            if cand.is_file():
                return cand.resolve().relative_to(ws_root).as_posix(), False
    return ".".join(names), True


def _resolve_python_import(
    ws_dir: Path,
    source_rel_path: str,
    imp: dict[str, Any],
    py_module_index: dict[str, str],
) -> tuple[str | None, bool]:
    """Return (resolved_rel_path, is_broken_local)."""
    module_name = imp["module"]
    level = imp.get("level", 0)
    names = imp.get("names", [])
    source_dir = (ws_dir / source_rel_path).parent

    if level > 0:
        return _resolve_relative_python_import(ws_dir, source_dir, module_name, names, level)
    if not module_name:
        return None, False
    if module_name in py_module_index:
        return py_module_index[module_name], False

    top_pkg = module_name.split(".")[0]
    if top_pkg in py_module_index:
        return py_module_index[top_pkg], False
    for name in names:
        combined = f"{module_name}.{name}"
        if combined in py_module_index:
            return py_module_index[combined], False

    local_same_dir = source_dir / f"{top_pkg}.py"
    if local_same_dir.is_file():
        return local_same_dir.resolve().relative_to(ws_dir.resolve()).as_posix(), False
    if top_pkg in STDLIB_MODULES or top_pkg in COMMON_THIRD_PARTY_MODULES:
        return None, False
    return module_name, True


def _resolve_js_import(ws_dir: Path, source_rel_path: str, spec: str, known_files: set[str]) -> tuple[str | None, bool]:
    cleaned = spec.split("?", 1)[0].split("#", 1)[0].strip()
    if not cleaned.startswith((".", "/")):
        return None, False
    source_parent = (ws_dir / source_rel_path).parent
    base_candidate = (ws_dir / cleaned.lstrip("/")).resolve() if cleaned.startswith("/") else (source_parent / cleaned).resolve()
    ws_root = ws_dir.resolve()
    candidates = [
        base_candidate,
        base_candidate.with_suffix(".js"),
        base_candidate.with_suffix(".ts"),
        base_candidate / "index.js",
        base_candidate / "index.ts",
    ]
    for cand in candidates:
        try:
            rel = cand.relative_to(ws_root).as_posix()
        except ValueError:
            continue
        if rel in known_files:
            return rel, False
    return cleaned, True


def _collect_workspace_files(ws_dir: Path) -> tuple[list[Path], set[str], dict[str, str]]:
    files: list[Path] = []
    known_files: set[str] = set()
    py_module_index: dict[str, str] = {}
    for path in sorted(ws_dir.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if not (path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS):
            continue
        files.append(path)
        rel_path = path.relative_to(ws_dir).as_posix()
        known_files.add(rel_path)
        if path.suffix.lower() == ".py":
            dotted = rel_path[:-3].replace("/", ".")
            py_module_index[dotted] = rel_path
            if dotted.endswith(".__init__"):
                py_module_index[dotted[: -len(".__init__")]] = rel_path
            if path.stem != "__init__" and path.stem not in py_module_index:
                py_module_index[path.stem] = rel_path
    return files, known_files, py_module_index


def _record_asset_refs(
    ws_dir: Path,
    rel_path: str,
    refs: list[str],
    known_files: set[str],
    kind: tuple[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    edge_type, missing_type = kind
    edges: list[dict[str, str]] = []
    broken: list[dict[str, Any]] = []
    for ref in refs:
        resolved = _resolve_relative_asset(ws_dir, rel_path, ref)
        if resolved is None:
            continue
        if resolved in known_files or (ws_dir / resolved).is_file():
            edges.append({"source": rel_path, "target": resolved, "type": edge_type})
        else:
            broken.append({"source": rel_path, "target": ref, "resolved": resolved, "type": missing_type})
    return edges, broken


def _process_python_file(
    ws_dir: Path,
    rel_path: str,
    source: str,
    py_module_index: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, Any]]]:
    parsed = parse_python_file(source, rel_path)
    node = {
        "id": rel_path,
        "language": "python",
        "classes": [c["name"] for c in parsed["classes"]],
        "functions": [f["name"] for f in parsed["functions"]],
        "routes": parsed["routes"],
    }
    edges: list[dict[str, str]] = []
    broken: list[dict[str, Any]] = []
    for imp in parsed["imports"]:
        target_rel, is_broken = _resolve_python_import(ws_dir, rel_path, imp, py_module_index)
        if target_rel and not is_broken:
            if target_rel != rel_path:
                edges.append({"source": rel_path, "target": target_rel, "type": "python_import"})
        elif is_broken:
            broken.append({
                "source": rel_path,
                "target": str(target_rel),
                "type": "missing_python_import",
                "line": imp.get("line", 1),
            })
    return parsed, node, edges, broken


def _process_js_file(
    ws_dir: Path,
    rel_path: str,
    source: str,
    known_files: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, Any]]]:
    parsed = parse_js_ts_file(source, rel_path)
    node = {
        "id": rel_path,
        "language": parsed["language"],
        "classes": [c["name"] for c in parsed["classes"]],
        "functions": [f["name"] for f in parsed["functions"]],
        "exports": parsed["exports"],
        "api_calls": parsed["api_calls"],
    }
    edges: list[dict[str, str]] = []
    broken: list[dict[str, Any]] = []
    for spec in parsed["imports"]:
        target_rel, is_broken = _resolve_js_import(ws_dir, rel_path, spec, known_files)
        if target_rel and not is_broken:
            edges.append({"source": rel_path, "target": target_rel, "type": "js_import"})
        elif is_broken:
            broken.append({"source": rel_path, "target": spec, "type": "missing_js_import"})
    return parsed, node, edges, broken


def _process_workspace_file(
    ws_dir: Path,
    file_path: Path,
    known_files: set[str],
    py_module_index: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, Any]]] | None:
    rel_path = file_path.relative_to(ws_dir).as_posix()
    ext = file_path.suffix.lower()
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        source = ""

    if ext == ".py":
        return _process_python_file(ws_dir, rel_path, source, py_module_index)
    if ext in {".js", ".ts"}:
        return _process_js_file(ws_dir, rel_path, source, known_files)
    if ext == ".html":
        parsed = parse_html_file(source)
        node = {"id": rel_path, "language": "html", "ids": parsed["ids"], "css_classes": parsed["css_classes"]}
        s_edges, s_broken = _record_asset_refs(ws_dir, rel_path, parsed["scripts"], known_files, ("html_script", "missing_html_script"))
        l_edges, l_broken = _record_asset_refs(ws_dir, rel_path, parsed["stylesheets"], known_files, ("html_stylesheet", "missing_html_stylesheet"))
        return parsed, node, s_edges + l_edges, s_broken + l_broken
    if ext == ".css":
        parsed = parse_css_file(source)
        node = {"id": rel_path, "language": "css", "css_classes": parsed["css_classes"], "ids": parsed["ids"]}
        c_edges, c_broken = _record_asset_refs(ws_dir, rel_path, parsed["imports"], known_files, ("css_import", "missing_css_import"))
        return parsed, node, c_edges, c_broken
    if ext == ".sql":
        parsed = parse_sql_file(source)
        return parsed, {"id": rel_path, "language": "sql", "tables": parsed["tables"]}, [], []
    return None


def build_workspace_code_graph(ws_dir: Path) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    if not ws_dir.exists():
        return {"workspace": str(ws_dir), "nodes": [], "edges": [], "symbols": {}, "broken_references": []}

    files, known_files, py_module_index = _collect_workspace_files(ws_dir)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    symbols: dict[str, dict[str, Any]] = {}
    broken_references: list[dict[str, Any]] = []

    for file_path in files:
        result = _process_workspace_file(ws_dir, file_path, known_files, py_module_index)
        if result is None:
            continue
        parsed, node, file_edges, file_broken = result
        symbols[node["id"]] = parsed
        nodes.append(node)
        edges.extend(file_edges)
        broken_references.extend(file_broken)

    return {
        "workspace": str(ws_dir),
        "nodes": nodes,
        "edges": edges,
        "symbols": symbols,
        "broken_references": broken_references,
    }


def _format_python_contract(sym: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for cls in sym.get("classes", []):
        bases = f"({', '.join(cls['bases'])})" if cls.get("bases") else ""
        lines.append(f"- class `{cls['name']}{bases}`")
        for method in cls.get("methods", []):
            lines.append(f"  - `{method['signature']}`")
    for fn in sym.get("functions", []):
        lines.append(f"- `{fn['signature']}`")
    for route in sym.get("routes", []):
        lines.append(f"- route `{route['method']} {route['path']}` -> `{route['handler']}`")
    return lines


def _format_js_contract(sym: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for cls in sym.get("classes", []):
        ext = f" extends {cls['extends']}" if cls.get("extends") else ""
        lines.append(f"- class `{cls['name']}{ext}`")
    for fn in sym.get("functions", []):
        lines.append(f"- `{fn['signature']}`")
    if sym.get("exports"):
        lines.append(f"- exports: {', '.join(f'`{e}`' for e in sym['exports'])}")
    if sym.get("api_calls"):
        lines.append(f"- api_calls: {', '.join(f'`{c}`' for c in sym['api_calls'])}")
    return lines


def _format_markup_or_sql_contract(lang: str, sym: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if lang == "html":
        if sym.get("ids"):
            lines.append(f"- DOM IDs: {', '.join(f'`#{i}`' for i in sym['ids'][:30])}")
        if sym.get("css_classes"):
            lines.append(f"- CSS classes: {', '.join(f'`.{c}`' for c in sym['css_classes'][:30])}")
    elif lang == "css":
        if sym.get("css_classes"):
            lines.append(f"- Defined CSS classes: {', '.join(f'`.{c}`' for c in sym['css_classes'][:30])}")
        if sym.get("ids"):
            lines.append(f"- Defined IDs: {', '.join(f'`#{i}`' for i in sym['ids'][:30])}")
    elif lang == "sql" and sym.get("tables"):
        lines.append(f"- SQL tables: {', '.join(f'`{t}`' for t in sym['tables'])}")
    return lines


def _format_symbol_contract(rel_path: str, sym: dict[str, Any]) -> str:
    lang = sym.get("language", "unknown")
    lines = [f"### File: `{rel_path}` ({lang})"]
    if lang == "python":
        lines.extend(_format_python_contract(sym))
    elif lang in {"javascript", "typescript"}:
        lines.extend(_format_js_contract(sym))
    else:
        lines.extend(_format_markup_or_sql_contract(lang, sym))
    return "\n".join(lines)


def _append_contract_section(sections: list[str], heading: str, paths: list[str], symbols: dict[str, dict[str, Any]]) -> None:
    matched = [p for p in paths if p in symbols]
    if not matched:
        return
    sections.append(heading)
    for rel in matched:
        sections.append(_format_symbol_contract(rel, symbols[rel]))


def get_file_context_contract(ws_dir: Path, target_rel_path: str) -> str:
    graph = build_workspace_code_graph(ws_dir)
    norm_target = target_rel_path.replace("\\", "/").lstrip("/")
    symbols = graph.get("symbols", {})
    edges = graph.get("edges", [])

    direct_deps = list(dict.fromkeys(e["target"] for e in edges if e["source"] == norm_target))
    dependents = list(dict.fromkeys(e["source"] for e in edges if e["target"] == norm_target))

    sections: list[str] = [f"# Interface Context Contract for `{norm_target}`"]
    if norm_target in symbols:
        sections.append("## Target File Symbols")
        sections.append(_format_symbol_contract(norm_target, symbols[norm_target]))

    _append_contract_section(sections, "## Direct Dependencies (Imported / Referenced by Target)", direct_deps, symbols)
    _append_contract_section(sections, "## Reverse Dependents (Files Importing / Referencing Target)", dependents, symbols)

    if not direct_deps and not dependents:
        other_files = [k for k in symbols if k != norm_target][:8]
        _append_contract_section(sections, "## Workspace Sibling Contracts", other_files, symbols)

    target_broken = [b for b in graph.get("broken_references", []) if b.get("source") == norm_target]
    if target_broken:
        sections.append("## Broken References Detected")
        sections.extend(f"- `{b['type']}` referencing `{b['target']}`" for b in target_broken)

    return "\n\n".join(sections)
