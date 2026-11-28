"""The architecture fitness guardian's eyes: size and complexity ceilings, copies, dead weight and layer rules.

Static analysis of a generated project on the CPU, no model: Python through its syntax tree, JavaScript, CSS and HTML
through their text. Every finding is (kind, file, subject, detail).
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

MAX_COMPLEXITY, MAX_FUNCTION_LINES, MAX_FILE_LINES = 10, 60, 300
_CLONE_STATEMENTS = 4
_SKIP_DIRS = {".history", ".ai-os", "venv", ".venv", "__pycache__", "node_modules", "dist", "build", "vendor"}
_BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension, ast.match_case)
_JS_FUNCTION_RE = re.compile(r"(?:\bfunction\s+(\w+)\s*\([^)]*\)|\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>)\s*\{")
_JS_BRANCH_RE = re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?(?![.?:])")
_JS_NOISE_RE = re.compile(r"/\*.*?\*/|(?<![:\"'\\])//[^\n]*|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", re.DOTALL)
_DB_DRIVERS = {"sqlite3", "sqlalchemy", "psycopg2", "pymysql", "pymongo", "duckdb"}
_HTTP = {"fastapi", "flask", "starlette", "django"}
_UI_PARTS = re.compile(r"(^|/)(ui|views?|templates|components|frontend|gui)(/|_|\.)", re.IGNORECASE)
_DOMAIN_PARTS = re.compile(r"(^|/)(domain|services?|core|models?)(/|_|\.)", re.IGNORECASE)
_CSS_RULE_RE = re.compile(r"(?<![\w-])([.#])([a-zA-Z_][\w-]*)(?=[^{}]*\{)")


@dataclass(frozen=True)
class Finding:
    kind: str
    file: str
    subject: str
    detail: str

    def line(self) -> str:
        return f"{self.kind}: {self.file} {self.subject} ({self.detail})".replace("  ", " ")


def sources(ws_dir: Path, *suffixes: str) -> dict[str, str]:
    return {
        p.relative_to(ws_dir).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(ws_dir.rglob("*"))
        if p.suffix in suffixes and p.is_file() and not _SKIP_DIRS & set(p.relative_to(ws_dir).parts) and not p.name.endswith(".min.js")
    }


def _trees(ws_dir: Path) -> dict[str, ast.Module]:
    trees = {}
    for path, text in sources(ws_dir, ".py").items():
        try:
            trees[path] = ast.parse(text)
        except SyntaxError:
            continue  # reported by the static proof
    return trees


def complexity(function: ast.AST) -> int:
    score = 1
    for node in ast.walk(function):
        score += isinstance(node, _BRANCHES)
        if isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
    return score


def js_functions(text: str) -> list[tuple[str, str]]:
    """(name, body) of the named functions; strings and comments are blanked so their braces do not count."""
    clean = _JS_NOISE_RE.sub(lambda m: '""' if m.group(0)[0] in "'\"`" else "", text)
    found = []
    for match in _JS_FUNCTION_RE.finditer(clean):
        depth, index = 1, match.end()
        while index < len(clean) and depth:
            depth += {"{": 1, "}": -1}.get(clean[index], 0)
            index += 1
        found.append((match.group(1) or match.group(2), clean[match.end() : index - 1]))
    return found


def _scripts(ws_dir: Path) -> dict[str, str]:
    inline = {path: "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.DOTALL | re.IGNORECASE)) for path, text in sources(ws_dir, ".html").items()}
    return {**sources(ws_dir, ".js", ".ts"), **{path: body for path, body in inline.items() if body.strip()}}


def _size(kind_of: str, path: str, name: str, measured: tuple[int, int]) -> list[Finding]:
    score, lines = measured
    found = [Finding("karmaşıklık", path, name, f"{score} > {MAX_COMPLEXITY}")] if score > MAX_COMPLEXITY else []
    return found + ([Finding(kind_of, path, name, f"{lines} satır > {MAX_FUNCTION_LINES}")] if lines > MAX_FUNCTION_LINES else [])


def ceilings(ws_dir: Path) -> list[Finding]:
    found = [Finding("uzun dosya", path, "", f"{text.count(chr(10)) + 1} satır > {MAX_FILE_LINES}") for path, text in sources(ws_dir, ".py", ".js", ".ts").items() if text.count("\n") + 1 > MAX_FILE_LINES]
    for path, tree in _trees(ws_dir).items():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                found += _size("uzun fonksiyon", path, node.name, (complexity(node), (node.end_lineno or node.lineno) - node.lineno + 1))
    for path, text in _scripts(ws_dir).items():
        for name, body in js_functions(text):
            found += _size("uzun fonksiyon", path, name, (1 + len(_JS_BRANCH_RE.findall(body)), body.count("\n") + 1))
    return found


class _Blind(ast.NodeTransformer):
    """Forgets names and values, so copies with renamed variables still look alike."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.Name(id="_", ctx=node.ctx)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.arg(arg="_")

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.Constant(value=type(node.value).__name__)


def shape(function: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    body = function.body[1:] if function.body and isinstance(function.body[0], ast.Expr) and isinstance(getattr(function.body[0], "value", None), ast.Constant) else function.body
    blind = [_Blind().visit(copy.deepcopy(statement)) for statement in body]
    return hashlib.sha256("".join(ast.dump(s) for s in blind).encode("utf-8")).hexdigest()


def _statements(function: ast.AST) -> int:
    return sum(isinstance(n, ast.stmt) for n in ast.walk(function)) - 1


def clones(ws_dir: Path) -> list[Finding]:
    seen: dict[str, list[tuple[str, str]]] = {}
    for path, tree in _trees(ws_dir).items():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _statements(node) >= _CLONE_STATEMENTS and not node.name.startswith("test_"):
                seen.setdefault(shape(node), []).append((path, node.name))
    for path, text in _scripts(ws_dir).items():
        for name, body in js_functions(text):
            flat = re.sub(r"\s+", "", body)
            if len(flat) >= 120:
                seen.setdefault("js" + hashlib.sha256(flat.encode("utf-8")).hexdigest(), []).append((path, name))
    return [Finding("kopya kod", copies[1][0], copies[1][1], f"{copies[0][0]}::{copies[0][1]} ile aynı yapı") for copies in seen.values() if len(copies) > 1]


def _used_names(trees: dict[str, ast.Module]) -> set[str]:
    used: set[str] = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.alias):
                used.add(node.name.split(".")[-1])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isidentifier():
                used.add(node.value)
    return used


def dead_functions(ws_dir: Path) -> list[Finding]:
    """Top-level functions nobody calls; decorated ones (routes, fixtures) and entry points are in use by definition."""
    trees = _trees(ws_dir)
    used = _used_names(trees)
    return [
        Finding("ölü kod", path, node.name, "hiçbir yerden çağrılmıyor")
        for path, tree in trees.items()
        if not Path(path).name.startswith("test_")
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.decorator_list and node.name not in used and node.name not in ("main", "lifespan") and not node.name.startswith(("test_", "__"))
    ]


def dead_css(ws_dir: Path) -> list[Finding]:
    markup = "\n".join(re.sub(r"<style\b.*?</style>", "", t, flags=re.DOTALL | re.IGNORECASE) for t in sources(ws_dir, ".html", ".js", ".ts", ".jsx", ".tsx", ".py").values())
    styles = {**sources(ws_dir, ".css"), **{p: "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", t, re.DOTALL | re.IGNORECASE)) for p, t in sources(ws_dir, ".html").items()}}
    found = []
    for path, text in styles.items():
        for mark, name in dict.fromkeys(_CSS_RULE_RE.findall(re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL))):
            if not re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", markup) and not re.fullmatch(r"[0-9a-fA-F]{3,8}", name):
                found.append(Finding("kullanılmayan CSS", path, mark + name, "hiçbir sayfada ya da betikte yok"))
    return found


def orphans(ws_dir: Path) -> list[Finding]:
    """Scripts and styles no page loads, and endpoints the project's own page never calls."""
    pages = sources(ws_dir, ".html")
    if not pages:
        return []
    everything = "\n".join([*pages.values(), *sources(ws_dir, ".js", ".ts", ".css", ".py").values()])
    found = [Finding("yetim dosya", path, "", "hiçbir sayfa yüklemiyor") for path in sources(ws_dir, ".js", ".css") if Path(path).name not in everything and not path.startswith("tests/")]
    client = "\n".join([*pages.values(), *sources(ws_dir, ".js", ".ts").values()])
    for path, text in sources(ws_dir, ".py").items():
        for route in re.findall(r"@\w+\.(?:get|post|put|patch|delete)\(\s*[\"'](/api/[^\"'{]*)", text):
            if "fetch(" in client and route.rstrip("/") not in client:
                found.append(Finding("yetim uç nokta", path, route, "arayüz hiç çağırmıyor"))
    return found


def _imports(tree: ast.Module) -> set[str]:
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    return names | {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}


def _module_graph(trees: dict[str, ast.Module]) -> dict[str, set[str]]:
    modules = {path[:-3].replace("/", ".").removesuffix(".__init__"): path for path in trees}
    graph = {}
    for module, path in modules.items():
        top = [n for n in trees[path].body if isinstance(n, ast.Import | ast.ImportFrom)]  # a deferred import inside a function breaks no cycle rule
        wanted = _imports(ast.Module(body=top, type_ignores=[]))
        wanted |= {f"{n.module}.{a.name}" for n in top if isinstance(n, ast.ImportFrom) and n.module for a in n.names}
        graph[module] = {other for other in modules if other != module and (other in wanted or other.rsplit(".", 1)[-1] in wanted)}
    return graph


def cycles(ws_dir: Path) -> list[Finding]:
    graph = _module_graph(_trees(ws_dir))
    found: dict[frozenset[str], Finding] = {}

    def walk(node: str, trail: list[str]) -> None:
        for other in graph.get(node, ()):
            if other in trail:
                loop = trail[trail.index(other) :]
                found.setdefault(frozenset(loop), Finding("döngüsel içe aktarma", loop[0], "", " -> ".join([*loop, loop[0]])))
            elif len(trail) < len(graph):
                walk(other, [*trail, other])

    for module in graph:
        walk(module, [module])
    return list(found.values())


def layers(ws_dir: Path) -> list[Finding]:
    found = []
    for path, tree in _trees(ws_dir).items():
        imported = {name.split(".")[0] for name in _imports(tree)}
        if _UI_PARTS.search(path) and imported & _DB_DRIVERS:
            found.append(Finding("katman ihlali", path, "", f"arayüz katmanı veritabanı sürücüsü kullanıyor: {', '.join(sorted(imported & _DB_DRIVERS))}"))
        if _DOMAIN_PARTS.search(path) and imported & _HTTP:
            found.append(Finding("katman ihlali", path, "", f"alan mantığı HTTP çatısına bağlı: {', '.join(sorted(imported & _HTTP))}"))
    return found


def scan(ws_dir: Path) -> list[Finding]:
    return [f for check in (cycles, layers, ceilings, clones, dead_functions, dead_css, orphans) for f in check(ws_dir)]


def blocking(ws_dir: Path) -> list[str]:
    """What fails a build outright: circular imports and broken layer rules."""
    return [f.line() for check in (cycles, layers) for f in check(ws_dir)]
