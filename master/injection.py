"""Prompt-injection detector for text that arrives as data: documents, web pages and tool output (SEC-09).

Rule-based and weighted. One signal alone is rarely proof; a text is flagged when the weights add up to
THRESHOLD or when a single strong signal is present. Turkish and English phrasings are covered.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

THRESHOLD = 3

_I = re.IGNORECASE

# Verbs that cancel earlier instructions, followed within a few words by what is being cancelled.
_CANCEL_VERB = r"(?:ignore|disregard|forget|override|bypass|ignora|unut\w*|yok\s+say\w*|geçersiz\s+(?:say|kıl)\w*|devre\s+dışı\s+bırak\w*)"
_CANCEL_OBJECT = (
    r"(?:previous|prior|above|earlier|safety|security|the\s+user|everything\s+you|"
    r"instructions?|rules?|guidelines?|polic(?:y|ies)|guardrails?|approval\s+gate|"
    r"önceki|yukarıdaki|güvenlik|kuralları|talimat\w*|instrucciones|anteriores)"
)

_STRONG: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\b{_CANCEL_VERB}\b(?:\W+\w+){{0,4}}?\W+{_CANCEL_OBJECT}", _I),
    re.compile(rf"\b{_CANCEL_OBJECT}\b(?:\W+\w+){{0,3}}?\W+{_CANCEL_VERB}", _I),
    re.compile(r"<\s*script\b|javascript\s*:|\bonerror\s*=", _I),
    re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash)\b|\brm\s+-rf\b", _I),
    re.compile(r"\[\s*/?\s*(?:INST|SYSTEM)\s*\]|#{2,}\s*SYSTEM\s+OVERRIDE|\bdeveloper\s+mode\b|\bjailbreak\b", _I),
    re.compile(r"\bDAN\b"),
    re.compile(r"\byou\s+are\s+no\s+longer\s+bound\b|\bno\s+restrictions\b|\bunrestricted\s+assistant\b", _I),
    re.compile(r"\b(?:do\s+not|don'?t)\s+follow\s+the\s+user", _I),
    re.compile(r"\b(?:new|yeni)\s+(?:system\s+|sistem\s+)?(?:instructions?|talimat\w*)\s*(?:from|:)", _I),
    re.compile(r"\bbypass\s+the\s+content\s+policy|\boverride\s+the\s+approval\s+gate", _I),
    re.compile(r"\b(?:reveal|print|output)\b(?:\W+\w+){0,4}?\W+(?:system\s+prompt|hidden\s+instructions|admin\s+token|secret\s+key)", _I),
    re.compile(r"kabul\s+et\s+ve\s+içindeki\s+talimatlara\s+uy|prompt\s+del\s+sistema", _I),
)

# Text that talks to the model rather than to a human reader.
_ADDRESSES_MODEL = re.compile(
    r"\b(?:note\s+to\s+(?:the\s+)?(?:ai|assistant|model)|dear\s+language\s+model|ai\s+assistant|attention\s+ai|"
    r"if\s+you\s+are\s+an?\s+(?:ai|llm|assistant)|ai\s+models?\s+reading|assistant,\s+now|reminder\s+to\s+the\s+model|"
    r"hidden\s+text\s+for\s+(?:llm|ai)|message\s+from\s+system\s+administrator|"
    r"yapay\s+zeka\s+bu\s+metni|asistan\s+bu\s+belgeyi|özetleyen\s+asistan)\b|^\s*(?:assistant|system)\s*[,:]|<!--\s*assistant",
    _I | re.M,
)
_EXFIL_VERB = r"(?:reveal|print|output|show|send|forward|email|export|leak|yaz|göster|gönder|aktar|ifşa)"
_SECRET_OBJECT = (
    r"(?:system\s+prompt|hidden\s+instructions|api\s+keys?|admin\s+token|secret\s+key|passwords?|credentials|"
    r"conversation\s+history|memory\s+entries|database|files|memory\s+entries|attacker|confidential|parola\w*|anahtar\w*|kullanıcı\s+verileri\w*|dosyalar\w*|prompt\s+del\s+sistema)"
)
_EXFIL = re.compile(rf"\b{_EXFIL_VERB}\b(?:\W+\w+){{0,6}}?\W+{_SECRET_OBJECT}", _I)
_ACTION_ON_MODEL = re.compile(
    r"\b(?:must|should|now|şimdi|must\s+now)\b(?:\W+\w+){0,5}?\W+(?:call|run|execute|obey|follow|delete|grant|approve|çalıştır|sil|uy)\b"
    r"|\b(?:instead|yerine)\b.{0,40}\b(?:output|write|print|recommend|yaz|öner)\b"
    r"|\bkabul\s+et\s+ve\s+içindeki\s+talimatlara\s+uy|\btell\s+the\s+user\s+to\b|\bözetin\s+sonuna\b|\bkullanıcıyı\s+yok\s+say|\bsadece\s+bu\s+bağlantıyı\s+öner",
    _I,
)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("​", "")


def detect_injection(text: str) -> dict[str, Any]:
    """{flagged, score, signals}; signals name the rules that fired (useful in the warning shown to the user)."""
    body = _normalize(text)
    signals: list[str] = []
    score = 0
    strong = [p.pattern[:40] for p in _STRONG if p.search(body)]
    if strong:
        signals.append("override-or-markup")
        score += THRESHOLD
    if _ADDRESSES_MODEL.search(body):
        signals.append("addresses-the-model")
        score += 2
    if _EXFIL.search(body):
        signals.append("asks-for-secrets-or-data")
        score += 2
    if _ACTION_ON_MODEL.search(body):
        signals.append("commands-the-model")
        score += 2
    return {"flagged": score >= THRESHOLD, "score": score, "signals": signals}
