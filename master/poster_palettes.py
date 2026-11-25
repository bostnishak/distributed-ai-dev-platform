"""Colour palette choice for posters and logos from the colours the user names (never from words inside quoted titles/slogans)."""

from __future__ import annotations

import re

EXTRA: dict[str, dict[str, str]] = {
    "navy_gold": {"name": "Lacivert ve Altın", "bg1": "#070d22", "bg2": "#0d1a3f", "bg3": "#12255a", "primary": "#d4a017", "secondary": "#1e40af", "accent": "#f5d27a", "text": "#f8fafc", "muted": "#b4c0dd", "card": "#0d1a3f", "grid": "#d4a017"},
    "sunset_orange": {"name": "Turuncu ve Kömür", "bg1": "#140a05", "bg2": "#24120a", "bg3": "#2a160d", "primary": "#f97316", "secondary": "#ef4444", "accent": "#fdba74", "text": "#fff7ed", "muted": "#d6b9a0", "card": "#24120a", "grid": "#f97316"},
    "rose_pink": {"name": "Gül ve Antrasit", "bg1": "#16070f", "bg2": "#240c1a", "bg3": "#1f1126", "primary": "#ec4899", "secondary": "#a855f7", "accent": "#f9a8d4", "text": "#fdf2f8", "muted": "#d8b4cc", "card": "#240c1a", "grid": "#ec4899"},
    "forest_cream": {"name": "Orman ve Krem", "bg1": "#f7f3e8", "bg2": "#efe8d4", "bg3": "#e2d9bd", "primary": "#2f6b3f", "secondary": "#7a5c2e", "accent": "#4c9a5d", "text": "#1d2b1f", "muted": "#5b6b58", "card": "#fbf8ef", "grid": "#2f6b3f"},
}
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mono_bw", ("siyah beyaz", "siyah-beyaz", "siyah ve beyaz", "black and white", "black & white", "monokrom", "monochrome", "grayscale")),
    ("crimson_carbon", ("kırmızı", "kirmizi", "bordo", "red")),
    ("sunset_orange", ("turuncu", "orange")),
    ("rose_pink", ("pembe", "pink", "gül rengi")),
    ("violet_aurora", ("mor", "violet", "purple", "eflatun")),
    ("emerald_slate", ("yeşil", "yesil", "green", "zümrüt")),
    ("obsidian_gold", ("altın", "altin", "gold", "sarı", "sari", "yellow", "lüks", "luks", "premium")),
    ("azure_white", ("mavi", "blue", "lacivert", "navy", "okyanus")),
    ("nordic_light", ("açık renk", "acik renk", "beyaz", "white", "pastel", "minimalist")),
    ("emerald_slate", ("doğa", "doga", "ekoloji", "orman", "sağlık", "eco", "nature")),
    ("crimson_carbon", ("spor", "otomotiv", "konser", "enerji", "sport", "energy")),
    ("violet_aurora", ("yapay zeka", "uzay", "galaksi", "fütüristik", "cyberpunk", "space", "ai ")),
    ("obsidian_gold", ("gün batımı", "gun batimi", "sunset")),
)
_QUOTED_RE = re.compile(r"[\"'“‘][^\"'”’]{2,60}[\"'”’]")  # noqa: RUF001


def pick(text: str, seed: int, keys: list[str]) -> str:
    """Palette key for the colours/themes named in `text` (quoted names and slogans are ignored); a seed-based choice when none is named."""
    low = _QUOTED_RE.sub(" ", (text or "").lower())

    def has(words: tuple[str, ...]) -> bool:
        return any(re.search(rf"(?<!\w){re.escape(w)}", low) for w in words)

    if has(("lacivert", "navy", "mavi", "blue")) and has(("altın", "altin", "gold", "sarı", "sari", "yellow")):
        return "navy_gold"
    if has(("yeşil", "yesil", "green")) and has(("krem", "cream", "bej", "beige")):
        return "forest_cream"
    for key, words in _RULES:
        if has(words):
            return key
    quoted = " ".join(_QUOTED_RE.findall((text or "").lower()))  # a brand called 'Mavi Orman' still suggests blue when nothing else names a colour
    for key, words in _RULES[:9]:
        if any(re.search(rf"(?<!\w){re.escape(w)}", quoted) for w in words):
            return key
    return keys[seed % len(keys)]
