"""One full-text index for chats, artifacts, files and code (DAT-10).

SQLite's FTS5 handles ranking; what it cannot do is Turkish: ``I``/``İ``/``ı`` fold wrongly, and a query for
"sözleşmelerin" misses a document that says "sözleşme". Text is therefore folded and lightly stemmed here, on
the way in and on the way out, and every search is filtered by owner.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata

_FOLD = str.maketrans({"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"})
_WORD = re.compile(r"[a-z0-9]+")
# Longest first so "lerin" goes before "in". A suffix is only cut when at least four letters remain.
_SUFFIXES = (
    "lerin", "larin", "leri", "lari", "ler", "lar", "nin", "nun", "den", "dan", "ten", "tan",
    "de", "da", "te", "ta", "in", "un", "yi", "yu", "ya", "ye", "e", "a", "i", "u",
)
MIN_STEM = 4


def fold(text: str) -> str:
    """Turkish-aware lower-casing, then diacritics and dotless i folded away."""
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = unicodedata.normalize("NFKD", text.translate(_FOLD))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def stem(word: str) -> str:
    changed = True
    while changed:
        changed = False
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM:
                word = word[: -len(suffix)]
                changed = True
                break
    return word


def tokens(text: str) -> list[str]:
    return [stem(w) for w in _WORD.findall(fold(text))]


def normalise(text: str) -> str:
    return " ".join(tokens(text))


def index(conn: sqlite3.Connection, kind: str, owner: str, ref: str, title: str, body: str) -> None:
    """Add or replace the entry for (kind, ref)."""
    remove(conn, kind, owner, ref)
    conn.execute(
        "INSERT INTO search_index (title, body, kind, owner_id, ref) VALUES (?, ?, ?, ?, ?)",
        (normalise(title), normalise(body), kind, owner, ref),
    )


def remove(conn: sqlite3.Connection, kind: str, owner: str, ref: str) -> int:
    return conn.execute(
        "DELETE FROM search_index WHERE kind = ? AND owner_id = ? AND ref = ?", (kind, owner, ref)
    ).rowcount


def _match_expression(query: str) -> str | None:
    words = tokens(query)
    return " ".join(f'"{w}"*' for w in words) if words else None


def search(
    conn: sqlite3.Connection,
    owner: str,
    query: str,
    kinds: tuple[str, ...] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Best matches first; only ever returns the owner's own entries."""
    expression = _match_expression(query)
    if expression is None:
        return []
    sql = (
        "SELECT kind, ref, title, snippet(search_index, 1, '[', ']', '…', 12) AS snippet, "
        "bm25(search_index, 4.0, 1.0) AS score FROM search_index "
        "WHERE search_index MATCH ? AND owner_id = ?"
    )
    params: list = [expression, owner]
    if kinds:
        sql += f" AND kind IN ({','.join('?' for _ in kinds)})"
        params += list(kinds)
    sql += " ORDER BY score LIMIT ? OFFSET ?"
    params += [int(limit), int(offset)]
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def reindex_chats(conn: sqlite3.Connection) -> int:
    """Rebuild chat entries from the conversation tables (after an import, or if the index was lost)."""
    conn.execute("DELETE FROM search_index WHERE kind = 'chat'")
    count = 0
    for conv in conn.execute("SELECT id, user_id, title FROM conversations").fetchall():
        body = " ".join(
            r[0] or "" for r in conn.execute("SELECT content FROM conversation_messages WHERE conversation_id = ?", (conv[0],))
        )
        index(conn, "chat", conv[1], conv[0], conv[2] or "", body)
        count += 1
    return count
