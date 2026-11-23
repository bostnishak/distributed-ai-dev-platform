"""Cluster D ([M48]): Multi-Controller CNC CAM Post-Processor (Fanuc, Siemens, Heidenhain, Haas)."""

from __future__ import annotations

from cad_cam_physics import (
    generate_cmm_wear_offset_gcode,
    generate_multi_controller_gcode,
)

SUPPORTED_CONTROLLERS: tuple[str, ...] = ("fanuc", "siemens", "heidenhain", "haas")

__all__ = [
    "SUPPORTED_CONTROLLERS",
    "generate_cmm_wear_offset_gcode",
    "generate_multi_controller_gcode",
]
