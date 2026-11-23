"""Acceptance tests for Master Plan v2 Parca 1 DEF-01..24 deliverables."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"


def _load_plan_tool():
    spec = importlib.util.spec_from_file_location("plan_tool_def", SCRIPTS_DIR / "plan_tool.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_def01_and_def02_wiring_gate_and_triage_completeness(tmp_path: Path):
    """DEF-01 & DEF-02: plan_tool wiring detects new unwired modules and WIRING_TRIAGE covers every allowlist entry."""
    plan_tool = _load_plan_tool()

    fake_master = tmp_path / "master"
    fake_master.mkdir()
    (fake_master / "app.py").write_text("import used_mod\n", encoding="utf-8")
    (fake_master / "used_mod.py").write_text("X = 1\n", encoding="utf-8")
    (fake_master / "orphan_mod.py").write_text("Y = 2\n", encoding="utf-8")
    fake_plan = tmp_path / "plan"
    fake_plan.mkdir()
    (fake_plan / "wiring_allowlist.txt").write_text("", encoding="utf-8")

    rc = plan_tool.main(["--plan-dir", str(fake_plan), "--master-dir", str(fake_master), "wiring", "--fail-on-new"])
    assert rc == 1

    allow = [
        line.strip()
        for line in (ROOT / "docs" / "plan-v2" / "wiring_allowlist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    triage = (ROOT / "docs" / "plan-v2" / "WIRING_TRIAGE.md").read_text(encoding="utf-8")
    for mod_name in allow:
        assert f"`{mod_name}`" in triage, f"Module '{mod_name}' missing from WIRING_TRIAGE.md"


def test_def11_dynamic_data_dir(tmp_path: Path, monkeypatch):
    """DEF-11: config.data_dir(), workspaces_dir(), cnc_jobs_dir() track DB_PATH dynamically."""
    import config

    custom_db = tmp_path / "nested" / "platform.db"
    monkeypatch.setattr(config, "DB_PATH", custom_db)
    assert config.data_dir() == custom_db.resolve().parent
    assert config.workspaces_dir() == custom_db.resolve().parent / "workspaces"
    assert config.cnc_jobs_dir() == custom_db.resolve().parent / "cnc_jobs"


def test_def13_def14_def19_def20_hygiene_files():
    """DEF-13, DEF-14, DEF-19, DEF-20: Python version, optional deps, CI Docker smoke, deprecated JSON, .gitattributes."""
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip().startswith("3.12")
    assert (ROOT / "master" / "requirements-optional.txt").is_file()
    ci_txt = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "docker run -d" in ci_txt and "/health" in ci_txt

    legacy = json.loads((ROOT / "docs" / "IMPLEMENTATION_PROGRESS.json").read_text(encoding="utf-8"))
    assert "ARCHIVED" in legacy.get("_deprecated_notice", "")

    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "eol=lf" in attrs and "*.ps1" in attrs


def test_def15_assistant_config_reports_capabilities(client):
    """DEF-15: /api/assistant/config exposes per-capability available/reason entries."""
    resp = client.get("/api/assistant/config")
    assert resp.status_code == 200
    body = resp.json()
    caps = body.get("capabilities")
    assert isinstance(caps, dict)
    for key in ("stt", "tts", "ocr", "web_search", "image_gen", "sandbox", "vector_index"):
        assert key in caps
        assert "available" in caps[key] and "reason" in caps[key]


def test_def21_supervised_loop_recovers_after_crash():
    """DEF-21: SupervisedLoop catches crashes, logs/records error, and restarts cleanly."""
    from process_utils import SupervisedLoop

    attempts = {"n": 0}

    def _flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("injected-loop-failure")

    sup = SupervisedLoop("test-flaky-loop", _flaky, interval_s=0.01, base_backoff_s=0.01)
    sup.start()
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and (sup.restarts < 1 or sup.runs < 1):
            time.sleep(0.01)
    finally:
        sup.stop()

    st = sup.status()
    assert st["restarts"] >= 1
    assert st["runs"] >= 1
    assert "injected-loop-failure" in st["last_error"]
    assert st["last_ok_ts"] is not None


def test_def22_extended_deterministic_calculator():
    """DEF-22: try_calculate deterministically solves percentages, KDV, units, dates, and compound interest."""
    from assistant import try_calculate

    assert "30" in (try_calculate("200'ün %15'i") or "")
    assert "1200.00" in (try_calculate("1000 TL %20 KDV") or "")
    assert "5000 m" in (try_calculate("5 km kaç m") or "")
    assert "77.0 F" in (try_calculate("25 C kaç F") or "")
    assert "30 gün" in (try_calculate("2026-01-01 ile 2026-01-31 kaç gün") or "")
    assert "14400.00" in (try_calculate("10000 TL %20 2 yıl bileşik faiz") or "")


def test_def23_strip_emojis_preserves_code_and_technical_symbols():
    """DEF-23: _strip_emojis strips emojis in prose while preserving ->, ✓, ≤, © and fenced code blocks."""
    from assistant import _strip_emojis

    rocket = "\U0001F680"
    sample = f"Sonuç {rocket}: A → B ✓ (x ≤ 10, © 2026)\n```python\nprint('{rocket} ✓ →')\n```"
    cleaned = _strip_emojis(sample)
    assert rocket not in cleaned.split("```")[0]
    assert "→" in cleaned and "✓" in cleaned and "≤" in cleaned and "©" in cleaned
    assert f"print('{rocket} ✓ →')" in cleaned


def test_def24_run_process_handles_utf8_and_invalid_bytes():
    """DEF-24: run_process uses UTF-8 with errors='replace' so cp1254 never crashes on Turkish or raw bytes."""
    from process_utils import run_process

    res = run_process(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write('Türkçe ğüşiöç '.encode('utf-8') + b'\\x81\\xff')"],
        timeout_s=10.0,
    )
    assert res.returncode == 0
    assert res.timed_out is False
    assert "Türkçe ğüşiöç" in res.stdout
