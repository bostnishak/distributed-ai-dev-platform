"""Cluster D ([M49]): Kienzle Cutting Force, Spindle Power/Torque, Taylor Tool Life,
Cantilever Tool Deflection, and Chatter Stability Physics Engine.
"""

from __future__ import annotations

from cad_cam_physics import (
    MATERIAL_PHYSICS_DB,
    TOOL_MODULUS_MPA,
    simulate_cutting_physics_and_fea,
)

__all__ = [
    "MATERIAL_PHYSICS_DB",
    "TOOL_MODULUS_MPA",
    "simulate_cutting_physics_and_fea",
]
