"""Small write-through persistent containers backed by one SQLite table.

The F204 endpoints used module-level dicts, so archived chats, custom agents, scheduled tasks and
document versions vanished on every restart. These containers keep the same interface for the few
operations the code needs, but every change is stored in the platform database.
"""

import json
from collections.abc import Iterator
from typing import Any

import db

_TABLE = "CREATE TABLE IF NOT EXISTS app_kv (ns TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY (ns, k))"


def _read(ns: str) -> dict[str, Any]:
    with db.connect() as conn:
        conn.execute(_TABLE)
        rows = conn.execute("SELECT k, v FROM app_kv WHERE ns = ? ORDER BY rowid", (ns,)).fetchall()
    return {r[0]: json.loads(r[1]) for r in rows}


def _write(ns: str, key: str, value: Any) -> None:
    with db.connect() as conn:
        conn.execute(_TABLE)
        conn.execute(
            "INSERT INTO app_kv (ns, k, v) VALUES (?, ?, ?) ON CONFLICT(ns, k) DO UPDATE SET v = excluded.v",
            (ns, key, json.dumps(value, ensure_ascii=False)),
        )


def _delete(ns: str, key: str) -> None:
    with db.connect() as conn:
        conn.execute(_TABLE)
        conn.execute("DELETE FROM app_kv WHERE ns = ? AND k = ?", (ns, key))


class PersistentDict:
    """dict-like view of one namespace; values must be JSON serialisable and are replaced as a whole."""

    def __init__(self, ns: str) -> None:
        self.ns = ns

    def __getitem__(self, key: str) -> Any:
        data = _read(self.ns)
        if key not in data:
            raise KeyError(key)
        return data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        _write(self.ns, key, value)

    def __delitem__(self, key: str) -> None:
        _delete(self.ns, key)

    def __contains__(self, key: object) -> bool:
        return key in _read(self.ns)

    def __len__(self) -> int:
        return len(_read(self.ns))

    def __iter__(self) -> Iterator[str]:
        return iter(_read(self.ns))

    def get(self, key: str, default: Any = None) -> Any:
        return _read(self.ns).get(key, default)

    def values(self) -> list[Any]:
        return list(_read(self.ns).values())

    def items(self) -> list[tuple[str, Any]]:
        return list(_read(self.ns).items())


class PersistentSet:
    def __init__(self, ns: str) -> None:
        self.ns = ns

    def add(self, item: str) -> None:
        _write(self.ns, item, True)

    def discard(self, item: str) -> None:
        _delete(self.ns, item)

    def __contains__(self, item: object) -> bool:
        return item in _read(self.ns)

    def __len__(self) -> int:
        return len(_read(self.ns))

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(_read(self.ns)))


class PersistentList:
    """Append-only list (keys are zero padded counters so order survives restarts)."""

    def __init__(self, ns: str) -> None:
        self.ns = ns

    def append(self, item: Any) -> None:
        n = len(_read(self.ns))
        _write(self.ns, f"{n:09d}", item)

    def _all(self) -> list[Any]:
        data = _read(self.ns)
        return [data[k] for k in sorted(data)]

    def __getitem__(self, index: Any) -> Any:
        return self._all()[index]

    def __len__(self) -> int:
        return len(_read(self.ns))

    def __iter__(self) -> Iterator[Any]:
        return iter(self._all())
