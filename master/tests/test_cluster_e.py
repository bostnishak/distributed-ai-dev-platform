"""Unit tests for Cluster E: Domain Experts [M57] and Media Lab 2.0 & Cognitive ELO Arena [M58]."""

from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import config
import domain_experts
import media_lab_arena


def test_legal_contract_risk_and_redline_analyzer():
    contract_text = """
    MADDE 1 - FESIH: İşveren, hiçbir gerekçe göstermeksizin tek taraflı ve bildirimsiz fesih hakkına sahiptir.
    MADDE 2 - SORUMLULUK: Yüklenici, kâr kaybı dahil ve dolaylı zararlar dahil sınırsız sorumluluk kabul eder.
    MADDE 3 - CEZAI SART: Gecikme halinde sözleşme bedelinin %50'si oranında tenkis edilemez cezai şart ödenir.
    MADDE 4 - ODEME: Fatura kesildikten sonra 180 gün vade ile ödeme yapılacaktır.
    """
    result = domain_experts.analyze_legal_contract(contract_text)

    assert result["overall_risk"] == "HIGH"
    assert result["high_risk_count"] >= 3
    assert "kvkk_gdpr" in result["missing_clauses"]
    assert "force_majeure" in result["missing_clauses"]
    assert "confidentiality" in result["missing_clauses"]
    assert len(result["redline_recommendations"]) >= 5

    clause_ids = {c["clause_id"]: c for c in result["clauses"]}
    assert clause_ids["termination"]["risk_level"] == "HIGH"
    assert clause_ids["unlimited_liability"]["risk_level"] == "HIGH"
    assert clause_ids["penalty"]["risk_level"] == "HIGH"
    assert clause_ids["payment_terms"]["risk_level"] == "HIGH"


def test_cfo_financial_analysis_dcf_and_monte_carlo():
    report = domain_experts.run_cfo_financial_analysis(
        revenue=20_000_000.0,
        cogs=11_000_000.0,
        ebitda=5_000_000.0,
        net_income=3_000_000.0,
        current_assets=8_000_000.0,
        inventory=2_000_000.0,
        current_liabilities=4_000_000.0,
        total_assets=25_000_000.0,
        total_debt=5_000_000.0,
        total_equity=15_000_000.0,
        initial_fcf=3_200_000.0,
        growth_rate=0.10,
        wacc=0.09,
        terminal_growth_rate=0.025,
        initial_investment=18_000_000.0,
        monte_carlo_runs=500,
    )

    ratios = report["ratios"]
    assert ratios["current_ratio"] == 2.0
    assert ratios["quick_ratio"] == 1.5
    assert ratios["gross_margin"] == 0.45
    assert ratios["ebitda_margin"] == 0.25
    assert ratios["roe"] == 0.2
    assert ratios["roa"] == 0.12
    assert round(ratios["debt_to_equity"], 4) == 0.3333

    dcf = report["dcf"]
    assert len(dcf["projected_fcfs"]) == 5
    assert len(dcf["discounted_fcfs"]) == 5
    assert dcf["enterprise_value"] > dcf["pv_of_fcfs"]
    assert dcf["terminal_value"] > 0

    mc = report["monte_carlo"]
    assert mc["runs"] == 500
    assert mc["p10_npv"] < mc["p50_npv"] < mc["p90_npv"]
    assert 0.0 <= mc["prob_positive_npv"] <= 1.0


def test_taguchi_doe_orthogonal_arrays_and_citations():
    factors_3lvl = {
        "cutting_speed_m_min": [120, 180, 240],
        "feed_rate_mm_rev": [0.10, 0.18, 0.26],
        "depth_of_cut_mm": [1.0, 2.0, 3.0],
    }
    responses = [
        [1.42, 1.48, 1.45],
        [1.85, 1.90, 1.88],
        [2.30, 2.25, 2.28],
        [1.15, 1.12, 1.18],
        [1.60, 1.58, 1.62],
        [2.05, 2.10, 2.08],
        [0.92, 0.95, 0.90],
        [1.35, 1.32, 1.38],
        [1.75, 1.78, 1.72],
    ]
    res = domain_experts.generate_taguchi_doe(
        factors=factors_3lvl,
        responses=responses,
        objective="smaller-is-better",
    )

    assert res["orthogonal_array"] == "L9"
    assert res["num_runs"] == 9
    assert len(res["experiments"]) == 9
    # Run 7 has the lowest surface roughness (~0.92), so highest S/N under smaller-is-better
    assert res["optimal_run"]["run"] == 7
    assert "apa" in res["citations"] and "ieee" in res["citations"]
    assert "[1]" in res["citations"]["ieee"]

    # Also verify L4 and L8 selection
    res_l4 = domain_experts.generate_taguchi_doe(
        {"A": [1, 2], "B": [10, 20]},
        objective="larger-is-better",
    )
    assert res_l4["orthogonal_array"] == "L4"
    assert res_l4["num_runs"] == 4

    res_l8 = domain_experts.generate_taguchi_doe(
        {"A": [1, 2], "B": [1, 2], "C": [1, 2], "D": [1, 2]},
        objective="nominal-is-best",
    )
    assert res_l8["orthogonal_array"] == "L8"
    assert res_l8["num_runs"] == 8


def test_sqlite_introspection_erd_and_readonly_sql(tmp_path: Path):
    db_file = tmp_path / "erp_sample.db"
    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(
            """
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                salary REAL NOT NULL,
                department_id INTEGER NOT NULL REFERENCES departments(id)
            );
            INSERT INTO departments (id, name) VALUES (1, 'Engineering'), (2, 'Finance');
            INSERT INTO employees (id, name, salary, department_id) VALUES
                (1, 'Ada', 95000.0, 1),
                (2, 'Kerem', 112000.0, 1),
                (3, 'Zeynep', 88000.0, 2);
            """
        )
        conn.commit()
    finally:
        conn.close()

    res = domain_experts.introspect_sqlite_and_query(
        db_path=db_file,
        natural_query="En yüksek salary alan employees listesini getir",
    )
    assert "erDiagram" in res["er_diagram"]
    assert "departments ||--o{ employees" in res["er_diagram"]
    assert res["row_count"] == 3
    assert res["rows"][0]["name"] == "Kerem"

    # Reject mutating SQL overrides
    try:
        domain_experts.introspect_sqlite_and_query(
            db_path=db_file,
            natural_query="",
            sql_override="DROP TABLE employees",
        )
        raise AssertionError("Should have blocked mutating SQL")
    except ValueError as exc:
        assert "read-only" in str(exc).lower()


def test_document_scanner_adaptive_shadow_removal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    # Create a synthetic photographed document with a heavy diagonal shadow gradient
    w, h = 320, 220
    x_grid, y_grid = np.meshgrid(np.linspace(0.35, 1.0, w), np.linspace(0.4, 1.0, h))
    illum = (x_grid * y_grid * 240.0).astype(np.uint8)
    doc_img = Image.fromarray(illum, mode="L").convert("RGB")
    draw = ImageDraw.Draw(doc_img)
    # Dark text lines across both shadowed and bright areas
    for y in range(40, 180, 28):
        draw.line([(30, y), (290, y)], fill=(18, 18, 18), width=3)

    buf = io.BytesIO()
    doc_img.save(buf, format="PNG")

    scan_res = media_lab_arena.scan_and_clean_document_image(buf.getvalue())
    out_file = Path(scan_res["output_path"])
    assert out_file.exists()
    assert scan_res["width"] == w and scan_res["height"] == h
    # Background illumination unevenness should be drastically reduced
    assert scan_res["cleaned_illumination_std"] < scan_res["original_illumination_std"]
    assert scan_res["mean_brightness"] > 200.0


def test_visual_revision_pixel_diff_heatmap(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    img_a = Image.new("RGB", (200, 200), (245, 245, 245))
    draw_a = ImageDraw.Draw(img_a)
    draw_a.rectangle([30, 30, 170, 170], outline=(20, 20, 20), width=3)

    img_b = img_a.copy()
    draw_b = ImageDraw.Draw(img_b)
    # Modify a 40x40 region (1600 pixels out of 40000 = 4.0% area)
    draw_b.rectangle([80, 80, 119, 119], fill=(15, 15, 15))

    buf_a, buf_b = io.BytesIO(), io.BytesIO()
    img_a.save(buf_a, format="PNG")
    img_b.save(buf_b, format="PNG")

    diff_res = media_lab_arena.compute_visual_revision_diff(buf_a.getvalue(), buf_b.getvalue())
    out_path = Path(diff_res["output_path"])
    assert out_path.exists()
    assert diff_res["changed_pixels"] == 1600
    assert diff_res["changed_area_pct"] == 4.0
    assert diff_res["url"].endswith(".png")


def test_kvkk_pii_sensitive_text_redactor():
    raw_text = (
        "Müşteri TC: 28491057362, Ödeme IBAN: TR33 0006 1005 1978 6457 8413 26, "
        "Kart: 4543-1234-5678-9010, Tel: +90 532 411 22 33, E-posta: ahmet.yilmaz@example.com.tr"
    )
    redacted = media_lab_arena.redact_sensitive_pii(raw_text)

    assert redacted["has_pii"] is True
    assert redacted["total_redacted"] == 5
    assert redacted["counts"]["tc_kimlik"] == 1
    assert redacted["counts"]["iban"] == 1
    assert redacted["counts"]["credit_card"] == 1
    assert redacted["counts"]["phone"] == 1
    assert redacted["counts"]["email"] == 1

    cleaned = redacted["cleaned_text"]
    assert "28491057362" not in cleaned
    assert "TR33" not in cleaned
    assert "4543-1234" not in cleaned
    assert "532 411" not in cleaned
    assert "ahmet.yilmaz@example.com.tr" not in cleaned
    assert "[REDACTED_TC_KIMLIK]" in cleaned
    assert "[REDACTED_IBAN]" in cleaned


def test_cognitive_arena_12_disciplines_elo_and_confidence():
    arena = media_lab_arena.CognitiveArena()
    assert len(arena.disciplines) == 12
    assert len(arena.models) == 7

    initial_qwen = arena.get_rating("qwen3.5:9b", "math")
    initial_llama = arena.get_rating("llama3.2:3b", "math")
    assert initial_qwen == 1500.0 and initial_llama == 1500.0

    match = arena.record_match("math", "qwen3.5:9b", "llama3.2:3b", score_a=1.0)
    assert match["new_elo_a"] == 1516.0
    assert match["new_elo_b"] == 1484.0

    board = arena.get_leaderboard("math")
    assert board[0]["model"] == "qwen3.5:9b"
    assert board[-1]["model"] == "llama3.2:3b"

    high_conf = arena.calibrate_confidence(
        answer="Hesaplanan kesme kuvveti Fc = 1420 N olarak doğrulanmıştır. | Tablo 1 |",
        tool_verified=True,
        citations_count=2,
    )
    assert high_conf["confidence_score"] >= 0.90
    assert high_conf["needs_cross_verification"] is False

    low_conf = arena.calibrate_confidence(
        answer="Sanırım belki bu değer olabilir emin değilim.",
        tool_verified=False,
        citations_count=0,
    )
    assert low_conf["confidence_score"] < 0.75
    assert low_conf["needs_cross_verification"] is True
