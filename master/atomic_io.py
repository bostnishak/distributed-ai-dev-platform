"""File writes and deletes that survive Windows: momentary locks, long paths, read-only files.

A write goes to a temporary file in the same folder and is moved over the target in one step, so a reader (or a crash)
sees the old or the new content, never half of it. Antivirus, indexer and language-server locks (WinError 5/32) are
waited out with growing pauses. Paths longer than the classic 260 limit get the \\\\?\\ prefix. Text is UTF-8 with LF.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

_ATTEMPTS = 9  # 0.02 s doubling: about five seconds in total
_LONG = 240


def long_path(path: str | os.PathLike[str], force: bool = False) -> str:
    """The path in the form Windows accepts at any length (unchanged elsewhere and for short paths)."""
    text = os.path.abspath(os.fspath(path))
    if sys.platform != "win32" or (len(text) < _LONG and not force) or text.startswith("\\\\?\\"):
        return text
    return "\\\\?\\UNC\\" + text[2:] if text.startswith("\\\\") else "\\\\?\\" + text


def retrying(action: Callable[[], Any], attempts: int = _ATTEMPTS) -> Any:
    """Run an action, waiting out sharing violations; the last error is raised when it never clears."""
    delay = 0.02
    for attempt in range(attempts):
        try:
            return action()
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2
    return None


def write_bytes(path: str | os.PathLike[str], data: bytes) -> None:
    target = long_path(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".yaz-", suffix=".tmp", dir=os.path.dirname(target))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        retrying(lambda: os.replace(temporary, target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_text(path: str | os.PathLike[str], text: str) -> None:
    write_bytes(path, text.replace("\r\n", "\n").encode("utf-8"))


def read_text(path: str | os.PathLike[str]) -> str:
    def read() -> str:
        with open(long_path(path), encoding="utf-8-sig", errors="replace", newline="") as stream:
            return stream.read().replace("\r\n", "\n")

    return retrying(read)


def remove_tree(path: str | os.PathLike[str]) -> None:
    """Delete a folder including read-only files (.git objects) and very deep ones (node_modules)."""
    root = long_path(path, force=True)  # the children may be far longer than the root
    if not os.path.lexists(root):
        return

    def unlock(function: Callable[[str], Any], failed: str, _error: Any) -> None:
        os.chmod(failed, stat.S_IWRITE | stat.S_IREAD)
        retrying(lambda: function(failed))

    shutil.rmtree(root, onexc=unlock) if sys.version_info >= (3, 12) else shutil.rmtree(root, onerror=unlock)


def size_of(path: Path) -> int:
    """Bytes used by a file or a folder; unreadable entries count as zero."""
    total = 0
    for base, _dirs, files in os.walk(long_path(path, force=True)):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                continue
    if os.path.isfile(long_path(path)):
        total = os.path.getsize(long_path(path))
    return total
