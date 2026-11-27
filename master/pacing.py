"""Matching the reader and the clock: how to explain, and when to say that something is taking longer than usual."""

from __future__ import annotations

import re

import complexity_governor

_SIMPLE_RE = re.compile(r"\b(?:basitçe|basit\s+anlat|çocuğa\s+anlatır|yeni\s+başl\w+|hiç\s+bilmiyorum|anlamıyorum|eli5|in simple terms|beginner)\b", re.IGNORECASE)
_EXPERT_RE = re.compile(r"\b(?:uzman\w*\s+için|ileri\s+düzey|teknik\s+detay\w*|derinlemesine\s+teknik|for\s+experts?|advanced)\b", re.IGNORECASE)
_URGENT_RE = re.compile(r"\b(?:acil|hemen|kısaca|tek\s+cümle\w*|quickly|urgent|tl;?dr)\b", re.IGNORECASE)
_BUDGET_S = {0: 45, 1: 90, 2: 360, 3: 720, 4: 1500}


def audience_note(prompt: str) -> str:
    """A system line about how to answer, only when the message itself says who is asking or how fast."""
    notes = []
    if _SIMPLE_RE.search(prompt):
        notes.append("Okuyan konuya yeni: terimleri günlük dille açıkla, bir somut örnek ver, formülü ancak gerekliyse göster.")
    elif _EXPERT_RE.search(prompt):
        notes.append("Okuyan uzman: temel tanımları atla, doğrudan teknik ayrıntı, sınır durumları ve ödünleşimleri ver.")
    if _URGENT_RE.search(prompt):
        notes.append("Kullanıcının acelesi var: önce sonucu tek cümleyle ver, ayrıntı en fazla üç madde olsun.")
    return " ".join(notes)


def budget_seconds(request: str) -> int:
    return _BUDGET_S[complexity_governor.classify(request).level]


def overrun_note(request: str, elapsed: float) -> str:
    """One status line once a build passes its soft time budget ('' before that)."""
    budget = budget_seconds(request)
    if elapsed <= budget:
        return ""
    return (f"Bu iş beklenen süreyi ({round(budget / 60)} dk) aştı. Beklemek istemezsen durdurabilirsin; yazılan dosyalar korunur ve 'devam et' ile "
            "kaldığı yerden sürer.")
