"""Fold the per-module SQLite files into ``platform.db`` (DAT-01).

``user_profile.db``, ``cognitive_memory.db``, ``graph_rag.db`` and ``cmm_quality.db`` each had their own
connection settings, backup story and lock domain. With ``UNIFIED_DB=true`` every module opens ``platform.db``
instead; this module moves the existing data across once. Legacy files are renamed to ``*.migrated`` (never
deleted) after every table has been copied and its row count verified.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import dbconn
import migrate

LEGACY_FILES = ("user_profile.db", "cognitive_memory.db", "graph_rag.db", "cmm_quality.db")
_FTS_SHADOW = re.compile(r"_(data|idx|content|docsize|config)$")


class UnifyError(RuntimeError):
    pass


def _tables(conn: sqlite3.Connection, schema: str) -> list[tuple[str, str]]:
    import sql_safe

    rows = conn.execute(
        sql_safe.build_select(
            "sqlite_master",
            "name, sql",
            schema=schema,
            where="type = 'table' AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL",
            order_by="rowid",
        )
    ).fetchall()
    virtual = {name for name, sql in rows if sql.upper().startswith("CREATE VIRTUAL TABLE")}
    keep = []
    for name, sql in rows:
        shadow_of = _FTS_SHADOW.sub("", name)
        if name not in virtual and shadow_of != name and shadow_of in virtual:
            continue  # FTS5 rebuilds its own shadow tables when the rows are inserted
        keep.append((name, sql))
    return keep


def _copy_one(conn: sqlite3.Connection, legacy: Path) -> dict[str, int]:
    import sql_safe

    conn.execute("ATTACH DATABASE ? AS legacy", (str(legacy),))
    copied: dict[str, int] = {}
    try:
        existing = {r[0] for r in conn.execute("SELECT name FROM main.sqlite_master WHERE type = 'table'")}
        for name, sql in _tables(conn, "legacy"):
            if name not in existing:
                conn.execute(sql)
            else:
                mine = [r[1] for r in conn.execute(f'PRAGMA main.table_info("{name}")')]
                theirs = [r[1] for r in conn.execute(f'PRAGMA legacy.table_info("{name}")')]
                if mine != theirs:
                    raise UnifyError(f"{legacy.name}: '{name}' tablosu platform.db'dekiyle aynı adı taşıyor ama sütunları farklı")
            conn.execute(sql_safe.build_copy_table("main", "legacy", name))
            before = conn.execute(sql_safe.build_select(name, "COUNT(*)", schema="legacy")).fetchone()[0]
            after = conn.execute(sql_safe.build_select(name, "COUNT(*)", schema="main")).fetchone()[0]
            if after < before:
                raise UnifyError(f"{legacy.name}: '{name}' tablosunda {before} satırdan yalnız {after} kopyalandı")
            copied[name] = before
        for kind in ("index", "trigger"):
            for (sql,) in conn.execute(
                "SELECT sql FROM legacy.sqlite_master WHERE type = ? AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'",
                (kind,),
            ).fetchall():
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError as exc:
                    if "already exists" not in str(exc):
                        raise
        conn.commit()
    finally:
        conn.rollback()
        conn.execute("DETACH DATABASE legacy")
    return copied


def unify(data_dir: Path, target: Path) -> dict[str, dict[str, int]]:
    """Copy every legacy file found in ``data_dir`` into ``target``; returns rows copied per file and table."""
    found = [data_dir / name for name in LEGACY_FILES if (data_dir / name).is_file() and (data_dir / name) != target]
    if not found:
        return {}
    migrate.snapshot(target, data_dir / "backups")
    report: dict[str, dict[str, int]] = {}
    conn = dbconn.open_db(target)
    try:
        for legacy in found:
            report[legacy.name] = _copy_one(conn, legacy)
    finally:
        conn.close()
    for legacy in found:
        for suffix in ("", "-wal", "-shm"):
            part = Path(str(legacy) + suffix)
            if part.exists():
                part.replace(Path(str(legacy) + suffix + ".migrated"))
    return report
