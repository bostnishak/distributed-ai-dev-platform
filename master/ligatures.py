"""PDF fonts often store "fi", "fl" and friends as one joined character; text read from a PDF gets the letters back."""

from __future__ import annotations

_PARTS = {0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl", 0xFB05: "st", 0xFB06: "st"}


def split(text: str) -> str:
    return text.translate(_PARTS)
