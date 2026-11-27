"""Who may write what: file and symbol leases for parallel writers.

A lease names a file ("app.py") or one symbol in it ("app.py::total"). Two leases collide when they touch the same file
and either wants the whole file or both want the same symbol. A writer gets all its leases at once or none, so two
writers can never wait for each other (no deadlock). A symbol writer re-reads the file at the moment of writing and
replaces only its own function, so parallel writers do not undo each other.
"""

from __future__ import annotations

import ast
import asyncio
import textwrap
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from pathlib import Path

import atomic_io

_WAIT_S = 600.0


class LeaseTimeout(TimeoutError):
    pass


def collides(one: str, other: str) -> bool:
    file_a, _, symbol_a = one.partition("::")
    file_b, _, symbol_b = other.partition("::")
    return file_a.replace("\\", "/").casefold() == file_b.replace("\\", "/").casefold() and (not symbol_a or not symbol_b or symbol_a == symbol_b)


class Table:
    def __init__(self) -> None:
        self.held: dict[str, str] = {}  # resource -> owner
        self._changed: asyncio.Condition | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def try_acquire(self, owner: str, resources: Iterable[str]) -> bool:
        wanted = list(resources)
        if any(holder != owner and collides(resource, held) for resource in wanted for held, holder in self.held.items()):
            return False
        self.held.update(dict.fromkeys(wanted, owner))
        return True

    def release(self, owner: str) -> None:
        self.held = {resource: holder for resource, holder in self.held.items() if holder != owner}

    def _condition(self) -> asyncio.Condition:
        loop = asyncio.get_running_loop()
        if self._changed is None or self._loop is not loop:
            self._changed, self._loop = asyncio.Condition(), loop
        return self._changed

    @asynccontextmanager
    async def lease(self, owner: str, resources: Iterable[str], wait_s: float = _WAIT_S) -> AsyncIterator[None]:
        wanted, changed = list(resources), self._condition()
        async with changed:
            try:
                await asyncio.wait_for(changed.wait_for(lambda: self.try_acquire(owner, wanted)), wait_s)
            except TimeoutError as exc:
                holders = sorted({h for r in wanted for held, h in self.held.items() if collides(r, held)})
                raise LeaseTimeout(f"{owner} yazma kirasını {wait_s:.0f} sn içinde alamadı; tutan: {', '.join(holders)}") from exc
        try:
            yield
        finally:
            async with changed:
                self.release(owner)
                changed.notify_all()


TABLE = Table()


def replace_symbol(path: Path, name: str, code: str) -> None:
    """Swaps one top-level function or class for `code`, against the file as it is now; ValueError when it cannot."""
    current = path.read_text(encoding="utf-8")
    node = next((n for n in ast.parse(current).body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and n.name == name), None)
    if node is None:
        raise ValueError(f"{path.name} içinde '{name}' yok")
    start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
    lines = current.splitlines()
    merged = "\n".join([*lines[: start - 1], textwrap.dedent(code).strip("\n"), *lines[node.end_lineno :]]) + "\n"
    ast.parse(merged)
    atomic_io.write_text(path, merged)


async def write_symbol(ws_dir: Path, owner: str, resource: str, code: str) -> None:
    """`resource` is "file::symbol"; only that symbol changes, under its lease."""
    name, _, symbol = resource.partition("::")
    async with TABLE.lease(owner, [f"{ws_dir.name}/{resource}"]):
        replace_symbol(ws_dir / name, symbol, code)
