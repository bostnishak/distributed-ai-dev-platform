"""Catches the repair loop going A -> B -> A: a patch that brings a file back to a state it already had is refused.

States are compared by meaning, not by bytes: the syntax tree for Python (comments and layout do not count), the text
without comments and whitespace for everything else. The first return bans the patch and forces a clean start; a
second one stops the loop.
"""

from __future__ import annotations

import ast
import hashlib
import logging
import re
from pathlib import Path

_COMMENT_RE = re.compile(r"/\*.*?\*/|<!--.*?-->|(?<![:\"'])//[^\n]*", re.DOTALL)
_SPACE_RE = re.compile(r"\s+")
MAX_RETURNS = 2
_log = logging.getLogger(__name__)


def canonical(path: str, code: str) -> str:
    """The hash of what the file means."""
    shape = ""
    if path.endswith(".py"):
        try:
            shape = ast.dump(ast.parse(code))
        except SyntaxError:
            shape = ""  # an unparsable state is compared as text
    if not shape:
        shape = _SPACE_RE.sub("", _COMMENT_RE.sub("", code))
    return hashlib.sha256(shape.encode("utf-8")).hexdigest()


class Tracker:
    """The states every file has been in during one repair loop."""

    def __init__(self) -> None:
        self.states: dict[str, list[str]] = {}
        self.returns: list[str] = []

    def remember(self, path: str, code: str) -> None:
        digest = canonical(path, code)
        history = self.states.setdefault(path, [])
        if digest not in history:
            history.append(digest)

    def repeats(self, path: str, current: str, proposed: str) -> bool:
        """True when `proposed` is a state the file already had (including "no change"); nothing is recorded then."""
        self.remember(path, current)
        if canonical(path, proposed) not in self.states[path]:
            self.remember(path, proposed)
            return False
        self.returns.append(path)
        _log.warning("Salınım: %s için önerilen yama dosyayı daha önceki bir duruma döndürüyor (%s. kez)", Path(path).name, len(self.returns))
        return True

    @property
    def halted(self) -> bool:
        return len(self.returns) >= MAX_RETURNS
