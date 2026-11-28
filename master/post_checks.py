"""Checks run once on a finished project: security scan, real-browser layout audit, signed provenance record."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import a11y
import api_fuzz
import arch_heal
import code_audit
import complexity_governor
import deploy_kit
import design_slop
import flow_analysis
import js_mutation
import leak_check
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
    steps = (  # name, check, only for a web page; one row each, so a name can never drift away from its check
        ("Gizli anahtar ve güvensiz kalıp taraması", (security_scan.report, ws_dir), False),
        ("Veri akışı denetimi", (flow_analysis.report, ws_dir), False),
        ("Gerçek tarayıcıda yerleşim denetimi", (visual_audit.report, ws_dir), True),
        ("Şablon tasarım denetimi", (design_slop.report, ws_dir, request), True),
        ("Bağımlılık denetimi", (package_check.report, ws_dir), False),
        ("Statik tanılama, performans ve lisans", (code_audit.report, ws_dir, request), False),
        ("Veritabanı göçü denetimi", (migration_check.report, ws_dir), False),
        ("Rastgele tıklama dayanıklılığı", (ui_chaos.report, ws_dir), True),
        ("API zorlama testi", (api_fuzz.report, ws_dir), False),
        ("Mimari sağlık", (arch_heal.report, ws_dir), False),
        ("Erişilebilirlik (axe-core, klavye, pencere)", (a11y.report, ws_dir), True),
        ("Bellek ve DOM sızıntısı", (leak_check.report, ws_dir), True),
    )
    found = await asyncio.gather(*(asyncio.to_thread(*call) for _name, call, _page in steps))  # read-only checks run at the same time
    web = (ws_dir / "index.html").is_file()  # without a page, the page checks are not listed as verified
    checks = {name: result for (name, _call, needs_page), result in zip(steps, found, strict=True) if web or not needs_page}
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
