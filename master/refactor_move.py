"""Split a module and migrate a function signature by code, without asking a model to rewrite files.

  topla, carp fonksiyonlarını hesap modülüne taşı
  hesapla fonksiyonuna kdv parametresi ekle varsayılan 20
  hesapla fonksiyonunda oran parametresini kdv_orani yap

Moved names are imported back into the old module, so every caller keeps working. Nothing is written unless every
changed file still parses.
"""

from __future__ import annotations

import ast
import keyword
import re
from pathlib import Path

import atomic_io

_MOVE_RE = re.compile(r"^\s*(?P<names>[A-Za-z_]\w*(?:\s*(?:,|ve)\s*[A-Za-z_]\w*)*)\s+(?:fonksiyon(?:larını|unu)|sınıf(?:larını|ını))\s+(?P<module>[A-Za-z_]\w*)(?:\.py)?\s+modülüne\s+taşı\s*[.!]?\s*$", re.IGNORECASE)
_ADD_RE = re.compile(r"^\s*(?P<function>[A-Za-z_]\w*)\s+fonksiyonuna\s+(?P<param>[A-Za-z_]\w*)\s+parametresi\s+ekle\s+varsayılan\s+(?:değer\s+)?(?P<default>\S+)\s*[.!]?\s*$", re.IGNORECASE)
_RENAME_RE = re.compile(r"^\s*(?P<function>[A-Za-z_]\w*)\s+fonksiyonunda\s+(?P<old>[A-Za-z_]\w*)\s+parametresini\s+(?P<new>[A-Za-z_]\w*)\s+yap\s*[.!]?\s*$", re.IGNORECASE)
_SKIP = {".history", ".ai-os", "venv", ".venv", "node_modules", "__pycache__", ".git"}


def parse(prompt: str) -> tuple[str, dict[str, str]] | None:
    for kind, pattern in (("move", _MOVE_RE), ("add", _ADD_RE), ("param", _RENAME_RE)):
        if match := pattern.match(prompt):
            return kind, match.groupdict()
    return None


def _sources(ws_dir: Path) -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in sorted(ws_dir.rglob("*.py")) if not _SKIP & set(p.relative_to(ws_dir).parts)}


def _definitions(source: str) -> dict[str, ast.stmt]:
    return {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)}


def _owner(sources: dict[Path, str], name: str) -> Path:
    owners = [path for path, source in sources.items() if name in _definitions(source)]
    if len(owners) != 1:
        raise ValueError(f"`{name}` {'hiçbir dosyada' if not owners else 'birden çok dosyada'} tanımlı")
    return owners[0]


def _span(node: ast.stmt) -> tuple[int, int]:
    return min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno]) - 1, node.end_lineno or node.lineno


def _loaded(nodes: list[ast.stmt]) -> set[str]:
    return {n.id for node in nodes for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def move(ws_dir: Path, names: list[str], module: str) -> list[str]:
    """Move top-level functions or classes into a new module; returns the changed files."""
    sources = _sources(ws_dir)
    origin = _owner(sources, names[0])
    source = sources[origin]
    defined = _definitions(source)
    if missing := [n for n in names if n not in defined]:
        raise ValueError(f"{origin.name} içinde yok: {', '.join(missing)}")
    target = origin.with_name(f"{module}.py")
    if target.exists():
        raise ValueError(f"{target.name} zaten var; var olan dosyanın üzerine taşınmaz")
    nodes = [defined[n] for n in names]
    tree = ast.parse(source)
    top_level = set(defined) | {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    if stays := sorted((_loaded(nodes) & top_level) - set(names)):
        raise ValueError(f"taşınacak kod {origin.name} içindeki şunları kullanıyor, döngüsel içe aktarma olur: {', '.join(stays)} (onları da taşı)")
    used = _loaded(nodes)
    imports = [ast.get_source_segment(source, n) for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)
               and any((a.asname or a.name.split(".")[0]) in used for a in n.names)]
    lines = source.splitlines(keepends=True)
    blocks = ["".join(lines[start:end]).rstrip("\n") for start, end in map(_span, nodes)]
    for start, end in sorted(map(_span, nodes), reverse=True):
        del lines[start:end]
    kept = ast.parse("".join(lines))
    after = max((n.end_lineno or 0 for n in kept.body if isinstance(n, ast.Import | ast.ImportFrom)), default=0)
    package = ".".join(origin.relative_to(ws_dir).parts[:-1])
    lines.insert(after, f"from {package + '.' if package else ''}{module} import {', '.join(names)}  # noqa: F401 - moved, still importable from here\n")
    moved = ("\n".join(i for i in imports if i) + "\n\n\n" if imports else "") + "\n\n\n".join(blocks) + "\n"
    remaining = re.sub(r"\n{4,}", "\n\n\n", "".join(lines))
    for text in (moved, remaining):
        ast.parse(text)
    atomic_io.write_text(target, moved)
    atomic_io.write_text(origin, remaining)
    return [target.relative_to(ws_dir).as_posix(), origin.relative_to(ws_dir).as_posix()]


def _offset(source: str, line: int, column: int) -> int:
    """ast columns are UTF-8 byte offsets; turn one into a character index of the whole text."""
    lines = source.splitlines(keepends=True)
    return sum(len(x) for x in lines[: line - 1]) + len(lines[line - 1].encode("utf-8")[:column].decode("utf-8"))


def _apply(source: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, text in sorted(edits, reverse=True):
        source = source[:start] + text + source[end:]
    ast.parse(source)
    return source


def add_parameter(ws_dir: Path, function: str, param: str, default: str) -> list[str]:
    """Add a parameter with a default, so existing calls stay valid."""
    sources = _sources(ws_dir)
    path = _owner(sources, function)
    source = sources[path]
    node = _definitions(source)[function]
    if isinstance(node, ast.ClassDef) or not param.isidentifier() or keyword.iskeyword(param):
        raise ValueError("yalnız bir fonksiyona, geçerli adlı bir parametre eklenebilir")
    if param in [a.arg for a in (*node.args.args, *node.args.kwonlyargs)]:
        raise ValueError(f"`{param}` zaten parametre")
    ast.literal_eval(default)  # only a plain value may be written into code
    opening = source.index("(", _offset(source, node.lineno, node.col_offset))
    depth, index = 0, opening
    for index in range(opening, len(source)):
        depth += {"(": 1, ")": -1}.get(source[index], 0)
        if depth == 0:
            break
    inside = source[opening + 1 : index].rstrip()
    addition = f"{'' if not inside or inside.endswith(',') else ', '}{'*, ' if node.args.kwarg else ''}{param}={default}"
    if node.args.kwarg:
        raise ValueError("**kwargs alan fonksiyonda parametre eklemeyi elle yap")
    atomic_io.write_text(path, _apply(source, [(index, index, addition)]))
    return [path.relative_to(ws_dir).as_posix()]


def _parameter_edits(source: str, change: tuple[str, str, str], owns: bool) -> list[tuple[int, int, str]]:
    """Positions to rewrite for (function, old name, new name); the body is only touched in the defining file."""
    function, old, new = change
    tree, edits = ast.parse(source), []
    for node in ast.walk(tree):
        if owns and isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function:
            if new in {a.arg for a in node.args.args + node.args.kwonlyargs} | _loaded(node.body):
                raise ValueError(f"`{new}` fonksiyonda zaten kullanılıyor")
            for part in ast.walk(node):
                if (isinstance(part, ast.arg) and part.arg == old) or (isinstance(part, ast.Name) and part.id == old):
                    start = _offset(source, part.lineno, part.col_offset)
                    edits.append((start, start + len(old), new))
        elif isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == function:
            for item in node.keywords:
                if item.arg == old:
                    start = _offset(source, item.lineno, item.col_offset)
                    edits.append((start, start + len(old), new))
    return edits


def rename_parameter(ws_dir: Path, function: str, old: str, new: str) -> list[str]:
    """Rename a parameter in the definition, its body and every keyword argument at the call sites."""
    sources = _sources(ws_dir)
    owner = _owner(sources, function)
    node = _definitions(sources[owner])[function]
    if isinstance(node, ast.ClassDef) or old not in [a.arg for a in (*node.args.args, *node.args.kwonlyargs)] or not new.isidentifier() or keyword.iskeyword(new):
        raise ValueError(f"`{function}` fonksiyonunda `{old}` adlı bir parametre yok ya da yeni ad geçersiz")
    changed = {}
    for path, source in sources.items():
        if edits := _parameter_edits(source, (function, old, new), path == owner):
            changed[path] = _apply(source, edits)
    for path, text in changed.items():
        atomic_io.write_text(path, text)
    return [p.relative_to(ws_dir).as_posix() for p in changed]


def run(ws_dir: Path, kind: str, values: dict[str, str]) -> list[str]:
    """Changed files; ValueError says why nothing was changed."""
    try:
        if kind == "move":
            return move(ws_dir, re.split(r"\s*,\s*|\s+ve\s+", values["names"].strip()), values["module"])
        if kind == "add":
            return add_parameter(ws_dir, values["function"], values["param"], values["default"].rstrip(".!"))
        return rename_parameter(ws_dir, values["function"], values["old"], values["new"])
    except SyntaxError as exc:
        raise ValueError(f"sonuç ayrıştırılamadı, hiçbir şey değiştirilmedi: {exc}") from exc
