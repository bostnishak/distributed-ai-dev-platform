"""Take a user's data to another machine and bring it back (DAT-08).

``export_user`` writes one ZIP: ``data.json`` with every owned row (children included) and ``blobs/<sha256>``
for their files. Nothing secret is part of it: API keys and tokens live in tables no user owns. ``import_user``
re-creates the rows under a chosen owner id, keeps existing rows by default, and rebuilds the search index.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import blobstore
import dbconn
import ownership
import retention
import search_index

FORMAT = "cm6453-user-export-v1"
_RESERVED = {"search_index"}


def _encode(value):
    return {"__b64__": base64.b64encode(value).decode()} if isinstance(value, bytes) else value


def _decode(value):
    return base64.b64decode(value["__b64__"]) if isinstance(value, dict) and "__b64__" in value else value


def _rows(conn: sqlite3.Connection, sql: str, params: tuple) -> list[dict]:
    return [{k: _encode(r[k]) for k in r.keys()} for r in conn.execute(sql, params)]


def export_user(owner: str, destination: Path) -> dict[str, int]:
    tables: dict[str, list[dict]] = {}
    blob_hashes: set[str] = set()
    for path in retention.database_files():
        with dbconn.connection(path) as conn:
            present = ownership.table_names(conn)
            for table, column in ownership.OWNED.items():
                if table in present and table not in _RESERVED:
                    tables.setdefault(table, []).extend(
                        _rows(conn, f"SELECT * FROM {table} WHERE {column} = ?", (owner,)))
            for child, (col, parent, key) in ownership.CHILDREN.items():
                if child in present:
                    tables.setdefault(child, []).extend(_rows(
                        conn, f"SELECT * FROM {child} WHERE {col} IN "
                              f"(SELECT {key} FROM {parent} WHERE {ownership.OWNED[parent]} = ?)", (owner,)))
    blob_hashes = {row["sha256"] for row in tables.get("files", [])}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps({"format": FORMAT, "owner": owner, "tables": tables}, ensure_ascii=False))
        for sha in sorted(blob_hashes):
            blob = blobstore.blob_path(sha)
            if blob.is_file():
                zf.write(blob, f"blobs/{sha}")
    return {table: len(rows) for table, rows in tables.items()}


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}


def import_user(source: Path, new_owner: str | None = None, *, replace: bool = False) -> dict[str, int]:
    """Re-create the exported rows (default: keep rows that already exist); returns rows written per table."""
    with zipfile.ZipFile(source) as zf:
        payload = json.loads(zf.read("data.json"))
        if payload.get("format") != FORMAT:
            raise ValueError("tanınmayan dışa aktarma biçimi")
        owner = new_owner or payload["owner"]
        verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
        written: dict[str, int] = {}
        for path in retention.database_files() or [dbconn.database_file("platform.db")]:
            with dbconn.connection(path) as conn:
                present = ownership.table_names(conn)
                for table, rows in payload["tables"].items():
                    if table not in present:
                        continue
                    allowed = _table_columns(conn, table)
                    owner_col = ownership.OWNED.get(table)
                    for row in rows:
                        values = {k: _decode(v) for k, v in row.items() if k in allowed}
                        if owner_col:
                            values[owner_col] = owner
                        if table == "files":
                            sha = values["sha256"]
                            data = zf.read(f"blobs/{sha}") if f"blobs/{sha}" in zf.namelist() else None
                            if data is None or hashlib.sha256(data).hexdigest() != sha:
                                raise ValueError(f"dosya içeriği eksik veya bozuk: {sha}")
                            target = blobstore.blob_path(sha)
                            if not target.is_file():
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(data)
                            conn.execute("INSERT OR IGNORE INTO blobs (sha256, size, created_at) VALUES (?,?,?)",
                                         (sha, len(data), values["created_at"]))
                        cols = ", ".join(values)
                        marks = ", ".join("?" for _ in values)
                        cur = conn.execute(f"{verb} INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))
                        written[table] = written.get(table, 0) + max(cur.rowcount, 0)
                if "search_index" in present and "conversations" in present:
                    search_index.reindex_chats(conn)
    return written
