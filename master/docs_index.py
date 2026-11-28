"""Full-text index of the downloaded DevDocs sets (SQLite FTS5), so documentation answers work offline and fast.

Built once from the vault's `docs/<set>/index.json` and `db.json`; rebuilt only when those files change. A query
matches entry names and page text, names weighing far more than body words.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import config

_TAG_RE = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>|<[^>]+>", re.DOTALL | re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z_][\w.]{1,}")
_log = logging.getLogger(__name__)


def folder() -> Path:
    """The platform's own vault; the repository's when this data folder has none."""
    own = config.data_dir() / "vendor" / "docs"
    return own if own.is_dir() else Path(__file__).resolve().parent / "data" / "vendor" / "docs"


def database() -> Path:
    return config.data_dir() / "docs.sqlite"


def _stamp(sets: list[Path]) -> str:
    return json.dumps([[s.name, (s / "db.json").stat().st_size, int((s / "db.json").stat().st_mtime)] for s in sets])


def _sets() -> list[Path]:
    return sorted(p for p in folder().glob("*") if (p / "index.json").is_file() and (p / "db.json").is_file()) if folder().is_dir() else []


def _plain(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", markup))).strip()


def _rows(docset: Path):
    entries = json.loads((docset / "index.json").read_text(encoding="utf-8"))["entries"]
    pages = json.loads((docset / "db.json").read_text(encoding="utf-8"))
    seen = set()
    for entry in entries:
        key = entry["path"].split("#")[0]
        if key not in seen and key in pages:
            seen.add(key)
            yield docset.name, key, entry["name"], _plain(pages[key])[:20000]


def build(force: bool = False) -> int:
    """Number of indexed pages; the existing index is kept when the documentation did not change."""
    sets = _sets()
    if not sets:
        return 0
    database().parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database())) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS stamp (value TEXT)")
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(docset UNINDEXED, path UNINDEXED, name, body)")
        current, known = _stamp(sets), conn.execute("SELECT value FROM stamp").fetchone()
        if force or not known or known[0] != current:
            conn.execute("DELETE FROM pages")
            for docset in sets:
                try:
                    conn.executemany("INSERT INTO pages VALUES (?,?,?,?)", _rows(docset))
                except (OSError, ValueError, KeyError) as exc:
                    _log.warning("belge kümesi okunamadı (%s): %s", docset.name, exc)
            conn.execute("DELETE FROM stamp")
            conn.execute("INSERT INTO stamp VALUES (?)", (current,))
        return conn.execute("SELECT count(*) FROM pages").fetchone()[0]


def search(query: str, docsets: tuple[str, ...] = (), limit: int = 3) -> list[tuple[str, str, str, str]]:
    """[(docset, path, name, text)] best first; [] when nothing is indexed or nothing matches."""
    words = list(dict.fromkeys(w.strip(".") for w in _WORD_RE.findall(query)))[:12]
    if not words or not database().is_file():
        return []
    match = " OR ".join(f'"{word}"' for word in words)
    marks = ",".join("?" * len(docsets))
    narrowed = f" AND docset IN ({marks})" if docsets else ""
    sql = f"SELECT docset, path, name, body FROM pages WHERE pages MATCH ?{narrowed} ORDER BY bm25(pages, 0, 0, 12.0, 1.0) LIMIT ?"  # noqa: S608, RUF100  # only placeholders are interpolated
    try:
        with closing(sqlite3.connect(f"file:{database().as_posix()}?mode=ro", uri=True)) as conn:
            return conn.execute(sql, (match, *docsets, limit)).fetchall()
    except sqlite3.Error as exc:
        _log.warning("belge araması yapılamadı: %s", exc)
        return []
