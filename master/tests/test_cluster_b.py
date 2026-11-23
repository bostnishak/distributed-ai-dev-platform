from __future__ import annotations

import sys
from pathlib import Path

import pytest

MASTER_DIR = Path(__file__).resolve().parent.parent
if str(MASTER_DIR) not in sys.path:
    sys.path.insert(0, str(MASTER_DIR))

from automl_studio import profile_dataset, train_and_forecast, what_if_predict  # noqa: E402
from code_graph import build_workspace_code_graph, get_file_context_contract  # noqa: E402
from self_healing_runner import run_workspace_smoke_check, scan_code_security  # noqa: E402


def test_code_graph_multilang_extraction_and_edges(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(
        "class Order:\n"
        "    def total(self, tax_rate: float = 0.2) -> float:\n"
        "        return 100.0 * (1.0 + tax_rate)\n\n"
        "def format_currency(amount: float) -> str:\n"
        "    return f'${amount:.2f}'\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\n"
        "import models\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/api/orders')\n"
        "async def list_orders(limit: int = 10) -> list[dict]:\n"
        "    return [{'total': models.Order().total()}]\n",
        encoding="utf-8",
    )
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, amount REAL);\n"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, msg TEXT);\n",
        encoding="utf-8",
    )
    (tmp_path / "styles.css").write_text(
        ".order-card { padding: 12px; }\n"
        "#main-panel { display: flex; }\n",
        encoding="utf-8",
    )
    (tmp_path / "client.js").write_text(
        "export class OrderClient {\n"
        "    constructor() {}\n"
        "}\n"
        "export async function fetchOrders(limit) {\n"
        "    const res = await fetch('/api/orders');\n"
        "    return res.json();\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text(
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><link rel=\"stylesheet\" href=\"styles.css\"></head>\n"
        "<body>\n"
        "  <div id=\"main-panel\" class=\"order-card container\"></div>\n"
        "  <script src=\"client.js\"></script>\n"
        "</body>\n"
        "</html>\n",
        encoding="utf-8",
    )

    graph = build_workspace_code_graph(tmp_path)
    assert len(graph["nodes"]) == 6
    assert graph["broken_references"] == []

    symbols = graph["symbols"]
    assert "Order" in [c["name"] for c in symbols["models.py"]["classes"]]
    assert symbols["models.py"]["functions"][0]["name"] == "format_currency"
    assert symbols["models.py"]["functions"][0]["returns"] == "str"

    assert symbols["app.py"]["routes"][0]["path"] == "/api/orders"
    assert symbols["client.js"]["api_calls"] == ["/api/orders"]
    assert "fetchOrders" in [f["name"] for f in symbols["client.js"]["functions"]]
    assert "OrderClient" in [c["name"] for c in symbols["client.js"]["classes"]]

    assert symbols["schema.sql"]["tables"] == ["orders", "audit_logs"]
    assert "order-card" in symbols["styles.css"]["css_classes"]
    assert "main-panel" in symbols["index.html"]["ids"]

    edge_pairs = {(e["source"], e["target"], e["type"]) for e in graph["edges"]}
    assert ("app.py", "models.py", "python_import") in edge_pairs
    assert ("index.html", "client.js", "html_script") in edge_pairs
    assert ("index.html", "styles.css", "html_stylesheet") in edge_pairs


def test_code_graph_broken_references_and_context_contract(tmp_path: Path) -> None:
    (tmp_path / "utils.py").write_text(
        "def compute_score(x: int, y: int = 5) -> int:\n"
        "    return x + y\n",
        encoding="utf-8",
    )
    (tmp_path / "service.py").write_text(
        "import utils\n"
        "import nonexistent_local_module\n\n"
        "def run_service() -> int:\n"
        "    return utils.compute_score(10)\n",
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text(
        "<link rel=\"stylesheet\" href=\"missing_theme.css\">\n"
        "<script src=\"missing_bundle.js\"></script>\n",
        encoding="utf-8",
    )

    graph = build_workspace_code_graph(tmp_path)
    broken_types = {(b["source"], b["target"], b["type"]) for b in graph["broken_references"]}
    assert ("service.py", "nonexistent_local_module", "missing_python_import") in broken_types
    assert ("index.html", "missing_theme.css", "missing_html_stylesheet") in broken_types
    assert ("index.html", "missing_bundle.js", "missing_html_script") in broken_types

    contract = get_file_context_contract(tmp_path, "service.py")
    assert "compute_score(x: int, y: int = 5) -> int" in contract
    assert "nonexistent_local_module" in contract


def test_security_scanner_detects_all_vulnerability_classes(tmp_path: Path) -> None:
    (tmp_path / "vulnerable.py").write_text(
        "import sqlite3\n\n"
        "API_KEY = 'sk-1234567890abcdefghijklmnop'\n\n"
        "def bad_query(conn, user_id):\n"
        "    conn.execute(f'SELECT * FROM users WHERE id = {user_id}')\n\n"
        "def bad_eval(expr):\n"
        "    return eval(expr)\n\n"
        "def bad_file(rel):\n"
        "    return open('../../etc/' + rel).read()\n",
        encoding="utf-8",
    )
    (tmp_path / "ui.js").write_text(
        "function renderComment(el, rawUserHtml) {\n"
        "    el.innerHTML = rawUserHtml;\n"
        "}\n",
        encoding="utf-8",
    )

    report = scan_code_security(tmp_path)
    assert report["ok"] is False
    assert report["total_issues"] >= 5

    categories = {issue["category"] for issue in report["issues"]}
    assert "SQL_INJECTION" in categories
    assert "XSS" in categories
    assert "PATH_TRAVERSAL" in categories
    assert "HARDCODED_SECRET" in categories
    assert "UNSAFE_EVAL_EXEC" in categories
    assert report["severity_counts"]["CRITICAL"] >= 3
    assert report["severity_counts"]["HIGH"] >= 2


def test_self_healing_smoke_check_clean_vs_broken(tmp_path: Path) -> None:
    clean_dir = tmp_path / "clean_ws"
    clean_dir.mkdir()
    (clean_dir / "main.py").write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    (clean_dir / "config.json").write_text('{"version": 1, "active": true}', encoding="utf-8")
    (clean_dir / "app.js").write_text("console.log('ready');\n", encoding="utf-8")
    (clean_dir / "index.html").write_text('<script src="app.js"></script>\n', encoding="utf-8")

    clean_res = run_workspace_smoke_check(clean_dir)
    assert clean_res["ok"] is True
    assert clean_res["errors"] == []
    assert clean_res["security"]["ok"] is True

    broken_dir = tmp_path / "broken_ws"
    broken_dir.mkdir()
    (broken_dir / "bad_syntax.py").write_text("def broken(:\n    return 1\n", encoding="utf-8")
    (broken_dir / "bad.json").write_text('{"unclosed": [1, 2}', encoding="utf-8")
    (broken_dir / "index.html").write_text('<script src="ghost.js"></script>\n', encoding="utf-8")

    broken_res = run_workspace_smoke_check(broken_dir)
    assert broken_res["ok"] is False
    err_types = {e["type"] for e in broken_res["errors"]}
    assert "python_syntax_error" in err_types
    assert "json_decode_error" in err_types
    assert "missing_html_script" in err_types


def test_automl_profile_dataset_stats_correlation_and_anomalies() -> None:
    rows = []
    for i in range(1, 25):
        rows.append(
            {
                "temperature": float(20 + i),
                "pressure": float(100 + 2 * i),
                "machine": "CNC-A" if i % 2 == 0 else "CNC-B",
            }
        )
    # Add one missing row and one extreme outlier row
    rows.append({"temperature": None, "pressure": "", "machine": "CNC-A"})
    rows.append({"temperature": 500.0, "pressure": 1000.0, "machine": "CNC-C"})

    profile = profile_dataset(rows)
    assert profile["row_count"] == 26
    assert profile["column_count"] == 3
    assert set(profile["numeric_columns"]) == {"temperature", "pressure"}
    assert profile["categorical_columns"] == ["machine"]
    assert profile["missing_counts"]["temperature"] == 1
    assert profile["missing_counts"]["pressure"] == 1

    corr = profile["correlation_matrix"]["temperature"]["pressure"]
    assert corr > 0.95

    anomaly_indices = [a["row_index"] for a in profile["anomalies"]]
    assert 25 in anomaly_indices


def test_automl_train_and_forecast_and_what_if() -> None:
    rows = []
    for t in range(30):
        ad_spend = 10.0 + 1.5 * t + (t % 3) * 2.0
        price = 50.0 - 0.3 * t + (t % 4) * 1.2
        revenue = 120.0 + 3.5 * ad_spend - 2.0 * price + 4.0 * t
        rows.append(
            {
                "ad_spend": ad_spend,
                "price": price,
                "revenue": revenue,
                "region": "EU" if t % 2 == 0 else "NA",
            }
        )

    result = train_and_forecast(rows, target_col="revenue", horizon=5, l2_alpha=1e-4)
    assert result["target_column"] == "revenue"
    assert result["sample_count"] == 30
    assert result["metrics"]["r2"] > 0.999
    assert result["metrics"]["rmse"] < 0.5
    assert len(result["forecasts"]) == 5

    imp_sum = sum(result["feature_importance"].values())
    assert pytest.approx(imp_sum, rel=1e-3) == 1.0

    for fc in result["forecasts"]:
        assert fc["lower_ci"] <= fc["prediction"] <= fc["upper_ci"]

    base_pred = what_if_predict(result["weights"], result["feature_means"])
    higher_ad_pred = what_if_predict(
        result["weights"],
        result["feature_means"],
        overrides={"ad_spend": result["feature_means"]["ad_spend"] + 20.0},
    )
    assert higher_ad_pred > base_pred


def test_automl_validation_edge_cases() -> None:
    empty_profile = profile_dataset([])
    assert empty_profile["row_count"] == 0
    assert empty_profile["anomalies"] == []

    with pytest.raises(ValueError, match="cannot be empty"):
        train_and_forecast([], target_col="y")

    with pytest.raises(ValueError, match="not found among numeric columns"):
        train_and_forecast(
            [{"x": 1.0, "label": "cat"}, {"x": 2.0, "label": "dog"}, {"x": 3.0, "label": "bird"}],
            target_col="label",
        )
