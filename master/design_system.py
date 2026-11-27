"""A colour and type system computed in OKLCH for visual requests that name no colours.

Perceived lightness is set directly, text and button colours are checked against WCAG contrast, and the user's own
choices (any hex code, or a named theme) always win: then nothing is added.
"""

from __future__ import annotations

import hashlib
import math
import re

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_COLOUR_WORDS = re.compile(
    r"\b(?:renk|rengi\w*|palet|siyah|beyaz|kırmızı|mavi|yeşil|sarı|mor|turuncu|pembe|gri|lacivert|colou?r|palette|black|white|red|blue|green|yellow|purple|orange|pink|gr[ae]y)\w*",
    re.IGNORECASE,
)
_VISUAL_RE = re.compile(r"\b(?:tasarım\w*|şık|modern|sade|minimalist|estetik|güzel|panel\w*|dashboard|landing|portfolyo|portfolio|site\w*|web\s*(?:sayfa|uygulama)\w*|arayüz\w*|design|sleek|elegant|beautiful)\b", re.IGNORECASE)
_DARK_RE = re.compile(r"\b(?:koyu|karanlık|dark)\b", re.IGNORECASE)
_HUES = {"finans|banka|fintech|muhasebe": 255, "sağlık|klinik|hasta|health": 185, "doğa|tarım|çevre|eco|bahçe": 145, "yemek|restoran|kafe|food": 45,
         "eğitim|okul|kurs|ders": 275, "spor|fitness": 25, "seyahat|tur|otel|travel": 220}


def oklch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    """sRGB hex of an OKLCH colour; chroma is reduced until the colour exists in sRGB."""
    while True:
        a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
        l_, m_, s_ = ((lightness + x * a + y * b) ** 3 for x, y in ((0.3963377774, 0.2158037573), (-0.1055613458, -0.0638541728), (-0.0894841775, -1.2914855480)))
        linear = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_, -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
                  -0.0041960863 * l_ - 0.7034186168 * m_ + 1.7076147010 * s_)
        if chroma <= 0 or all(-0.0005 <= c <= 1.0005 for c in linear):
            break
        chroma = max(chroma - 0.005, 0)
    srgb = (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055 for c in (min(max(c, 0.0), 1.0) for c in linear))
    return "#" + "".join(f"{round(c * 255):02x}" for c in srgb)


def contrast(first: str, second: str) -> float:
    def luminance(colour: str) -> float:
        channels = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
        r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def hue_for(request: str) -> int:
    for words, hue in _HUES.items():
        if re.search(rf"\b(?:{words})\w*", request, re.IGNORECASE):
            return hue
    return int(hashlib.sha256(request.encode()).hexdigest(), 16) % 360


def _on(background: str) -> str:
    return "#ffffff" if contrast("#ffffff", background) >= contrast("#0b0f14", background) else "#0b0f14"


def palette(request: str, dark: bool) -> dict[str, str]:
    hue = hue_for(request)
    levels = (0.17, 0.22, 0.32, 0.95, 0.74, 0.72) if dark else (0.98, 1.0, 0.90, 0.22, 0.45, 0.52)
    background, surface, border, text, muted, accent = levels
    out = {
        "--bg": oklch_to_hex(background, 0.008, hue), "--surface": oklch_to_hex(surface, 0.006 if surface < 1 else 0.0, hue),
        "--border": oklch_to_hex(border, 0.012, hue), "--text": oklch_to_hex(text, 0.015, hue), "--text-muted": oklch_to_hex(muted, 0.02, hue),
        "--accent": oklch_to_hex(accent, 0.15, hue), "--accent-hover": oklch_to_hex(accent + (0.06 if dark else -0.07), 0.15, hue),
    }
    step = 0.02 if dark else -0.02
    while contrast(out["--accent"], _on(out["--accent"])) < 4.5 and 0.2 < accent < 0.92:
        accent += step
        out["--accent"] = oklch_to_hex(accent, 0.15, hue)
    out["--on-accent"] = _on(out["--accent"])
    return out


def brief(request: str) -> str:
    """Extra writer notes for an open-ended visual request; '' when the user chose colours or it is not visual."""
    if _HEX_RE.search(request) or _COLOUR_WORDS.search(request) or not _VISUAL_RE.search(request):
        return ""
    colours = palette(request, bool(_DARK_RE.search(request)))
    tokens = "; ".join(f"{name}: {value}" for name, value in colours.items())
    return (f"\n\nTASARIM SİSTEMİ (kullanıcı renk vermedi; bunları CSS değişkeni olarak tanımla ve yalnız bunları kullan):\n{tokens}\n"
            "Yazı ölçeği (1,25 oranlı): 14 / 16 / 20 / 25 / 31 px, başka boyut kullanma; gövde satır aralığı 1.5, başlık 1.2; "
            "tüm dış ve iç boşluklar 4px'in katı (dikey ritim 8px); köşe yarıçapı her yerde 8px; metin satırı en çok 70 karakter. Gradyan, emoji ve boş pazarlama cümlesi kullanma.")
