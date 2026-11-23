"""Cluster D ([M50]): 3-Jaw Chuck Thin-Wall Ring Ovalization & Elastic Deflection FEA Solver."""

from __future__ import annotations

from typing import Any

from cad_cam_physics import simulate_cutting_physics_and_fea


def solve_chuck_clamping_fea(
    material: str = "AISI 4140",
    chuck_clamp_force_n: float = 18000.0,
    ring_mean_radius_mm: float = 35.0,
    grip_length_mm: float = 20.0,
    wall_thickness_mm: float = 2.5,
    tolerance_band_mm: float = 0.025,
) -> dict[str, Any]:
    """Compute 3-jaw chuck thin-wall ring elastic ovalization and safe clamping pressure threshold."""
    sim = simulate_cutting_physics_and_fea(
        material=material,
        chuck_clamp_force_n=chuck_clamp_force_n,
        ring_mean_radius_mm=ring_mean_radius_mm,
        grip_length_mm=grip_length_mm,
        wall_thickness_mm=wall_thickness_mm,
        tolerance_band_mm=tolerance_band_mm,
    )
    oval_mm = float(sim["chuck_ovalization_mm"])
    max_allowable_oval_mm = round(float(tolerance_band_mm) * 0.30, 6)
    ratio = oval_mm / max(max_allowable_oval_mm, 1e-9)
    recommended_max_clamp_n = round(
        float(chuck_clamp_force_n) / max(ratio, 1.0) if ratio > 1.0 else float(chuck_clamp_force_n),
        1,
    )
    return {
        "material": material,
        "chuck_clamp_force_n": float(chuck_clamp_force_n),
        "ring_mean_radius_mm": float(ring_mean_radius_mm),
        "wall_thickness_mm": float(wall_thickness_mm),
        "chuck_ovalization_mm": oval_mm,
        "max_allowable_ovalization_mm": max_allowable_oval_mm,
        "is_within_tolerance": oval_mm <= max_allowable_oval_mm,
        "recommended_max_clamp_force_n": recommended_max_clamp_n,
        "recommended_fixture": "6-Jaw Chuck or Full-Wrap Soft Pie Jaws" if oval_mm > max_allowable_oval_mm else "Standard 3-Jaw Hard/Soft Chuck",
        "dfm_warnings": sim["dfm_warnings"],
    }


__all__ = [
    "simulate_cutting_physics_and_fea",
    "solve_chuck_clamping_fea",
]
