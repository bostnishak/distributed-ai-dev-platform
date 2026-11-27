"""Turkish letter rules that Python's default casing gets wrong (I/ı and İ/i), and Turkish alphabetical order."""

from __future__ import annotations

_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_UPPER = str.maketrans({"i": "İ", "ı": "I"})
_ALPHABET = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_RANK = {letter: index for index, letter in enumerate(_ALPHABET)}


def lower(text: str) -> str:
    return text.translate(_LOWER).lower()


def upper(text: str) -> str:
    return text.translate(_UPPER).upper()


def sort_key(text: str) -> tuple[tuple[int, int], ...]:
    """Alphabetical order as a Turkish reader expects it: c, ç, d ... h, ı, i, j; non-letters come first by code."""
    return tuple((1, _RANK[ch]) if ch in _RANK else (0, ord(ch)) for ch in lower(text))


def matches(needle: str, haystack: str) -> bool:
    """Case-insensitive search in Turkish: "İstanbul" finds "istanbul", "IĞDIR" finds "ığdır"."""
    return lower(needle) in lower(haystack)
