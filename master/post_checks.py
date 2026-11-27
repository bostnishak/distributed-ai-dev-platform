"""Checks run once on a finished project: security scan, real-browser layout audit, signed provenance record."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import complexity_governor
import design_slop
import provenance
import security_scan
import visual_audit
import vlm_critique

_log = logging.getLogger(__name__)


async def apply(ws_dir: Path, request: str, done: dict[str, Any]) -> dict[str, Any]:
    """The finished event with the findings added to its warnings."""
    warnings = [str(w) for w in done.get("warnings") or []]
    warnings += [w for w in (security_scan.report(ws_dir), await asyncio.to_thread(visual_audit.report, ws_dir), design_slop.report(ws_dir, request)) if w]
    if complexity_governor.classify(request).level >= 3 and (seen := await vlm_critique.report(ws_dir, request)):
        warnings.append(seen)
    try:
        provenance.write(ws_dir, request, warnings)
    except (OSError, ValueError, TypeError) as exc:
        _log.warning("Köken kaydı yazılamadı: %s", exc)
    return {**done, "warnings": warnings}
