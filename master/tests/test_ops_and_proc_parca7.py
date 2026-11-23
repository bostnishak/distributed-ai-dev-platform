"""Verification tests for Parca 7 OPS & PROC deliverables, security ownership fixes, and Plan v2 sync."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = ROOT / "master"
SCRIPTS_DIR = ROOT / "scripts"


def _load_script(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"script_{name}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fake_ollama_vcr_server_chat_stream_and_fault_injection():
    """OPS-10: Deterministic fake Ollama server supports tags, chat, NDJSON stream, embed, and fault injection."""
    from gateway.fake_ollama import create_fake_ollama_app

    fake_app = create_fake_ollama_app(canned_responses={"merhaba": "Merhaba test cevabı."})
    client = TestClient(fake_app)

    tags = client.get("/api/tags")
    assert tags.status_code == 200
    assert len(tags.json()["models"]) >= 1

    chat = client.post(
        "/api/chat",
        json={"model": "qwen3.5:9b", "messages": [{"role": "user", "content": "Merhaba dünya"}], "stream": False},
    )
    assert chat.status_code == 200
    assert chat.json()["message"]["content"] == "Merhaba test cevabı."

    stream_resp = client.post(
        "/api/chat",
        json={"model": "qwen3.5:9b", "messages": [{"role": "user", "content": "Merhaba"}], "stream": True},
    )
    assert stream_resp.status_code == 200
    assert '"done": true' in stream_resp.text.lower()

    embed = client.post("/api/embed", json={"model": "bge-m3", "input": "test"})
    assert embed.status_code == 200
    assert len(embed.json()["embeddings"][0]) == 64

    fault_app = create_fake_ollama_app(inject_error="500")
    fault_client = TestClient(fault_app)
    assert fault_client.get("/api/tags").status_code == 500
    assert fault_client.post("/api/chat", json={"messages": []}).status_code == 503


def test_power_manager_idle_unload_and_battery_downgrade():
    """OPS-24: Idle models after 10 min are flagged for unload and low-battery downgrades large models."""
    from gateway.power_manager import PowerManager

    pm = PowerManager(idle_unload_seconds=600.0)
    pm.touch("qwen3.5:9b", now=100.0)
    pm.touch("qwen3.5:4b", now=650.0)
    assert pm.models_due_for_unload(now=750.0) == ["qwen3.5:9b"]

    low_batt = pm.recommend_for_power_profile("qwen3.5:9b", on_battery=True, battery_pct=25)
    assert low_batt["downgraded"] is True
    assert low_batt["recommended_model"] == "qwen3.5:4b"

    plugged = pm.recommend_for_power_profile("qwen3.5:9b", on_battery=False, battery_pct=100)
    assert plugged["downgraded"] is False
    assert plugged["recommended_model"] == "qwen3.5:9b"


def test_readiness_links_runbooks():
    """OPS-03 + OPS-15: Every readiness failure attaches a valid runbook path under docs/runbooks/."""
    import readiness

    for name in ("database-locked", "disk-full", "ollama-down", "model-missing"):
        res = readiness._result("degraded", "simulated", name)
        assert res["runbook"] == f"docs/runbooks/{name}.md"
        assert (ROOT / res["runbook"]).is_file()


def test_memory_compact_blocks_cross_user_access():
    """Security debt fix: compact_conversation enforces conversation user_id ownership (403)."""
    import app as master_app
    import memory_engine

    cid = "conv-owner-check-test"
    memory_engine.init_memory_db()
    with memory_engine._connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO conversations (id, user_id, title, summary, created_at, updated_at) "
            "VALUES (?, ?, ?, '', '2026-11-23T00:00:00Z', '2026-11-23T00:00:00Z')",
            (cid, "alice", "Alice Private Chat"),
        )
        conn.commit()

    client = TestClient(master_app.app)
    resp = client.post(f"/api/memory/compact/{cid}", params={"user_id": "bob"})
    assert resp.status_code == 403


def test_quality_gate_sbom_and_load_benchmark(tmp_path: Path):
    """OPS-13, OPS-16, OPS-20: Quality gate, CycloneDX SBOM, and concurrent load benchmark pass."""
    qg = _load_script("quality_gate")
    qg_res = qg.check_function_lengths(MASTER_DIR)
    assert qg_res["passed"] is True, f"New long functions detected: {qg_res['new_violations']}"

    sbom_mod = _load_script("generate_sbom")
    out_sbom = tmp_path / "sbom.json"
    sbom = sbom_mod.generate_cyclonedx_sbom(out_sbom)
    assert out_sbom.is_file()
    assert sbom["bomFormat"] == "CycloneDX"
    assert len(sbom["components"]) > 0

    bench_mod = _load_script("load_and_chaos_bench")
    bench = asyncio.run(bench_mod.run_load_benchmark(concurrent_chats=6))
    assert bench["passed"] is True
    assert bench["error_rate"] == 0.0


def test_proc_scripts_trello_scrum_academic_and_plan_check(tmp_path: Path):
    """PROC-02, PROC-03, PROC-07, PROC-09: Trello dry-run, Scrum reports, Academic bundle, and plan_tool check pass."""
    plan_tool = _load_script("plan_tool")
    assert plan_tool.main(["check"]) == 0

    trello = _load_script("trello_sync")
    cards = trello.build_backlog_cards(ROOT / "docs" / "plan-v2", priority_filter="P0")
    assert len(cards) > 0
    dry = trello.sync_to_trello(cards, dry_run=True)
    assert dry["mode"] == "dry_run"
    assert dry["total_cards"] == len(cards)

    scrum = _load_script("generate_scrum_reports")
    scrum_res = scrum.generate_reports(ROOT / "docs" / "plan-v2", tmp_path / "scrum")
    assert Path(scrum_res["svg"]).is_file()
    assert Path(scrum_res["report"]).is_file()
    assert "<svg" in Path(scrum_res["svg"]).read_text(encoding="utf-8")

    acad = _load_script("generate_academic_report")
    acad_res = acad.build_academic_bundle(ROOT / "eval" / "reports", tmp_path / "acad")
    assert Path(acad_res["markdown"]).is_file()
    assert Path(acad_res["latex"]).is_file()
    assert Path(acad_res["chart"]).is_file()
    assert "\\begin{table}" in Path(acad_res["latex"]).read_text(encoding="utf-8")


def test_all_adrs_runbooks_docs_and_hardened_compose_exist():
    """OPS-06, OPS-12, OPS-14, OPS-15, OPS-21, OPS-22, PROC-01/04/05/06/08."""
    adrs = sorted((ROOT / "docs" / "adr").glob("000[1-8]-*.md"))
    assert len(adrs) == 8

    expected_runbooks = [
        "README.md",
        "ollama-down.md",
        "model-missing.md",
        "database-locked.md",
        "disk-full.md",
        "agent-offline.md",
        "tailscale-connectivity.md",
        "eval-regression.md",
        "backup-restore.md",
    ]
    for rb in expected_runbooks:
        assert (ROOT / "docs" / "runbooks" / rb).is_file(), f"Missing runbook {rb}"

    required_files = [
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        ".pre-commit-config.yaml",
        ".github/pull_request_template.md",
        "mkdocs.yml",
        "scripts/dev.sh",
        "scripts/install_windows.ps1",
        "scripts/demo_checklist.ps1",
        "docs/scrum/traceability.md",
        "docs/scrum/definition-of-done.md",
        "docs/scrum/demo-script.md",
        "docs/scrum/academic-report-template.md",
        "docs/plan-v2/model-licenses-ethics.md",
    ]
    for rel in required_files:
        assert (ROOT / rel).is_file(), f"Missing required artifact {rel}"

    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "litellm-gateway" not in compose_text
    for profile in ('"core"', '"agents"', '"web-search"', '"sandbox"'):
        assert profile in compose_text


def test_dat12_cli_ops17_chaos_proc01_links_proc08_licenses_and_proc09_evidence_gate(tmp_path: Path):
    """Strict Parca 7 acceptance checks: DAT-12 CLI, OPS-17 chaos, PROC-01 links, PROC-08 licenses, PROC-09 gate."""
    import re

    from gateway import registry

    # DAT-12: scripts/db_doctor.py CLI works on a clean DB
    db_doc_cli = _load_script("db_doctor")
    assert (SCRIPTS_DIR / "db_doctor.py").is_file()
    import dbconn

    test_db = tmp_path / "doctor_check.db"
    with dbconn.connection(test_db) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, val TEXT)")
    assert db_doc_cli.main(["--db", str(test_db), "--json"]) == 0

    # OPS-17: Chaos fault-injection resilience suite passes with zero data loss
    bench_mod = _load_script("load_and_chaos_bench")
    chaos = asyncio.run(bench_mod.run_chaos_resilience_suite())
    assert chaos["passed"] is True
    assert chaos["data_loss"] == 0

    # PROC-01: Every backticked repo path in docs/scrum/traceability.md resolves to an existing file/dir
    trace_text = (ROOT / "docs" / "scrum" / "traceability.md").read_text(encoding="utf-8")
    for ref in re.findall(r"`([A-Za-z0-9_./-]+)`", trace_text):
        if "/" in ref:
            assert (ROOT / ref).exists(), f"Broken traceability link: {ref}"

    # PROC-08: Every fleet model has a non-empty license in gateway.registry and appears in model-licenses-ethics.md
    ethics_text = (ROOT / "docs" / "plan-v2" / "model-licenses-ethics.md").read_text(encoding="utf-8")
    for model_name in ("qwen3.5:4b", "qwen2.5-coder:7b", "qwen3:1.7b", "phi4-mini", "llama3.2:3b", "gemma4:e4b", "bge-m3"):
        rec = registry.upsert_model(model_name)
        assert rec["license"], f"Missing license for {model_name}"
        assert model_name in ethics_text

    # PROC-09: plan_tool.merge_progress strictly rejects 'done' without tests + commit evidence
    plan_tool = _load_script("plan_tool")
    items, _ = plan_tool.parse_plan(ROOT / "docs" / "plan-v2")
    merged, errs = plan_tool.merge_progress(
        items[:1],
        {"items": {items[0].id: {"status": "done", "evidence": {"tests": [], "commit": "", "eval_report": ""}}}},
    )
    assert len(errs) == 1
    assert merged["items"][items[0].id]["status"] == "claimed_without_evidence"
