"""G-code generation: parameters become real, checked toolpaths."""

from __future__ import annotations

import itertools
import re

import pytest

import gcode_chat as gc
import gcode_gen as gg
import gcode_patterns as gpat

pytestmark = pytest.mark.unit

RAW = {"material": "6061 alüminyum", "stock": {"x": 60, "y": 40, "z": 12},
       "operations": [{"type": "hole", "diameter": 14, "through": True}, {"type": "holes", "pattern": "corners", "diameter": 5, "through": True}]}


def _prog(raw=RAW, request=""):
    job, question = gc.build_job(raw, request)
    assert job is not None, question
    return job, gg.generate(job)


def _text(prog):
    return "\n".join(prog.lines)


def test_request_detection():
    assert gc.is_gcode_request("60x40 blok için G-code yaz", False)
    assert gc.is_gcode_request("CNC freze programı hazırla", False)
    assert not gc.is_gcode_request("G-code nedir?", False)
    assert not gc.is_gcode_request("G-code yaz", True)


def test_speeds_follow_material_and_tool():
    _job, prog = _prog()
    mill = prog.tools[0]
    assert mill["kind"] == "mill" and 9000 <= mill["rpm"] <= 10000  # Vc 300 m/min on a 10 mm cutter
    assert prog.tools[1]["kind"] == "drill" and prog.tools[1]["feed"] < mill["feed"]


def test_big_hole_is_climb_helical_and_small_holes_are_pecked_at_corners():
    _, prog = _prog()
    text = _text(prog)
    assert re.search(r"G2 X32 Y20 Z-[\d.]+ I-2 J0", text)  # (14 - 10) / 2 = 2 mm path radius, clockwise = climb inside a hole
    assert "G83" in text and "X8 Y8" in text and "X52 Y32" in text and "G80" in text


def test_program_is_checked_and_warns_about_through_cuts():
    _, prog = _prog()
    assert prog.stats["min_z"] <= -12 and prog.stats["cut_mm"] > 100
    assert any("altlık" in w for w in prog.warnings)


def test_hole_too_close_to_edge_is_reported():
    _, prog = _prog({**RAW, "operations": [{"type": "holes", "points": [[3, 20]], "diameter": 5}]})
    assert any("kenar" in w for w in prog.warnings)


def test_missing_numbers_become_questions_not_guesses():
    assert gc.build_job({"stock": {"x": 60, "y": None, "z": 12}, "operations": [{"type": "face"}]})[0] is None
    assert gc.build_job({"stock": {"x": 60, "y": 40, "z": 12}, "operations": [{"type": "hole"}]})[0] is None
    assert gc.build_job({"stock": {"x": 60, "y": 40, "z": 12}, "operations": []})[1]
    assert "PCD" in gc.build_job({"stock": {"x": 60, "y": 40, "z": 12}, "operations": [{"type": "holes", "pattern": "circle", "diameter": 5}]})[1]
    assert "derinliğini" in gc.build_job({"stock": {"x": 60, "y": 40, "z": 12}, "operations": [{"type": "pocket", "width": 10, "length": 10}]})[1]


def test_grbl_has_no_tool_change_and_no_canned_cycles():
    _, prog = _prog({**RAW, "flavor": "grbl"})
    text = _text(prog)
    assert "M6" not in text and "G83" not in text and "G81" not in text and "M0 (CHANGE TOOL" in text


def test_operations_the_user_never_asked_for_are_dropped():
    raw = {**RAW, "operations": [{"type": "face", "depth": 0.5}, {"type": "hole", "diameter": 14}]}
    job, _ = gc.build_job(raw, "ortasına 14 mm delik açacak G-code yaz")
    assert [op["type"] for op in job.ops] == ["holes"]
    job2, _ = gc.build_job(raw, "önce yüzey frezeleme sonra 14 mm delik G-code yaz")
    assert {op["type"] for op in job2.ops} == {"face", "holes"}


def test_bolt_circle_grid_and_ordering():
    stock = (100.0, 100.0, 10.0)
    pts = gpat.hole_points({"pattern": "circle", "pcd": 60, "count": 6}, stock)
    assert len(pts) == 6 and all(abs(((x - 50) ** 2 + (y - 50) ** 2) ** 0.5 - 30) < 1e-3 for x, y in pts)
    grid = gpat.hole_points({"pattern": "grid", "nx": 4, "ny": 3, "pitch_x": 25, "pitch_y": 25}, stock)
    assert len(grid) == 12 and min(p[0] for p in grid) == 12.5 and max(p[0] for p in grid) == 87.5
    # nearest-neighbour ordering never jumps back and forth across the part
    assert sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in itertools.pairwise(grid)) <= 11 * 25 + 1e-6


def test_pocket_enters_with_a_helix_in_equal_layers_and_finishes_walls():
    raw = {"material": "çelik", "stock": {"x": 80, "y": 60, "z": 20}, "operations": [{"type": "pocket", "width": 40, "length": 25, "depth": 8}]}
    _job, prog = _prog(raw)
    text = _text(prog)
    assert "(finish walls at full depth)" in text and re.search(r"G2 X[\d.]+ Y30 Z-2 I-3.5", text)
    depths = sorted({float(m) for m in re.findall(r"G2 X[\d.]+ Y[\d.]+ Z(-[\d.]+) I", text)}, reverse=True)
    assert depths[-1] == -8 and all(abs(b - a + 2) < 1e-6 for a, b in itertools.pairwise(depths))  # equal 2 mm layers
    assert not re.search(r"G1 Z-[\d.]+ F", text.split("(POCKET")[1].split("finish")[0].replace("G1 Z0 F", ""))  # never plunges into the pocket
    assert prog.stats["bounds"][0] >= 25 - 1e-6 and prog.stats["bounds"][2] <= 55 + 1e-6  # tool centre stays inside 40 mm minus the cutter


def test_auto_tool_fits_narrow_features_and_slot_is_ramped():
    job, prog = _prog({"material": "pirinç", "stock": {"x": 70, "y": 50, "z": 10}, "operations": [{"type": "slot", "length": 40, "width": 8, "depth": 5}]})
    assert job.mill_dia == 6.0  # narrower than the slot so the wall loop sets the width
    text = _text(prog)
    assert re.search(r"G1 X51 Y25 Z-[\d.]+", text) and "G2 X51 Y24" in text


def test_round_parts_and_through_cuts_get_overtravel():
    _job, prog = _prog({"material": "alüminyum", "stock": {"x": 70, "y": 70, "z": 6}, "operations": [{"type": "profile", "shape": "circle", "diameter": 60}]})
    assert prog.stats["min_z"] == -6.3 and "G3 X70.2 Y35 Z-" in _text(prog)


def test_inch_input_gives_g20_program_with_converted_numbers():
    raw = {"material": "aluminum", "units": "inch", "stock": {"x": 4, "y": 3, "z": 0.5}, "operations": [{"type": "holes", "pattern": "corners", "inset": 0.5, "diameter": 0.25}]}
    job, prog = _prog(raw)
    text = _text(prog)
    assert job.stock == (101.6, 76.2, 12.7) and "G20" in text and "G21" not in text.split("(")[-1] and "X0.5 Y0.5" in text


def test_material_default_is_an_assumption_and_feed_is_modal():
    job, prog = _prog({"stock": {"x": 60, "y": 40, "z": 12}, "operations": [{"type": "pocket", "width": 30, "length": 20, "depth": 4}]})
    assert any("alüminyum" in a for a in job.assumptions)
    feeds = [m for m in re.findall(r"F(\d+)", _text(prog))]
    assert all(a != b for a, b in itertools.pairwise(feeds))  # F only when it changes


def test_engraving_uses_its_own_small_tool_and_profile_comes_last():
    _job, prog = _prog({"material": "alüminyum", "stock": {"x": 80, "y": 80, "z": 5},
                       "operations": [{"type": "profile", "depth": 5}, {"type": "engrave", "shape": "star", "diameter": 40, "points": 5, "depth": 0.6}]})
    names = [t["name"] for t in prog.tools]
    text = _text(prog)
    assert any("engraving" in n for n in names) and text.index("(ENGRAVE") < text.index("(PROFILE")
    assert not [w for w in prog.warnings if "dışına taşıyor" in w]  # lead-in/out of the contour is not an overrun
