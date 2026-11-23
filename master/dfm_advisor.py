"""Cluster D ([M50]): Design for Manufacturability (DFM) Tolerance & Geometry Cost Advisor."""

from __future__ import annotations

from typing import Any


def advise_dfm_optimizations(
    part_spec: dict[str, Any],
    base_unit_cost_eur: float = 45.0,
) -> dict[str, Any]:
    """Analyze part tolerances, hole L/D ratios, wall thicknesses, corner radii, and surface
    roughness to recommend actionable DFM cost-reduction changes.
    """
    recommendations: list[dict[str, Any]] = []
    total_savings_pct = 0.0

    min_tol_mm = float(part_spec.get("tightest_tolerance_mm", part_spec.get("tolerance_mm", 0.02)))
    ra_um = float(part_spec.get("surface_roughness_ra_um", part_spec.get("ra_um", 1.6)))
    wall_mm = float(part_spec.get("min_wall_thickness_mm", part_spec.get("wall_thickness_mm", 3.0)))
    hole_dia = float(part_spec.get("hole_diameter_mm", 8.0))
    hole_depth = float(part_spec.get("hole_depth_mm", 32.0))
    corner_r = float(part_spec.get("pocket_corner_radius_mm", 2.0))
    pocket_depth = float(part_spec.get("pocket_depth_mm", 15.0))

    if min_tol_mm < 0.015:
        recommendations.append(
            {
                "rule_id": "DFM-TOL-01",
                "feature": "Tight Dimensional Tolerance",
                "current": f"+/-{min_tol_mm:.3f} mm",
                "suggestion": "Relax non-mating features to ISO 2768-mK (+/-0.10 mm) or H7 (+/-0.0125 mm) to avoid cylindrical grinding.",
                "estimated_cost_saving_pct": 18.0,
            }
        )
        total_savings_pct += 18.0

    if ra_um < 0.8:
        recommendations.append(
            {
                "rule_id": "DFM-SURF-02",
                "feature": "Ultra-Fine Surface Finish",
                "current": f"Ra {ra_um:.2f} um",
                "suggestion": "Relax non-sealing surfaces to Ra 1.6 um or Ra 3.2 um so standard finish turning/milling suffices without lapping.",
                "estimated_cost_saving_pct": 14.0,
            }
        )
        total_savings_pct += 14.0

    ld_ratio = hole_depth / max(hole_dia, 0.5)
    if ld_ratio > 5.0:
        recommendations.append(
            {
                "rule_id": "DFM-HOLE-03",
                "feature": "Deep Hole L/D Ratio",
                "current": f"L/D = {ld_ratio:.1f} (D={hole_dia} mm, L={hole_depth} mm)",
                "suggestion": "Reduce hole depth to L/D <= 4.0 or step-drill from both sides to eliminate specialized gun-drilling.",
                "estimated_cost_saving_pct": 12.0,
            }
        )
        total_savings_pct += 12.0

    if wall_mm < 2.0:
        recommendations.append(
            {
                "rule_id": "DFM-WALL-04",
                "feature": "Thin Wall Section",
                "current": f"{wall_mm:.2f} mm",
                "suggestion": "Increase minimum wall thickness to >= 2.5 mm to prevent chatter and 3-jaw chuck ovalization.",
                "estimated_cost_saving_pct": 10.0,
            }
        )
        total_savings_pct += 10.0

    if pocket_depth / max(corner_r * 2.0, 0.5) > 4.0:
        recommendations.append(
            {
                "rule_id": "DFM-POCKET-05",
                "feature": "Sharp Internal Pocket Corner",
                "current": f"R={corner_r:.2f} mm at depth {pocket_depth:.1f} mm",
                "suggestion": f"Increase internal corner radius to >= {round(pocket_depth / 3.0, 1)} mm to allow a stiffer, larger-diameter endmill.",
                "estimated_cost_saving_pct": 9.0,
            }
        )
        total_savings_pct += 9.0

    if not recommendations:
        recommendations.append(
            {
                "rule_id": "DFM-OK-00",
                "feature": "Overall Geometry & Tolerances",
                "current": "Standard CNC Machinable",
                "suggestion": "Geometry complies with standard 3-axis / turning DFM guidelines.",
                "estimated_cost_saving_pct": 0.0,
            }
        )

    capped_savings_pct = round(min(total_savings_pct, 45.0), 2)
    base_cost = max(0.01, float(base_unit_cost_eur))
    optimized_cost = round(base_cost * (1.0 - capped_savings_pct / 100.0), 2)

    return {
        "manufacturability_score": round(max(35.0, 100.0 - capped_savings_pct * 1.1), 1),
        "base_unit_cost_eur": round(base_cost, 2),
        "optimized_unit_cost_eur": optimized_cost,
        "estimated_total_saving_pct": capped_savings_pct,
        "recommendations": recommendations,
    }


__all__ = ["advise_dfm_optimizations"]
