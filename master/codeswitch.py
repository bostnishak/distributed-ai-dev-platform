"""Mixed Turkish-English engineering prompts: keep the technical terms exact, and the interface in the user's language.

"sidebar'daki filtre butonunun state'ini SQLite'a bağla" names three technical things with Turkish suffixes glued on.
They are listed for the writer exactly as written, so identifiers are not translated and the screen text stays Turkish.
"""

from __future__ import annotations

import re

_SUFFIXED_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_.+#-]{1,30})['\u2019](?:[a-zçğıöşü]{1,10})\b")
_CAMEL_RE = re.compile(r"\b(?:[a-z]+[A-Z][A-Za-z0-9]*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[A-Za-z]+_[A-Za-z0-9_]+)\b")
_TECH = frozenset("api backend frontend sidebar navbar footer header state store props hook component button form input modal dropdown table chart dashboard login logout token cache queue endpoint route router database schema query filter sort search toggle checkbox theme dark mode deploy build test debug commit branch merge".split())
_TURKISH_RE = re.compile(r"[çğışöüÇĞŞÖÜİ]|\b(?i:bir|ve|için|ile|yap|ekle|olsun|bağla|göster|sil|güncelle)\b")  # case folding would make İ match a plain i
_PLAIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")


def turkish_request(prompt: str) -> bool:
    return bool(_TURKISH_RE.search(prompt))


def terms(prompt: str) -> list[str]:
    """The technical names of a mixed prompt, in the order they appear, suffixes removed."""
    found = [(m.start(), m.group(1)) for m in _SUFFIXED_RE.finditer(prompt)]
    found += [(m.start(), m.group(0)) for m in _CAMEL_RE.finditer(prompt)]
    found += [(m.start(), m.group(0)) for m in _PLAIN_WORD_RE.finditer(prompt) if m.group(0).lower() in _TECH]
    ordered: dict[str, str] = {}
    for _position, term in sorted(found):
        ordered.setdefault(term.lower(), term)
    return list(ordered.values())[:15]


def note(prompt: str) -> str:
    """The block added to the writer's request; "" unless the prompt mixes Turkish with technical English."""
    named = terms(prompt)
    if not named or not turkish_request(prompt):
        return ""
    return (f"\n\nDİL KURALI: istek Türkçe-İngilizce karışık. Şu teknik adları aynen anla ve kodda İngilizce kullan: {', '.join(named)}. "
            "Değişken, fonksiyon, API yolu ve veritabanı adları İngilizce; ekranda görünen TÜM yazılar doğal Türkçe. "
            "Sıralama ve büyük/küçük harf işlemlerinde toLocaleLowerCase('tr') ve localeCompare(x, 'tr') kullan.")
