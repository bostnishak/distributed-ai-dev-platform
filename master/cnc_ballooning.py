"""CNC Technical Drawing Ballooning & Quality Inspection Engine.

Coordinates modular sub-engines:
- `cnc_ballooning_plan`: ISO 2768/286 tolerances, `BalloonItem`, OP10..OP50 planning, costing, Fanuc G-code.
- `cnc_ballooning_extract`: PDF/Image/DOCX/XLSX/DXF ingestion, regex dimension parser, VLM extraction.
- `cnc_ballooning_render`: Non-overlapping red balloon renderer & synthetic sample drawing generators.
- `cnc_ballooning_reports`: AS9102 / FAI multi-page PDF, 4-sheet Excel (.xlsx), and Word (.docx) exporters.
"""

from __future__ import annotations

import math
from typing import Any

from cnc_ballooning_extract import (
    CNC_VISION_SYSTEM_PROMPT,
    _analyze_image_with_vlm,
    _extract_dxf_balloons,
    _extract_largest_zip_image,
    _extract_metadata_from_texts,
    _extract_pdf_vector_balloons,
    _pick_vision_model,
    parse_cnc_dimension,
    process_drawing,
)
from cnc_ballooning_plan import (
    GDT_KEYWORDS,
    ISO_286_FITS,
    ISO_2768_M_LINEAR,
    MATERIAL_CUTTING_DB,
    BalloonItem,
    build_cnc_manufacturing_plan,
    compute_zone,
    enrich_cnc_engineering_fields,
    estimate_cnc_cost_and_time,
    generate_fanuc_gcode_template,
    lookup_iso286_fit,
    lookup_iso2768_m,
)
from cnc_ballooning_render import (
    _load_font,
    _render_spec_sheet_image,
    generate_sample_cnc_drawing_pdf,
    generate_sample_cnc_dxf,
    render_ballooned_image,
)
from cnc_ballooning_reports import (
    export_ballooned_pdf,
    export_excel_report,
    export_word_report,
)


def _compute_spc_capability(
    samples: list[float], mean_val: float, min_lim: float | None, max_lim: float | None
) -> tuple[float | None, float | None]:
    if len(samples) < 2 or min_lim is None or max_lim is None:
        return None, None
    variance = sum((s - mean_val) ** 2 for s in samples) / (len(samples) - 1)
    sigma = math.sqrt(variance)
    if sigma <= 1e-7:
        return None, None
    cp = round((max_lim - min_lim) / (6.0 * sigma), 2)
    cpk = round(min((max_lim - mean_val) / (3.0 * sigma), (mean_val - min_lim) / (3.0 * sigma)), 2)
    return cp, cpk


def evaluate_cmm_measurements(
    balloons: list[BalloonItem],
    measurements: dict[int, list[float]],
) -> dict[str, Any]:
    """Evaluate CMM / operator measured sample values against balloon tolerances and compute SPC (Cp/Cpk)."""
    results: list[dict[str, Any]] = []
    ok_count = 0
    nok_count = 0

    for b in balloons:
        samples = [float(x) for x in measurements.get(b.balloon_no, []) if x is not None]
        if not samples:
            continue
        mean_val = sum(samples) / len(samples)
        dev = round(mean_val - b.nominal, 4) if b.nominal is not None else 0.0

        status = "OK"
        if b.min_limit is not None and any(s < b.min_limit for s in samples):
            status = "NOK (ALT LİMİT DIŞI)"
        elif b.max_limit is not None and any(s > b.max_limit for s in samples):
            status = "NOK (ÜST LİMİT DIŞI)"

        ok_count += 1 if status == "OK" else 0
        nok_count += 0 if status == "OK" else 1
        cp, cpk = _compute_spc_capability(samples, mean_val, b.min_limit, b.max_limit)

        results.append({
            "balloon_no": b.balloon_no,
            "raw_text": b.raw_text,
            "min_limit": b.min_limit,
            "max_limit": b.max_limit,
            "samples": samples,
            "mean": round(mean_val, 4),
            "deviation": dev,
            "cp": cp,
            "cpk": cpk,
            "status": status,
        })

    return {
        "evaluated_count": len(results),
        "ok_count": ok_count,
        "nok_count": nok_count,
        "first_pass_yield_pct": round((ok_count / len(results)) * 100.0, 1) if results else 100.0,
        "items": results,
    }


__all__ = [
    "CNC_VISION_SYSTEM_PROMPT", "GDT_KEYWORDS", "ISO_286_FITS", "ISO_2768_M_LINEAR", "MATERIAL_CUTTING_DB",
    "BalloonItem", "_analyze_image_with_vlm", "_extract_dxf_balloons", "_extract_largest_zip_image",
    "_extract_metadata_from_texts", "_extract_pdf_vector_balloons", "_load_font", "_pick_vision_model",
    "_render_spec_sheet_image", "build_cnc_manufacturing_plan", "compute_zone", "enrich_cnc_engineering_fields",
    "estimate_cnc_cost_and_time", "evaluate_cmm_measurements", "export_ballooned_pdf", "export_excel_report",
    "export_word_report", "generate_fanuc_gcode_template", "generate_sample_cnc_drawing_pdf",
    "generate_sample_cnc_dxf", "lookup_iso286_fit", "lookup_iso2768_m", "parse_cnc_dimension",
    "process_drawing", "render_ballooned_image",
]
