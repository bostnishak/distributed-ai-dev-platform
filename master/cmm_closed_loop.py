"""Cluster D ([M51]): Closed-Loop CMM Quality Control, X-bar/R SPC Control Charts,
Cp/Cpk Capability Analysis, and Automatic G10 Tool Wear Offset SQLite Engine.
"""

from __future__ import annotations

import math
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dbconn
from cad_cam_physics import generate_cmm_wear_offset_gcode
from prompt_loader import load_prompt


def _cmm_db_path() -> Path:
    path = dbconn.database_file("cmm_quality.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_cmm_quality_db(db_path: Path | None = None) -> Path:
    """Create ``cnc_inspection_lots`` and ``cnc_cmm_measurements`` tables matching Section 13.D."""
    target = db_path or _cmm_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(target)) as conn:
        conn.executescript(load_prompt("b2_cmm_schema.txt"))
    return target


_CMM_LOT_POS_NAMES = (
    "nominal",
    "tol_plus",
    "tol_minus",
    "measurements",
    "controller",
    "tool_no",
    "balloon_no",
    "machine_id",
    "operator_name",
)


def record_cmm_lot_measurements(
    cnc_job_id: str,
    part_number: str,
    lot_number: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Persist CMM inspection lot & serial measurements into ``cmm_quality.db``, compute
    X-bar/R SPC control limits (UCL, LCL, center_line), Cp, Cpk, First Pass Yield (fpy_percent),
    and closed-loop G10 tool wear offset G-code.
    """
    params = dict(zip(_CMM_LOT_POS_NAMES, args, strict=False))
    params.update(kwargs)
    nominal = float(params["nominal"])
    tol_plus = float(params["tol_plus"])
    tol_minus = float(params["tol_minus"])
    measurements: list[float] = params["measurements"]
    controller = str(params.get("controller", "fanuc"))
    tool_no = int(params.get("tool_no", 1))
    balloon_no = int(params.get("balloon_no", 1))
    machine_id = str(params.get("machine_id", "CNC-TURN-01"))
    operator_name = str(params.get("operator_name", "CMM-AUTO"))

    if not measurements:
        raise ValueError("measurements list must contain at least one CMM reading")

    db_path = init_cmm_quality_db()
    samples = [float(x) for x in measurements]
    n = len(samples)
    nom = float(nominal)
    usl = nom + abs(float(tol_plus))
    lsl = nom - abs(float(tol_minus))

    mean_val = sum(samples) / n
    sample_range = max(samples) - min(samples) if n > 1 else 0.0

    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in samples) / (n - 1)
        sigma = max(math.sqrt(variance), 1e-6)
    else:
        sigma = max((usl - lsl) / 8.0, 1e-6)

    cp = (usl - lsl) / (6.0 * sigma)
    cpk = min((usl - mean_val) / (3.0 * sigma), (mean_val - lsl) / (3.0 * sigma))

    ok_flags = [1 if (lsl - 1e-9 <= val <= usl + 1e-9) else 0 for val in samples]
    fpy_percent = round((sum(ok_flags) / n) * 100.0, 2)

    # X-bar / R SPC 3-sigma control limits around process center line
    se_mean = sigma / math.sqrt(n)
    ucl_xbar = round(mean_val + 3.0 * se_mean, 5)
    lcl_xbar = round(mean_val - 3.0 * se_mean, 5)

    offset_info = generate_cmm_wear_offset_gcode(
        controller=controller,
        tool_no=tool_no,
        nominal=nom,
        measured_mean=mean_val,
        measurements=samples,
        tolerance_plus=tol_plus,
        tolerance_minus=tol_minus,
    )

    if fpy_percent < 100.0 and cpk < 1.0:
        status = "REJECTED"
    elif offset_info["spc"]["action_required"]:
        status = "OFFSET_ADJUSTED"
    else:
        status = "APPROVED"

    lot_id = f"LOT-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(UTC).isoformat()

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO cnc_inspection_lots
            (id, cnc_job_id, part_number, lot_number, machine_id, operator_name, sample_count, fpy_percent, min_cpk, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot_id,
                cnc_job_id.strip(),
                part_number.strip(),
                lot_number.strip(),
                machine_id.strip(),
                operator_name.strip(),
                n,
                fpy_percent,
                round(cpk, 3),
                status,
                now_iso,
            ),
        )
        for idx, val in enumerate(samples, start=1):
            dev = round(val - nom, 5)
            is_ok = ok_flags[idx - 1]
            conn.execute(
                """
                INSERT INTO cnc_cmm_measurements
                (lot_id, balloon_no, serial_no, measured_value, deviation, is_ok, measured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lot_id, balloon_no, idx, val, dev, is_ok, now_iso),
            )

    return {
        "lot_id": lot_id,
        "db_path": str(db_path),
        "cnc_job_id": cnc_job_id,
        "part_number": part_number,
        "lot_number": lot_number,
        "sample_count": n,
        "nominal_mm": round(nom, 4),
        "usl_mm": round(usl, 4),
        "lsl_mm": round(lsl, 4),
        "measured_mean_mm": round(mean_val, 5),
        "range_r_mm": round(sample_range, 5),
        "sigma_mm": round(sigma, 6),
        "cp": round(cp, 3),
        "cpk": round(cpk, 3),
        "fpy_percent": fpy_percent,
        "status": status,
        "spc_control_limits": {
            "center_line": round(mean_val, 5),
            "UCL": ucl_xbar,
            "LCL": lcl_xbar,
            "range_r": round(sample_range, 5),
        },
        "offset_gcode": offset_info["offset_gcode"],
        "wear_compensation_mm": offset_info["wear_compensation_mm"],
        "deviation_mm": offset_info["deviation_mm"],
    }


__all__ = [
    "generate_cmm_wear_offset_gcode",
    "init_cmm_quality_db",
    "record_cmm_lot_measurements",
]
