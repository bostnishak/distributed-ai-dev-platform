"""plan.json: the delivered files, their build order and endpoints, and every requirement mapped to the check that proves it.

Built by code from the specification contract and the files that were really written, so it cannot promise a file
that does not exist. A requirement no check can decide is listed as "elle bakılmalı", never as covered.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import repo_map

FILE_NAME = "plan.json"
ORACLE = ".ai-os/oracles/contract.json"
_ROUTE_RE = re.compile(r"@\w+\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"'](?:[^)]*status_code\s*=\s*(\d{3}))?", re.IGNORECASE)
_EXPRESS_RE = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"'`](/[^\"'`]*)[\"'`]")


def endpoints(ws_dir: Path, files: list[str]) -> list[dict[str, Any]]:
    """Routes declared in the delivered code (method, path, success status, file)."""
    found = []
    for relative in files:
        if not relative.endswith((".py", ".js", ".ts")):
            continue
        source = (ws_dir / relative).read_text(encoding="utf-8", errors="replace")
        matches = _ROUTE_RE.findall(source) if relative.endswith(".py") else [(m, p, "") for m, p in _EXPRESS_RE.findall(source)]
        found += [{"method": method.upper(), "path": path, "status": int(status or 200), "file": relative} for method, path, status in matches]
    return found


def matrix(contract: dict[str, Any], routes: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(kind: str, wanted: str, check: str) -> None:
        rows.append({"id": f"REQ-{len(rows) + 1:03d}", "kind": kind, "requirement": wanted, "check": check})

    for colour in contract.get("colors") or []:
        add("renk", colour, "spec_contract: renk sayfada geçiyor")
    for label in contract.get("labels") or []:
        add("etiket", label, "spec_contract: etiket sayfada geçiyor")
    for size in contract.get("sizes") or []:
        add("ölçü", size, "spec_contract: ölçü CSS'te geçiyor")
    for button in contract.get("buttons") or []:
        add("davranış", f"{button['label']}: {button['behavior']}", "gerçek tarayıcı: düğme bağlı (done_gate C)")
    for item in contract.get("forbidden") or []:
        add("yasak", item, "elle bakılmalı")
    for region in contract.get("regions") or []:
        add("yerleşim", region, "görsel denetim: taşma ve çakışma; bölgenin varlığı elle bakılmalı")
    for endpoint in contract.get("endpoints") or []:
        declared = any(r["method"] == endpoint["method"].upper() and r["path"].rstrip("/") == endpoint["path"].rstrip("/") for r in routes)
        add("uç nokta", f"{endpoint['method'].upper()} {endpoint['path']}", "kodda tanımlı" if declared else "EKSİK: kodda tanımlı değil")
    if contract.get("persistence"):
        add("kalıcılık", str(contract["persistence"]), "canlı yolculuk: yenileme ve yeniden başlatma")
    return rows


def build(ws_dir: Path, contract: dict[str, Any], files: list[str]) -> dict[str, Any]:
    routes = endpoints(ws_dir, files)
    graph = repo_map.build(ws_dir, "", budget=1500)
    return {"files": files, "build_order": files, "dependencies": graph, "endpoints": routes, "acceptance": matrix(contract, routes)}


def write_oracle(ws_dir: Path, contract: dict[str, Any]) -> None:
    """What the request promised, written before any repair and never rewritten: later steps are judged against it."""
    target = ws_dir / ORACLE
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    promised = {key: contract.get(key) for key in ("endpoints", "labels", "colors", "persistence")}
    target.write_text(json.dumps(promised, ensure_ascii=False, indent=2), encoding="utf-8")


def missing_endpoints(ws_dir: Path, openapi: dict[str, Any]) -> list[str]:
    """Endpoints the oracle promises that the running server does not offer."""
    try:
        promised = json.loads((ws_dir / ORACLE).read_text(encoding="utf-8")).get("endpoints") or []
    except (OSError, ValueError, AttributeError):
        return []

    def shape(path: str) -> str:
        return re.sub(r"\{[^}]*\}|:\w+", "{}", path.rstrip("/")) or "/"

    offered = {(method.upper(), shape(path)) for path, operations in openapi.get("paths", {}).items() for method in operations}
    return [f"{e['method'].upper()} {e['path']}" for e in promised if (e["method"].upper(), shape(e["path"])) not in offered]


def write(ws_dir: Path, contract: dict[str, Any], files: list[str]) -> list[str]:
    """Writes plan.json beside the project record; returns warnings for requirements the code visibly does not meet."""
    plan = build(ws_dir, contract, files)
    folder = ws_dir / ".ai-os"
    folder.mkdir(exist_ok=True)
    (folder / FILE_NAME).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    write_oracle(ws_dir, contract)
    return [f"Sözleşme: {row['requirement']} {row['check']}" for row in plan["acceptance"] if row["check"].startswith("EKSİK")]
