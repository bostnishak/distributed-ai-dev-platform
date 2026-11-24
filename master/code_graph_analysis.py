from __future__ import annotations

import ast
import re
from typing import Any

STDLIB_MODULES = {
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "concurrent", "contextlib",
    "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib", "email", "enum",
    "errno", "faulthandler", "fnmatch", "fractions", "functools", "gc", "getpass", "gettext",
    "glob", "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma",
    "math", "mimetypes", "mmap", "multiprocessing", "numbers", "operator", "os", "pathlib",
    "pickle", "pkgutil", "platform", "plistlib", "poplib", "posixpath", "pprint", "profile",
    "pstats", "queue", "quopri", "random", "re", "reprlib", "resource", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtplib",
    "socket", "socketserver", "sqlite3", "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sys", "sysconfig", "tarfile", "tempfile", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "tomllib", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "types", "typing", "unicodedata", "unittest", "urllib",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
    "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "zoneinfo", "__future__",
}

COMMON_THIRD_PARTY_MODULES = {
    "aiofiles", "aiohttp", "bs4", "certifi", "chardet", "click", "cryptography", "cv2", "docx",
    "dotenv", "fastapi", "fitz", "flask", "httpx", "jinja2", "joblib", "matplotlib", "multipart",
    "numpy", "openpyxl", "ortools", "pandas", "passlib", "pdfplumber", "peft", "PIL", "playwright",
    "pptx", "psutil", "pydantic", "pyinstaller", "pypdf", "pytest", "pytz", "redis", "reportlab",
    "requests", "rich", "ruff", "scipy", "seaborn", "sklearn", "sqlalchemy", "starlette", "sympy",
    "torch", "tqdm", "transformers", "typer", "urllib3", "uvicorn", "websockets", "werkzeug",
    "xgboost", "yaml",
}


def _unparse_annotation(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except (ValueError, TypeError, AttributeError, RuntimeError):
        return ""


def _parse_python_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args_list: list[dict[str, str]] = []
    pos_args = list(node.args.posonlyargs) + list(node.args.args)
    defaults = [None] * (len(pos_args) - len(node.args.defaults)) + list(node.args.defaults)
    for arg_node, default_node in zip(pos_args, defaults, strict=False):
        args_list.append({
            "name": arg_node.arg,
            "annotation": _unparse_annotation(arg_node.annotation),
            "default": _unparse_annotation(default_node) if default_node is not None else "",
        })
    if node.args.vararg:
        args_list.append({
            "name": f"*{node.args.vararg.arg}",
            "annotation": _unparse_annotation(node.args.vararg.annotation),
            "default": "",
        })
    for kw_arg, kw_default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False):
        args_list.append({
            "name": kw_arg.arg,
            "annotation": _unparse_annotation(kw_arg.annotation),
            "default": _unparse_annotation(kw_default) if kw_default is not None else "",
        })
    if node.args.kwarg:
        args_list.append({
            "name": f"**{node.args.kwarg.arg}",
            "annotation": _unparse_annotation(node.args.kwarg.annotation),
            "default": "",
        })

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
    return {
        "name": node.name,
        "line": node.lineno,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "args": args_list,
        "returns": returns,
        "signature": f"{prefix} {node.name}({', '.join(sig_parts)}){ret_str}",
    }


def _extract_python_routes(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for dec in node.decorator_list:
        if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
            continue
        method = dec.func.attr.upper()
        if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "ROUTE"} and dec.args:
            first_arg = dec.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                routes.append({"method": method, "path": first_arg.value, "handler": node.name, "line": node.lineno})
    return routes


def _extract_python_imports(tree: ast.AST) -> list[dict[str, Any]]:
    imports: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "names": [alias.asname or alias.name],
                    "level": 0,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            imports.append({
                "module": node.module or "",
                "names": [alias.name for alias in node.names],
                "level": node.level,
                "line": node.lineno,
            })
    return imports


def parse_python_file(source: str, rel_path: str) -> dict[str, Any]:
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return {
            "language": "python",
            "classes": classes,
            "functions": functions,
            "imports": [],
            "routes": routes,
            "syntax_error": f"{exc.msg} (line {exc.lineno})",
        }

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_parse_python_function(node))
            routes.extend(_extract_python_routes(node))
        elif isinstance(node, ast.ClassDef):
            methods = [
                _parse_python_function(item)
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "bases": [_unparse_annotation(b) for b in node.bases],
                "methods": methods,
            })

    return {
        "language": "python",
        "classes": classes,
        "functions": functions,
        "imports": _extract_python_imports(tree),
        "routes": routes,
        "syntax_error": None,
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
_JS_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]([^`'"]+)[`'"]""", re.MULTILINE)


def _extract_js_exports(source: str) -> list[str]:
    exports: list[str] = []
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
    return exports


def parse_js_ts_file(source: str, rel_path: str) -> dict[str, Any]:
    functions: list[dict[str, Any]] = []
    for match in _JS_FUNC_RE.finditer(source):
        fn_name = match.group(1) or match.group(3)
        raw_args = (match.group(2) if match.group(1) else match.group(4)) or ""
        args = [a.strip() for a in raw_args.split(",") if a.strip()]
        line = source.count("\n", 0, match.start()) + 1
        functions.append({
            "name": fn_name,
            "args": args,
            "line": line,
            "signature": f"function {fn_name}({', '.join(args)})",
        })

    classes = [
        {
            "name": match.group(1),
            "extends": match.group(2) or "",
            "line": source.count("\n", 0, match.start()) + 1,
        }
        for match in _JS_CLASS_RE.finditer(source)
    ]
    imports = list(dict.fromkeys(
        target for match in _JS_IMPORT_RE.finditer(source) if (target := match.group(1) or match.group(2))
    ))
    api_calls = list(dict.fromkeys(match.group(1).strip() for match in _JS_FETCH_RE.finditer(source)))
    return {
        "language": "typescript" if rel_path.endswith(".ts") else "javascript",
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "exports": _extract_js_exports(source),
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
    css_classes = list(dict.fromkeys(
        token for match in _HTML_CLASS_RE.finditer(source) for token in match.group(1).split()
    ))
    return {"language": "html", "scripts": scripts, "stylesheets": stylesheets, "ids": ids, "css_classes": css_classes}


_CSS_CLASS_SELECTOR_RE = re.compile(r"\.([A-Za-z_-][\w-]*)")
_CSS_ID_SELECTOR_RE = re.compile(r"#([A-Za-z_-][\w-]*)")
_CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\()?\s*['"]([^'"]+)['"]""")


def parse_css_file(source: str) -> dict[str, Any]:
    stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    selector_blocks = re.findall(r"([^{}]+)\{[^{}]*\}", stripped)
    class_names = list(dict.fromkeys(
        m.group(1) for selector in selector_blocks for m in _CSS_CLASS_SELECTOR_RE.finditer(selector)
    ))
    id_names = list(dict.fromkeys(
        m.group(1) for selector in selector_blocks for m in _CSS_ID_SELECTOR_RE.finditer(selector)
    ))
    imports = [m.group(1).strip() for m in _CSS_IMPORT_RE.finditer(stripped)]
    return {"language": "css", "css_classes": class_names, "ids": id_names, "imports": imports}


_SQL_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?([A-Za-z_][\w]*)[`\"']?",
    re.IGNORECASE,
)


def parse_sql_file(source: str) -> dict[str, Any]:
    tables = list(dict.fromkeys(m.group(1) for m in _SQL_TABLE_RE.finditer(source)))
    return {"language": "sql", "tables": tables}
