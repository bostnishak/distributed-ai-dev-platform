"""Ask instead of guessing: open-ended or ambiguous requests get a short clarifying question, not an invented answer.

The check is deliberately conservative. It only fires when the request names something to create but gives no
specifics ("bir logo yap", "web sitesi yap"), or points at something that does not exist yet ("bunu düzelt" in a new chat).
A prompt that carries concrete details, an attached file or an earlier conversation goes straight through.
"""

from __future__ import annotations

import json
import re

CLARIFY_MARKER = "Doğru anlamam için birkaç şeyi netleştireyim"

_CREATE_VERB_RE = re.compile(
    r"\b(yap\w*|oluştur\w*|olustur\w*|hazırla\w*|hazirla\w*|yaz\w*|tasarla\w*|üret\w*|uret\w*|çiz\w*|ciz\w*|geliştir\w*|gelistir\w*|kur\w*|ver\w*|istiyorum|lazım|lazim)\b",
    re.IGNORECASE,
)
_DEICTIC_RE = re.compile(
    r"^\s*(bunu|bunları|bunlari|şunu|sunu|onu|bu|şu|o)\b.*\b(düzelt|duzelt|çevir|cevir|özetle|ozetle|değiştir|degistir|geliştir|gelistir|iyileştir|iyilestir|yeniden yaz|incele|kontrol et|aç|ac)\w*",
    re.IGNORECASE,
)

_PRONOUN_START_RE = re.compile(r"^\s*(?:peki\s+)?(?:ya\s+)?(?:onun|bunun|şunun|onlar\w*|bunlar\w*|şunlar\w*|o\s+da|bu\s+da)\b", re.IGNORECASE)
_CONTINUATION_RE = re.compile(r"\b(bunu|şunu|sunu|onu|aynı|ayni|devam|daha|tekrar|yeniden|başka|baska|farklı|farkli|bi de|bir de|ekle\w*|değiştir\w*|degistir\w*|çevir\w*|cevir\w*|düzelt\w*|duzelt\w*)\b", re.IGNORECASE)

# (object pattern, what the assistant needs to know)
_TOPICS: tuple[tuple[re.Pattern[str], str, tuple[str, ...]], ...] = (
    (
        re.compile(r"\b(logo\w*|poster\w*|afiş\w*|afis\w*|banner\w*|görsel\w*|gorsel\w*|resim\w*|fotoğraf\w*|fotograf\w*|illüstrasyon\w*|amblem\w*)\b", re.IGNORECASE),
        "görsel",
        ("Ne için? a) marka/logo b) etkinlik afişi c) sosyal medya görseli d) başka (yaz) — adını ya da üzerindeki yazıyı da ekle", "Stil? a) sade/minimal b) kurumsal c) canlı/çizgi d) gerçekçi"),
    ),
    (
        re.compile(r"\b(web\s*sitesi\w*|site\w*|uygulama\w*|oyun\w*|program\w*|sayfa\w*|bot\w*)\b", re.IGNORECASE),
        "yazılım",
        ("Ne işe yarayacak? a) bir şeyi kaydedip listelemek b) tanıtım sayfası c) oyun/araç d) başka (yaz)", "Veriler nerede dursun? a) yalnız bu tarayıcıda b) sunucuda veritabanında c) veri yok"),
    ),
    (
        re.compile(r"\b(rapor\w*|sunum\w*|doküman\w*|dokuman\w*|belge\w*|makale\w*|ödev\w*|odev\w*|mektup\w*|özgeçmiş\w*|ozgecmis\w*|cv\b|yazı\w*|metin\w*|özet\w*|ozet\w*|excel\w*|tablo\w*)\b", re.IGNORECASE),
        "belge",
        ("Konusu ne ve kim okuyacak? a) yönetici b) müşteri c) hoca/öğrenci d) ekip — konuyu yaz", "Biçim? a) 1 sayfa b) 3-5 sayfa c) sunum d) tablo"),
    ),
    (
        re.compile(r"\b(kod\w*|script\w*|fonksiyon\w*|algoritma\w*|sınıf\w*|sinif\w*|sorgu\w*)\b", re.IGNORECASE),
        "kod",
        ("Ne yapmalı? Girdiyi ve beklenen çıktıyı bir örnekle yaz", "Dil? a) Python b) JavaScript c) SQL d) başka (yaz)"),
    ),
)

# words that carry no content for the purpose of deciding whether the request is specific
_FILLER = frozenset(
    "bana bir bi şu bu o ve ile için icin de da mı mi mu mü lütfen lutfen biraz hızlıca hizlica güzel guzel iyi bir tane benim bize biz sen şey sey olsun olur web mobil basit".split()
)


def _history_items(history: str) -> list[dict]:
    try:
        items = json.loads(history) if history else []
    except ValueError:
        return []
    return [i for i in items if isinstance(i, dict) and i.get("text")] if isinstance(items, list) else []


def _content_words(prompt: str, topic_re: re.Pattern[str]) -> list[str]:
    words = re.findall(r"[\wçğıöşüÇĞİÖŞÜ-]+", prompt.lower())
    return [w for w in words if w not in _FILLER and not _CREATE_VERB_RE.fullmatch(w) and not topic_re.fullmatch(w)]


def _format_question(kind: str, questions: tuple[str, ...]) -> str:
    bullets = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))
    return f"{CLARIFY_MARKER} ({kind} isteği), sonra hemen başlarım:\n\n{bullets}\n\nİstersen bunların bir kısmını yanıtla, kalanını ben makul varsayımlarla yaparım ve neyi varsaydığımı yazarım."


def clarifying_question(prompt: str, history: str = "", has_file: bool = False) -> str | None:
    """Return a clarifying question when the request is too open-ended to answer faithfully, else None."""
    text = (prompt or "").strip()
    if not text or has_file or len(text) > 140 or "\n" in text:
        return None
    items = _history_items(history)
    if items and CLARIFY_MARKER in str(items[-1].get("text", "")):
        return None  # the user is answering our question: go ahead
    inline_content = bool(re.search(r"[:\"'“\u2018«]\s*\S.{12,}", text))  # the text to work on is inside the message itself
    if not items and not inline_content and (_DEICTIC_RE.search(text) or _PRONOUN_START_RE.search(text)):
        return "Neyi kastettiğini anlayamadım: \"bunu/şunu\" dediğin metin, dosya ya da konu bu sohbette yok. Üzerinde çalışmamı istediğin içeriği yapıştırır mısın ya da dosyayı yükler misin?"
    if not _CREATE_VERB_RE.search(text) or (items and _CONTINUATION_RE.search(text)):
        return None  # not a creation request, or a follow-up that leans on the conversation so far
    for topic_re, kind, questions in _TOPICS:
        if not topic_re.search(text):
            continue
        extra = _content_words(text, topic_re)
        if len(extra) == 0 or (len(extra) == 1 and len(text.split()) <= 4):
            return _format_question(kind, questions)
        return None
    return None
