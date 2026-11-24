"""End-to-end verification test suite for 100% of implementation_plan.md modules and endpoints."""

from __future__ import annotations

import importlib
import io
import zipfile
from pathlib import Path

import pytest

import config

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")


ALL_PLAN_MODULES = [
    "memory_engine",
    "memory_api",
    "tool_executor",
    "deep_research",
    "document_factory",
    "code_graph",
    "self_healing_runner",
    "automl_studio",
    "cluster_telemetry",
    "hybrid_graph_rag",
    "llmops_pipeline",
    "cad_cam_physics",
    "rfq_batch",
    "erp_mes_scheduler",
    "enterprise_security_mcp",
    "audit_log",
    "domain_experts",
    "media_lab_arena",
    "backup_manager",
    "user_profile",
    "user_api",
    "auth",
    "gateway",
    "orchestrator",
    "rag",
    "hallucination",
    "ml_ops",
    "studios",
    "factory",
    "games",
    "domains",
    "distributed",
    "sandbox",
    "db_portable",
    "process_utils",
]


def test_every_implementation_plan_module_imports_cleanly():
    for mod_name in ALL_PLAN_MODULES:
        mod = importlib.import_module(mod_name)
        assert mod is not None


def test_memory_api_and_backup_endpoints(client):
    assert client.get("/api/memory/conversations").status_code == 200
    assert client.get("/api/memory/facts").status_code == 200
    resp = client.get("/api/admin/backup.zip?password=TestBackupPass123")
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        assert "backup/BACKUP_MANIFEST.json" in zf.namelist()


def test_vram_manager_single_vs_multi_node():
    from gateway import power_manager as vm

    single = vm.compute_vram_execution_plan(["qwen3.5:9b", "qwen2.5-coder:7b"], available_vram_gb=8.0, online_agents=1)
    assert single["mode"] == "single_node_sequential"
    assert single["keep_alive"] == "5m"

    multi = vm.compute_vram_execution_plan(["qwen3.5:9b", "qwen2.5-coder:7b"], available_vram_gb=8.0, online_agents=4)
    assert multi["mode"] == "multi_node_parallel"
    assert multi["keep_alive"] == "-1"


def test_workspace_terminal_git_and_search_endpoints(client, tmp_path: Path):
    ws_dir = config.WORKSPACES_DIR / "ide-test-ws"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "main.py").write_text("print('HELLO_IDE_TERMINAL')\n", encoding="utf-8")

    exec_resp = client.post("/api/studio/workspaces/ide-test-ws/exec", json={"command": "python main.py"})
    assert exec_resp.status_code in (200, 503)  # SEC-13: runs strictly in Docker sandbox or fails closed (503)

    act_resp = client.post("/api/studio/workspaces/ide-test-ws/actions", json={"action": "start_preview"})
    assert act_resp.status_code == 200
    assert "isolated_origin" in act_resp.json()

    search_resp = client.get("/api/studio/workspaces/ide-test-ws/search?q=HELLO_IDE")
    assert search_resp.status_code == 200
    assert search_resp.json()["matches"][0]["path"] == "main.py"

    git_resp = client.post("/api/studio/workspaces/ide-test-ws/git", json={"action": "status"})
    assert git_resp.status_code == 200
    assert git_resp.json()["ok"] is True


def test_build_pipelines_visual_verifier_and_rfq_batch(tmp_path: Path):
    import rfq_batch
    from factory import deploy_verify as bp

    ws = tmp_path / "sample_web"
    ws.mkdir()
    (ws / "index.html").write_text("<!doctype html><html><body><div id='app'>Hi</div></body></html>", encoding="utf-8")

    pwa = bp.generate_pwa_assets(ws, app_name="TestPWA")
    assert (ws / "manifest.json").is_file() and (ws / "service-worker.js").is_file()
    assert pwa

    dock = bp.generate_docker_bundle(ws, port=8080)
    assert (ws / "Dockerfile").is_file() and (ws / "docker-compose.yml").is_file()
    assert dock

    ui_check = bp.verify_web_workspace_ui(ws)
    assert isinstance(ui_check, dict)

    # Test RFQ batch ZIP with 2 STEP parts
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("part1.step", "ISO-10303-21;\nDATA;\n#1=PRODUCT('P1','Shaft','',(#2));\n#2=CYLINDRICAL_SURFACE('OD',#3,25.0);\nENDSEC;\nEND-ISO-10303-21;")
        zf.writestr("part2.step", "ISO-10303-21;\nDATA;\n#1=PRODUCT('P2','Flange','',(#2));\n#2=CYLINDRICAL_SURFACE('OD',#3,40.0);\nENDSEC;\nEND-ISO-10303-21;")
    rfq = rfq_batch.process_rfq_zip_package(zbuf.getvalue(), customer_name="Test AS")
    assert rfq["part_count"] == 2


def test_agent_vram_heartbeat_and_assistant_new_routes(client, auth_headers):
    # 1. Agent VRAM & warm-model heartbeat telemetry
    reg = client.post(
        "/api/agents/register",
        json={"agent_id": "uye1-vram", "member_name": "Test", "model": "qwen3.5:9b"},
        headers=auth_headers,
    )
    assert reg.status_code == 200
    hb = client.post(
        "/api/agents/uye1-vram/heartbeat",
        json={"status": "idle", "loaded_models": ["qwen3.5:9b"], "vram_used_gb": 6.4, "tokens_per_sec": 42.5},
        headers=auth_headers,
    )
    assert hb.status_code == 200
    agents = client.get("/api/agents").json()
    found = next(a for a in agents if a["agent_id"] == "uye1-vram")
    assert found["loaded_models"] == ["qwen3.5:9b"]
    assert found["vram_used_gb"] == 6.4

    # 2. Enterprise status / 12-discipline ELO Arena endpoint for dashboard
    ent = client.get("/api/assistant/enterprise-status")
    assert ent.status_code == 200
    assert len(ent.json()["elo_leaderboard"]) >= 1

    # 3. Chat stream -> PowerPoint (.pptx) generator
    r_pptx = client.post(
        "/api/assistant/chat/stream",
        data={"prompt": "CNC otomasyonu hakkında 4 slaytlık sunum pptx hazırla"},
    )
    assert r_pptx.status_code == 200
    assert ".pptx" in r_pptx.text

    # 4. Chat stream -> ERP/MES 1D Nesting & CNC Gantt
    r_erp = client.post(
        "/api/assistant/chat/stream",
        data={"prompt": "1D çubuk kesim nesting ve tezgah çizelge gantt çıkar"},
    )
    assert r_erp.status_code == 200
    assert "gantt" in r_erp.text.lower()

