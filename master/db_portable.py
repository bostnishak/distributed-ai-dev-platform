"""DAT-16: Portable SQLite / PostgreSQL Compatibility Layer (DSN detection, SQL placeholder & DDL translation)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import dbconn

_AUTOINC_RE = re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", re.IGNORECASE)
_INSERT_OR_REPLACE_RE = re.compile(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", re.IGNORECASE)


def detect_dialect(dsn: str | Path | None = None) -> str:
    raw = str(dsn if dsn is not None else os.environ.get("DATABASE_URL", "")).strip().lower()
    if raw.startswith(("postgres://", "postgresql://")):
        return "postgresql"
    return "sqlite"


def translate_placeholders(sql: str, dialect: str) -> str:
    """Convert SQLite `?` positional placeholders to psycopg `%s` outside string literals."""
    if dialect != "postgresql" or "?" not in sql:
        return sql
    out: list[str] = []
    in_single = False
    for ch in sql:
        if ch == "'":
            in_single = not in_single
            out.append(ch)
        elif ch == "?" and not in_single:
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


def translate_ddl(ddl: str, dialect: str) -> str:
    """Translate basic SQLite DDL statements to PostgreSQL-compatible DDL."""
    if dialect != "postgresql":
        return ddl
    return _AUTOINC_RE.sub("SERIAL PRIMARY KEY", ddl)


class PortableDB:
    """Thin cross-dialect wrapper supporting SQLite natively and PostgreSQL (via psycopg) when DATABASE_URL is set."""

    def __init__(self, dsn: str | Path) -> None:
        self.dsn = str(dsn)
        self.dialect = detect_dialect(dsn)
        if self.dialect == "postgresql":
            import psycopg  # type: ignore[import-not-found]

            self._conn: Any = psycopg.connect(self.dsn)
        else:
            self._conn = dbconn.open_db(Path(dsn))

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        q = translate_placeholders(sql, self.dialect)
        return self._conn.execute(q, params)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PortableDB:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self._conn.commit()
        self.close()
