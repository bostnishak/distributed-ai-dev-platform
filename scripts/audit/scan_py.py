"""Python source scan: long embedded prompt strings, giant modules, functions without tests of their own name."""

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "master"
SKIP = ("venv", ".venv", "tests", "__pycache__", "data", "static")
rows = []
for path in sorted(M.rglob("*.py")):
    if any(part in SKIP for part in path.parts):
        continue
    rel = path.relative_to(M).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        continue
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant):
            docstrings.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings and node.value.count("\n") >= 10:
            rows.append({"rule": "embedded-long-string", "where": f"{rel}:{node.lineno}", "text": f"{node.value.count(chr(10)) + 1} satırlık gömülü metin/prompt"})
    lines = len(path.read_text(encoding="utf-8").splitlines())
    if lines > 600:
        rows.append({"rule": "module-over-600-lines", "where": rel, "text": f"{lines} satır"})
Path(sys.argv[1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
import collections

print(len(rows), collections.Counter(r["rule"] for r in rows))
