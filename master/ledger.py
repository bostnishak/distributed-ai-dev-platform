"""What is known about a delivered project, in three honest buckets.

verified: a check ran on the files and found nothing. assumed: decisions the architect had to take that the request
does not state. open: findings of the checks, and checks that could not run at all.
"""

from __future__ import annotations

import json
from pathlib import Path

FILE = ".history/ledger.json"
_ASSUMPTION = "Varsayım (doğrulanmadı): "


def build(checks: dict[str, object], assumptions: list[str] | None = None) -> dict[str, list[str]]:
    """`checks` maps a check name to its finding: "" / [] = clean, None = not run, anything else = findings."""
    out: dict[str, list[str]] = {"verified": [], "assumed": list(assumptions or []), "open": []}
    for name, finding in checks.items():
        if finding is None:
            out["open"].append(f"{name}: çalıştırılamadı")
        elif finding:
            out["open"].extend(finding if isinstance(finding, list) else [str(finding)])
        else:
            out["verified"].append(f"{name}: sorun bulunmadı")
    return out


def assumption_lines(messages: list[str]) -> list[str]:
    return [m[len(_ASSUMPTION):] for m in messages if m.startswith(_ASSUMPTION)]


def write(ws_dir: Path, entry: dict[str, list[str]]) -> None:
    path = ws_dir / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = read(ws_dir)
    entry = {**entry, "assumed": entry["assumed"] or previous.get("assumed", [])}
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")


def assume(ws_dir: Path, assumptions: list[str]) -> None:
    current = read(ws_dir) or {"verified": [], "assumed": [], "open": []}
    current["assumed"] = assumptions
    path = ws_dir / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=1), encoding="utf-8")


def read(ws_dir: Path) -> dict[str, list[str]]:
    try:
        return json.loads((ws_dir / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
