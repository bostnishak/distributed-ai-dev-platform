"""Streaming text fix-ups: models sometimes write JSON with \\uXXXX escapes, which are unreadable for Turkish text."""

from __future__ import annotations

import re

_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_PARTIAL_RE = re.compile(r"\\(?:u[0-9a-fA-F]{0,3})?$")


class JsonUnescaper:
    """Turns \\u0131-style escapes into real characters, but only when the answer is a JSON document.

    ASCII escapes (quotes, backslashes, control characters) stay as they are so the JSON remains valid. A partial escape at the
    end of a chunk is held back until the next chunk completes it.
    """

    def __init__(self) -> None:
        self._active: bool | None = None
        self._carry = ""

    @staticmethod
    def _replace(match: re.Match[str]) -> str:
        code = int(match.group(1), 16)
        return chr(code) if code >= 0x80 and not 0xD800 <= code <= 0xDFFF else match.group(0)

    def feed(self, chunk: str) -> str:
        text = self._carry + chunk
        self._carry = ""
        if self._active is None:
            stripped = text.lstrip()
            if not stripped:
                return text
            self._active = stripped[0] in "[{"
        if not self._active:
            return text
        if (partial := _PARTIAL_RE.search(text)) is not None:
            self._carry, text = text[partial.start():], text[: partial.start()]
        return _ESCAPE_RE.sub(self._replace, text)

    def flush(self) -> str:
        rest, self._carry = self._carry, ""
        return rest
