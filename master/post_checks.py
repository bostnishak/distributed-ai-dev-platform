"""Checks run once on a finished project: security scan, real-browser layout audit, signed provenance record."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import api_fuzz
import code_audit
import complexity_governor
import deploy_kit
import design_slop
import flow_analysis
import js_mutation
import ledger
import migration_check
import mutation
import package_check
import property_check
import provenance
import security_scan
import ui_chaos
import visual_audit
import vlm_critique
import workspace_requirements

_log = logging.getLogger(__name__)


async def apply(ws_dir: Path, request: str, done: dict[str, Any]) -> dict[str, Any]:
    """The finished event with the findings added to its warnings."""
    warnings = [str(w) for w in done.get("warnings") or []]
    deployment = deploy_kit.apply(ws_dir, request)  # the only step that writes files: before the readers start
    found = await asyncio.gather(  # read-only checks are independent of each other, so they run at the same time
        asyncio.to_thread(security_scan.report, ws_dir), asyncio.to_thread(flow_analysis.report, ws_dir), asyncio.to_thread(visual_audit.report, ws_dir), asyncio.to_thread(design_slop.report, ws_dir, request),
        asyncio.to_thread(package_check.report, ws_dir), asyncio.to_thread(code_audit.report, ws_dir, request), asyncio.to_thread(migration_check.report, ws_dir), asyncio.to_thread(ui_chaos.report, ws_dir), asyncio.to_thread(api_fuzz.report, ws_dir))
    names = ("Gizli anahtar ve güvensiz kalıp taraması", "Gerçek tarayıcıda yerleşim denetimi", "Şablon tasarım denetimi", "Bağımlılık denetimi",
             "Statik tanılama, veri akışı, performans ve lisans", "Veritabanı göçü denetimi", "Rastgele tıklama dayanıklılığı", "API zorlama testi")
    checks = dict(zip(names, found, strict=True))
    if not (ws_dir / "index.html").is_file():
        checks.pop(names[1]), checks.pop(names[2]), checks.pop(names[6])
    ledger.write(ws_dir, ledger.build(checks))
    for result in (*found, deployment):
        warnings += result if isinstance(result, list) else [result] if result else []
    if property_check.rules(request) and (checked := await property_check.report(ws_dir, request, workspace_requirements.declared_packages(ws_dir))):
        warnings.append(checked)
    if complexity_governor.classify(request).level >= 3:
        pkgs = workspace_requirements.declared_packages(ws_dir)
        deep = (await vlm_critique.report(ws_dir, request), await asyncio.to_thread(mutation.report, ws_dir, pkgs), await asyncio.to_thread(js_mutation.report, ws_dir))
        warnings += [w for w in deep if w]
    try:
        provenance.write(ws_dir, request, warnings)
    except (OSError, ValueError, TypeError) as exc:
        _log.warning("Köken kaydı yazılamadı: %s", exc)
    return {**done, "warnings": warnings}
