"""A real language server (python-lsp-server) answers questions about a workspace: references and diagnostics.

The server only reads and parses the files; it never runs the project's code.
"""

from __future__ import annotations

import itertools
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import process_registry
import protocol_io

_log = logging.getLogger(__name__)
_SKIP = {".history", "venv", ".venv", "__pycache__", "node_modules"}
_ASK_RE = re.compile(r"^\s*(?P<a>[A-Za-z_]\w{1,60})\s+(?:nerede\s+kullanılıyor|nerelerde\s+kullanılıyor)\??\s*$|^\s*find\s+references\s+(?:of\s+)?(?P<b>[A-Za-z_]\w{1,60})\s*$", re.IGNORECASE)
_TIMEOUT = 25.0


class Session:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._ids = itertools.count(1)
        self.diagnostics: dict[str, list[dict[str, Any]]] = {}
        # -P keeps the workspace off the server's import path: a planted pylsp.py in the project must not be executed
        self._proc = subprocess.Popen([sys.executable, "-E", "-P", "-m", "pylsp"], cwd=self.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)  # noqa: S603, RUF100
        process_registry.track(self._proc, "kod dil sunucusu", memory_mb=4096)  # jedi commits more than the 1 GB a generated project gets
        self._channel = protocol_io.Channel(self._proc.stdout, self._proc.stdin)
        self.request("initialize", {"processId": None, "rootUri": self.root.as_uri(), "capabilities": {}})
        self.notify("initialized", {})
        for path in self.files():
            self.notify("textDocument/didOpen", {"textDocument": {"uri": path.as_uri(), "languageId": "python", "version": 1, "text": path.read_text(encoding="utf-8", errors="replace")}})

    def files(self) -> list[Path]:
        return [p for p in sorted(self.root.rglob("*.py")) if not _SKIP & set(p.relative_to(self.root).parts)][:200]

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._channel.send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> Any:
        number = next(self._ids)
        self._channel.send({"jsonrpc": "2.0", "id": number, "method": method, "params": params})

        def mine(message: dict[str, Any]) -> bool:
            if message.get("method") == "textDocument/publishDiagnostics":
                self.diagnostics[message["params"]["uri"]] = message["params"]["diagnostics"]
            return message.get("id") == number and "method" not in message

        reply = self._channel.wait(mine, _TIMEOUT)
        if "error" in reply:
            raise RuntimeError(reply["error"].get("message", "dil sunucusu hatası"))
        return reply.get("result")

    def close(self) -> None:
        self._proc.kill()
        self._proc.wait(timeout=5)
        process_registry.untrack(self._proc.pid)

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _norm(uri: str) -> str:
    return unquote(uri).casefold()


def _definition(files: list[Path], symbol: str) -> tuple[Path, int, int] | None:
    pattern = re.compile(rf"^([ \t]*(?:async[ \t]+)?(?:def|class)[ \t]+){re.escape(symbol)}\b|^(){re.escape(symbol)}[ \t]*=", re.MULTILINE)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if match := pattern.search(text):
            line = text.count("\n", 0, match.start())
            return path, line, len(match.group(1) or "")
    return None


def references(root: Path, symbol: str) -> list[tuple[str, int, str]] | None:
    """(file, 1-based line, source line) for every use of a symbol; None when the project does not define it."""
    with Session(root) as session:
        found = _definition(session.files(), symbol)
        if not found:
            return None
        path, line, column = found
        result = session.request("textDocument/references", {"textDocument": {"uri": path.as_uri()}, "position": {"line": line, "character": column},
                                                             "context": {"includeDeclaration": True}}) or []
        out = []
        by_uri = {_norm(p.as_uri()): p for p in session.files()}  # servers percent-encode paths differently
        for item in result:
            target = by_uri.get(_norm(item["uri"]))
            if target is None:
                continue
            row = item["range"]["start"]["line"]
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            out.append((target.relative_to(session.root).as_posix(), row + 1, lines[row].strip()[:90]))
        return sorted(set(out))


def asked_symbol(prompt: str) -> str:
    match = _ASK_RE.match(prompt)
    return (match["a"] or match["b"]) if match else ""


def answer(root: Path, symbol: str) -> str:
    try:
        found = references(root, symbol)
    except (OSError, TimeoutError, RuntimeError, subprocess.SubprocessError) as exc:
        _log.warning("language server failed: %r", exc)
        return "Dil sunucusu çalıştırılamadı."
    if found is None:
        return f"Projede `{symbol}` adında tanımlı bir sembol yok."
    lines = "\n".join(f"- `{name}:{row}` — `{source}`" for name, row, source in found[:30])
    return f"`{symbol}` için {len(found)} başvuru (dil sunucusundan):\n{lines}"
