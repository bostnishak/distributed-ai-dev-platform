"""How much machinery a request deserves (gears 0-4), decided without a model in well under a millisecond.

`@fast` / `@hızlı` skips research and the extra agents; `@deep` / `@derin` forces them even for a short request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FAST_RE = re.compile(r"(?<!\w)@(?:fast|hızlı|hizli)\b", re.IGNORECASE)
_DEEP_RE = re.compile(r"(?<!\w)@(?:deep|derin|verify-max)\b", re.IGNORECASE)
_HEAVY_RE = re.compile(r"\b(?:mikroservis|microservice|çoklu repo|multi[- ]repo|migration|göç|güvenlik|security|ödeme|payment|kimlik doğrulama|authentication)\b", re.IGNORECASE)
_BUILD_RE = re.compile(r"\b(?:uygulama|proje|site|api|oyun|panel|dashboard|app|project|website|rapor|sunum|excel|pdf|word)\w*", re.IGNORECASE)
_TWEAK_RE = re.compile(r"\b(?:rengi\w*|renk|yazı\w*|font|boyut\w*|colou?r|text)\b|#[0-9a-fA-F]{6}", re.IGNORECASE)
_DETAILED_CHARS = 300


@dataclass(frozen=True)
class Gear:
    level: int
    research: bool
    agents: bool
    reason: str


def strip_override(prompt: str) -> str:
    return _DEEP_RE.sub("", _FAST_RE.sub("", prompt)).strip()


def classify(prompt: str, *, editing: bool = False) -> Gear:
    if _FAST_RE.search(prompt):
        return Gear(1, False, False, "kullanıcı hızlı mod istedi")
    if _DEEP_RE.search(prompt):
        return Gear(3, True, True, "kullanıcı derin mod istedi")
    if editing:
        return Gear(0, False, False, "küçük görünüm değişikliği") if len(prompt) < 120 and _TWEAK_RE.search(prompt) else Gear(1, False, False, "mevcut projede düzenleme")
    if not _BUILD_RE.search(prompt) and len(prompt) < _DETAILED_CHARS:
        return Gear(0, False, False, "doğrudan yanıt")
    if _HEAVY_RE.search(prompt):
        return Gear(3, True, True, "güvenlik ya da çok parçalı sistem")
    detailed = len(prompt) >= _DETAILED_CHARS
    return Gear(2, not detailed, detailed, "ayrıntılı tarif" if detailed else "standart üretim")
