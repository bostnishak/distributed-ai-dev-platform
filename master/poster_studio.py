"""Poster text: only words the user actually wrote appear on the poster.

Headline, slogan, date, place and line-up are read from the request with patterns first and then (optionally) by the model; every
model-extracted value must literally occur in the request or it is dropped, so no event name, date, city or tag is ever invented.
Elements without text are left out and the layout closes up instead of showing filler. Layout lives in poster_layout.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_LLM = Callable[[str, str], Awaitable[dict[str, Any] | None]]
_SLOGAN_RE = re.compile(r"(?:slogan\w*|söz\w*|motto\w*|tagline)\s*[:=]?\s*[\"'“‘]([^\"'”’]{2,60})[\"'”’]", re.IGNORECASE)  # noqa: RUF001
_QUOTED_RE = re.compile(r"[\"'“‘]([^\"'”’]{2,40})[\"'”’]")  # noqa: RUF001
_MONTHS_TR = "ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık"
_MONTHS_EN = "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
_DATE_RES = (
    re.compile(rf"\b\d{{1,2}}\s*(?:{_MONTHS_TR})(?:\s*\d{{4}})?", re.IGNORECASE),
    re.compile(rf"\b(?:{_MONTHS_EN})\.?\s+\d{{1,2}}(?:,?\s*\d{{4}})?", re.IGNORECASE),
    re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"),
)
_CITIES = (
    "Adana Adıyaman Afyonkarahisar Ağrı Amasya Ankara Antalya Artvin Aydın Balıkesir Bilecik Bingöl Bitlis Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli Diyarbakır Edirne "
    "Elazığ Erzincan Erzurum Eskişehir Gaziantep Giresun Gümüşhane Hakkari Hatay Isparta Mersin İstanbul İzmir Kars Kastamonu Kayseri Kırklareli Kırşehir Kocaeli Konya Kütahya "
    "Malatya Manisa Kahramanmaraş Mardin Muğla Muş Nevşehir Niğde Ordu Rize Sakarya Samsun Siirt Sinop Sivas Tekirdağ Tokat Trabzon Tunceli Şanlıurfa Uşak Van Yozgat Zonguldak "
    "Aksaray Bayburt Karaman Kırıkkale Batman Şırnak Bartın Ardahan Iğdır Yalova Karabük Kilis Osmaniye Düzce Bodrum Alanya Fethiye Çeşme Marmaris London Paris Berlin Istanbul Izmir"
).split()
_CITY_RE = re.compile(r"(?<!\w)(" + "|".join(sorted(map(re.escape, _CITIES), key=len, reverse=True)) + r")(?:'?(?:da|de|ta|te|dan|den))?(?!\w)((?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşü]+){0,2})", re.IGNORECASE)
_LINEUP_RE = re.compile(r"(?:sanatçılar|sanatçı|konuklar|konuşmacılar|katılımcılar|menü|program|artists|guests|speakers|lineup|line-up)\s*[:\-]\s*([^.;\n\"'“‘]{3,80})", re.IGNORECASE)  # noqa: RUF001
_EN_RE = re.compile(r"\b(poster|for|the|with|slogan|palette|festival|party|race|charity|night)\b", re.IGNORECASE)
_TR_CHARS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_EXTRACT_SYSTEM = (
    "Extract ONLY text that is explicitly written in the user's poster request. Return JSON: "
    '{"title":"","slogan":"","kicker":"","date":"","location":"","tags":[]}. Copy words exactly as the user wrote them. '
    "Leave a field empty when the user did not give it; never invent a title, date, city, slogan or tag. "
    "title may be a short headline (max 4 words) naming what the poster is about."
)
_LIMITS = {"title": 34, "slogan": 56, "kicker": 28, "date": 24, "location": 30}
_TITLE_NOISE = re.compile(r"\b(bir|için|afiş\w*|poster\w*|yap\w*|hazırla\w*|tasarla\w*|üret\w*|olsun|renk\w*|siyah|beyaz|minimal)\b", re.IGNORECASE)


def is_turkish(prompt: str) -> bool:
    """Turkish unless the request is clearly English: the upper-case rule (i -> İ) must only be applied to Turkish text."""
    return bool(_TR_CHARS.search(prompt)) or not _EN_RE.search(prompt)


def tr_upper(text: str) -> str:
    """Turkish-aware upper case: i -> İ and ı -> I (str.upper turns 'lezzetli' into 'LEZZETLI')."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def _in_request(value: str, prompt: str) -> bool:
    norm = lambda s: re.sub(r"\W+", " ", tr_upper(s)).strip()  # noqa: E731
    return bool(norm(value)) and norm(value) in norm(prompt)


def pattern_fields(prompt: str) -> dict[str, Any]:
    """Date, place and line-up that literally occur in the request (found by patterns, no model involved)."""
    out: dict[str, Any] = {"date": "", "location": "", "tags": []}
    for rx in _DATE_RES:
        if m := rx.search(prompt):
            out["date"] = m.group(0).strip()
            break
    if m := _CITY_RE.search(prompt):
        out["location"] = (m.group(1) + m.group(2)).strip()
    if m := _LINEUP_RE.search(prompt):
        items = m.group(1).split(",") if "," in m.group(1) else re.split(r"\s+(?:ve|and|&)\s+", m.group(1))  # "Mor ve Ötesi" stays one name when commas separate the list
        out["tags"] = [t.strip() for t in items if 2 <= len(t.strip()) <= 22][:3]
    return out


def _guess_title(prompt: str) -> str:
    """The longest run of capitalised words that is not the first word of the sentence, else the request without filler words."""
    runs = [m.group(0).strip() for m in re.finditer(r"(?:[A-ZÇĞİÖŞÜ][\wçğıöşü'’]+\s+){0,3}[A-ZÇĞİÖŞÜ][\wçğıöşü'’]+", prompt) if m.start() > 0]  # noqa: RUF001
    best = max(runs, key=lambda r: (len(r.split()), len(r)), default="")
    return best or _TITLE_NOISE.sub(" ", prompt).strip()


async def build_spec(prompt: str, palette: str, llm: _LLM, model: str) -> dict[str, Any]:
    turkish = is_turkish(prompt)
    spec: dict[str, Any] = {"subject": prompt, "title": "", "slogan": "", "kicker": "", "date": "", "location": "", "tags": [], "palette": palette, "model": model, "turkish": turkish}
    if m := _SLOGAN_RE.search(prompt):
        spec["slogan"] = m.group(1).strip()
    quoted = [q.strip() for q in _QUOTED_RE.findall(prompt) if q.strip() != spec["slogan"]]
    if quoted:
        spec["title"] = quoted[0]
    found = pattern_fields(prompt)
    spec.update({k: v for k, v in found.items() if v})
    parsed = await llm(_EXTRACT_SYSTEM, prompt) or {}
    for key in ("title", "slogan", "kicker", "date", "location"):
        val = str(parsed.get(key) or "").strip()
        if val and not spec[key] and (key == "title" or _in_request(val, prompt)):
            spec[key] = val
    if not spec["tags"]:
        spec["tags"] = [str(t).strip() for t in parsed.get("tags") or [] if str(t).strip() and _in_request(str(t), prompt)][:3]
    up = tr_upper if turkish else str.upper
    for key, limit in _LIMITS.items():
        spec[key] = up(spec[key])[:limit] if key != "slogan" else spec[key][:limit]
    spec["tags"] = [up(t)[:18] for t in spec["tags"]]
    if not spec["title"]:
        spec["title"] = up(_guess_title(prompt))[:_LIMITS["title"]]
    return spec
