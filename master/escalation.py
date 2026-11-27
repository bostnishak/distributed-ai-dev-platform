"""Prepare a problem for an outside expert or a stronger model without giving away who or what it is about.

Nothing is ever sent from here: secrets, e-mail addresses, phone numbers, paths, addresses and the project's own
identifiers are replaced by neutral names, and the result is shown to the user to copy if they choose.
"""

from __future__ import annotations

import re

import security_scan

_TRIGGER_RE = re.compile(r"^\s*(?:buluta\s+hazırla|anonimleştir|anonymi[sz]e)\s*:\s*(?P<body>.+)$", re.IGNORECASE | re.DOTALL)
_RULES = (
    ("E-POSTA", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("ADRES", re.compile(r"\bhttps?://[^\s)\"']+")),
    ("YOL", re.compile(r"(?:[A-Za-z]:\\[^\s\"']+|(?<![\w.])/(?:home|Users|var|etc|srv)/[^\s\"']+)")),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("KİMLİK-NO", re.compile(r"\b[1-9]\d{10}\b")),
    ("TELEFON", re.compile(r"(?<!\w)(?:\+90|0)\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b")),
)
_IDENTIFIER_RE = re.compile(r"\b(?:[A-Z][a-z0-9]+){2,}\b|\b[a-z]+(?:_[a-z0-9]+)+\b")
_COMMON = {"__init__", "get_json", "set_up", "to_string", "read_text", "write_text", "is_file", "is_dir", "TypeError", "ValueError", "KeyError",
           "RuntimeError", "AttributeError", "ImportError", "IndexError", "OSError", "JavaScript", "TypeScript", "FastAPI", "PostgreSQL"}


def anonymize(text: str) -> tuple[str, dict[str, str]]:
    """(text safe to share, {placeholder: original}). Code names keep their kind: classes ClassA, functions name_a."""
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}

    def swap(original: str, placeholder: str) -> str:
        if original not in reverse:
            reverse[original] = placeholder.format(n=len(reverse) + 1)
            mapping[reverse[original]] = original
        return reverse[original]

    out = security_scan.redact(text)
    for label, pattern in _RULES:
        out = pattern.sub(lambda m, label=label: swap(m.group(0), f"<{label}-{{n}}>"), out)
    out = _IDENTIFIER_RE.sub(lambda m: m.group(0) if m.group(0) in _COMMON else swap(m.group(0), "Class{n}" if m.group(0)[0].isupper() else "name_{n}"), out)
    return out, mapping


def answer(prompt: str) -> str:
    match = _TRIGGER_RE.match(prompt)
    if not match:
        return ""
    safe, mapping = anonymize(match["body"].strip())
    table = "\n".join(f"- `{placeholder}` = {original}" for placeholder, original in list(mapping.items())[:20])
    return (f"Hiçbir yere gönderilmedi. Paylaşmak istersen aşağıdaki anonim metni kopyala:\n\n```\n{safe}\n```\n\n"
            f"Eşleştirme (yalnız sende kalsın):\n{table or '- değiştirilecek bir şey bulunmadı'}\n\n"
            "Kendi yazdığın kişi ve şirket adları gibi düz sözcükleri tanıyamam; paylaşmadan önce metni bir kez oku.")
