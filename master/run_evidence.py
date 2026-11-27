"""What the war room shows beside a run: how a branch differs from where it came from, and what was proved."""

from __future__ import annotations

import difflib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import ledger
import workspace_builder as wb
from sandbox import runner

_PROOF_WORDS = re.compile(r"mutasyon|z3|biçimsel|iş kuralı|karşı örnek|teslim durumu|özellik testi|veri akışı|sızıntı", re.IGNORECASE)
_MAX_DIFF = 6000


def isolation_tier(ready: Callable[[], tuple[bool, str]] = runner.docker_daemon_ready, platform: str = sys.platform) -> str:
    """Where generated code runs right now: the strongest layer that is actually available."""
    if ready()[0]:
        return "Yalıtım: Docker kutusu (ağsız, yetkisiz kullanıcı)"
    if platform == "win32":
        return "Yalıtım: yalnız Windows süreç sınırı — Docker kapalı, proje kodu çalıştırılmıyor"
    return "Yalıtım yok — Docker kapalı, proje kodu çalıştırılmıyor"


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []


def compare(left: Path, right: Path) -> list[dict[str, Any]]:
    """Files that differ between two projects, each with a unified diff (left is "before")."""
    out = []
    for name in sorted(set(wb.list_relative_files(left)) | set(wb.list_relative_files(right))):
        before, after = _read(left / name), _read(right / name)
        if before == after and (left / name).is_file() == (right / name).is_file():
            continue
        status = "eklendi" if not (left / name).is_file() else "silindi" if not (right / name).is_file() else "değişti"
        diff = "\n".join(difflib.unified_diff(before, after, fromfile=f"{left.name}/{name}", tofile=f"{right.name}/{name}", lineterm="", n=2))
        out.append({"path": name, "status": status, "diff": diff[:_MAX_DIFF]})
    return out


def compare_with_origin(ws_id: str) -> dict[str, Any]:
    """The branch against the project it was branched from; ValueError when it is not a branch."""
    right = wb.safe_workspace_dir(ws_id)
    origin = (wb.load_workspace_meta(right).get("branched_from") or {}).get("workspace", "")
    if not origin or not wb.safe_workspace_dir(origin).is_dir():
        raise ValueError("Bu proje bir dal değil ya da asıl proje silinmiş.")
    return {"origin": origin, "branch": ws_id, "files": compare(wb.safe_workspace_dir(origin), right)}


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def proofs(ws_id: str) -> dict[str, Any]:
    """Delivery stages, the lines about formal, mutation and property checks, and the verified/open ledger."""
    ws_dir = wb.safe_workspace_dir(ws_id)
    record = _json(ws_dir / ".ai-os" / "proof.json")
    warnings = [str(w) for w in _json(ws_dir / ".provenance.json").get("warnings", [])]
    known = ledger.read(ws_dir)
    return {"stages": record.get("proofs", {}), "evidence": [w for w in warnings if _PROOF_WORDS.search(w)][:12],
            "verified": known.get("verified", [])[:20], "open": known.get("open", [])[:20]}
