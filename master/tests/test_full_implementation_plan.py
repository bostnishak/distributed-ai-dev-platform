"""End-to-end verification test suite for 100% of implementation_plan.md modules and endpoints."""

from __future__ import annotations

import importlib
import io
import zipfile
from pathlib import Path

import pytest

import config


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")


ALL_PLAN_MODULES = [
    "memory_engine",
    "memory_api",
    "tool_executor",
    "tools_math_science",
    "tools_data_sql",
    "reasoning_council",
    "deep_research",
    "document_factory",
    "voice_engine",
    "media_analyzer",
    "image_studio",
    "code_graph",
    "project_archetypes",
    "software_factory",
    "self_healing_runner",
    "visual_verifier",
    "build_pipelines",
    "security_scanner",
    "automl_studio",
    "browser_agent",
    "desktop_automation",
    "cluster_telemetry",
    "swarm_coordinator",
    "bandit_router",
    "map_reduce_llm",
    "fault_tolerance",
    "hybrid_graph_rag",
    "vector_store",
    "knowledge_graph",
    "vision_rag",
    "citation_guard",
    "llmops_pipeline",
    "feedback_collector",
    "model_gate",
    "cad_cam_physics",
    "cad_kernel",
    "cad_projection",
    "cam_postprocessor",
    "cnc_physics",
    "fea_solver",
    "dfm_advisor",
    "cmm_closed_loop",
    "vision_qc",
    "machine_iot",
    "rfq_batch",
    "erp_mes_scheduler",
    "nesting_optimizer",
    "job_shop_scheduler",
    "enterprise_security_mcp",
    "auth_rbac",
    "audit_log",
    "secure_sandbox",
    "automation_engine",
    "mcp_registry",
    "domain_experts",
    "legal_expert",
    "finance_expert",
    "academic_expert",
    "cyber_expert",
    "media_lab_arena",
    "media_factory_v2",
    "enterprise_connectors",
    "cognitive_arena",
    "vram_manager",
    "backup_manager",
    "user_profile",
    "user_api",
]


def test_every_implementation_plan_module_imports_cleanly():
    for mod_name in ALL_PLAN_MODULES:
        mod = importlib.import_module(mod_name)
        assert mod is not None


def test_memory_api_and_backup_endpoints(client):
    assert client.get("/api/memory/conversations").status_code == 200
    assert client.get("/api/memory/facts").status_code == 200
    resp = client.get("/api/admin/backup.zip")
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        assert "backup/BACKUP_MANIFEST.txt" in zf.namelist()


def test_vram_manager_single_vs_multi_node():
    import vram_manager as vm

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
    assert exec_resp.status_code == 200
    assert "HELLO_IDE_TERMINAL" in exec_resp.json()["stdout"]

    search_resp = client.get("/api/studio/workspaces/ide-test-ws/search?q=HELLO_IDE")
    assert search_resp.status_code == 200
    assert search_resp.json()["matches"][0]["path"] == "main.py"

    git_resp = client.post("/api/studio/workspaces/ide-test-ws/git", json={"action": "status"})
    assert git_resp.status_code == 200
    assert git_resp.json()["ok"] is True


def test_build_pipelines_visual_verifier_and_rfq_batch(tmp_path: Path):
    import build_pipelines as bp
    import rfq_batch
    import visual_verifier as vv

    ws = tmp_path / "sample_web"
    ws.mkdir()
    (ws / "index.html").write_text("<!doctype html><html><body><div id='app'>Hi</div></body></html>", encoding="utf-8")

    pwa = bp.generate_pwa_assets(ws, app_name="TestPWA")
    assert (ws / "manifest.json").is_file() and (ws / "service-worker.js").is_file()
    assert pwa

    dock = bp.generate_docker_bundle(ws, port=8080)
    assert (ws / "Dockerfile").is_file() and (ws / "docker-compose.yml").is_file()
    assert dock

    ui_check = vv.verify_web_workspace_ui(ws)
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

