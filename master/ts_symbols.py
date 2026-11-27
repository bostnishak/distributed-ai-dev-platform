"""Symbols of a source file with their line ranges, read with Tree-sitter (Python, JS/TS, HTML, CSS, JSON, YAML, SQL)."""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

_GRAMMARS = {
    ".py": ("tree_sitter_python", "language"), ".js": ("tree_sitter_javascript", "language"), ".jsx": ("tree_sitter_javascript", "language"),
    ".mjs": ("tree_sitter_javascript", "language"), ".ts": ("tree_sitter_typescript", "language_typescript"), ".tsx": ("tree_sitter_typescript", "language_tsx"),
    ".html": ("tree_sitter_html", "language"), ".css": ("tree_sitter_css", "language"), ".json": ("tree_sitter_json", "language"),
    ".yaml": ("tree_sitter_yaml", "language"), ".yml": ("tree_sitter_yaml", "language"), ".sql": ("tree_sitter_sql", "language"),
}
_NAMED = {"function_declaration": "def", "generator_function_declaration": "def", "function_definition": "def", "class_declaration": "class",
          "class_definition": "class", "interface_declaration": "interface", "type_alias_declaration": "type", "enum_declaration": "enum"}
_ROUTE_RE = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"'`]([^\"'`]+)", re.IGNORECASE)


@dataclass(frozen=True)
class Symbol:
    key: str
    start: int  # 1-based lines
    end: int
    text: str


@lru_cache(maxsize=16)
def _parser(suffix: str) -> Any:
    if suffix not in _GRAMMARS:
        return None
    try:
        from tree_sitter import Language, Parser

        module, attribute = _GRAMMARS[suffix]
        return Parser(Language(getattr(importlib.import_module(module), attribute)()))
    except ImportError:
        return None


def _text(node: Any, data: bytes) -> str:
    return data[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _name(node: Any, data: bytes) -> str:
    field = node.child_by_field_name("name")
    return _text(field, data) if field is not None else ""


def _key(node: Any, data: bytes) -> str:
    """A stable name for a top-level node; two versions of the same thing get the same key."""
    inner = node
    if node.type == "export_statement":
        inner = node.child_by_field_name("declaration") or node
    if inner.type in _NAMED:
        return f"{_NAMED[inner.type]} {_name(inner, data)}"
    if inner.type in ("lexical_declaration", "variable_declaration"):
        names = [_name(c, data) for c in inner.named_children if c.type == "variable_declarator"]
        return "set " + ",".join(names)
    if inner.type == "rule_set":
        return "rule " + " ".join(_text(inner.named_children[0], data).split())
    if inner.type == "import_statement":
        return "import " + " ".join(_text(inner, data).split())
    return "stmt " + " ".join(_text(inner, data).split())[:200]


def top_level(source: str, suffix: str) -> list[Symbol] | None:
    """Every top-level node as a symbol; None when the language is not supported or the file does not parse cleanly."""
    parser = _parser(suffix)
    if parser is None:
        return None
    data = source.encode("utf-8")
    root = parser.parse(data).root_node
    if root.has_error:
        return None
    return [Symbol(_key(n, data), n.start_point[0] + 1, n.end_point[0] + 1, _text(n, data)) for n in root.named_children]


def _walk(node: Any) -> Any:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.named_children))


def _top_key(node: Any) -> bool:
    return node.parent is not None and node.parent.parent is not None and node.parent.parent.type == "document"


def _label(node: Any, data: bytes, suffix: str) -> str:
    """What the outline calls this node; "" when it is not worth listing."""
    if node.type in _NAMED:
        return f"{_NAMED[node.type]} {_name(node, data)}"
    if node.type == "rule_set":
        return _key(node, data)
    if node.type == "create_table":
        return "table " + " ".join(_text(node, data).split("(", 1)[0].split()[2:])
    text = _text(node, data) if node.type in ("declaration", "attribute", "pair") else ""
    if suffix == ".css" and node.type == "declaration" and text.startswith("--"):
        return "var " + text.split(":", 1)[0]
    if suffix == ".html" and node.type == "attribute" and text.startswith("id="):
        return "#" + text[3:].strip("\"'")
    if suffix in (".json", ".yaml", ".yml") and node.type == "pair" and _top_key(node):
        return "key " + text.split(":", 1)[0].strip("\"'")
    return ""


def outline(source: str, suffix: str, limit: int = 24) -> list[str]:
    """"name  L<start>-<end>" lines: functions, classes, CSS rules and custom properties, element ids, keys and routes."""
    parser = _parser(suffix)
    if parser is None:
        return []
    data = source.encode("utf-8")
    out: list[str] = []
    for node in _walk(parser.parse(data).root_node):
        if label := _label(node, data, suffix):
            out.append(f"{label}  L{node.start_point[0] + 1}-{node.end_point[0] + 1}")
        if len(out) >= limit:
            break
    out += [f"route {method.upper()} {path}  L{source.count(chr(10), 0, match.start()) + 1}" for match in _ROUTE_RE.finditer(source) for method, path in [match.groups()]]
    return out[:limit]
