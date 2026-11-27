"""The Content-Length framed JSON messages that both the language server and debug adapter protocols use."""

from __future__ import annotations

import json
import queue
import threading
from typing import IO, Any


class Channel:
    """Send messages to a process and receive them on a background thread, with a timeout."""

    def __init__(self, reader: IO[bytes], writer: IO[bytes]) -> None:
        self._writer = writer
        self.inbox: queue.Queue[dict[str, Any]] = queue.Queue()
        threading.Thread(target=self._read, args=(reader,), daemon=True).start()

    def send(self, message: dict[str, Any]) -> None:
        body = json.dumps(message).encode()
        self._writer.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        self._writer.flush()

    def _read(self, reader: IO[bytes]) -> None:
        try:
            while True:
                length = 0
                while line := reader.readline():
                    if not line.strip():
                        break
                    name, _, value = line.partition(b":")
                    if name.strip().lower() == b"content-length":
                        length = int(value.strip())
                if not length:
                    return
                self.inbox.put(json.loads(reader.read(length)))
        except (OSError, ValueError):
            return

    def wait(self, wanted, timeout: float) -> dict[str, Any]:
        """The first message `wanted` accepts; others are dropped. TimeoutError when none arrives."""
        import time

        end = time.monotonic() + timeout
        while (left := end - time.monotonic()) > 0:
            try:
                message = self.inbox.get(timeout=left)
            except queue.Empty:
                break
            if wanted(message):
                return message
        raise TimeoutError("protokol yanıtı gelmedi")
