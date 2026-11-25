"""Lenient loader for the JSON a local model writes: the outermost object only, with the usual slips repaired.

Repairs: markdown fences, trailing commas, raw line breaks / tabs inside strings, and output cut off by the token limit
(open strings, arrays and objects are closed). It never returns an inner object when the outer one is broken, which is what a
"find any parsable {" scan does.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_DANGLING_RE = re.compile(r',?\s*"[^"\\]*"?\s*:?\s*$')


class _State:
    """Scanner state for _sanitize: inside a string, after a backslash, and the stack of open brackets."""

    def __init__(self) -> None:
        self.in_str = False
        self.esc = False
        self.stack: list[str] = []


def _in_string(ch: str, st: _State) -> str:
    """Handle one character inside a JSON string; raw line breaks and tabs are escaped."""
    if st.esc:
        st.esc = False
    elif ch == "\\":
        st.esc = True
    elif ch == '"':
        st.in_str = False
    elif ch == "\n":
        return "\\n"
    elif ch == "\t":
        return "\\t"
    return ch


def _sanitize(body: str) -> str:
    out: list[str] = []
    st = _State()
    for ch in body:
        if st.in_str:
            out.append(_in_string(ch, st))
            continue
        out.append(ch)
        if ch == '"':
            st.in_str = True
        elif ch in "{[":
            st.stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and st.stack:
            st.stack.pop()
            if not st.stack:
                break
    text = "".join(out)
    if st.in_str:
        text += '"'
    if st.stack:
        text = _DANGLING_RE.sub("", text.rstrip()) if text.rstrip().endswith((",", ":")) else text
        text += "".join(reversed(st.stack))
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def loads_top(raw: str) -> dict[str, Any] | None:
    """The outermost JSON object in `raw`, repaired if needed, else None."""
    text = _FENCE_RE.sub(r"\1", raw or "")
    start = text.find("{")
    if start == -1:
        return None
    for candidate in (text[start:], _sanitize(text[start:])):
        try:
            obj, _ = json.JSONDecoder().raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None
