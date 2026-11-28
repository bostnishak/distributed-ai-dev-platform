"""Personal data is removed before anything leaves the machine: e-mail, phone, Turkish ID, IBAN, card and IP address.

Identity numbers and cards are only treated as such when their check digits are right, so ordinary long numbers in
code stay. Names of people cannot be recognised reliably by rules and are not claimed to be removed.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_IBAN_RE = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<![\w.])(?:\+90[\s-]?|0)5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?![\w.])")
_TCKN_RE = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_IP_RE = re.compile(r"(?<![\d.])(?!127\.|0\.0\.0\.0)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
_USER_PATH_RE = re.compile(r"((?:[A-Za-z]:\\Users\\|/home/|/Users/))([^\\/\s\"']+)")


def _tckn(match: re.Match) -> str:
    digits = [int(c) for c in match.group(0)]
    tenth = (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10
    return "[KİMLİK-NO]" if digits[9] == tenth and digits[10] == sum(digits[:10]) % 10 else match.group(0)


def _card(match: re.Match) -> str:
    digits = [int(c) for c in match.group(0) if c.isdigit()]
    total = sum(d if i % 2 == 0 else sum(divmod(d * 2, 10)) for i, d in enumerate(reversed(digits)))
    return "[KART-NO]" if 13 <= len(digits) <= 19 and total % 10 == 0 and len(set(digits)) > 1 else match.group(0)


def scrub(text: str) -> str:
    text = _EMAIL_RE.sub("[E-POSTA]", text)
    text = _IBAN_RE.sub("[IBAN]", text)
    text = _PHONE_RE.sub("[TELEFON]", text)
    text = _TCKN_RE.sub(_tckn, text)
    text = _CARD_RE.sub(_card, text)
    text = _IP_RE.sub("[IP]", text)
    return _USER_PATH_RE.sub(r"\1[KULLANICI]", text)
