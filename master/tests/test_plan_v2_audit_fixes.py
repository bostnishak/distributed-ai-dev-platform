"""Deep audit verification tests for Plan v2 fixes (SEC-04, DEF-06, DEF-11, OPS-09, UX-08, UX-25)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.security
def test_sec04_every_openapi_route_classified_in_policy():
    """SEC-04: Every single OpenAPI route must be explicitly classified in auth.policy.MATRIX."""
    import app as mapp
    from auth import policy

    spec = mapp.app.openapi()
    uncovered = [
        (method.upper(), path)
        for path, ops in spec["paths"].items()
        for method in ops
        if method in ("get", "post", "put", "delete", "patch")
        and policy.action_for(method.upper(), path) is None
    ]
    assert uncovered == [], f"SEC-04 ihlali — rol matrisinde tanımsız rotalar: {uncovered}"
    assert policy.can("developer", "POST", "/api/custom-agents") is True
    assert policy.can("viewer", "POST", "/api/custom-agents") is False
    assert policy.can("admin", "POST", "/api/ha/drain/node-1") is True
    assert policy.can("developer", "POST", "/api/ha/drain/node-1") is False


@pytest.mark.unit
def test_def06_csv_forecast_only_on_explicit_request():
    """DEF-06: CSV upload summarizes without unsolicited forecast; adds forecast + uncertainty only when asked."""
    import assistant_prep

    csv_bytes = b"ay,satis\n1,100\n2,120\n3,140\n4,160\n5,180\n"
    summary_out = assistant_prep._extract_csv_with_automl("satis.csv", csv_bytes, "bu dosyayı özetle")
    assert "AutoML Veri Profili Özeti" in summary_out
    assert "L2 Ridge Tahmin" not in summary_out

    forecast_out = assistant_prep._extract_csv_with_automl("satis.csv", csv_bytes, "gelecek 3 ayı tahmin et")
    assert "L2 Ridge Tahmin" in forecast_out
    assert "belirsizlik aralığı" in forecast_out


@pytest.mark.unit
def test_def11_dynamic_data_dir_isolation(tmp_path, monkeypatch):
    """DEF-11: Changing DB_PATH dynamically redirects data_dir(), workspaces_dir(), and cnc_jobs_dir()."""
    import config

    custom = tmp_path / "alt_env"
    monkeypatch.setattr(config, "DB_PATH", custom / "platform.db")
    assert config.data_dir() == custom.resolve()
    assert config.workspaces_dir() == custom.resolve() / "workspaces"
    assert config.cnc_jobs_dir() == custom.resolve() / "cnc_jobs"


@pytest.mark.e2e
def test_ux08_and_ux25_message_tools_e2e():
    """UX-08 (chat export) & UX-25 (browser notification/tab-title fallback) verified via Node test runner."""
    node_bin = shutil.which("node")
    assert node_bin is not None, "node ikilisi bulunamadı"
    proc = subprocess.run(
        [node_bin, "--test", "frontend/tests/message_tools.test.mjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "UX-08" in proc.stdout
    assert "UX-25" in proc.stdout
