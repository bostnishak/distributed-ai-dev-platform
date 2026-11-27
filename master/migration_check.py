"""Are the database migrations of a project reversible? up, down and up again on a scratch SQLite database.

Looks for pairs named *.up.sql / *.down.sql. After "down" the schema must be what it was before "up", and "up" must
work a second time.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _schema(conn: sqlite3.Connection) -> list[tuple]:
    return sorted(conn.execute("SELECT type, name, COALESCE(sql, '') FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall())


def check(ws_dir: Path) -> list[str] | None:
    """Problems found, [] when every pair round-trips, None when there are no migration pairs."""
    ups = sorted(p for p in ws_dir.rglob("*.up.sql") if ".history" not in p.parts)
    if not ups:
        return None
    problems: list[str] = []
    conn = sqlite3.connect(":memory:")
    try:
        for up in ups:
            down = up.with_name(up.name[: -len(".up.sql")] + ".down.sql")
            name = up.relative_to(ws_dir).as_posix()
            if not down.is_file():
                problems.append(f"{name}: geri alma (down) dosyası yok")
                continue
            before = _schema(conn)
            try:
                conn.executescript(up.read_text(encoding="utf-8"))
                after = _schema(conn)
                conn.executescript(down.read_text(encoding="utf-8"))
                if _schema(conn) != before:
                    problems.append(f"{name}: down çalıştıktan sonra şema eski haline dönmüyor")
                conn.executescript(up.read_text(encoding="utf-8"))
                if _schema(conn) != after:
                    problems.append(f"{name}: ikinci kez uygulanınca farklı şema çıkıyor")
            except sqlite3.Error as exc:
                problems.append(f"{name}: {exc}")
    finally:
        conn.close()
    return problems


def report(ws_dir: Path) -> str:
    problems = check(ws_dir)
    if problems is None:
        return ""
    return "Veritabanı göçü denetimi: " + ("; ".join(problems[:4]) if problems else "her adım ileri-geri-ileri denendi, sorun yok.")
