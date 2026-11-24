"""Which rows belong to a user, and a query helper that cannot forget to filter by owner (DAT-15).

Every table is classified: owned by a user, a child of an owned table, or deliberately shared by the team
(agents, projects, tasks...). A table that is none of these is a bug that the test suite reports, so a new
table forces a decision about who may read it.
"""

from __future__ import annotations

import ast
import re
import sqlite3
from pathlib import Path

OWNED: dict[str, str] = {
    "profiles": "user_id",
    "conversations": "user_id",
    "semantic_memories": "user_id",
    "saved_chats": "user_id",
    "usage_events": "user_id",
    "files": "owner_id",
    "retention_policies": "owner_id",
    "feature_overrides": "owner_id",
    "search_index": "owner_id",
}

# child table -> (its column, parent table, parent key)
CHILDREN: dict[str, tuple[str, str, str]] = {
    "conversation_messages": ("conversation_id", "conversations", "id"),
}

SHARED = frozenset({
    "agent_scores", "agents", "blobs", "cnc_cmm_measurements", "cnc_inspection_lots", "conflicts", "error_events",
    "eval_sessions", "events", "feature_flags", "kg_edges", "kg_entities", "mcp_connectors", "procedural_skills",
    "projects", "rag_documents", "schema_migrations", "schema_version", "secrets", "task_dependencies", "tasks",
    "vision_drawings",
})

# Infrastructure that must see every owner's rows (garbage collection, repair, retention, index upkeep).
# Anything else that touches owned tables has to filter by owner.
MAINTENANCE_MODULES = frozenset({
    "blobstore.py", "db_doctor.py", "dbindexes.py", "ownership.py", "portability.py", "retention.py",
    "search_index.py", "maintenance.py",
})

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COLUMNS = re.compile(r"^[A-Za-z0-9_,\s*.()]+$")


class UnscopedQuery(ValueError):
    pass


def table_names(conn: sqlite3.Connection) -> set[str]:
    """Real tables only: SQLite internals and the shadow tables of full-text indexes are left out."""
    rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    virtual = {name for name, sql in rows if (sql or "").upper().startswith("CREATE VIRTUAL TABLE")}
    shadow = re.compile(r"_(data|idx|content|docsize|config)$")
    names = set()
    for name, _sql in rows:
        base = shadow.sub("", name)
        if name in virtual or base not in virtual:
            names.add(name)
    return names - virtual | {n for n in virtual if n in OWNED}


def unclassified_tables(conn: sqlite3.Connection) -> list[str]:
    known = set(OWNED) | set(CHILDREN) | SHARED
    return sorted(t for t in table_names(conn) if t not in known and not t.endswith("_fts"))


def scoped_select(
    conn: sqlite3.Connection,
    table: str,
    owner: str,
    where: str = "1 = 1",
    params: tuple = (),
    columns: str = "*",
    order_by: str = "",
    limit: int | None = None,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """SELECT from an owned table; the owner filter is added here and cannot be left out."""
    if table not in OWNED:
        raise UnscopedQuery(f"'{table}' kullanıcıya ait bir tablo olarak kayıtlı değil")
    if not _COLUMNS.match(columns) or (order_by and not _COLUMNS.match(order_by)):
        raise UnscopedQuery("sütun listesi geçersiz")
    import sql_safe

    owner_col = sql_safe.safe_ident(OWNED[table])
    sql = sql_safe.build_select(table, columns, where=f"{owner_col} = ? AND ({where})", order_by=order_by or "")
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    return conn.execute(sql, (owner, *params)).fetchall()


def delete_owner(conn: sqlite3.Connection, owner: str) -> dict[str, int]:
    """Remove everything a user owns, children first. Blobs are collected separately (blobstore)."""
    import sql_safe

    removed: dict[str, int] = {}
    existing = table_names(conn)
    for child, (col, parent, key) in CHILDREN.items():
        if child not in existing or parent not in existing:
            continue
        sub = sql_safe.build_select(parent, key, where=f"{sql_safe.safe_ident(OWNED[parent])} = ?")
        cur = conn.execute(sql_safe.build_delete(child, f"{sql_safe.safe_ident(col)} IN ({sub})"), (owner,))
        removed[child] = cur.rowcount
    try:
        conn.execute(
            "DELETE FROM messages_fts WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)", (owner,)
        )
    except sqlite3.OperationalError:
        pass  # the chat full-text table only exists once chats were indexed
    for table, column in OWNED.items():
        if table in existing:
            removed[table] = conn.execute(
                sql_safe.build_delete(table, f"{sql_safe.safe_ident(column)} = ?"), (owner,)
            ).rowcount
    return removed


def count_owned(conn: sqlite3.Connection, owner: str) -> dict[str, int]:
    import sql_safe

    existing = table_names(conn)
    return {
        t: conn.execute(sql_safe.build_select(t, "COUNT(*)", where=f"{sql_safe.safe_ident(c)} = ?"), (owner,)).fetchone()[0]
        for t, c in OWNED.items()
        if t in existing
    }


_VERB = re.compile(r"\s*(SELECT|DELETE|UPDATE)\b", re.IGNORECASE)
_STATEMENT = re.compile(r"\b(?:FROM|UPDATE)\s+(" + "|".join(OWNED) + r")\b", re.IGNORECASE)


def find_unscoped_queries(master_dir: Path) -> dict[str, str]:
    """SQL literals that read, change or delete owned rows without mentioning the owner column.

    Returns ``{key: "file:line"}`` where the key (file plus the normalised statement) survives line shifts.
    """
    hits: dict[str, str] = {}
    for path in sorted(master_dir.glob("*.py")):
        if path.name in MAINTENANCE_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            text = node.value
            match = _STATEMENT.search(text)
            if not match or not _VERB.match(text):
                continue
            if OWNED[match.group(1).lower()] not in text:
                statement = " ".join(text.split())[:110]
                hits[f"{path.name}|{statement}"] = f"{path.name}:{node.lineno}"
    return hits
