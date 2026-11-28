"""One immutable spec.json per project; every writer gets a pointer to it and the exact REQ ids that are its job.

No agent summarises the user's wishes for the next one. The spec is written once into the oracle folder (builders may
not touch it), carries its own hash, and a changed file is refused instead of followed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import req_ledger

SPEC = ".ai-os/oracles/spec.json"
_BY_SUFFIX = {
    ".html": ("renk", "ölçü", "bölge", "yazı", "dar ekran", "düğme", "kalıcılık", "boş girdi", "dış kaynak yok", "açılır pencere yok", "elle"),
    ".css": ("renk", "ölçü", "bölge", "dar ekran", "dış kaynak yok"),
    ".js": ("yazı", "düğme", "kalıcılık", "boş girdi", "dış kaynak yok", "açılır pencere yok", "elle"),
    ".ts": ("yazı", "düğme", "kalıcılık", "boş girdi", "elle"),
    ".py": ("uç nokta", "kalıcılık", "boş girdi", "elle"),
}


def _digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def freeze(ws_dir: Path, request: str, ledger: tuple[req_ledger.Req, ...]) -> str:
    """Writes the spec if the project has none yet; returns the hash of the spec that is in force."""
    target = ws_dir / SPEC
    if target.exists():
        return load(ws_dir)["sha256"]
    body = {"request": request, "requirements": req_ledger.as_dicts(ledger)}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({**body, "sha256": _digest(body)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return _digest(body)


def load(ws_dir: Path) -> dict[str, Any]:
    """The spec of the project; ValueError when it was changed after it was frozen."""
    data = json.loads((ws_dir / SPEC).read_text(encoding="utf-8"))
    body = {"request": data.get("request"), "requirements": data.get("requirements")}
    if _digest(body) != data.get("sha256"):
        raise ValueError("spec.json sonradan değiştirilmiş; sözleşme geçersiz")
    return data


def subset(ledger: tuple[req_ledger.Req, ...], path: str) -> tuple[req_ledger.Req, ...]:
    """The requirements a file of this kind has to carry."""
    kinds = _BY_SUFFIX.get(Path(path).suffix.lower(), ())
    return tuple(r for r in ledger if r.kind in kinds)


def pointer(ws_dir: Path, path: str, ledger: tuple[req_ledger.Req, ...]) -> str:
    """The block appended to one writer's prompt: where the truth is, and which numbered lines of it are this file's."""
    mine = subset(ledger, path)
    if not mine:
        return ""
    sha = freeze(ws_dir, "", ledger) if not (ws_dir / SPEC).exists() else load(ws_dir)["sha256"]
    return f"\n\nSÖZLEŞME {SPEC} (sha256 {sha[:12]}). Bu dosyanın sorumlu olduğu maddeler (başka özetlerle çelişirse bunlar geçerli):\n{req_ledger.listing(mine)}"
