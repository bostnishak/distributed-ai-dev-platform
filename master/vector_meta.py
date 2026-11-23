"""Remember which embedding model produced each stored vector (DAT-11).

Vectors from different models are not comparable; silently mixing them returns plausible but meaningless
neighbours. Each document row records its model, dimension and a version counter, and a search can ask which
rows are stale for the model that is currently configured.
"""

from __future__ import annotations

import sqlite3

TABLE = "rag_documents"
COLUMNS = (
    ("embedding_model", "TEXT"),
    ("embedding_dim", "INTEGER"),
    ("embedding_version", "INTEGER DEFAULT 1"),
)


def ensure_columns(conn: sqlite3.Connection) -> bool:
    """Add the bookkeeping columns if the document table exists; True when it does."""
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLE})")}
    if not existing:
        return False
    for name, ddl in COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {name} {ddl}")
    return True


def stamp(conn: sqlite3.Connection, doc_id: str, model: str, dim: int, version: int = 1) -> None:
    conn.execute(
        f"UPDATE {TABLE} SET embedding_model = ?, embedding_dim = ?, embedding_version = ? WHERE doc_id = ?",
        (model, dim, version, doc_id),
    )


def stale(conn: sqlite3.Connection, model: str, dim: int, version: int = 1) -> list[str]:
    """Documents whose vector was made by another model, size or version (or is unstamped)."""
    if not ensure_columns(conn):
        return []
    return [r[0] for r in conn.execute(
        f"SELECT doc_id FROM {TABLE} WHERE embedding_model IS NOT ? OR embedding_dim IS NOT ? "
        "OR embedding_version IS NOT ?", (model, dim, version))]
