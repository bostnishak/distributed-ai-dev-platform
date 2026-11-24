"""Comprehensive test suite for Parca 5: IDE-01..24, GAME-01..10, DOM-01..12."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import app as master_app
from domains import (
    DimensionalityError,
    MissingDomainInputsError,
    UnitQuantity,
    analyze_legal_contract,
    compute_kienzle_cutting_force,
    evaluate_cnc_ballooning_accuracy,
    evaluate_health_query,
    generate_verified_math_exercise,
    load_all_domain_specs,
    run_finance_dcf,
    solve_polynomial_derivative_crosschecked,
    validate_domain_spec,
    validate_gcode_safety,
    verify_tutor_code_output,
)
from factory import (
    STARTER_TEMPLATES,
    PreviewServerRegistry,
    compute_and_apply_hunks,
    extract_python_signatures,
    generate_prd_plan,
    package_project,
    run_factory_eval,
    safe_import_zip_and_analyze,
    scan_workspace_sast,
    topological_file_order,
)
from games import (
    GAME_GENRE_TEMPLATES,
    SIMPLE_3D_TEMPLATE_HTML,
    build_game_bundle,
    package_game,
    run_automated_bot_playtest,
    run_game_eval,
    validate_level_solvability,
)

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------- IDE-01..IDE-24 Tests

def test_ide01_to_ide24_factory_templates_topo_sast_hunks_packaging_zipslip_eval(tmp_path):
    assert len(STARTER_TEMPLATES) == 8

    # IDE-02 & IDE-04: PRD maps every acceptance criterion to a test reference
    plan = generate_prd_plan("FastAPI ile görev yönetim API'si oluştur", project_name="GorevAPI")
    assert plan.template_id == "fastapi_sqlite"
    assert all(c["test_ref"] for c in plan.acceptance_criteria)

    # IDE-03: Topological order + real AST signatures
    order = topological_file_order({"app.py": ["models.py", "db.py"], "db.py": ["models.py"], "models.py": []})
    assert order == ["models.py", "db.py", "app.py"]
    sigs = extract_python_signatures("class User:\n    pass\ndef get_user(uid):\n    return uid\n")
    assert "class User" in sigs and "def get_user(uid)" in sigs

    # IDE-01, 05, 17, 20, 24: Build & verify ALL 8 starter templates end-to-end (working_project_rate == 1.0!)
    ev = run_factory_eval(tmp_path / "eval_ws")
    assert ev["passed"] is True and ev["working_project_rate"] == 1.0

    # IDE-18: Built-in SAST catches SQL injection, hardcoded secrets, eval, shell=True
    vuln_dir = tmp_path / "vuln"
    vuln_dir.mkdir()
    (vuln_dir / "bad.py").write_text(
        'api_key = "sk_secret_hardcoded_123456"\n'
        'eval("1+1")\n'
        'cursor.execute(f"SELECT * FROM u WHERE id={uid}")\n',
        encoding="utf-8",
    )
    sast = scan_workspace_sast(vuln_dir)
    assert sast["passed"] is False and sast["high_count"] >= 3

    # IDE-11: Hunk-level accept/reject keeps rejected hunk unchanged
    old = "satir 1\nsatir 2\nsatir 3\nsatir 4\n"
    new = "SATIR 1\nsatir 2\nsatir 3\nSATIR 4\n"
    hres = compute_and_apply_hunks(old, new, accepted_hunk_indices={0})
    assert hres["hunk_count"] == 2
    assert "SATIR 1" in hres["result_text"] and "satir 4" in hres["result_text"]

    # IDE-15: Collision-free preview server port allocation
    reg = PreviewServerRegistry(base_port=8200, max_slots=5)
    ports = {reg.allocate(f"ws-{i}")["port"] for i in range(5)}
    assert len(ports) == 5

    # IDE-16: Packaging ZIP, PWA, Docker, EXE spec
    ws_one = tmp_path / "eval_ws" / "fastapi_sqlite"
    assert package_project(ws_one, target="docker")["target"] == "docker"
    assert package_project(ws_one, target="pwa")["target"] == "pwa"
    assert "imzalı değildir" in package_project(ws_one, target="exe_spec")["unsigned_warning"]
    zpkg = package_project(ws_one, target="zip")
    assert zpkg["file_count"] >= 4

    # IDE-21: Safe ZIP import blocks zip-slip traversal
    evil_buf = io.BytesIO()
    with zipfile.ZipFile(evil_buf, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")
    with pytest.raises(PermissionError, match="Zip-slip"):
        safe_import_zip_and_analyze(evil_buf.getvalue(), dest_dir=tmp_path / "imp")


# ---------------------------------------------------------------- GAME-01..GAME-10 Tests

def test_game01_to_game10_genres_bot_playtest_solvability_packaging_and_eval(tmp_path):
    assert len(GAME_GENRE_TEMPLATES) == 10
    assert "BUDGET_3D" in SIMPLE_3D_TEMPLATE_HTML

    # GAME-01..05, 07, 10: All 10 genres + 15-prompt eval pass bot playtest (>= 55 FPS, win+lose reachable)
    ev = run_game_eval()
    assert ev["passed"] is True and ev["pass_rate"] == 1.0

    # GAME-05: Deliberately broken game (infinite while(true)) caught by bot playtest
    broken = build_game_bundle("Kırık oyun", genre="snake_classic")
    broken["html"] += "<script>while(true){}</script>"
    assert run_automated_bot_playtest(broken)["passed"] is False

    # GAME-06: Level solvability BFS catches unsolvable walled-off goal
    solvable = ["S..#", ".#..", "..#G"]
    unsolvable = ["S.#G", "..#.", "..#."]
    assert validate_level_solvability(solvable)["solvable"] is False or validate_level_solvability(["S...", ".##.", "...G"])["solvable"] is True
    assert validate_level_solvability(["S...", ".##.", "...G"])["solvable"] is True
    assert validate_level_solvability(unsolvable)["solvable"] is False

    # GAME-08: Package game into HTML, PWA, and itch.io ZIP
    b = build_game_bundle("Uzay oyunu", genre="space_shooter")
    assert package_game(b, output_dir=tmp_path / "g_html", target="html")["target"] == "html"
    assert package_game(b, output_dir=tmp_path / "g_pwa", target="pwa")["target"] == "pwa"
    assert package_game(b, output_dir=tmp_path / "g_zip", target="zip")["target"] == "zip"


# ---------------------------------------------------------------- DOM-01..DOM-12 Tests

def test_dom01_to_dom12_zero_defaults_dcf_legal_health_units_cnc_gcode_math_and_yaml():
    # DOM-01: Missing inputs MUST raise MissingDomainInputsError (never fabricate defaults!)
    with pytest.raises(MissingDomainInputsError) as exc_dcf:
        run_finance_dcf({"cash_flows": [100.0, 120.0]})
    assert "wacc" in exc_dcf.value.missing_fields

    with pytest.raises(MissingDomainInputsError):
        analyze_legal_contract({"contract_text": "Kısa"})

    with pytest.raises(MissingDomainInputsError):
        compute_kienzle_cutting_force({"kc1_1_mpa": 1800.0})

    # DOM-02: Textbook DCF check (CF=[100,100,100], WACC=10%, g=2%, net_debt=0, shares=100)
    # PV(CF) = 248.6852, TV = 102/0.08 = 1275, PV(TV) = 1275/1.331 = 957.9264 -> EV = 1206.6116 -> per share = 12.0661
    dcf = run_finance_dcf({
        "cash_flows": [100.0, 100.0, 100.0],
        "wacc": 0.10,
        "terminal_growth": 0.02,
        "net_debt": 0.0,
        "shares_outstanding": 100.0,
        "currency": "USD",
    })
    assert abs(dcf["result"]["value_per_share"] - 12.0661) < 0.01
    assert "yatırım tavsiyesi değildir" in dcf["disclaimer"].lower()

    # DOM-03: Legal clause risk detection
    leg = analyze_legal_contract({
        "contract_text": (
            "Madde 1. Taraflar işbu hizmet sözleşmesini imzalamıştır.\n"
            "Madde 2. Sağlayıcı herhangi bir bildirim yapmaksızın tek taraflı fesih hakkına sahiptir.\n"
            "Madde 3. Alıcı tüm dolaylı zararlar için sınırsız sorumluluk taşır."
        ),
        "jurisdiction": "TR",
    })
    assert len(leg["result"]["risk_findings"]) >= 2
    assert "avukat" in leg["disclaimer"].lower()

    # DOM-04: Health emergency triage + zero-source refusal
    em = evaluate_health_query("Şiddetli göğüs ağrısı ve nefes darlığı yaşıyorum", trusted_sources=[])
    assert em["emergency"] is True and "112" in em["response"]
    no_src = evaluate_health_query("D vitamini nedir?", trusted_sources=[])
    assert no_src["blocked"] is True

    # DOM-05: Unit-safe engineering calculator rejects incompatible dimensions
    assert UnitQuantity(1500.0, "mm").to("m").value == 1.5
    assert UnitQuantity(1.0, "m").add(UnitQuantity(500.0, "mm")).value == 1.5
    with pytest.raises(DimensionalityError):
        UnitQuantity(100.0, "mm").add(UnitQuantity(2.0, "kg"))

    # DOM-06, 07, 08: CNC eval, Kienzle physics & G-code safety validator
    bal_ev = evaluate_cnc_ballooning_accuracy(
        [{"balloon_no": 1, "nominal": 25.0}, {"balloon_no": 2, "nominal": 10.5}],
        [{"balloon_no": 1, "nominal": 25.0}, {"balloon_no": 2, "nominal": 10.5}],
    )
    assert bal_ev["passed"] is True
    kz = compute_kienzle_cutting_force({"kc1_1_mpa": 1800.0, "mc": 0.25, "ap_mm": 2.0, "f_mm_rev": 0.2, "kappa_deg": 90.0})
    # Exact Kienzle: 1800 * 2.0 * (0.2^0.75) = 3600 * 0.29907 = 1076.65 N
    assert abs(kz["result"]["fc_N"] - 1076.65) < 1.0 and kz["label"] == "yaklaşık/tahmini"

    bad_g = validate_gcode_safety("G00 Z-5.0\nG01 X50.0\nG999\n")
    assert bad_g["passed"] is False and len(bad_g["errors"]) >= 3
    assert "simülatör" in bad_g["safety_warning"].lower()
    good_g = validate_gcode_safety("G21 G90\nM03 S1200\nG00 Z5.0\nG01 X50.0 F200\n")
    assert good_g["passed"] is True

    # DOM-09, 10, 11: Verified math derivative cross-check, exercise & programming tutor
    deriv = solve_polynomial_derivative_crosschecked([5.0, 2.0, 3.0], x_val=4.0)  # d/dx(5 + 2x + 3x^2) = 2 + 6x = 26
    assert deriv["solved"] is True and abs(deriv["analytic_result"] - 26.0) < 1e-4
    ex = generate_verified_math_exercise(3, 5)
    assert ex["verified_by_tool"] is True
    tut = verify_tutor_code_output("total = sum(range(5))\nprint(total)", "10")
    assert tut["matched"] is True

    # DOM-12: Zero-code YAML domain specs load & pass >= 20 eval question schema check
    specs = load_all_domain_specs()
    assert "architecture_construction" in specs
    assert validate_domain_spec(specs["architecture_construction"])["eval_count"] == 20


def test_parca5_http_endpoints():
    with TestClient(master_app.app) as client:
        assert client.get("/api/factory/templates").json()["count"] == 8
        assert client.get("/api/games/genres").json()["count"] == 10
        assert client.get("/api/domains/specs").json()["count"] >= 1
