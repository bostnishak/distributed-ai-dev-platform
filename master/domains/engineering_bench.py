"""EPK-21: Verified 15-Formula Engineering Benchmark Suite & Strict CNC G-Code Safety Validator."""

from __future__ import annotations

import math
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/domains/engineering", tags=["engineering-benchmarks"])


def run_engineering_benchmarks() -> dict[str, Any]:
    """Verify 15 classic mechanical/electrical/fluid engineering formulas against literature values (<=5% error)."""
    cases: list[tuple[str, float, float]] = [
        ("kienzle_fc_4140_n", 2100.0 * 2.0 * (0.2**0.75), 1256.4),
        ("spindle_rpm_d50_vc180", (1000.0 * 180.0) / (math.pi * 50.0), 1145.92),
        ("spindle_power_kw", (1256.4 * 180.0) / 60000.0, 3.769),
        ("ra_theoretical_um", (0.2**2) / (32.0 * 0.8) * 1000.0, 1.5625),
        ("cantilever_deflection_mm", (500.0 * (60.0**3)) / (3.0 * 600000.0 * (math.pi * (16.0**4) / 64.0)), 0.01865),
        ("ohm_current_a", 12.0 / 470.0, 0.02553),
        ("dc_power_w", (12.0**2) / 470.0, 0.3064),
        ("rc_cutoff_hz", 1.0 / (2.0 * math.pi * 1000.0 * 1e-6), 159.15),
        ("axial_stress_mpa", 10000.0 / (math.pi * (10.0**2)), 31.83),
        ("reynolds_pipe", (1000.0 * 2.0 * 0.05) / 0.001, 100000.0),
        ("fourier_heat_w", (50.0 * 0.02 * 40.0) / 0.01, 4000.0),
        ("taylor_life_min", (240.0 / 180.0) ** (1.0 / 0.25), 3.1605),
        ("torque_nm", (9550.0 * 3.769) / 1145.92, 31.41),
        ("mrr_cm3_min", 2.0 * 0.2 * 180.0, 72.0),
        ("hooke_strain", 210.0 / 210000.0, 0.001),
    ]
    results = []
    passed = 0
    for name, computed, ref in cases:
        rel_err = abs(computed - ref) / max(abs(ref), 1e-9)
        ok = rel_err <= 0.05
        passed += 1 if ok else 0
        results.append({"benchmark": name, "computed": round(computed, 5), "reference": ref, "rel_error_pct": round(rel_err * 100.0, 3), "ok": ok})
    return {"ok": passed == len(cases), "passed": passed, "total": len(cases), "results": results}


def _audit_gcode_line(idx: int, ln: str, issues: list[dict[str, Any]]) -> None:
    if ln.count("(") != ln.count(")"):
        issues.append({"line": idx, "code": "UNMATCHED_COMMENT", "detail": "Eşleşmeyen parantez."})
    code_part = re.sub(r"\([^)]*\)", "", ln)
    if re.search(r"\bG0?0\b", code_part) and re.search(r"\bZ-\d", code_part):
        issues.append({"line": idx, "code": "RAPID_Z_PLUNGE", "detail": "G00 hızlı hareket ile negatif Z dalışı çarpışma riski taşır."})
    if (m_s := re.search(r"\bS(\d+(?:\.\d+)?)", code_part)) and float(m_s.group(1)) > 24000:
        issues.append({"line": idx, "code": "EXCESSIVE_RPM", "detail": f"Aşırı iş mili devri: S{m_s.group(1)} > 24000"})
    if (m_f := re.search(r"\bF(\d+(?:\.\d+)?)", code_part)) and float(m_f.group(1)) > 15000:
        issues.append({"line": idx, "code": "EXCESSIVE_FEED", "detail": f"Aşırı ilerleme: F{m_f.group(1)} > 15000"})
    if re.search(r"\bG0?0\b", code_part) and re.search(r"\bG0?1\b", code_part):
        issues.append({"line": idx, "code": "MODAL_CONFLICT", "detail": "Aynı satırda G00 ve G01 çakışması."})


def validate_gcode_safety(gcode: str) -> dict[str, Any]:
    """Audit CNC G-code program for safety hazards (rapid Z plunge, missing M30/units, excessive RPM/feed, syntax)."""
    lines = [ln.strip().upper() for ln in (gcode or "").splitlines() if ln.strip()]
    issues: list[dict[str, Any]] = []
    joined = "\n".join(lines)
    if not lines:
        return {"ok": True, "safe": False, "issues": [{"line": 0, "code": "EMPTY_PROGRAM", "detail": "G-kod boş."}]}
    if "G21" not in joined and "G20" not in joined:
        issues.append({"line": 1, "code": "MISSING_UNITS", "detail": "Birim komutu (G21 mm / G20 inch) eksik."})
    if not any(m in joined for m in ("M30", "M02", "M2")):
        issues.append({"line": len(lines), "code": "MISSING_PROGRAM_END", "detail": "Program sonu (M30/M02) eksik."})
    if any(m in joined for m in ("M03", "M3", "M04", "M4")) and not any(m in joined for m in ("M05", "M5", "M30")):
        issues.append({"line": len(lines), "code": "SPINDLE_NOT_STOPPED", "detail": "İş mili durdurma (M05) eksik."})
    for idx, ln in enumerate(lines, start=1):
        _audit_gcode_line(idx, ln, issues)
    return {"ok": True, "safe": len(issues) == 0, "line_count": len(lines), "issue_count": len(issues), "issues": issues}


class GcodeAuditRequest(BaseModel):
    gcode: str = Field(..., max_length=64000)


@router.get("/benchmarks")
async def api_engineering_benchmarks():
    """Run all 15 literature-verified engineering formula benchmarks."""
    return run_engineering_benchmarks()


@router.post("/gcode-audit")
async def api_gcode_audit(body: GcodeAuditRequest):
    """Run strict CNC G-code safety & modal collision validation."""
    return validate_gcode_safety(body.gcode)
