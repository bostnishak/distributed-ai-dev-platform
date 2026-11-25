"""Deterministic guard for chat messages that try to extract the assistant's hidden instructions."""

from __future__ import annotations

import re

_I = re.IGNORECASE
_TARGET = r"(?:system\s*prompt\w*|sistem\s*(?:prompt|istem|talimat|mesaj)\w*|gizli\s+(?:talimat|prompt|istem)\w*|hidden\s+(?:prompt|instruction)s?|initial\s+instructions?|başlangıç\s+talimat\w*)"
_VERB = r"(?:yazdır\w*|yaz\b|göster\w*|paylaş\w*|ver\b|açıkla\w*|tekrarla\w*|söyle\w*|dök\w*|print|show|reveal|repeat|display|output|tell|leak|dump)"
_LEAK_RE = re.compile(rf"{_TARGET}.{{0,60}}{_VERB}|{_VERB}.{{0,60}}{_TARGET}", _I | re.S)
_OVERRIDE_RE = re.compile(r"(?:önceki|yukarıdaki|tüm|bütün)\s+(?:tüm\s+)?(?:talimat|kural|komut)\w*\s+(?:unut|yok\s+say|geçersiz)\w*|ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules)", _I)

REFUSAL = (
    "Sistem talimatlarımı ve gizli ayarlarımı paylaşamam; bunları yazdırma ya da yok sayma isteklerini uygulamıyorum. "
    "Ama asıl ihtiyacını söylersen (soru, belge, kod, görsel…) hemen yardımcı olurum."
)


def refusal_for(prompt: str) -> str | None:
    text = prompt or ""
    return REFUSAL if len(text) < 1500 and (_LEAK_RE.search(text) or _OVERRIDE_RE.search(text)) else None
