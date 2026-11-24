"""SQL-01..26: Strictly validated SQL identifier quoting and safe parameterized query builders."""

from __future__ import annotations

import re
from typing import Any

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def safe_ident(name: str) -> str:
    """Validate and double-quote an SQL identifier; rejects injection characters."""
    clean = (name or "").strip().strip('"')
    if not _IDENT_RE.fullmatch(clean):
        raise ValueError(f"Geçersiz SQL tanımlayıcısı: {name!r}")
    return f'"{clean}"'


_IDENT = r'"?[A-Za-z_][A-Za-z0-9_]{0,63}"?'
_PROJECTION = re.compile(
    rf"(?:\*|{_IDENT}|(?:COUNT|SUM|AVG|MIN|MAX|BM25)\((?:\*|{_IDENT})\))(?:\s+AS\s+[A-Za-z_][A-Za-z0-9_]{{0,63}})?",
    re.IGNORECASE,
)


def safe_columns(columns: str) -> str:
    """Validate a comma-separated projection list: '*', identifiers, simple aggregates and `AS alias`."""
    if columns.strip() == "*":
        return "*"
    parts = [part.strip() for part in columns.split(",") if part.strip()]
    if not parts:
        raise ValueError("Boş sütun listesi.")
    for part in parts:
        if not _PROJECTION.fullmatch(part):
            raise ValueError(f"Geçersiz sütun ifadesi: {part!r}")
    return ", ".join(parts)


def placeholders_for(count: int) -> str:
    if count <= 0:
        raise ValueError("Yer tutucu sayısı pozitif olmalıdır.")
    return ", ".join("?" for _ in range(count))


def build_select(table: str, columns: str = "*", **opts: Any) -> str:
    where = str(opts.get("where", ""))
    order_by = str(opts.get("order_by", ""))
    limit: int | None = opts.get("limit")
    schema = str(opts.get("schema", ""))
    tbl = f"{safe_ident(schema)}.{safe_ident(table)}" if schema else safe_ident(table)
    cols = safe_columns(columns)
    parts = ["SELECT", cols, "FROM", tbl]
    if where:
        parts.extend(["WHERE", where])
    if order_by:
        parts.extend(["ORDER BY", order_by])
    if limit is not None:
        parts.extend(["LIMIT", str(max(1, limit))])
    return " ".join(parts)


def build_delete(table: str, where: str) -> str:
    return " ".join(["DELETE", "FROM", safe_ident(table), "WHERE", where])


def build_insert_values(table: str, count: int, *, or_ignore: bool = False) -> str:
    verb = "INSERT OR IGNORE INTO" if or_ignore else "INSERT INTO"
    return " ".join([verb, safe_ident(table), "VALUES", f"({placeholders_for(count)})"])


def build_copy_table(dst_schema: str, src_schema: str, table: str) -> str:
    qt = safe_ident(table)
    return " ".join(["INSERT OR IGNORE INTO", f"{safe_ident(dst_schema)}.{qt}", "SELECT * FROM", f"{safe_ident(src_schema)}.{qt}"])
