"""Rename a function, class or variable across a whole project by code, not by asking a model to rewrite files.

Works on tokens, so strings and comments stay as they are; refuses when the new name already exists or a file would
no longer parse.
"""

from __future__ import annotations

import ast
import io
import keyword
import re
import tokenize
from pathlib import Path

_RENAME_RE = re.compile(
    r"^\s*(?:(?P<a>[A-Za-z_]\w*)\s*(?:fonksiyonunun|sınıfının|değişkeninin|metodunun)\s+(?:adını|ismini)\s+(?P<b>[A-Za-z_]\w*)\s+(?:yap|olarak değiştir)\w*"
    r"|rename\s+(?:function\s+|class\s+|variable\s+)?(?P<c>[A-Za-z_]\w*)\s+to\s+(?P<d>[A-Za-z_]\w*))\s*[.!]?\s*$",
    re.IGNORECASE,
)
_SKIP = {".history", "venv", ".venv", "node_modules", "__pycache__", ".git"}


def parse(instruction: str) -> tuple[str, str] | None:
    match = _RENAME_RE.match(instruction)
    if not match:
        return None
    return (match["a"] or match["c"], match["b"] or match["d"])


def rename_python(source: str, old: str, new: str) -> str:
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type == tokenize.NAME and t.string == old]
    lines = source.splitlines(keepends=True)
    for token in sorted(tokens, key=lambda t: t.start, reverse=True):
        row, col = token.start
        line = lines[row - 1]
        lines[row - 1] = line[:col] + new + line[col + len(old):]
    return "".join(lines)


def rename(ws_dir: Path, old: str, new: str) -> list[str]:
    """Changed files. Empty when nothing matched; ValueError when the rename would be unsafe."""
    if keyword.iskeyword(new) or not new.isidentifier() or old == new:
        raise ValueError(f"'{new}' geçerli bir ad değil")
    files = [p for p in sorted(ws_dir.rglob("*.py")) if not _SKIP & set(p.relative_to(ws_dir).parts)]
    changes: dict[Path, str] = {}
    for path in files:
        source = path.read_text(encoding="utf-8")
        try:
            names = {t.string for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type == tokenize.NAME}
            if old not in names:
                continue
            if new in names:
                raise ValueError(f"'{new}' adı {path.name} içinde zaten kullanılıyor")
            updated = rename_python(source, old, new)
            ast.parse(updated)
        except (tokenize.TokenError, SyntaxError) as exc:
            raise ValueError(f"{path.name} ayrıştırılamadı: {exc}") from exc
        changes[path] = updated
    for path, updated in changes.items():  # only after every file passed
        path.write_text(updated, encoding="utf-8")
    return [p.relative_to(ws_dir).as_posix() for p in changes]
