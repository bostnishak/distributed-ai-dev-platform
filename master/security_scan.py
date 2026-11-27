"""Deterministic security scan of generated source: hard-coded secrets and the common unsafe patterns (no model)."""

from __future__ import annotations

import re
from pathlib import Path

_EXTS = (".py", ".js", ".ts", ".html", ".json", ".env", ".yml", ".yaml")
_SECRET_RULES = (
    ("gizli anahtar", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})")),
    ("özel anahtar", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("koda gömülü parola/anahtar", re.compile(r"""(?i)\b(?:password|passwd|secret_key|api_key|apikey|jwt_secret|access_token)\b\s*[:=]\s*["'](?!change|your|<|example|test|dummy)[^"'\s]{8,}["']""")),
)
_UNSAFE_RULES = (
    ("eval kullanımı (kod enjeksiyonu riski)", re.compile(r"(?<![\w.])eval\s*\(")),
    ("innerHTML'e değişken yazılıyor (XSS riski)", re.compile(r"\.innerHTML\s*\+?=\s*(?:[A-Za-z_$][\w$.]*\s*(?:\+|;|$)|[^;]*\+\s*[A-Za-z_$])")),
    ("SQL metni birleştiriliyor (SQL enjeksiyonu riski)", re.compile(r"""execute\w*\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format))""")),
    ("kabuk komutu metin birleştirilerek kuruluyor (komut enjeksiyonu riski)", re.compile(r"""(?:os\.system|os\.popen)\s*\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format))|shell\s*=\s*True""")),
    ("CORS her kaynağa açık", re.compile(r"""allow_origins\s*=\s*\[\s*["']\*["']""")),
)


def _sources(ws_dir: Path):
    for path in ws_dir.rglob("*"):
        parts = path.relative_to(ws_dir).parts
        if path.is_file() and path.suffix in _EXTS and not any(p.startswith(".") or p == "node_modules" for p in parts[:-1]):
            yield path


def scan(ws_dir: Path) -> list[dict[str, object]]:
    """Findings as {file, line, rule, secret}."""
    found: list[dict[str, object]] = []
    for path in _sources(ws_dir):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            for rules, secret in ((_SECRET_RULES, True), (_UNSAFE_RULES, False)):
                found += [{"file": path.relative_to(ws_dir).as_posix(), "line": number, "rule": name, "secret": secret} for name, rx in rules if rx.search(line)]
    return found


def report(ws_dir: Path, limit: int = 4) -> str:
    """One warning line for the chat, or an empty string when nothing was found."""
    found = sorted(scan(ws_dir), key=lambda f: not f["secret"])
    listed = "; ".join(f"{f['rule']} ({f['file']}:{f['line']})" for f in found[:limit])
    return f"Güvenlik taraması {len(found)} bulgu: {listed}" if found else ""


def redact(text: str) -> str:
    """The text with anything that looks like a secret removed (used before a run is stored)."""
    for _name, rx in _SECRET_RULES:
        text = rx.sub("[GİZLİ]", text)
    return text
