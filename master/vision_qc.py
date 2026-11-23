"""Cluster D ([M52]): Camera / Microscope Cutting Tool Flank Wear (VB) & Surface Defect Vision QC.

Analyzes tool insert images via Pillow/NumPy bright-band edge profiling to estimate flank wear
land width ``vb_mm`` and compares against ISO 3685 ``vb_max_mm = 0.30``.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image

ISO_3685_VB_MAX_MM = 0.30
ISO_3685_VB_WARNING_MM = 0.20


def analyze_tool_flank_wear_image(
    raw_bytes: bytes,
    pixel_to_mm: float = 0.005,
    vb_max_mm: float = ISO_3685_VB_MAX_MM,
) -> dict[str, Any]:
    """Analyze a carbide insert flank image via bright-band edge profiling to estimate ``vb_mm``."""
    if not raw_bytes:
        raise ValueError("raw_bytes cannot be empty")
    scale = max(1e-6, float(pixel_to_mm))
    limit_mm = max(0.05, float(vb_max_mm))

    with Image.open(io.BytesIO(raw_bytes)) as img:
        gray = img.convert("L")
        arr = np.asarray(gray, dtype=np.float32)

    h, w = arr.shape
    mean_lum = float(np.mean(arr))
    std_lum = float(np.std(arr))

    # Bright wear band detection: worn flank reflects light more strongly than dark TiAlN coating
    thresh = max(165.0, min(235.0, mean_lum + 0.9 * max(std_lum, 15.0)))
    bright_mask = arr >= thresh

    # Measure vertical span of bright wear band across columns
    col_counts = np.sum(bright_mask, axis=0).astype(np.float32)
    active_cols = col_counts[col_counts > 0]
    if active_cols.size > 0:
        mean_band_px = float(np.percentile(active_cols, 75))
        max_band_px = float(np.max(active_cols))
    else:
        # Fallback gradient edge band estimation
        gy = np.abs(np.diff(arr, axis=0))
        edge_rows = np.sum(gy > 18.0, axis=0)
        mean_band_px = float(np.mean(edge_rows)) if edge_rows.size else 8.0
        max_band_px = float(np.max(edge_rows)) if edge_rows.size else 12.0

    vb_mean_mm = round(mean_band_px * scale, 4)
    vb_peak_mm = round(max_band_px * scale, 4)

    # Local high-frequency roughness / chipping defect score (0..100)
    gx = np.abs(np.diff(arr, axis=1))
    surface_defect_score = round(min(100.0, float(np.mean(gx) / 2.55)), 2)

    if vb_mean_mm >= limit_mm:
        wear_status = "REPLACE_INSERT"
        recommendation = (
            f"Flank wear VB={vb_mean_mm:.3f} mm exceeds ISO 3685 limit ({limit_mm:.2f} mm). "
            "Index or replace carbide insert immediately."
        )
    elif vb_mean_mm >= ISO_3685_VB_WARNING_MM:
        wear_status = "WARNING"
        recommendation = (
            f"Flank wear VB={vb_mean_mm:.3f} mm approaching ISO 3685 threshold ({limit_mm:.2f} mm). "
            "Apply G10 wear offset and schedule insert replacement."
        )
    else:
        wear_status = "OK"
        recommendation = f"Flank wear VB={vb_mean_mm:.3f} mm is within ISO 3685 safe cutting zone."

    remaining_life_pct = round(max(0.0, min(100.0, (1.0 - vb_mean_mm / limit_mm) * 100.0)), 1)

    return {
        "width_px": int(w),
        "height_px": int(h),
        "pixel_to_mm": scale,
        "vb_mm": vb_mean_mm,
        "vb_max_observed_mm": vb_peak_mm,
        "vb_limit_mm": limit_mm,
        "wear_status": wear_status,
        "remaining_life_pct": remaining_life_pct,
        "surface_defect_score": surface_defect_score,
        "recommendation": recommendation,
    }


__all__ = [
    "ISO_3685_VB_MAX_MM",
    "ISO_3685_VB_WARNING_MM",
    "analyze_tool_flank_wear_image",
]
