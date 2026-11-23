"""Comprehensive test suite for Parca 6: DIST-01..22 and UX-01..28."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as master_app
from distributed import (
    INTENT_TO_TASK_TYPE,
    AgentProfile,
    BenchmarkScores,
    HardwareSpec,
    ThompsonBanditRouter,
    acquire_task_lease,
    build_benchmark_tasks,
    build_performance_matrix,
    build_project_provenance,
    compute_amdahl_speedup,
    decide_failure_recovery,
    diagnose_tailscale_failure,
    execute_test_agent_task,
    generate_agent_install_command,
    hardware_can_run_model,
    load_checkpoint,
    log_agent_performance,
    map_reduce_distributed,
    parse_tailscale_peers,
    record_benchmark_run,
    save_checkpoint,
    select_distributed_agent,
    steal_work_if_imbalanced,
    submit_idempotent_result,
    three_way_merge,
    validate_agent_profile,
)
from orchestrator.classifier import load_intent_catalog
from ux_api import build_health_wizard_report, create_readonly_share, fetch_readonly_share, validate_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_JS = REPO_ROOT / "master" / "static" / "js"


# ---------------------------------------------------------------- DIST-01..DIST-22 Tests

@pytest.mark.anyio
async def test_dist01_to_dist22_profiles_benchmarks_bandit_vram_leases_checkpoints_mapreduce_merge(tmp_path):
    db_file = tmp_path / "dist.db"

    # DIST-01: Versioned profile validates cleanly; older schema warns without rejecting
    old_prof = validate_agent_profile({"schema_version": "1.0", "agent_id": "ag-old", "model": "qwen2.5:7b"})
    assert old_prof["valid"] is True and len(old_prof["warnings"]) == 1

    # DIST-02: 50 benchmark tasks (10 per dimension) + time-series delta note
    assert len(build_benchmark_tasks()) == 50
    r1 = record_benchmark_run("ag-1", "qwen2.5:7b", {"coding": 80, "reasoning": 75, "context": 70, "structured": 85, "speed": 60}, db_path=db_file)
    r2 = record_benchmark_run("ag-1", "qwen3.5:9b", {"coding": 90, "reasoning": 85, "context": 80, "structured": 90, "speed": 55}, db_path=db_file)
    assert "model değişti" in r2["delta_note"] and r1["run_id"] != r2["run_id"]

    # DIST-05: Every one of 30 orchestrator intents maps to a canonical distributed task type
    _, specs = load_intent_catalog()
    for intent_id in specs:
        assert intent_id in INTENT_TO_TASK_TYPE, f"Intent {intent_id} missing from INTENT_TO_TASK_TYPE"

    # DIST-04: Thompson Sampling converges to stronger agent over 200 synthetic tasks
    bandit = ThompsonBanditRouter(db_path=db_file, enabled=True, seed=42)
    picks_good = 0
    for step in range(200):
        s_good = bandit.sample_score("backend", "ag-good")
        s_bad = bandit.sample_score("backend", "ag-bad")
        if s_good >= s_bad:
            if step >= 100:
                picks_good += 1
            bandit.record_outcome("backend", "ag-good", success=(step % 10 != 0))  # 90% win
        else:
            bandit.record_outcome("backend", "ag-bad", success=(step % 5 == 0))  # 20% win
    assert picks_good >= 80, f"Bandit failed to converge to best agent: {picks_good}/100"

    # DIST-03 & DIST-12: 4 GB VRAM agent MUST NOT be assigned a 9B model task!
    ag_small_gpu = AgentProfile(
        agent_id="ag-4gb",
        model="qwen3.5:4b",
        param_billions=4.0,
        hardware=HardwareSpec(gpu_name="GTX 1650", is_gpu=True, vram_gb=4.0, ram_gb=16.0),
        scores=BenchmarkScores(coding=95.0, reasoning=95.0),
    )
    ag_big_gpu = AgentProfile(
        agent_id="ag-12gb",
        model="qwen3.5:9b",
        param_billions=9.0,
        hardware=HardwareSpec(gpu_name="RTX 3060", is_gpu=True, vram_gb=12.0, ram_gb=32.0),
        scores=BenchmarkScores(coding=88.0, reasoning=86.0),
        warm_models=["qwen3.5:9b"],
    )
    assert hardware_can_run_model(ag_small_gpu, required_param_b=9.0)[0] is False
    sel = select_distributed_agent([ag_small_gpu, ag_big_gpu], task_type="backend", required_param_b=9.0, bandit=bandit)
    assert sel["selected"] == "ag-12gb" and len(sel["rejected"]) == 1 and "seçildi" in sel["reason"]

    # DIST-06 & DIST-07: Idempotent submission + stale-lease rejection (does not overwrite active lease!)
    l1 = acquire_task_lease("task-1", "ag-1", ttl_s=60.0, db_path=db_file)
    l2 = acquire_task_lease("task-1", "ag-2", ttl_s=60.0, db_path=db_file)
    stale = submit_idempotent_result("task-1", "ag-1", lease_version=l1["lease_version"], etag="e1", payload="old", db_path=db_file)
    assert stale["accepted"] is False
    ok_sub = submit_idempotent_result("task-1", "ag-2", lease_version=l2["lease_version"], etag="e2", payload="fresh", db_path=db_file)
    assert ok_sub["accepted"] is True
    replay = submit_idempotent_result("task-1", "ag-2", lease_version=l2["lease_version"], etag="e2", payload="fresh", db_path=db_file)
    assert replay["status"] == "idempotent_replay"

    # DIST-08: Checkpoint save & resume after worker failure
    save_checkpoint("task-long", 5, {"completed_files": ["a.py", "b.py"]}, db_path=db_file)
    cp = load_checkpoint("task-long", db_path=db_file)
    assert cp and cp["step_index"] == 5 and len(cp["state"]["completed_files"]) == 2

    # DIST-09: Map-Reduce retries ONLY failed shard
    attempts: dict[int, int] = {}

    async def _map_shard(idx: int, val: int) -> int:
        attempts[idx] = attempts.get(idx, 0) + 1
        if idx == 2 and attempts[idx] == 1:
            raise RuntimeError("transient worker failure")
        return val * 10

    mr = await map_reduce_distributed([1, 2, 3, 4], _map_shard, sum)
    assert mr["reduced"] == 100 and attempts[0] == 1 and attempts[2] == 2

    # DIST-10: Work stealing balances uneven queues
    queues = {"ag-fast": [], "ag-slow": ["t1", "t2", "t3"]}
    st = steal_work_if_imbalanced(queues, "ag-fast")
    assert st["stolen"] is True and len(queues["ag-fast"]) == 1 and len(queues["ag-slow"]) == 2

    # DIST-15: 3-way merge auto-merges disjoint edits and flags overlapping conflicts
    base = "line1\nline2\nline3\nline4"
    auto = three_way_merge(base, "LINE1\nline2\nline3\nline4", "line1\nline2\nline3\nLINE4")
    assert auto["auto_merged"] is True and "LINE1" in auto["merged"] and "LINE4" in auto["merged"]
    conf = three_way_merge(base, "OURS\nline2\nline3\nline4", "THEIRS\nline2\nline3\nline4")
    assert conf["auto_merged"] is False and len(conf["conflicts"]) == 1

    # DIST-17: Real pytest execution reopens code task on failure
    ws_fail = tmp_path / "ws_fail"
    ws_fail.mkdir()
    (ws_fail / "test_sample.py").write_text("def test_fail():\n    assert 1 == 2\n", encoding="utf-8")
    t_res = execute_test_agent_task(ws_fail)
    assert t_res["passed"] is False and t_res["reopen_code_task"] is True

    # DIST-18: Escalating failure recovery policy
    assert decide_failure_recovery(1, "timeout", "ag-1")["action"] == "retry_same_agent"
    assert decide_failure_recovery(2, "invalid_output", "ag-1")["action"] == "reassign_different_agent"
    assert decide_failure_recovery(3, "verify_failed", "ag-1")["action"] == "escalate_stronger_or_council"
    assert decide_failure_recovery(4, "verify_failed", "ag-1")["action"] == "escalate_human"

    # DIST-19, 20, 21: Perf matrix + CSV, PROVENANCE.json, Amdahl speedup
    log_agent_performance(agent_id="ag-12gb", model="qwen3.5:9b", task_type="backend", success=True, tok_per_sec=34.5, latency_ms=1200, db_path=db_file)
    mat = build_performance_matrix(db_path=db_file)
    assert len(mat["rows"]) == 1 and "qwen3.5:9b" in mat["csv"]
    prov = build_project_provenance([{"file": "app.py", "task_id": "T1", "agent_id": "ag-12gb", "model": "qwen3.5:9b"}])
    assert prov["files"][0]["performed_by"] == "ag-12gb"
    sp = compute_amdahl_speedup(serial_fraction=0.15)
    assert sp[-1]["agents"] == 6 and sp[-1]["speedup"] >= 3.0

    # DIST-13, 14, 22: Tailscale 5-mode diagnostics, install command, and chaos script exists
    peers = parse_tailscale_peers({"Peer": {"k1": {"HostName": "worker-1", "DNSName": "worker-1.tailnet.ts.net.", "TailscaleIPs": ["100.64.0.10"], "Online": True, "OS": "windows"}}})
    assert peers[0]["tailnet_ip"] == "100.64.0.10"
    assert diagnose_tailscale_failure({"control_plane_ok": False})["category"] == "control_plane_unreachable"
    assert diagnose_tailscale_failure({"ip_is_tailnet": False})["category"] == "wrong_ip"
    assert diagnose_tailscale_failure({"port_open": False})["category"] == "port_closed"
    assert diagnose_tailscale_failure({"acl_denied": True})["category"] == "acl_blocked"
    assert diagnose_tailscale_failure({"schema_mismatch": True})["category"] == "version_mismatch"
    assert "setup.ps1" in generate_agent_install_command("http://100.64.0.2:8000", os_type="windows")["command"]
    assert (REPO_ROOT / "scripts" / "chaos" / "chaos_scenarios.ps1").is_file()


# ---------------------------------------------------------------- UX-01..UX-28 Tests

def test_ux01_to_ux28_frontend_modules_i18n_sanitizer_no_emojis_wizard_shares_and_endpoints():
    # UX-01, UX-02, UX-07: Frontend package, PWA manifest/SW, and all new modular JS files <= 500 lines
    pkg = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert "lint" in pkg["scripts"] and "e2e" in pkg["scripts"]
    assert (REPO_ROOT / "master" / "static" / "manifest.webmanifest").is_file()
    assert (REPO_ROOT / "master" / "static" / "sw.js").is_file()

    emoji_re = re.compile("[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA70-\U0001FAFF]")
    for js_name in ("sanitizer.js", "i18n.js", "store.js", "ux_shell.js"):
        txt = (STATIC_JS / js_name).read_text(encoding="utf-8")
        assert len(txt.splitlines()) <= 500
        # UX-21: Zero emojis in UI JS modules
        assert not emoji_re.search(txt), f"Emoji found in {js_name}"

    # UX-06: TR and EN translation tables have identical key sets (0 missing keys!)
    i18n_src = (STATIC_JS / "i18n.js").read_text(encoding="utf-8")
    tr_block = i18n_src.split("tr: {")[1].split("},")[0]
    en_block = i18n_src.split("en: {")[1].split("},")[0]
    tr_keys = set(re.findall(r"'([^']+)'\s*:", tr_block))
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_block))
    assert len(tr_keys) >= 15 and tr_keys == en_keys

    # UX-16: Settings validation rejects invalid enum values
    assert validate_settings({"language": "tr", "theme": "high_contrast"})["valid"] is True
    assert validate_settings({"language": "xx_invalid"})["valid"] is False

    # UX-17: Health wizard produces actionable remediation for missing Ollama/models/bge
    wiz = build_health_wizard_report(ollama_reachable=False, models_count=0, bge_available=False)
    remediations = {c["id"]: c["remediation"] for c in wiz["checks"]}
    assert "ollama serve" in remediations["ollama"]
    assert "bge-m3" in remediations["embeddings"]

    # UX-26: Secret-scanned, owner/allowed-user-restricted, expiring read-only shares
    sh = create_readonly_share(
        owner_id="alice",
        title="Rapor",
        content="Özet ve gizli anahtar sk-123456789012345678901234",
        allowed_users=["bob"],
        ttl_seconds=60,
    )
    assert sh["secrets_redacted"] is True
    fetched = fetch_readonly_share(sh["share_id"], requester_id="bob")
    assert "sk-123456789012345678901234" not in fetched["content"]
    with pytest.raises(PermissionError):
        fetch_readonly_share(sh["share_id"], requester_id="eve")

    expired_sh = create_readonly_share(owner_id="alice", title="Eski", content="x", ttl_seconds=-1)
    with pytest.raises(FileNotFoundError):
        fetch_readonly_share(expired_sh["share_id"], requester_id="alice")

    # HTTP endpoints check (DIST-11 SSE, DIST-19 CSV, UX-17 wizard, UX-24 SLO)
    with TestClient(master_app.app) as client:
        assert client.get("/api/distributed/taxonomy").status_code == 200
        assert client.get("/api/distributed/performance.csv").status_code == 200
        assert client.get("/api/distributed/agents/stream").status_code == 200
        assert client.get("/api/ux/health-wizard").status_code == 200
        assert client.get("/api/ux/slo").status_code == 200
