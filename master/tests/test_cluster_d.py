"""Unit tests for Cluster D: 3D CAD/CAM, Cutting Physics & FEA, CMM G10 Offset, Nesting, Job-Shop Scheduling, RBAC, Audit Chain, and MCP."""

from __future__ import annotations

from pathlib import Path

import pytest

import cad_cam_physics
import config
import enterprise_security_mcp
import erp_mes_scheduler

SAMPLE_STEP_CONTENT = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Aerospace Flanged Housing'),'2;1');
FILE_NAME('FLANGE_HOUSING.STEP','2026-11-23T12:00:00',('Engineer'),('AeroCorp'),'','','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#1 = PRODUCT('AERO_FLANGE_4140','AERO_FLANGE_4140','',(#2));
#10 = CARTESIAN_POINT('Origin',(0.0,0.0,0.0));
#11 = CARTESIAN_POINT('P1',(-40.0,-40.0,0.0));
#12 = CARTESIAN_POINT('P2',(40.0,40.0,55.0));
#13 = CARTESIAN_POINT('P3',(20.0,20.0,25.0));
#20 = CYLINDRICAL_SURFACE('OuterOD',#10,40.0);
#21 = CYLINDRICAL_SURFACE('InnerBore',#10,16.0);
#22 = CYLINDRICAL_SURFACE('ThinSleeve',#10,37.5);
#30 = PLANE('TopFace',#10);
#31 = PLANE('BottomFace',#11);
#32 = PLANE('PocketFloor',#13);
#40 = CONICAL_SURFACE('EntryChamfer',#10,16.5,0.785398);
#41 = TOROIDAL_SURFACE('RootFillet',#10,20.0,2.5);
#50 = CIRCLE('HoleCircle',#10,16.0);
#51 = CIRCLE('OuterCircle',#10,40.0);
#60 = ADVANCED_FACE('F_OD',(#20),#20,.T.);
#61 = ADVANCED_FACE('F_BORE',(#21),#21,.F.);
#62 = ADVANCED_FACE('F_TOP',(#30),#30,.T.);
#63 = ADVANCED_FACE('F_POCKET',(#32),#32,.T.);
#70 = CLOSED_SHELL('SolidBody',(#60,#61,#62,#63));
ENDSEC;
END-ISO-10303-21;
"""

SAMPLE_STL_CONTENT = b"""solid test_block
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 40 0 0
      vertex 40 30 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 20
      vertex 40 30 20
      vertex 0 30 20
    endloop
  endfacet
endsolid test_block
"""


def test_analyze_3d_cad_step_and_stl() -> None:
    res = cad_cam_physics.analyze_3d_cad_file("aero_flange.step", SAMPLE_STEP_CONTENT)
    assert res["format"] == "STEP"
    assert res["product_name"] == "AERO_FLANGE_4140"
    assert res["entity_counts"]["CYLINDRICAL_SURFACE"] == 3
    assert res["entity_counts"]["PLANE"] == 3
    assert res["entity_counts"]["CONICAL_SURFACE"] == 1
    assert res["entity_counts"]["TOROIDAL_SURFACE"] == 1
    assert res["entity_counts"]["ADVANCED_FACE"] == 4
    assert res["entity_counts"]["CLOSED_SHELL"] == 1

    bbox = res["bounding_box_mm"]
    assert bbox["x"] == pytest.approx(80.0)
    assert bbox["y"] == pytest.approx(80.0)
    assert bbox["z"] == pytest.approx(55.0)
    assert res["volume_cm3"] > 50.0

    ftypes = set(res["feature_types"])
    for expected in ("THROUGH_HOLE", "BLIND_HOLE", "TURNED_OD", "POCKET", "BOSS", "CHAMFER", "FILLET", "THIN_WALL"):
        assert expected in ftypes

    assert len(res["mbd_2d_3d_matches"]) == len(res["features"])
    assert res["mbd_2d_3d_matches"][0]["face_id"].startswith("#")

    stl_res = cad_cam_physics.analyze_3d_cad_file("bracket.stl", SAMPLE_STL_CONTENT)
    assert stl_res["format"] == "STL"
    assert stl_res["bounding_box_mm"]["x"] == pytest.approx(40.0)
    assert stl_res["bounding_box_mm"]["y"] == pytest.approx(30.0)
    assert stl_res["bounding_box_mm"]["z"] == pytest.approx(20.0)
    assert stl_res["volume_cm3"] > 0.0


def test_multi_controller_gcode_generation() -> None:
    spec = {
        "part_number": "SHAFT_4140",
        "material": "AISI 4140",
        "outer_diameter_mm": 60.0,
        "finish_od_mm": 54.0,
        "length_mm": 90.0,
        "hole_diameter_mm": 10.0,
        "hole_depth_mm": 35.0,
        "thread_pitch_mm": 1.5,
        "thread_depth_mm": 22.0,
        "vc_m_min": 180,
        "max_rpm": 2500,
    }

    fanuc_nc = cad_cam_physics.generate_multi_controller_gcode("fanuc", spec)
    assert "G50 S2500" in fanuc_nc
    assert "G71 U2.00 R0.50" in fanuc_nc
    assert "G70 P10 Q20" in fanuc_nc
    assert "G83" in fanuc_nc
    assert "G84" in fanuc_nc

    siemens_nc = cad_cam_physics.generate_multi_controller_gcode("siemens", spec)
    assert "LIMS=2500" in siemens_nc
    assert "CYCLE95" in siemens_nc
    assert "CYCLE83" in siemens_nc
    assert "CYCLE84" in siemens_nc

    heidenhain_nc = cad_cam_physics.generate_multi_controller_gcode("heidenhain", spec)
    assert "BEGIN PGM SHAFT_4140 MM" in heidenhain_nc
    assert "TOOL CALL" in heidenhain_nc
    assert "CYCL DEF 200 DRILLING" in heidenhain_nc
    assert "CYCL DEF 207 RIGID TAPPING" in heidenhain_nc

    haas_nc = cad_cam_physics.generate_multi_controller_gcode("haas", spec)
    assert "HAAS NGC" in haas_nc
    assert "G71 P10 Q20" in haas_nc
    assert "G83" in haas_nc


def test_cutting_physics_and_fea_simulation() -> None:
    sim = cad_cam_physics.simulate_cutting_physics_and_fea(
        material="AISI 4140",
        vc_m_min=180.0,
        ap_mm=3.0,
        feed_mm_rev=0.25,
        kappa_r_deg=90.0,
        cutter_diameter_mm=50.0,
        spindle_efficiency=0.85,
        tool_stickout_mm=70.0,
        tool_shank_diameter_mm=12.0,
        tool_material="steel",
        nose_radius_mm=0.8,
        chuck_clamp_force_n=25000.0,
        ring_mean_radius_mm=40.0,
        grip_length_mm=18.0,
        wall_thickness_mm=2.0,
        tolerance_band_mm=0.020,
        max_spindle_power_kw=15.0,
    )
    # Kienzle check: kc1.1 = 2100, b = 3.0, h = 0.25, mc = 0.25 -> Fc = 2100 * 3 * 0.25^0.75 = 2227.386 N
    assert sim["cutting_force_fc_n"] == pytest.approx(2100.0 * 3.0 * (0.25**0.75), rel=1e-3)
    assert sim["spindle_power_kw"] > 5.0
    assert sim["spindle_torque_nm"] > 40.0
    assert sim["taylor_tool_life_min"] > 1.0
    assert sim["tool_deflection_mm"] > 0.005
    assert sim["chuck_ovalization_mm"] > 0.006
    # Theoretical Ra = (0.25^2 / (32 * 0.8)) * 1000 = 2.441 um
    assert sim["surface_roughness_ra_um"] == pytest.approx(2.441, rel=1e-2)
    assert len(sim["dfm_warnings"]) >= 2


def test_closed_loop_cmm_wear_offset_gcode() -> None:
    fanuc_off = cad_cam_physics.generate_cmm_wear_offset_gcode(
        controller="fanuc",
        tool_no=1,
        nominal=42.000,
        measured_mean=42.012,
        measurements=[42.011, 42.012, 42.013, 42.012],
    )
    assert fanuc_off["deviation_mm"] == pytest.approx(0.012)
    assert fanuc_off["wear_compensation_mm"] == pytest.approx(-0.012)
    assert fanuc_off["offset_gcode"] == "G10 L11 P01 R-0.0120"
    assert fanuc_off["spc"]["cp"] > 1.0

    siemens_off = cad_cam_physics.generate_cmm_wear_offset_gcode("siemens", 2, 25.0, 24.992)
    assert siemens_off["offset_gcode"] == "$TC_DP12[2,1] = +0.0080"

    heid_off = cad_cam_physics.generate_cmm_wear_offset_gcode("heidenhain", 3, 50.0, 50.015)
    assert heid_off["offset_gcode"] == "TOOL DEF 3 L+0 R-0.0150"


def test_1d_bar_and_2d_sheet_nesting_optimizer() -> None:
    bar_res = erp_mes_scheduler.optimize_1d_bar_nesting(
        stock_length_mm=6000.0,
        kerf_mm=3.0,
        parts=[
            {"part_id": "SHAFT-A", "length_mm": 2200.0, "quantity": 2},
            {"part_id": "SHAFT-B", "length_mm": 1500.0, "quantity": 3},
            {"part_id": "PIN-C", "length_mm": 800.0, "quantity": 2},
        ],
    )
    assert bar_res["total_parts_nested"] == 7
    assert bar_res["bar_count"] == 2
    assert bar_res["material_utilization_percent"] > 85.0
    assert bar_res["scrap_percent"] < 15.0

    sheet_res = erp_mes_scheduler.optimize_2d_sheet_nesting(
        sheet_width_mm=2000.0,
        sheet_height_mm=1000.0,
        kerf_mm=2.0,
        parts=[
            {"part_id": "PANEL-1", "width_mm": 950.0, "height_mm": 480.0, "quantity": 4},
            {"part_id": "GUSSET-2", "width_mm": 400.0, "height_mm": 300.0, "quantity": 2},
        ],
    )
    assert sheet_res["total_parts_nested"] == 6
    assert sheet_res["sheet_count"] == 2
    assert sheet_res["material_utilization_percent"] > 50.0


def test_finite_capacity_cnc_job_shop_scheduler() -> None:
    jobs = [
        {
            "job_id": "JOB-101",
            "quantity": 2,
            "due_date_min": 300.0,
            "operations": [
                {"op_code": "OP10", "machine": "CNC-TURN-01", "setup_min": 15.0, "run_min": 25.0},
                {"op_code": "OP20", "machine": "CNC-MILL-01", "setup_min": 20.0, "run_min": 30.0},
                {"op_code": "OP30", "machine": "CMM-01", "setup_min": 10.0, "run_min": 10.0},
            ],
        },
        {
            "job_id": "JOB-102",
            "quantity": 1,
            "due_date_min": 200.0,
            "operations": [
                {"op_code": "OP10", "machine": "CNC-TURN-01", "setup_min": 10.0, "run_min": 35.0},
                {"op_code": "OP20", "machine": "CNC-MILL-01", "setup_min": 15.0, "run_min": 25.0},
            ],
        },
    ]
    machines = ["CNC-TURN-01", "CNC-MILL-01", "CMM-01"]
    sched = erp_mes_scheduler.schedule_cnc_job_shop(jobs, machines)

    assert sched["total_operations_scheduled"] == 5
    assert sched["makespan_min"] > 0
    assert set(sched["machine_utilization_percent"].keys()) == set(machines)

    # Verify precedence: for each job, OP10 ends <= OP20 starts <= OP30 starts
    by_job: dict[str, list[dict]] = {}
    for bar in sched["gantt_bars"]:
        by_job.setdefault(bar["job_id"], []).append(bar)
    for job_bars in by_job.values():
        for i in range(len(job_bars) - 1):
            assert job_bars[i]["end_min"] <= job_bars[i + 1]["start_min"] + 1e-6


def test_rbac_manager_roles_passwords_and_tokens() -> None:
    rbac = enterprise_security_mcp.RBACManager(secret_key="unit-test-secret-key", iterations=15_000)
    assert len(rbac.ROLES) == 6
    for role in ("admin", "lead_engineer", "developer", "cam_programmer", "quality_inspector", "operator"):
        rbac.register_user(f"user_{role}", f"Pass_{role}_2026!", role)

    token_cam = rbac.authenticate("user_cam_programmer", "Pass_cam_programmer_2026!")
    claims = rbac.verify_token(token_cam)
    assert claims["sub"] == "user_cam_programmer"
    assert claims["role"] == "cam_programmer"

    assert rbac.has_permission(token_cam, "cam:generate") is True
    assert rbac.has_permission(token_cam, "users:manage") is False
    assert rbac.has_permission("admin", "users:manage") is True
    assert rbac.has_permission("operator", "cam:generate") is False

    with pytest.raises(PermissionError):
        rbac.authenticate("user_cam_programmer", "WrongPassword")


def test_as9100_audit_trail_and_mcp_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    audit = enterprise_security_mcp.AuditTrail()
    assert audit.log_path == tmp_path / "audit_chain.jsonl"

    e1 = audit.append_event("user_cam", "GENERATE_GCODE", {"part": "AERO_101", "controller": "siemens"})
    e2 = audit.append_event("user_qa", "APPLY_CMM_OFFSET", {"tool": 1, "offset_mm": -0.012})

    assert e1["prev_hash"] == audit.GENESIS_HASH
    assert e2["prev_hash"] == e1["entry_hash"]
    assert audit.verify_chain() is True

    # Tamper with the log file and verify that verify_chain detects it
    raw_text = audit.log_path.read_text(encoding="utf-8")
    audit.log_path.write_text(raw_text.replace("-0.012", "-0.099"), encoding="utf-8")
    assert audit.verify_chain() is False

    # Test Local MCP Tool Registry
    registry = enterprise_security_mcp.MCPRegistry()
    registry.register_tool(
        name="calc_spindle_rpm",
        description="Calculate spindle RPM from cutting speed Vc and diameter D",
        input_schema={
            "type": "object",
            "properties": {
                "vc_m_min": {"type": "number"},
                "diameter_mm": {"type": "number"},
            },
            "required": ["vc_m_min", "diameter_mm"],
        },
        handler=lambda vc_m_min, diameter_mm: round((1000.0 * vc_m_min) / (3.14159265 * diameter_mm), 1),
    )

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "calc_spindle_rpm"

    inv = registry.invoke_tool("calc_spindle_rpm", {"vc_m_min": 180.0, "diameter_mm": 50.0})
    assert inv["status"] == "ok"
    assert inv["result"] == pytest.approx(1145.9, rel=1e-3)
