"""Small vector icons that match what a poster is about; chosen from words in the request (cafe -> cup, sea -> waves ...).

Each icon is drawn in a 100x100 box with strokes only, so it follows the palette; `emblem` places up to two of them.
"""

from __future__ import annotations

import re

_ICONS: dict[str, str] = {
    "cup": '<path d="M18 38h46v22a22 22 0 0 1-22 22h-2a22 22 0 0 1-22-22z"/><path d="M64 44h8a10 10 0 0 1 0 20h-8"/><path d="M30 28c0-6 6-6 6-12M44 28c0-6 6-6 6-12M58 28c0-6 6-6 6-12"/><path d="M14 90h58"/>',
    "waves": '<path d="M8 36q10-12 21 0t21 0 21 0 21 0"/><path d="M8 56q10-12 21 0t21 0 21 0 21 0"/><path d="M8 76q10-12 21 0t21 0 21 0 21 0"/>',
    "mountain": '<path d="M6 82 38 26l18 30 12-16 26 42z"/><path d="M30 40l8 14 8-8"/>',
    "tree": '<path d="M50 90V54"/><circle cx="50" cy="34" r="22"/><path d="M50 66 38 54M50 60l12-10"/>',
    "sun": '<circle cx="50" cy="50" r="18"/><path d="M50 8v14M50 78v14M8 50h14M78 50h14M20 20l10 10M70 70l10 10M80 20 70 30M30 70 20 80"/>',
    "moon": '<path d="M66 14a38 38 0 1 0 22 60A32 32 0 0 1 66 14z"/>',
    "house": '<path d="M10 50 50 14l40 36"/><path d="M20 44v44h60V44"/><path d="M42 88V62h16v26"/>',
    "book": '<path d="M50 24c-10-8-26-10-38-6v58c12-4 28-2 38 6 10-8 26-10 38-6V18c-12-4-28-2-38 6z"/><path d="M50 24v58"/>',
    "heart": '<path d="M50 84C20 62 10 46 10 32a20 20 0 0 1 40-4 20 20 0 0 1 40 4c0 14-10 30-40 52z"/>',
    "note": '<path d="M38 74V22l44-10v52"/><circle cx="28" cy="76" r="12"/><circle cx="72" cy="66" r="12"/>',
    "car": '<path d="M8 62v-8l10-4 12-18h40l12 18 10 4v8z"/><circle cx="28" cy="66" r="9"/><circle cx="72" cy="66" r="9"/><path d="M30 32l-8 18h56L70 32z"/>',
    "plane": '<path d="M90 14 10 44l26 10 8 26 12-18 20 14z"/><path d="M36 54 90 14"/>',
    "phone": '<rect x="28" y="8" width="44" height="84" rx="8"/><path d="M44 80h12M38 18h24"/>',
    "dumbbell": '<path d="M26 50h48"/><rect x="12" y="34" width="14" height="32" rx="3"/><rect x="74" y="34" width="14" height="32" rx="3"/><path d="M4 42v16M96 42v16"/>',
    "fork": '<path d="M30 10v28a8 8 0 0 0 16 0V10M38 10v80"/><path d="M68 10c-10 8-12 24-12 40h12v40"/>',
    "paw": '<ellipse cx="50" cy="66" rx="20" ry="16"/><ellipse cx="22" cy="44" rx="8" ry="11"/><ellipse cx="40" cy="26" rx="8" ry="11"/><ellipse cx="60" cy="26" rx="8" ry="11"/><ellipse cx="78" cy="44" rx="8" ry="11"/>',
    "flower": '<circle cx="50" cy="40" r="8"/><circle cx="50" cy="20" r="10"/><circle cx="50" cy="60" r="10"/><circle cx="30" cy="40" r="10"/><circle cx="70" cy="40" r="10"/><path d="M50 70v22M50 82l14-8"/>',
    "laptop": '<rect x="18" y="20" width="64" height="44" rx="4"/><path d="M6 78h88l-8-14H14z"/>',
    "camera": '<path d="M10 32h20l6-10h28l6 10h20v52H10z"/><circle cx="50" cy="58" r="16"/>',
    "star": '<path d="M50 10l12 26 28 4-20 20 5 28-25-14-25 14 5-28L10 40l28-4z"/>',
    "shield": '<path d="M50 8 14 22v26c0 22 14 36 36 44 22-8 36-22 36-44V22z"/><path d="M34 50l12 12 22-24"/>',
    "key": '<circle cx="30" cy="50" r="18"/><path d="M48 50h42M76 50v14M64 50v10"/>',
    "scissors": '<circle cx="24" cy="26" r="10"/><circle cx="24" cy="74" r="10"/><path d="M32 32 90 70M32 68 90 30"/>',
    "runner": '<circle cx="60" cy="16" r="8"/><path d="M56 30 44 52l-16 6M44 52l14 14-6 24M56 30l16 14 14-2M44 52l-10 20-14 4"/>',
    "bolt": '<path d="M58 6 22 56h24l-6 38 38-52H54z"/>',
    "gear": '<circle cx="50" cy="50" r="16"/><circle cx="50" cy="50" r="32"/><path d="M50 6v12M50 82v12M6 50h12M82 50h12M19 19l9 9M72 72l9 9M81 19l-9 9M28 72l-9 9"/>',
    "cart": '<path d="M6 16h14l12 50h48l10-34H26"/><circle cx="38" cy="82" r="7"/><circle cx="74" cy="82" r="7"/>',
    "tooth": '<path d="M28 14c-12 0-18 12-14 28 4 14 4 30 10 44 4 8 10 2 12-10 2-10 4-14 8-14s6 4 8 14c2 12 8 18 12 10 6-14 6-30 10-44 4-16-2-28-14-28-8 0-12 4-16 4s-8-4-16-4z"/>',
    "cross": '<path d="M36 10h28v26h26v28H64v26H36V64H10V36h26z"/>',
    "bike": '<circle cx="22" cy="64" r="18"/><circle cx="78" cy="64" r="18"/><path d="M22 64 40 32h24l14 32M40 32l14 32H22M34 24h12M60 24h10"/>',
    "glass": '<path d="M24 10h52L68 44a18 18 0 0 1-36 0z"/><path d="M50 62v26M32 90h36M30 24h40"/>',
    "trophy": '<path d="M30 10h40v26a20 20 0 0 1-40 0z"/><path d="M30 18H14c0 16 6 24 18 26M70 18h16c0 16-6 24-18 26M50 56v18M34 90h32M40 74h20v16H40z"/>',
    "rocket": '<path d="M50 6c16 12 22 32 18 58H32C28 38 34 18 50 6z"/><circle cx="50" cy="38" r="8"/><path d="M32 52 18 70l16-4M68 52l14 18-16-4M42 76l8 18 8-18"/>',
    "bulb": '<path d="M34 64c-12-8-16-22-10-34a26 26 0 0 1 52 0c6 12 2 26-10 34v10H34z"/><path d="M36 84h28M42 94h16"/>',
    "globe": '<circle cx="50" cy="50" r="40"/><ellipse cx="50" cy="50" rx="18" ry="40"/><path d="M10 50h80M16 28h68M16 72h68"/>',
    "code": '<path d="M32 26 8 50l24 24M68 26l24 24-24 24M58 14 42 86"/>',
    "wrench": '<path d="M70 8a22 22 0 0 0-20 28L12 74a10 10 0 0 0 14 14l38-38a22 22 0 0 0 28-20l-14 14-12-4-4-12z"/>',
    "drop": '<path d="M50 8C32 34 18 48 18 64a32 32 0 0 0 64 0C82 48 68 34 50 8z"/><path d="M34 66a16 16 0 0 0 14 14"/>',
    "tent": '<path d="M6 86 50 12l44 74z"/><path d="M50 12v74M36 86l14-26 14 26"/>',
    "flame": '<path d="M50 6c4 18 28 28 28 56a28 28 0 0 1-56 0c0-14 8-20 12-30 4 8 8 10 10 12 4-10 6-22 6-38z"/><path d="M50 62c-8 6-10 22 0 28 10-6 8-22 0-28z"/>',
    "cake": '<path d="M12 56h76v32H12zM12 72q10 8 19 0t19 0 19 0 19 0"/><path d="M26 56V40h48v16M50 40V26"/><path d="M50 12c-6 6-2 12 0 14 2-2 6-8 0-14z"/>',
    "mic": '<rect x="36" y="8" width="28" height="48" rx="14"/><path d="M22 44a28 28 0 0 0 56 0M50 72v20M34 92h32"/>',
    "film": '<rect x="10" y="20" width="80" height="60" rx="6"/><path d="M26 20v60M74 20v60M10 36h16M10 52h16M10 68h16M74 36h16M74 52h16M74 68h16"/>',
    "gamepad": '<path d="M26 30h48c14 0 20 22 18 38-2 12-14 12-20 2l-6-10H34l-6 10c-6 10-18 10-20-2-2-16 4-38 18-38z"/><path d="M30 44v12M24 50h12"/><circle cx="66" cy="46" r="3"/><circle cx="76" cy="54" r="3"/>',
    "chart": '<path d="M10 10v80h82"/><path d="M24 70l20-24 14 14 28-34"/><path d="M70 26h16v16"/>',
    "bank": '<path d="M6 36 50 10l44 26zM16 42v36M38 42v36M62 42v36M84 42v36M6 90h88M10 78h80"/>',
    "ship": '<path d="M8 62h84l-12 24H20z"/><path d="M50 62V12l28 40H50M30 40l20-28"/>',
    "bag": '<path d="M18 30h64l6 60H12z"/><path d="M34 40V26a16 16 0 0 1 32 0v14"/>',
    "cap": '<path d="M50 14 6 38l44 24 44-24z"/><path d="M24 50v22c8 8 44 8 52 0V50M94 38v30"/>',
}
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sun", ("güneş", "gunes", "solar")),
    ("runner", ("koşu", "kosu", "maraton", "run ", "running", "marathon", "5k", "10k", "jog")),
    ("bike", ("bisiklet", "bike", "cycling", "pedal")),
    ("tooth", ("diş", "dis hekim", "dental", "dentist", "ortodonti")),
    ("rocket", ("girişim", "startup", "roket", "rocket", "lansman", "launch", "hackathon")),
    ("trophy", ("turnuva", "şampiyon", "sampiyon", "ödül", "odul", "kupa", "trophy", "tournament", "championship")),
    ("gamepad", ("oyun", "game", "gaming", "esports", "e-spor")),
    ("film", ("sinema", "film", "cinema", "movie", "belgesel")),
    ("mic", ("podcast", "mikrofon", "stand-up", "standup", "konuşma", "söyleşi", "soylesi")),
    ("cake", ("doğum günü", "dogum gunu", "pasta", "birthday", "bakery", "fırın", "firin", "pastane")),
    ("glass", ("bar ", "kokteyl", "cocktail", "şarap", "sarap", "wine", "pub", "içki")),
    ("tent", ("çadır", "cadir", "tent", "kamp", "camping")),
    ("flame", ("ateş", "ates", "yangın", "yangin", "bbq", "mangal", "ızgara", "izgara", "fire")),
    ("code", ("kodlama", "yazılım", "yazilim", "software", "developer", "programlama", "coding", "web ")),
    ("chart", ("finans", "borsa", "yatırım", "yatirim", "muhasebe", "finance", "invest", "analitik", "analytics")),
    ("bank", ("banka", "bank", "kredi", "sigorta", "insurance")),
    ("cart", ("mağaza", "magaza", "market", "alışveriş", "alisveris", "e-ticaret", "shop", "store")),
    ("bag", ("çanta", "canta", "butik", "boutique", "moda", "fashion", "bag")),
    ("ship", ("gemi", "liman", "denizcilik", "ship", "yacht", "yat ", "tekne", "boat")),
    ("globe", ("dünya", "dunya", "global", "uluslararası", "uluslararasi", "international", "world")),
    ("wrench", ("tamir", "tadilat", "servis", "usta", "repair", "plumbing", "tesisat")),
    ("gear", ("mühendislik", "muhendislik", "makine", "sanayi", "engineering", "machinery", "industrial")),
    ("bulb", ("fikir", "inovasyon", "yenilik", "idea", "innovation", "workshop", "atölye", "atolye")),
    ("drop", ("su ", "damla", "temizlik", "water", "cleaning", "hijyen")),
    ("cap", ("mezuniyet", "üniversite", "universite", "graduation", "university", "akademi", "academy")),
    ("cross", ("eczane", "pharmacy", "ilk yardım", "ilk yardim", "tıp", "tip ", "medical")),
    ("bolt", ("elektrik", "electric", "şarj", "sarj", "charging", "enerji", "energy")),
    ("cup", ("kafe", "kahve", "çay", "cay", "cafe", "coffee", "barista", "kafeterya")),
    ("waves", ("deniz", "dalga", "okyanus", "sahil", "plaj", "sea", "ocean", "wave", "balık", "balik")),
    ("mountain", ("dağ", "dag", "kamp", "trekking", "mountain", "doğa yürüyüşü")),
    ("tree", ("ağaç", "agac", "orman", "doğa", "doga", "çevre", "eko", "tree", "nature")),
    ("sun", ("güneş", "gunes", "yaz ", "sun", "enerji")),
    ("moon", ("gece", "ay ışığı", "night", "moon", "uyku")),
    ("house", ("ev ", "emlak", "konut", "kiralık", "satılık", "house", "real estate", "inşaat", "insaat")),
    ("book", ("kitap", "okul", "eğitim", "egitim", "kurs", "kütüphane", "book", "school", "education")),
    ("heart", ("sağlık", "saglik", "kalp", "hastane", "klinik", "sevgi", "heart", "health")),
    ("note", ("müzik", "muzik", "konser", "festival", "şarkı", "music", "concert")),
    ("car", ("araba", "otomotiv", "oto ", "galeri", "servis", "car", "auto")),
    ("plane", ("uçak", "ucak", "seyahat", "tatil", "turizm", "travel", "flight")),
    ("phone", ("telefon", "uygulama", "mobil", "app", "yazılım", "yazilim")),
    ("dumbbell", ("spor", "fitness", "gym", "antrenman", "halter")),
    ("fork", ("restoran", "yemek", "lokanta", "mutfak", "pizza", "burger", "restaurant", "food")),
    ("paw", ("veteriner", "hayvan", "kedi", "köpek", "kopek", "pet", "pati")),
    ("flower", ("çiçek", "cicek", "bahçe", "bahce", "florist", "flower", "düğün", "dugun")),
    ("laptop", ("bilgisayar", "teknoloji", "yazılım", "danışmanlık", "laptop", "tech", "ofis")),
    ("camera", ("fotoğraf", "fotograf", "kamera", "stüdyo", "studio", "photo")),
    ("shield", ("güvenlik", "guvenlik", "sigorta", "siber", "hukuk", "security", "avukat")),
    ("key", ("anahtar", "kilit", "çilingir", "cilingir", "key")),
    ("scissors", ("kuaför", "kuafor", "berber", "makas", "salon")),
)


def pick(prompt: str, limit: int = 2) -> list[str]:
    """Icon names for the subjects named in the request, most specific first; a star when nothing matches."""
    low = f" {prompt.lower()} "
    found = [name for name, words in _RULES if any(re.search(rf"(?<!\w){re.escape(w.strip())}", low) for w in words)]
    return (found or ["star"])[:limit]


def _draw(name: str, center: tuple[float, float], size: float, style: tuple[str, float]) -> str:
    (cx, cy), (color, width) = center, style
    scale = size / 100
    return (
        f'<g transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) scale({scale:.3f})" fill="none" stroke="{color}" '
        f'stroke-width="{width / scale:.2f}" stroke-linecap="round" stroke-linejoin="round">{_ICONS[name]}</g>'
    )


def emblem(prompt: str, cx: float, cy: float, pal: dict[str, str]) -> str:
    """SVG for the emblem area: a soft disc, the main icon large and an optional second icon smaller."""
    names = pick(prompt)
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="235" fill="{pal["primary"]}" opacity="0.10"/>',
        f'<circle cx="{cx}" cy="{cy}" r="190" fill="none" stroke="{pal["accent"]}" stroke-width="2" stroke-dasharray="3 10" opacity="0.55"/>',
        _draw(names[0], (cx, cy - (45 if len(names) > 1 else 0)), 230, (pal["primary"], 7)),
    ]
    if len(names) > 1:
        parts.append(_draw(names[1], (cx, cy + 118), 84, (pal["accent"], 5)))
    return "".join(parts)


def named_icon(prompt: str, size: float, color: str, width: float) -> tuple[str, str]:
    """(icon name, SVG centred on 0,0) for the subject of the request, or ("", "") when no subject is recognised."""
    name = pick(prompt, 1)[0]
    if name == "star":
        return "", ""
    return name, _draw(name, (0, 0), size, (color, width))
draw = _draw
