"""Preference pairs from real repairs: the file that failed the tests (rejected) and the one that passed (chosen)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import config
import security_scan

_LIMIT = 12_000


def _path() -> Path:
    return config.data_dir() / "repair_pairs.jsonl"


def record(failure: str, before: dict[str, str], after: dict[str, str]) -> int:
    """Keep one pair per changed file; secrets are removed. Returns how many were written."""
    changed = [name for name in after if before.get(name) not in (None, after[name]) and len(after[name]) <= _LIMIT]
    if not changed:
        return 0
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for name in changed:
            handle.write(json.dumps({"at": time.strftime("%Y-%m-%d"), "prompt": security_scan.redact(f"{name} dosyasını düzelt. Hata:\n{failure[:800]}"),
                                     "rejected": security_scan.redact(before[name][:_LIMIT]), "chosen": security_scan.redact(after[name])}, ensure_ascii=False) + "\n")
    return len(changed)


def load() -> list[dict[str, str]]:
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    pairs = []
    for line in lines:
        try:
            item = json.loads(line)
            pairs.append({"prompt": item["prompt"], "chosen": item["chosen"], "rejected": item["rejected"]})
        except (ValueError, KeyError):
            continue
    return pairs
