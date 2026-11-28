"""Does the README still describe the project that was delivered?

Files, endpoints, ports, start commands and command-line flags named in the README are checked against the code. A
reference to something that does not exist blocks delivery; the repair removes those lines and writes the real list.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import atomic_io
import plan_matrix

_README = ("README.md", "readme.md", "Readme.md")
_MARK = "<!-- koddan üretildi -->"
_FILE_RE = re.compile(r"`([\w./\\-]+\.(?:py|js|ts|html|css|json|yml|yaml|toml|txt|md|sql|ps1|bat|sh))`")
_ROUTE_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+`?(/[\w/{}:.-]*)")
_PORT_RE = re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d{2,5})|--port[ =](\d{2,5})|\bport[u]?\s+(\d{4,5})\b", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"\bpython3?\s+(?:-m\s+)?([\w./\\-]+\.py)((?:[ \t]+[^\n`]*)?)")
_UVICORN_RE = re.compile(r"\buvicorn\s+([\w.]+):(\w+)")
_FLAG_RE = re.compile(r"(?<![\w-])(--[a-z][\w-]*)")
_GENERATED = {"app.db", "database.db", "requirements.lock"}
_SKIP = {".history", ".ai-os", "venv", ".venv", "node_modules", "__pycache__", "vendor"}


@dataclass(frozen=True)
class Drift:
    line: int
    detail: str


def readme(ws_dir: Path) -> Path | None:
    return next((ws_dir / name for name in _README if (ws_dir / name).is_file()), None)


def _files(ws_dir: Path) -> set[str]:
    found = set()
    for path in ws_dir.rglob("*"):
        if path.is_file() and not _SKIP & set(path.relative_to(ws_dir).parts):
            found |= {path.relative_to(ws_dir).as_posix(), path.name}
    return found


def _routes(ws_dir: Path, files: set[str]) -> set[tuple[str, str]]:
    declared = plan_matrix.endpoints(ws_dir, [f for f in files if (ws_dir / f).is_file()])
    return {(route["method"], _shape(route["path"])) for route in declared}


def _shape(path: str) -> str:
    return re.sub(r"\{[^}]*\}|:\w+|<[^>]*>", "{}", path.rstrip("/.")) or "/"


def _ports(ws_dir: Path, files: set[str]) -> set[str]:
    """Ports the code or its start files really use; the usual defaults when they name none."""
    found: set[str] = set()
    for name in files:
        path = ws_dir / name
        if path.is_file() and path.suffix in (".py", ".js", ".ps1", ".bat", ".yml", ".yaml", "") and path.stat().st_size < 200_000:
            text = path.read_text(encoding="utf-8", errors="replace")
            found |= set(re.findall(r"port\s*[=:]\s*[\"']?(\d{4,5})", text, re.IGNORECASE)) | set(re.findall(r"--port[ =](\d{4,5})", text))
            found |= {p for pair in re.findall(r"[\"'](\d{4,5}):(\d{4,5})[\"']", text) for p in pair}
    return found or {"8000", "5000", "3000"}


def _flags(script: Path) -> set[str]:
    try:
        tree = ast.parse(script.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    return {
        arg.value for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument"
        for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    } | {"--help"}


def _command_drift(ws_dir: Path, line: str, files: set[str]) -> list[str]:
    found = []
    for script, rest in _SCRIPT_RE.findall(line):
        name = script.replace("\\", "/")
        if name not in files:
            found.append(f"olmayan betik: {name}")
            continue
        target = ws_dir / name if (ws_dir / name).is_file() else next(ws_dir.rglob(Path(name).name))
        found += [f"{name} böyle bir seçenek tanımlamıyor: {flag}" for flag in _FLAG_RE.findall(rest) if flag not in _flags(target)]
    for module, obj in _UVICORN_RE.findall(line):
        source = ws_dir / f"{module.replace('.', '/')}.py"
        if not source.is_file() or not re.search(rf"^{obj}\s*=", source.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
            found.append(f"uvicorn hedefi yok: {module}:{obj}")
    return found


def check(ws_dir: Path) -> list[Drift]:
    document = readme(ws_dir)
    if document is None:
        return []
    files = _files(ws_dir)
    routes, ports = _routes(ws_dir, files), _ports(ws_dir, files)
    found: list[Drift] = []
    for number, line in enumerate(document.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        wrong = [f"olmayan dosya: {name}" for name in _FILE_RE.findall(line) if name.replace("\\", "/").lstrip("./") not in files and Path(name).name not in _GENERATED]
        if routes:
            wrong += [f"olmayan uç nokta: {method} {path}" for method, path in _ROUTE_RE.findall(line) if (method, _shape(path)) not in routes]
        wrong += [f"kodda kullanılmayan port: {port}" for match in _PORT_RE.findall(line) for port in match if port and port not in ports]
        wrong += _command_drift(ws_dir, line, files)
        found += [Drift(number, detail) for detail in dict.fromkeys(wrong)]
    return found


def lines(ws_dir: Path) -> list[str]:
    return [f"README satır {d.line}: {d.detail}" for d in check(ws_dir)]


def repair(ws_dir: Path) -> list[str]:
    """Removes the lines that describe things that do not exist and appends the real endpoints; returns what changed."""
    document, drift = readme(ws_dir), check(ws_dir)
    if document is None or not drift:
        return []
    bad = {d.line for d in drift}
    kept = [text for number, text in enumerate(document.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if number not in bad]
    body = "\n".join(kept).split(_MARK)[0].rstrip()
    routes = sorted(_routes(ws_dir, _files(ws_dir)))
    if routes:
        body += f"\n\n{_MARK}\n## Uç noktalar (koddan)\n" + "\n".join(f"- {method} `{path}`" for method, path in routes)
    atomic_io.write_text(document, body + "\n")
    return [f"README gerçek koda göre düzeltildi: {len(bad)} satır kaldırıldı ({drift[0].detail})"]
