"""Which numbers in a generated deck are supported by the user's request or source document?

A number is supported when it appears in the request/source (any notation: 12.000, 1,2 milyon, %65) or is a plain arithmetic
consequence of two of those numbers (sum, difference, product, ratio, share in %). Everything else is an invented statistic.
"""

from __future__ import annotations

import itertools
import re

_NUM_RE = re.compile(r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(milyar|milyon|bin|billion|million|thousand|b\b|m\b|k\b)?", re.IGNORECASE)
_SCALE = {"milyar": 1e9, "billion": 1e9, "milyon": 1e6, "million": 1e6, "bin": 1e3, "thousand": 1e3}
_COUNT_PHRASE_RE = re.compile(r"\d+[\s-]*(?:adet|tane)?[\s-]*(?:slayt|sayfa|slide|page)\w*", re.IGNORECASE)
_MAX_BASE = 14


def _to_float(raw: str) -> float | None:
    text = raw.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", text):
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d+", text):
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def numbers_in(text: str) -> list[float]:
    """Every number in the text, with scale words applied ('1,2 milyon' -> 1200000)."""
    out: list[float] = []
    for m in _NUM_RE.finditer(text or ""):
        value = _to_float(m.group(1))
        if value is not None:
            out.append(value * _SCALE.get((m.group(2) or "").lower(), 1.0))
    return out


def claims_in(text: str) -> list[tuple[float, float]]:
    """(value, step) for every number: `step` is the unit of its last written digit ('22,63' -> 0.01, '4,2 milyon' -> 100000, '65.000' -> 1)."""
    out: list[tuple[float, float]] = []
    for m in _NUM_RE.finditer(text or ""):
        value = _to_float(m.group(1))
        if value is None:
            continue
        scale = _SCALE.get((m.group(2) or "").lower(), 1.0)
        decimals = len(m.group(1).split(",")[1]) if "," in m.group(1) else (len(m.group(1).split(".")[1]) if re.fullmatch(r"\d+\.\d{1,2}", m.group(1)) else 0)
        out.append((value * scale, (10.0 ** -decimals) * scale))
    return out


def source_numbers(source: str) -> list[float]:
    """Numbers of the request/source, without the requested slide count ('7 slaytlık')."""
    return numbers_in(_COUNT_PHRASE_RE.sub(" ", source or ""))


def _derived(base: list[float]) -> set[float]:
    uniq = list(dict.fromkeys(base))[:_MAX_BASE]
    out: set[float] = set()
    for a, b in itertools.permutations(uniq, 2):
        out |= {a + b, a - b, a * b}
        if b:
            out |= {a / b, a / b * 100, (a - b) / b * 100}
    return {round(v, 2) for v in out}


def supported_set(source: str) -> tuple[list[float], set[float]]:
    base = source_numbers(source)
    return base, _derived(base)


def _close(a: float, b: float) -> bool:
    """Equal within rounding: 0.3 % for small values, 0.6 % for large ones (reports round big numbers)."""
    return a == b or (b != 0 and abs(a - b) / abs(b) <= (0.003 if abs(b) < 100 else 0.006))


def is_supported(value: float, base: list[float], derived: set[float], step: float = 0.0) -> bool:
    """True when `value` is in the source (any scale) or derived from two source numbers.

    With `step` (the unit of the claim's last written digit) a derived value must match to that digit, so a wrongly rounded figure
    ('22,63' for 22,685) is rejected; without it the comparison tolerates ordinary rounding."""
    tol = min(step, 0.01 * abs(value)) if step else 0.0  # one unit of the last digit, but never more than 1 % of the value
    if any(_close(value, b) or abs(value - b) <= tol for b in base):
        return True
    if step:
        return any(abs(value - d) <= tol * 1.01 for d in derived)
    return any(_close(value, d) for d in derived)


def unsupported_numbers(text: str, source: str, *, ignore_small: bool = True) -> list[float]:
    """Numbers in `text` that neither the source contains nor simple arithmetic on it produces (single digits and years are ignored)."""
    base, derived = supported_set(source)
    bad = []
    for v in numbers_in(text):
        if ignore_small and (v < 10 or 1900 <= v <= 2100):
            continue
        if not is_supported(v, base, derived):
            bad.append(v)
    return bad


_WORD_NUMBERS = {"iki": 2.0, "üç": 3.0, "dört": 4.0, "beş": 5.0, "altı": 6.0, "yedi": 7.0, "sekiz": 8.0, "dokuz": 9.0, "on": 10.0}
_FOLD_RE = re.compile(r"(\d+(?:[.,]\d+)?|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)\s*(?:kat\b|katına|katı\b)", re.IGNORECASE)


def fold_claims(text: str) -> list[float]:
    """'üç katına çıkacak', '2,5 kat' -> [3.0], [2.5]: multiplication claims written with words or digits."""
    out: list[float] = []
    for m in _FOLD_RE.finditer(text or ""):
        raw = m.group(1).lower()
        value = _WORD_NUMBERS.get(raw) or _to_float(raw)
        if value:
            out.append(value)
    return out


def fold_supported(value: float, base: list[float]) -> bool:
    """A 'N times' claim is supported when some ratio of two source numbers is within 15 % of it."""
    return any(b and abs(value - a / b) / value <= 0.15 for a in base for b in base if a != b)


def scaled_supported(value: float, base: list[float], derived: set[float]) -> bool:
    """Chart values are often written in thousands or millions ('12' for 12.000): accept those scales too."""
    return any(is_supported(value * scale, base, derived) for scale in (1.0, 1e3, 1e6))
