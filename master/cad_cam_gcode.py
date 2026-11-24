"""Multi-Controller CAM G-Code Post-Processor and Closed-Loop CMM Wear Offset Engine.

Supports Fanuc 0i/31i, Siemens Sinumerik 840D/One, Heidenhain TNC 640, and Haas NGC.
"""

from __future__ import annotations

import math
from typing import Any


def _extract_gcode_params(part_spec: dict[str, Any]) -> dict[str, Any]:
    od_mm = float(part_spec.get("outer_diameter_mm") or part_spec.get("od_mm") or 60.0)
    thread_pitch_mm = float(part_spec.get("thread_pitch_mm", 1.5))
    tap_rpm = int(float(part_spec.get("tap_rpm", 400)))
    return {
        "part_no": str(part_spec.get("part_number") or part_spec.get("part_name") or "PART_1001").upper(),
        "material": str(part_spec.get("material") or "AISI 4140").upper(),
        "od_mm": od_mm,
        "length_mm": float(part_spec.get("length_mm", 80.0)),
        "finish_od_mm": float(part_spec.get("finish_od_mm", round(od_mm - 4.0, 2))),
        "hole_dia_mm": float(part_spec.get("hole_diameter_mm", 12.0)),
        "hole_depth_mm": float(part_spec.get("hole_depth_mm", 30.0)),
        "thread_pitch_mm": thread_pitch_mm,
        "thread_depth_mm": float(part_spec.get("thread_depth_mm", 20.0)),
        "vc_m_min": int(float(part_spec.get("vc_m_min", 180))),
        "max_rpm": int(float(part_spec.get("max_rpm", 2500))),
        "ap_mm": float(part_spec.get("ap_mm", 2.0)),
        "feed_rough": float(part_spec.get("feed_rough_mm_rev", 0.22)),
        "feed_finish": float(part_spec.get("feed_finish_mm_rev", 0.10)),
        "tap_rpm": tap_rpm,
        "tap_feed_mm_min": round(tap_rpm * thread_pitch_mm, 1),
    }


def _build_siemens_gcode(p: dict[str, Any]) -> str:
    lines = [
        f"; SIEMENS SINUMERIK 840D / ONE - PART: {p['part_no']} ({p['material']})",
        "G710 G40 G90 DIAMON",
        "G54",
        'T="ROUGH_TURN_80" D1',
        f"LIMS={p['max_rpm']}",
        f"G96 S{p['vc_m_min']} M3",
        f"G0 X{p['od_mm'] + 4.0:.3f} Z2.000 M8",
        f'CYCLE95("KONTUR_OD", {p["ap_mm"]:.2f}, 0.3, 0.1, , {p["feed_rough"]:.2f}, 0.15, 0.10, 1, , , )',
        'T="FINISH_TURN_55" D1',
        f"G96 S{int(p['vc_m_min'] * 1.2)} M3",
        f'CYCLE95("KONTUR_OD", {p["ap_mm"]:.2f}, 0.0, 0.0, , {p["feed_finish"]:.2f}, 0.10, 0.08, 9, , , )',
        'T="DRILL_D12" D1',
        "G97 S1200 M3",
        "G0 X0.000 Z5.000",
        f"CYCLE83(2, 0, 2, -{p['hole_depth_mm']:.3f}, , 4.0, , 1, , , 1.0, 0, 1, 4.0, 1.0, 0.5, 1)",
        'T="TAP_M12" D1',
        f"G97 S{p['tap_rpm']} M3",
        "G0 X0.000 Z5.000",
        f"CYCLE84(3, 0, 3, -{p['thread_depth_mm']:.3f}, , , 3, {p['thread_pitch_mm']:.3f}, {p['tap_rpm']}, {p['tap_rpm']})",
        "G0 X150.000 Z150.000 M9",
        "M30",
        "KONTUR_OD:",
        f"G1 X{p['finish_od_mm'] - 2.0:.3f} Z0.000",
        f"G1 X{p['finish_od_mm']:.3f} Z-1.000",
        f"G1 Z-{p['length_mm']:.3f}",
        f"G1 X{p['od_mm'] + 2.0:.3f}",
        "RET",
    ]
    return "\n".join(lines)


def _build_heidenhain_gcode(p: dict[str, Any]) -> str:
    lines = [
        f"0 BEGIN PGM {p['part_no']} MM",
        f"1 ; MATERIAL: {p['material']} - HEIDENHAIN TNC 640",
        f"2 BLK FORM 0.1 Z X+0 Y+0 Z-{p['length_mm']:.3f}",
        f"3 BLK FORM 0.2 X+{p['od_mm']:.3f} Y+{p['od_mm']:.3f} Z+0.000",
        f"4 TOOL CALL 1 Z S{p['vc_m_min']} F250",
        "5 L Z+100.000 R0 FMAX M3",
        "6 CYCL DEF 200 DRILLING ~",
        "    Q200=+2.000 ;SET-UP CLEARANCE ~",
        f"    Q201=-{p['hole_depth_mm']:.3f} ;DEPTH ~",
        "    Q206=+160.0 ;FEED RATE FOR PLUNGING ~",
        "    Q202=+4.000 ;PLUNGING DEPTH ~",
        "    Q210=+0.000 ;DWELL TIME AT TOP ~",
        "    Q203=+0.000 ;SURFACE COORDINATE ~",
        "    Q204=+50.000 ;2ND SET-UP CLEARANCE ~",
        "    Q211=+0.100 ;DWELL TIME AT DEPTH",
        "7 L X+0.000 Y+0.000 R0 FMAX M99",
        f"8 TOOL CALL 2 Z S{p['tap_rpm']}",
        "9 CYCL DEF 207 RIGID TAPPING ~",
        "    Q200=+3.000 ;SET-UP CLEARANCE ~",
        f"    Q201=-{p['thread_depth_mm']:.3f} ;DEPTH OF THREAD ~",
        f"    Q239=+{p['thread_pitch_mm']:.3f} ;THREAD PITCH ~",
        "    Q203=+0.000 ;SURFACE COORDINATE ~",
        "    Q204=+50.000 ;2ND SET-UP CLEARANCE",
        "10 L X+0.000 Y+0.000 R0 FMAX M99",
        "11 L Z+150.000 R0 FMAX M30",
        f"12 END PGM {p['part_no']} MM",
    ]
    return "\n".join(lines)


def _build_haas_gcode(p: dict[str, Any]) -> str:
    lines = [
        "%",
        f"O00100 ({p['part_no']} - HAAS NGC - {p['material']})",
        "G21 G17 G40 G80 G90 G99",
        "G28 U0. W0.",
        "T0101 (ROUGH TURNING CNMG 120408)",
        f"G50 S{p['max_rpm']}",
        f"G96 S{p['vc_m_min']} M03",
        f"G00 X{p['od_mm'] + 2.0:.3f} Z2.000 M08",
        f"G71 P10 Q20 U0.300 W0.100 D{p['ap_mm']:.3f} F{p['feed_rough']:.2f}",
        f"N10 G00 X{p['finish_od_mm'] - 2.0:.3f}",
        "G01 Z0.000 F0.15",
        f"G01 X{p['finish_od_mm']:.3f} Z-1.000",
        f"G01 Z-{p['length_mm']:.3f}",
        f"N20 G01 X{p['od_mm'] + 2.0:.3f}",
        "T0202 (FINISH TURNING DNMG 150604)",
        f"G96 S{int(p['vc_m_min'] * 1.2)} M03",
        f"G70 P10 Q20 F{p['feed_finish']:.2f}",
        f"T0303 (PECK DRILL D{p['hole_dia_mm']:.1f})",
        "G97 S1200 M03",
        "G00 X0.000 Z5.000",
        f"G83 X0.000 Z-{p['hole_depth_mm']:.3f} R2.000 Q4.000 F0.12",
        "G80",
        "T0404 (RIGID TAP)",
        f"G97 S{p['tap_rpm']} M03",
        "G00 X0.000 Z5.000",
        f"G84 X0.000 Z-{p['thread_depth_mm']:.3f} R3.000 F{p['thread_pitch_mm']:.3f}",
        "G80",
        "G28 U0. W0. M09",
        "M30",
        "%",
    ]
    return "\n".join(lines)


def _build_fanuc_gcode(p: dict[str, Any]) -> str:
    lines = [
        "%",
        f"O1001 ({p['part_no']} - FANUC 0I/31I - {p['material']})",
        "G21 G40 G80 G99",
        "G28 U0. W0.",
        "T0101 (ROUGH TURN CNMG120408)",
        f"G50 S{p['max_rpm']}",
        f"G96 S{p['vc_m_min']} M03",
        f"G00 X{p['od_mm'] + 2.0:.3f} Z2.000 M08",
        f"G71 U{p['ap_mm']:.2f} R0.50",
        f"G71 P10 Q20 U0.30 W0.10 F{p['feed_rough']:.2f}",
        f"N10 G00 X{p['finish_od_mm'] - 2.0:.3f}",
        "G01 Z0.000 F0.15",
        f"G01 X{p['finish_od_mm']:.3f} Z-1.000",
        f"G01 Z-{p['length_mm']:.3f}",
        f"N20 G01 X{p['od_mm'] + 2.0:.3f}",
        "T0202 (FINISH TURN DNMG150604)",
        f"G96 S{int(p['vc_m_min'] * 1.2)} M03",
        f"G70 P10 Q20 F{p['feed_finish']:.2f}",
        f"T0303 (DEEP HOLE PECK DRILL D{p['hole_dia_mm']:.1f})",
        "G97 S1200 M03",
        "G00 X0.000 Z5.000",
        f"G83 X0.000 Z-{p['hole_depth_mm']:.3f} R2.000 Q4.000 F160.0",
        "G80",
        "T0404 (RIGID TAP)",
        f"M29 S{p['tap_rpm']}",
        f"G98 G84 Z-{p['thread_depth_mm']:.3f} R3.000 F{p['tap_feed_mm_min']:.1f}",
        "G80 G99",
        "G28 U0. W0. M09",
        "M30",
        "%",
    ]
    return "\n".join(lines)


def generate_multi_controller_gcode(controller: str, part_spec: dict[str, Any]) -> str:
    """Generate collision-safe CNC G-code for Fanuc 0i/31i, Siemens Sinumerik 840D/One, Heidenhain TNC 640, or Haas NGC."""
    ctrl = (controller or "fanuc").strip().lower()
    params = _extract_gcode_params(part_spec)
    if "siemens" in ctrl or "840d" in ctrl or "sinumerik" in ctrl:
        return _build_siemens_gcode(params)
    if "heidenhain" in ctrl or "tnc" in ctrl:
        return _build_heidenhain_gcode(params)
    if "haas" in ctrl:
        return _build_haas_gcode(params)
    return _build_fanuc_gcode(params)


_CMM_OFFSET_EXTRA_POS = ("measurements", "tolerance_plus", "tolerance_minus")


def generate_cmm_wear_offset_gcode(
    controller: str,
    tool_no: int,
    nominal: float,
    measured_mean: float,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute CMM dimensional wear deviation and output closed-loop CNC wear offset update G-code."""
    extra = dict(zip(_CMM_OFFSET_EXTRA_POS, args, strict=False))
    extra.update(kwargs)
    measurements: list[float] | None = extra.get("measurements")
    tolerance_plus = float(extra.get("tolerance_plus", 0.025))
    tolerance_minus = float(extra.get("tolerance_minus", -0.025))

    ctrl = (controller or "fanuc").strip().lower()
    t_no = max(int(tool_no), 1)
    deviation = round(float(measured_mean) - float(nominal), 4)
    compensation = round(-deviation, 4)

    if "siemens" in ctrl or "840d" in ctrl or "sinumerik" in ctrl:
        offset_cmd = f"$TC_DP12[{t_no},1] = {compensation:+.4f}"
    elif "heidenhain" in ctrl or "tnc" in ctrl:
        offset_cmd = f"TOOL DEF {t_no} L+0 R{compensation:+.4f}"
    elif "haas" in ctrl:
        offset_cmd = f"G10 L12 P{t_no} R{compensation:+.4f}"
    else:
        offset_cmd = f"G10 L11 P{t_no:02d} R{compensation:+.4f}"

    samples = [float(x) for x in (measurements or [measured_mean])]
    usl = float(nominal) + abs(tolerance_plus)
    lsl = float(nominal) - abs(tolerance_minus)
    mean_val = sum(samples) / len(samples)
    if len(samples) > 1:
        variance = sum((x - mean_val) ** 2 for x in samples) / (len(samples) - 1)
        sigma = max(math.sqrt(variance), 1e-6)
    else:
        sigma = max((usl - lsl) / 8.0, 1e-6)

    cp = (usl - lsl) / (6.0 * sigma)
    cpk = min((usl - mean_val) / (3.0 * sigma), (mean_val - lsl) / (3.0 * sigma))

    return {
        "controller": ctrl,
        "tool_no": t_no,
        "nominal_mm": round(float(nominal), 4),
        "measured_mean_mm": round(float(measured_mean), 4),
        "deviation_mm": deviation,
        "wear_compensation_mm": compensation,
        "offset_gcode": offset_cmd,
        "spc": {
            "usl_mm": round(usl, 4),
            "lsl_mm": round(lsl, 4),
            "cp": round(cp, 3),
            "cpk": round(cpk, 3),
            "action_required": abs(deviation) > 0.002,
        },
    }
