from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

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

STDLIB_MODULES = {
    "abc",
    "argparse",
    "ast",
    "asyncio",
    "base64",
    "collections",
    "concurrent",
    "contextlib",
    "copy",
    "csv",
    "ctypes",
    " dataclasses",
    "dataclasses",
    "datetime",
    "decimal",
    "difflib",
    "email",
    "enum",
    "errno",
    "faulthandler",
    "fnmatch",
    "fractions",
    "functools",
    "gc",
    "getpass",
    "gettext",
    "glob",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "imaplib",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "math",
    "mimetypes",
    "mmap",
    "multiprocessing",
    "numbers",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "queue",
    "quopri",
    "random",
    "re",
    "reprlib",
    "resource",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtplib",
    "socket",
    "socketserver",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sys",
    "sysconfig",
    "tarfile",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
    "__future__",
}

COMMON_THIRD_PARTY_MODULES = {
    "aiofiles",
    "aiohttp",
    "bs4",
    "certifi",
    "chardet",
    "click",
    "cryptography",
    "cv2",
    "docx",
    "dotenv",
    "fastapi",
    "fitz",
    "flask",
    "httpx",
    "jinja2",
    "joblib",
    "matplotlib",
    "multipart",
    "numpy",
    "openpyxl",
    "ortools",
    "pandas",
    "passlib",
    "pdfplumber",
    "peft",
    "PIL",
    "playwright",
    "pptx",
    "psutil",
    "pydantic",
    "pyinstaller",
    "pypdf",
    "pytest",
    "pytz",
    "redis",
    "reportlab",
    "requests",
    "rich",
    "ruff",
    "scipy",
    "seaborn",
    "sklearn",
    "sqlalchemy",
    "starlette",
    "sympy",
    "torch",
    "tqdm",
    "transformers",
    "typer",
    "urllib3",
    "uvicorn",
    "websockets",
    "werkzeug",
    "xgboost",
    "yaml",
}


def _unparse_annotation(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _parse_python_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args_list: list[dict[str, str]] = []
    pos_args = list(node.args.posonlyargs) + list(node.args.args)
    defaults = [None] * (len(pos_args) - len(node.args.defaults)) + list(node.args.defaults)
    for arg_node, default_node in zip(pos_args, defaults, strict=False):
        args_list.append(
            {
                "name": arg_node.arg,
                "annotation": _unparse_annotation(arg_node.annotation),
                "default": _unparse_annotation(default_node) if default_node is not None else "",
            }
        )
    if node.args.vararg:
        args_list.append(
            {
                "name": f"*{node.args.vararg.arg}",
                "annotation": _unparse_annotation(node.args.vararg.annotation),
                "default": "",
            }
        )
    for kw_arg, kw_default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False):
        args_list.append(
            {
                "name": kw_arg.arg,
                "annotation": _unparse_annotation(kw_arg.annotation),
                "default": _unparse_annotation(kw_default) if kw_default is not None else "",
            }
        )
    if node.args.kwarg:
        args_list.append(
            {
                "name": f"**{node.args.kwarg.arg}",
                "annotation": _unparse_annotation(node.args.kwarg.annotation),
                "default": "",
            }
        )

    returns = _unparse_annotation(node.returns)
    sig_parts = []
    for a in args_list:
        part = a["name"]
        if a["annotation"]:
            part += f": {a['annotation']}"
        if a["default"]:
            part += f" = {a['default']}"
        sig_parts.append(part)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret_str = f" -> {returns}" if returns else ""
    signature = f"{prefix} {node.name}({', '.join(sig_parts)}){ret_str}"

    return {
        "name": node.name,
        "line": node.lineno,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "args": args_list,
        "returns": returns,
        "signature": signature,
    }


def parse_python_file(source: str, rel_path: str) -> dict[str, Any]:
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    syntax_error: str | None = None

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        syntax_error = f"{exc.msg} (line {exc.lineno})"
        return {
            "language": "python",
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "routes": routes,
            "syntax_error": syntax_error,
        }

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_info = _parse_python_function(node)
            functions.append(fn_info)
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    method = dec.func.attr.upper()
                    if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "ROUTE"} and dec.args:
                        first_arg = dec.args[0]
                        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                            routes.append(
                                {
                                    "method": method,
                                    "path": first_arg.value,
                                    "handler": node.name,
                                    "line": node.lineno,
                                }
                            )
        elif isinstance(node, ast.ClassDef):
            bases = [_unparse_annotation(b) for b in node.bases]
            methods: list[dict[str, Any]] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(_parse_python_function(item))
            classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "bases": bases,
                    "methods": methods,
                }
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {
                        "module": alias.name,
                        "names": [alias.asname or alias.name],
                        "level": 0,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(
                {
                    "module": mod_name,
                    "names": names,
                    "level": node.level,
                    "line": node.lineno,
                }
            )

    return {
        "language": "python",
        "classes": classes,
        "functions": functions,
        "imports": imports,
        "routes": routes,
        "syntax_error": syntax_error,
    }


_JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)"
    r"|(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
    re.MULTILINE,
)
_JS_CLASS_RE = re.compile(
    r"(?:export\s+)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$][\w$.]*))?",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""import\s+(?:[\w*\s{},$]+\s+from\s+)?['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)
_JS_EXPORT_RE = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)"
    r"|export\s*\{\s*([^}]+)\s*\}",
    re.MULTILINE,
)
_JS_FETCH_RE = re.compile(
    r"""fetch\(\s*[`'"]([^`'"]+)[`'"]""",
    re.MULTILINE,
)


def parse_js_ts_file(source: str, rel_path: str) -> dict[str, Any]:
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    imports: list[str] = []
    exports: list[str] = []
    api_calls: list[str] = []

    for match in _JS_FUNC_RE.finditer(source):
        fn_name = match.group(1) or match.group(3)
        raw_args = (match.group(2) if match.group(1) else match.group(4)) or ""
        args = [a.strip() for a in raw_args.split(",") if a.strip()]
        line = source.count("\n", 0, match.start()) + 1
        functions.append(
            {
                "name": fn_name,
                "args": args,
                "line": line,
                "signature": f"function {fn_name}({', '.join(args)})",
            }
        )

    for match in _JS_CLASS_RE.finditer(source):
        cls_name = match.group(1)
        base_name = match.group(2) or ""
        line = source.count("\n", 0, match.start()) + 1
        classes.append(
            {
                "name": cls_name,
                "extends": base_name,
                "line": line,
            }
        )

    for match in _JS_IMPORT_RE.finditer(source):
        target = match.group(1) or match.group(2)
        if target and target not in imports:
            imports.append(target)

    for match in _JS_EXPORT_RE.finditer(source):
        if match.group(1):
            name = match.group(1).strip()
            if name not in exports:
                exports.append(name)
        elif match.group(2):
            for part in match.group(2).split(","):
                cleaned = part.strip().split(" as ")[-1].strip()
                if cleaned and cleaned not in exports:
                    exports.append(cleaned)

    for match in _JS_FETCH_RE.finditer(source):
        url = match.group(1).strip()
        if url not in api_calls:
            api_calls.append(url)

    lang = "typescript" if rel_path.endswith(".ts") else "javascript"
    return {
        "language": lang,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "exports": exports,
        "api_calls": api_calls,
    }


_HTML_SCRIPT_RE = re.compile(r"""<script\b[^>]*\bsrc\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
_HTML_LINK_RE = re.compile(r"""<link\b[^>]*\bhref\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
_HTML_ID_RE = re.compile(r"""\bid\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
_HTML_CLASS_RE = re.compile(r"""\bclass\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)


def parse_html_file(source: str) -> dict[str, Any]:
    scripts = [m.group(1).strip() for m in _HTML_SCRIPT_RE.finditer(source)]
    stylesheets = [m.group(1).strip() for m in _HTML_LINK_RE.finditer(source)]
    ids = list(dict.fromkeys(m.group(1).strip() for m in _HTML_ID_RE.finditer(source) if m.group(1).strip()))
    css_classes: list[str] = []
    for match in _HTML_CLASS_RE.finditer(source):
        for token in match.group(1).split():
            if token not in css_classes:
                css_classes.append(token)
    return {
        "language": "html",
        "scripts": scripts,
        "stylesheets": stylesheets,
        "ids": ids,
        "css_classes": css_classes,
    }


_CSS_CLASS_SELECTOR_RE = re.compile(r"\.([A-Za-z_-][\w-]*)")
_CSS_ID_SELECTOR_RE = re.compile(r"#([A-Za-z_-][\w-]*)")
_CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\()?\s*['"]([^'"]+)['"]""")


def parse_css_file(source: str) -> dict[str, Any]:
    stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    selector_blocks = re.findall(r"([^{}]+)\{[^{}]*\}", stripped)
    class_names: list[str] = []
    id_names: list[str] = []
    for selector in selector_blocks:
        for cls_match in _CSS_CLASS_SELECTOR_RE.finditer(selector):
            name = cls_match.group(1)
            if name not in class_names:
                class_names.append(name)
        for id_match in _CSS_ID_SELECTOR_RE.finditer(selector):
            name = id_match.group(1)
            if name not in id_names:
                id_names.append(name)
    imports = [m.group(1).strip() for m in _CSS_IMPORT_RE.finditer(stripped)]
    return {
        "language": "css",
        "css_classes": class_names,
        "ids": id_names,
        "imports": imports,
    }


_SQL_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?([A-Za-z_][\w]*)[`\"']?",
    re.IGNORECASE,
)


def parse_sql_file(source: str) -> dict[str, Any]:
    tables = list(dict.fromkeys(m.group(1) for m in _SQL_TABLE_RE.finditer(source)))
    return {
        "language": "sql",
        "tables": tables,
    }


def _resolve_relative_asset(ws_dir: Path, source_rel_path: str, ref_url: str) -> str | None:
    cleaned = ref_url.split("?", 1)[0].split("#", 1)[0].strip()
    if not cleaned or cleaned.startswith(("http://", "https://", "//", "data:", "mailto:", "javascript:")):
        return None
    source_parent = (ws_dir / source_rel_path).parent
    if cleaned.startswith("/"):
        candidate = (ws_dir / cleaned.lstrip("/")).resolve()
    else:
        candidate = (source_parent / cleaned).resolve()
    ws_root = ws_dir.resolve()
    try:
        rel = candidate.relative_to(ws_root).as_posix()
        return rel
    except ValueError:
        return cleaned


def _resolve_python_import(
    ws_dir: Path,
    source_rel_path: str,
    imp: dict[str, Any],
    py_module_index: dict[str, str],
) -> tuple[str | None, bool]:
    """Return (resolved_rel_path, is_broken_local).

    Returns `(path, False)` when matched to a workspace file, `(None, False)` when
    recognized as stdlib or known third-party package, and `(missing_spec, True)`
    when it appears to be a missing local module.
    """
    module_name = imp["module"]
    level = imp.get("level", 0)
    names = imp.get("names", [])
    source_dir = (ws_dir / source_rel_path).parent

    if level > 0:
        base_dir = source_dir
        for _ in range(level - 1):
            base_dir = base_dir.parent
        if module_name:
            target_base = base_dir.joinpath(*module_name.split("."))
            candidates = [target_base.with_suffix(".py"), target_base / "__init__.py"]
            for cand in candidates:
                if cand.is_file():
                    return cand.resolve().relative_to(ws_dir.resolve()).as_posix(), False
            return module_name, True
        for name in names:
            cand_py = base_dir / f"{name}.py"
            cand_init = base_dir / name / "__init__.py"
            if cand_py.is_file():
                return cand_py.resolve().relative_to(ws_dir.resolve()).as_posix(), False
            if cand_init.is_file():
                return cand_init.resolve().relative_to(ws_dir.resolve()).as_posix(), False
        return ".".join(names), True

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
    if cleaned.startswith("/"):
        base_candidate = (ws_dir / cleaned.lstrip("/")).resolve()
    else:
        base_candidate = (source_parent / cleaned).resolve()

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


def build_workspace_code_graph(ws_dir: Path) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    if not ws_dir.exists():
        return {
            "workspace": str(ws_dir),
            "nodes": [],
            "edges": [],
            "symbols": {},
            "broken_references": [],
        }

    files: list[Path] = []
    for path in sorted(ws_dir.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)

    known_files: set[str] = set()
    py_module_index: dict[str, str] = {}
    for file_path in files:
        rel_path = file_path.relative_to(ws_dir).as_posix()
        known_files.add(rel_path)
        if file_path.suffix.lower() == ".py":
            no_ext = rel_path[:-3]
            dotted = no_ext.replace("/", ".")
            py_module_index[dotted] = rel_path
            if dotted.endswith(".__init__"):
                py_module_index[dotted[: -len(".__init__")]] = rel_path
            stem = file_path.stem
            if stem != "__init__" and stem not in py_module_index:
                py_module_index[stem] = rel_path

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    symbols: dict[str, dict[str, Any]] = {}
    broken_references: list[dict[str, Any]] = []

    for file_path in files:
        rel_path = file_path.relative_to(ws_dir).as_posix()
        ext = file_path.suffix.lower()
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            source = ""

        if ext == ".py":
            parsed = parse_python_file(source, rel_path)
            symbols[rel_path] = parsed
            nodes.append(
                {
                    "id": rel_path,
                    "language": "python",
                    "classes": [c["name"] for c in parsed["classes"]],
                    "functions": [f["name"] for f in parsed["functions"]],
                    "routes": parsed["routes"],
                }
            )
            for imp in parsed["imports"]:
                target_rel, is_broken = _resolve_python_import(ws_dir, rel_path, imp, py_module_index)
                if target_rel and not is_broken:
                    if target_rel != rel_path:
                        edges.append(
                            {
                                "source": rel_path,
                                "target": target_rel,
                                "type": "python_import",
                            }
                        )
                elif is_broken:
                    broken_references.append(
                        {
                            "source": rel_path,
                            "target": str(target_rel),
                            "type": "missing_python_import",
                            "line": imp.get("line", 1),
                        }
                    )

        elif ext in {".js", ".ts"}:
            parsed = parse_js_ts_file(source, rel_path)
            symbols[rel_path] = parsed
            nodes.append(
                {
                    "id": rel_path,
                    "language": parsed["language"],
                    "classes": [c["name"] for c in parsed["classes"]],
                    "functions": [f["name"] for f in parsed["functions"]],
                    "exports": parsed["exports"],
                    "api_calls": parsed["api_calls"],
                }
            )
            for spec in parsed["imports"]:
                target_rel, is_broken = _resolve_js_import(ws_dir, rel_path, spec, known_files)
                if target_rel and not is_broken:
                    edges.append(
                        {
                            "source": rel_path,
                            "target": target_rel,
                            "type": "js_import",
                        }
                    )
                elif is_broken:
                    broken_references.append(
                        {
                            "source": rel_path,
                            "target": spec,
                            "type": "missing_js_import",
                        }
                    )

        elif ext == ".html":
            parsed = parse_html_file(source)
            symbols[rel_path] = parsed
            nodes.append(
                {
                    "id": rel_path,
                    "language": "html",
                    "ids": parsed["ids"],
                    "css_classes": parsed["css_classes"],
                }
            )
            for script_src in parsed["scripts"]:
                resolved = _resolve_relative_asset(ws_dir, rel_path, script_src)
                if resolved is None:
                    continue
                if resolved in known_files or (ws_dir / resolved).is_file():
                    edges.append(
                        {
                            "source": rel_path,
                            "target": resolved,
                            "type": "html_script",
                        }
                    )
                else:
                    broken_references.append(
                        {
                            "source": rel_path,
                            "target": script_src,
                            "resolved": resolved,
                            "type": "missing_html_script",
                        }
                    )
            for link_href in parsed["stylesheets"]:
                resolved = _resolve_relative_asset(ws_dir, rel_path, link_href)
                if resolved is None:
                    continue
                if resolved in known_files or (ws_dir / resolved).is_file():
                    edges.append(
                        {
                            "source": rel_path,
                            "target": resolved,
                            "type": "html_stylesheet",
                        }
                    )
                else:
                    broken_references.append(
                        {
                            "source": rel_path,
                            "target": link_href,
                            "resolved": resolved,
                            "type": "missing_html_stylesheet",
                        }
                    )

        elif ext == ".css":
            parsed = parse_css_file(source)
            symbols[rel_path] = parsed
            nodes.append(
                {
                    "id": rel_path,
                    "language": "css",
                    "css_classes": parsed["css_classes"],
                    "ids": parsed["ids"],
                }
            )
            for css_imp in parsed["imports"]:
                resolved = _resolve_relative_asset(ws_dir, rel_path, css_imp)
                if resolved is None:
                    continue
                if resolved in known_files or (ws_dir / resolved).is_file():
                    edges.append(
                        {
                            "source": rel_path,
                            "target": resolved,
                            "type": "css_import",
                        }
                    )
                else:
                    broken_references.append(
                        {
                            "source": rel_path,
                            "target": css_imp,
                            "resolved": resolved,
                            "type": "missing_css_import",
                        }
                    )

        elif ext == ".sql":
            parsed = parse_sql_file(source)
            symbols[rel_path] = parsed
            nodes.append(
                {
                    "id": rel_path,
                    "language": "sql",
                    "tables": parsed["tables"],
                }
            )

    return {
        "workspace": str(ws_dir),
        "nodes": nodes,
        "edges": edges,
        "symbols": symbols,
        "broken_references": broken_references,
    }


def _format_symbol_contract(rel_path: str, sym: dict[str, Any]) -> str:
    lang = sym.get("language", "unknown")
    lines = [f"### File: `{rel_path}` ({lang})"]

    if lang == "python":
        for cls in sym.get("classes", []):
            bases = f"({', '.join(cls['bases'])})" if cls.get("bases") else ""
            lines.append(f"- class `{cls['name']}{bases}`")
            for method in cls.get("methods", []):
                lines.append(f"  - `{method['signature']}`")
        for fn in sym.get("functions", []):
            lines.append(f"- `{fn['signature']}`")
        for route in sym.get("routes", []):
            lines.append(f"- route `{route['method']} {route['path']}` -> `{route['handler']}`")
    elif lang in {"javascript", "typescript"}:
        for cls in sym.get("classes", []):
            ext = f" extends {cls['extends']}" if cls.get("extends") else ""
            lines.append(f"- class `{cls['name']}{ext}`")
        for fn in sym.get("functions", []):
            lines.append(f"- `{fn['signature']}`")
        if sym.get("exports"):
            lines.append(f"- exports: {', '.join(f'`{e}`' for e in sym['exports'])}")
        if sym.get("api_calls"):
            lines.append(f"- api_calls: {', '.join(f'`{c}`' for c in sym['api_calls'])}")
    elif lang == "html":
        if sym.get("ids"):
            lines.append(f"- DOM IDs: {', '.join(f'`#{i}`' for i in sym['ids'][:30])}")
        if sym.get("css_classes"):
            lines.append(f"- CSS classes: {', '.join(f'`.{c}`' for c in sym['css_classes'][:30])}")
    elif lang == "css":
        if sym.get("css_classes"):
            lines.append(f"- Defined CSS classes: {', '.join(f'`.{c}`' for c in sym['css_classes'][:30])}")
        if sym.get("ids"):
            lines.append(f"- Defined IDs: {', '.join(f'`#{i}`' for i in sym['ids'][:30])}")
    elif lang == "sql":
        if sym.get("tables"):
            lines.append(f"- SQL tables: {', '.join(f'`{t}`' for t in sym['tables'])}")

    return "\n".join(lines)


def get_file_context_contract(ws_dir: Path, target_rel_path: str) -> str:
    graph = build_workspace_code_graph(ws_dir)
    norm_target = target_rel_path.replace("\\", "/").lstrip("/")
    symbols = graph.get("symbols", {})
    edges = graph.get("edges", [])

    direct_deps: list[str] = []
    dependents: list[str] = []
    for edge in edges:
        if edge["source"] == norm_target and edge["target"] not in direct_deps:
            direct_deps.append(edge["target"])
        elif edge["target"] == norm_target and edge["source"] not in dependents:
            dependents.append(edge["source"])

    sections: list[str] = [f"# Interface Context Contract for `{norm_target}`"]

    if norm_target in symbols:
        sections.append("## Target File Symbols")
        sections.append(_format_symbol_contract(norm_target, symbols[norm_target]))

    if direct_deps:
        sections.append("## Direct Dependencies (Imported / Referenced by Target)")
        for dep in direct_deps:
            if dep in symbols:
                sections.append(_format_symbol_contract(dep, symbols[dep]))

    if dependents:
        sections.append("## Reverse Dependents (Files Importing / Referencing Target)")
        for rev in dependents:
            if rev in symbols:
                sections.append(_format_symbol_contract(rev, symbols[rev]))

    if not direct_deps and not dependents:
        other_files = [k for k in symbols if k != norm_target][:8]
        if other_files:
            sections.append("## Workspace Sibling Contracts")
            for sibling in other_files:
                sections.append(_format_symbol_contract(sibling, symbols[sibling]))

    target_broken = [b for b in graph.get("broken_references", []) if b.get("source") == norm_target]
    if target_broken:
        sections.append("## Broken References Detected")
        for b in target_broken:
            sections.append(f"- `{b['type']}` referencing `{b['target']}`")

    return "\n\n".join(sections)
