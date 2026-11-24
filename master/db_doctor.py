"""Health checks for the SQLite files, with repairs only where nothing can be lost (DAT-12).

``diagnose`` reports; ``repair`` fixes what is safe to fix (unreferenced blobs, full-text indexes rebuilt from
their own content, the write-ahead log) and leaves everything else to a person.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import blobstore
import dbconn
import ownership

WAL_WARN_BYTES = 64 * 1024 * 1024
_JSON_COLUMNS = {("tasks", "details"), ("tasks", "files"), ("projects", "spec"), ("saved_chats", "messages_json")}
_FTS_TABLES = ("search_index", "messages_fts")


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" needs a person, "warning" is worth a look, "info" was fixed or is harmless
    check: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.check}: {self.detail}"


def _exists(conn: sqlite3.Connection, table: str) -> bool:
    return table in ownership.table_names(conn)


def _json_columns(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    found = {pair for pair in _JSON_COLUMNS if _exists(conn, pair[0])}
    for table in ownership.table_names(conn):
        for _cid, name, *_rest in conn.execute(f'PRAGMA table_info("{table}")'):
            if re.search(r"_json$", name):
                found.add((table, name))
    return sorted(found)


def _check_json_columns(conn: sqlite3.Connection) -> list[Finding]:
    import sql_safe

    findings: list[Finding] = []
    for table, column in _json_columns(conn):
        if not _exists(conn, table):
            continue
        if column not in {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}:
            continue
        bad = 0
        q_col = sql_safe.safe_ident(column)
        for (text,) in conn.execute(sql_safe.build_select(table, column, where=f"{q_col} IS NOT NULL")):
            try:
                json.loads(text)
            except (TypeError, ValueError):
                bad += 1
        if bad:
            findings.append(Finding("error", "json", f"{table}.{column}: {bad} geçersiz JSON değeri"))
    return findings


def _check_ownership_and_blobs(conn: sqlite3.Connection) -> list[Finding]:
    import sql_safe

    findings: list[Finding] = []
    for table, column in ownership.OWNED.items():
        if not _exists(conn, table):
            continue
        q_col = sql_safe.safe_ident(column)
        empty = conn.execute(
            sql_safe.build_select(table, "COUNT(*)", where=f"{q_col} IS NULL OR TRIM({q_col}) = ''")
        ).fetchone()[0]
        if empty:
            findings.append(Finding("error", "owner", f"{table}: {empty} satırın sahibi yok"))
    if _exists(conn, "files"):
        lost = conn.execute("SELECT COUNT(*) FROM files WHERE sha256 NOT IN (SELECT sha256 FROM blobs)").fetchone()[0]
        if lost:
            findings.append(Finding("error", "blobs", f"{lost} dosya kaydının blob satırı yok"))
        loose = conn.execute("SELECT COUNT(*) FROM blobs WHERE sha256 NOT IN (SELECT sha256 FROM files)").fetchone()[0]
        if loose:
            findings.append(Finding("warning", "blobs", f"{loose} blob hiçbir dosyaya bağlı değil (onarılabilir)"))
        findings += [Finding("error", "blob_bytes", p) for p in blobstore.verify(conn)]
    return findings


def _check_fts_and_metadata(conn: sqlite3.Connection) -> list[Finding]:
    findings: list[Finding] = []
    for table in _FTS_TABLES:
        if not _exists(conn, table):
            continue
        try:
            conn.execute(f"INSERT INTO {table}({table}) VALUES('integrity-check')")
        except sqlite3.DatabaseError as exc:
            findings.append(Finding("error", "fts", f"{table}: {exc} (onarım: yeniden oluşturma)"))
    if _exists(conn, "rag_documents"):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(rag_documents)")}
        if "embedding_model" not in cols:
            findings.append(Finding("warning", "vectors", "rag_documents gömme modeli kaydı tutmuyor (DAT-11)"))
    unknown = ownership.unclassified_tables(conn)
    if unknown:
        findings.append(Finding("warning", "ownership", f"sahiplik sınıfı olmayan tablolar: {', '.join(unknown)}"))
    return findings


def diagnose(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    with dbconn.connection(path) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchall()
        if [r[0] for r in result] != ["ok"]:
            findings += [Finding("error", "integrity_check", r[0]) for r in result[:5]]
        for row in conn.execute("PRAGMA foreign_key_check").fetchall()[:20]:
            findings.append(Finding("error", "foreign_key_check", f"{row[0]} satır {row[1]} -> {row[2]}"))
        findings.extend(_check_json_columns(conn))
        findings.extend(_check_ownership_and_blobs(conn))
        findings.extend(_check_fts_and_metadata(conn))
    wal = Path(str(path) + "-wal")
    if wal.is_file() and wal.stat().st_size > WAL_WARN_BYTES:
        findings.append(Finding("warning", "wal", f"WAL dosyası {wal.stat().st_size // (1024 * 1024)} MB; checkpoint gerekli"))
    return findings


def repair(path: Path) -> list[str]:
    """Safe repairs only; returns what was done."""
    actions: list[str] = []
    with dbconn.connection(path) as conn:
        if _exists(conn, "files"):
            gone = blobstore.collect_garbage(conn)
            if gone["blobs"] or gone["stray_files"] or gone["expired_files"]:
                actions.append(f"çöp toplama: {gone}")
        for table in _FTS_TABLES:
            if _exists(conn, table):
                try:
                    conn.execute(f"INSERT INTO {table}({table}) VALUES('integrity-check')")
                except sqlite3.DatabaseError:
                    conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
                    actions.append(f"{table}: tam metin indeksi yeniden oluşturuldu")
    checkpoint = sqlite3.connect(str(path))
    try:
        checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        checkpoint.close()
    return actions
