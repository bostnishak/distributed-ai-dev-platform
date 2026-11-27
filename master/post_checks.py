"""Checks run once on a finished project: security scan, real-browser layout audit, signed provenance record."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import code_audit
import complexity_governor
import design_slop
import mutation
import package_check
import provenance
import security_scan
import visual_audit
import vlm_critique
import workspace_requirements

_log = logging.getLogger(__name__)


async def apply(ws_dir: Path, request: str, done: dict[str, Any]) -> dict[str, Any]:
    """The finished event with the findings added to its warnings."""
    warnings = [str(w) for w in done.get("warnings") or []]
    warnings += [w for w in (security_scan.report(ws_dir), await asyncio.to_thread(visual_audit.report, ws_dir), design_slop.report(ws_dir, request)) if w]
    warnings += [w for w in (await asyncio.to_thread(package_check.report, ws_dir),) if w]
    warnings += await asyncio.to_thread(code_audit.report, ws_dir, request)
    if complexity_governor.classify(request).level >= 3:
        pkgs = workspace_requirements.declared_packages(ws_dir)
        deep = (await vlm_critique.report(ws_dir, request), await asyncio.to_thread(mutation.report, ws_dir, pkgs))
        warnings += [w for w in deep if w]
    try:
        provenance.write(ws_dir, request, warnings)
    except (OSError, ValueError, TypeError) as exc:
        _log.warning("Köken kaydı yazılamadı: %s", exc)
    return {**done, "warnings": warnings}
