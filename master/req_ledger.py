"""The atomic requirement ledger: every thing a request asks for, numbered REQ-001.. and bound to a machine check.

A small model drops constraints when it gets fifteen at once, so each one is tracked on its own: it names the slice that
should build it and the check (source text, rendered page, real click) that decides it. What no check can decide stays
"elle" and is never counted as met.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from typing import Any

LAYOUT, DATA, CONTROLS = "yerleşim ve görünüm", "veri ve durum", "etkileşim ve uç durumlar"
SLICES = (LAYOUT, DATA, CONTROLS)
_EMPTY_RE = re.compile(r"boş\s+(?:girdi|giriş|metin|kayıt|ekleme|alan|bırak|ise|olunca|gönder)|empty\s+(?:input|value|submit)", re.IGNORECASE)
_RESPONSIVE_RE = re.compile(r"responsive|mobil|küçük ekran|dar ekran|telefon", re.IGNORECASE)
_EXTERNAL_RE = re.compile(r"harici|dış|cdn|external|kütüphane|library", re.IGNORECASE)
_DIALOG_RE = re.compile(r"alert|confirm|prompt|açılır pencere|popup", re.IGNORECASE)
ACTIVE: ContextVar[tuple[Req, ...]] = ContextVar("requirement_ledger", default=())


@dataclass(frozen=True)
class Req:
    id: str
    slice: str
    kind: str
    text: str
    target: str = ""

    def line(self) -> str:
        return f"{self.id} [{self.kind}] {self.text}"


def _look(contract: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    rows = [(LAYOUT, "renk", f"{c} rengi aynen kullanılacak", c) for c in contract.get("colors") or []]
    rows += [(LAYOUT, "ölçü", f"{s} ölçüsü CSS'te aynen geçecek", s) for s in contract.get("sizes") or []]
    rows += [(LAYOUT, "bölge", f"'{r}' bölgesi ekranda ayrı bir alan olacak", r) for r in contract.get("regions") or []]
    buttons = {b["label"].casefold() for b in contract.get("buttons") or []}
    rows += [(LAYOUT, "yazı", f"'{t}' yazısı ekranda aynen görünecek", t) for t in contract.get("labels") or [] if t.casefold() not in buttons]
    return rows


def _forbidden(item: str) -> tuple[str, str, str, str]:
    kind = "dış kaynak yok" if _EXTERNAL_RE.search(item) else "açılır pencere yok" if _DIALOG_RE.search(item) else "elle"
    return (CONTROLS, kind, f"yasak: {item}", item)


def build(contract: dict[str, Any], request: str) -> tuple[Req, ...]:
    """The numbered ledger of one request; the same input always gives the same numbers."""
    rows = _look(contract)
    if _RESPONSIVE_RE.search(request):
        rows.append((LAYOUT, "dar ekran", "375 piksel genişlikte yatay taşma olmayacak (@media)", ""))
    if contract.get("persistence"):
        rows.append((DATA, "kalıcılık", f"sayfa yenilenince eklenen kayıt duracak ({contract['persistence']})", ""))
    rows += [(CONTROLS, "düğme", f"'{b['label']}' düğmesi: {b['behavior']}", b["label"]) for b in contract.get("buttons") or []]
    if _EMPTY_RE.search(request):
        rows.append((CONTROLS, "boş girdi", "boş girdiyle kayıt eklenmeyecek", ""))
    rows += [(CONTROLS, "uç nokta", f"{e['method']} {e['path']} tanımlı olacak", f"{e['method']} {e['path']}") for e in contract.get("endpoints") or []]
    rows += [_forbidden(item) for item in contract.get("forbidden") or []]
    return tuple(Req(f"REQ-{number:03d}", *row) for number, row in enumerate(rows, 1))


def upto(ledger: tuple[Req, ...], stage: str) -> tuple[Req, ...]:
    """The requirements of this slice and of every earlier one."""
    wanted = SLICES[: SLICES.index(stage) + 1]
    return tuple(r for r in ledger if r.slice in wanted)


def listing(ledger: tuple[Req, ...]) -> str:
    return "\n".join(r.line() for r in ledger)


def as_dicts(ledger: tuple[Req, ...]) -> list[dict[str, str]]:
    return [asdict(r) for r in ledger]
