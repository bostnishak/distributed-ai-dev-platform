"""Architecture decision records taken from the conversation, and an engineering notebook of root causes.

A decision is recorded only when the user says so: "karar: ..." or a sentence stating what "we decided" or "will use".
It is written as a numbered ADR into the chat's project (or the platform's data folder). Every root cause the repair
loop finds and fixes goes into the notebook, so the same mistake can be recognised later.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import atomic_io
import config
import security_scan

_EXPLICIT_RE = re.compile(r"^\s*(?:mimari\s+)?karar\s*:\s*(?P<text>.{8,400})$", re.IGNORECASE | re.DOTALL)
_DECIDED_RE = re.compile(r"\b(?:karar\s+verdik|karar\s+verdim|kullanmaya\s+karar|bundan\s+sonra\s+(?:veritabanı|mimari|altyapı)|we\s+(?:decided|will\s+use))\b", re.IGNORECASE)
_LIST_RE = re.compile(r"^\s*(?:mimari\s+)?kararları\s+(?:göster|listele)\W*$", re.IGNORECASE)
_BOOK_RE = re.compile(r"^\s*(?:mühendislik\s+)?defter(?:i|ini)\s+(?:göster|listele)\W*$", re.IGNORECASE)
_REASON_RE = re.compile(r"\b(?:çünkü|nedeni|zira|because)\b[:,]?\s*(?P<why>.+)$", re.IGNORECASE | re.DOTALL)


def _folder(ws_dir: Path | None) -> Path:
    return (ws_dir / "docs" / "adr") if ws_dir is not None and ws_dir.is_dir() else config.data_dir() / "adr"


def _slug(text: str) -> str:
    plain = text.lower().translate(str.maketrans("çğıöşü", "cgiosu"))
    return "-".join(re.findall(r"[a-z0-9]+", plain)[:6]) or "karar"


def record(text: str, ws_dir: Path | None) -> Path:
    """Write the next ADR; the same decision is not written twice."""
    text = security_scan.redact(" ".join(text.split()))
    folder = _folder(ws_dir)
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(folder.glob("[0-9][0-9][0-9]-*.md"))
    for path in existing:
        if f"## Karar\n\n{text}\n" in path.read_text(encoding="utf-8"):
            return path
    reason = _REASON_RE.search(text)
    number = int(existing[-1].name[:3]) + 1 if existing else 1
    target = folder / f"{number:03d}-{_slug(text)}.md"
    atomic_io.write_text(target, f"# ADR {number:03d}: {text[:80]}\n\nTarih: {time.strftime('%Y-%m-%d')}\nDurum: kabul edildi\n\n## Karar\n\n{text}\n\n"
                                 f"## Gerekçe\n\n{reason['why'].strip() if reason else 'Konuşmada gerekçe belirtilmedi.'}\n")
    return target


def stated(prompt: str) -> str:
    """The sentence of an ordinary message that states a decision, or ""."""
    for sentence in re.split(r"(?<=[.!])\s+|\n", prompt.strip()):
        if 12 <= len(sentence) <= 400 and not sentence.endswith("?") and _DECIDED_RE.search(sentence):
            return sentence.strip()
    return ""


def note(prompt: str, ws_dir: Path | None) -> str:
    """Record a decision stated inside a normal request (the request still goes to the model)."""
    sentence = stated(prompt)
    return record(sentence, ws_dir).name if sentence else ""


def _book() -> Path:
    return config.data_dir() / "playbook.md"


def learned(project: str, causes: str) -> None:
    """One notebook line per root cause that was found and fixed."""
    path = _book()
    line = f"- {time.strftime('%Y-%m-%d')} [{project}] {' '.join(security_scan.redact(causes).split())[:300]}"
    old = path.read_text(encoding="utf-8").splitlines() if path.is_file() else ["# Mühendislik defteri: bulunan ve düzeltilen kök nedenler", ""]
    if any(entry.split("] ", 1)[-1] == line.split("] ", 1)[-1] for entry in old):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(path, "\n".join([*old, line]) + "\n")


def lessons(limit: int = 4) -> str:
    """Recent root causes, as notes for the next repair."""
    try:
        lines = [line for line in _book().read_text(encoding="utf-8").splitlines() if line.startswith("- ")][-limit:]
    except OSError:
        return ""
    return "ÖNCEKİ PROJELERDE BULUNAN KÖK NEDENLER (benzeri varsa dikkat et):\n" + "\n".join(lines) if lines else ""


def answer(prompt: str, ws_dir: Path | None) -> str:
    """The reply to a decision or notebook command; "" for everything else."""
    if explicit := _EXPLICIT_RE.match(prompt):
        return f"Karar kaydedildi: `{record(explicit['text'], ws_dir).name}`"
    if _LIST_RE.match(prompt):
        files = sorted(_folder(ws_dir).glob("[0-9][0-9][0-9]-*.md"))
        return "Mimari kararlar:\n" + "\n".join(f"- {p.read_text(encoding='utf-8').splitlines()[0][2:]}" for p in files) if files else "Kayıtlı mimari karar yok."
    if _BOOK_RE.match(prompt):
        return _book().read_text(encoding="utf-8") if _book().is_file() else "Mühendislik defteri henüz boş."
    return ""
