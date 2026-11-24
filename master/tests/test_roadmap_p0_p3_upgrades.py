"""End-to-end tests for all P0-P3 project-wide architectural upgrades."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_setup_env_module():
    spec = importlib.util.spec_from_file_location("dadp_setup_env", REPO_ROOT / "scripts" / "setup_env.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_p0_setup_env_hardening_and_idempotency(tmp_path: Path):
    """P0: setup_env generates strong missing secrets, sets UNIFIED_DB=true, and preserves existing keys."""
    setup_env = _load_setup_env_module()

    env_file = tmp_path / ".env"
    env_file.write_text("ADMIN_TOKEN=keep-my-existing-token\nSECRET_KEY=\n", encoding="utf-8")

    first = setup_env.ensure_hardened_env(env_file, write=True)
    assert first["written"] is True
    assert "ADMIN_TOKEN" in first["preserved_keys"]
    assert "SECRET_KEY" in first["generated_keys"]
    assert "BACKUP_PASSWORD" in first["generated_keys"]
    assert "UNIFIED_DB" in first["generated_keys"]

    content = env_file.read_text(encoding="utf-8")
    assert "ADMIN_TOKEN=keep-my-existing-token" in content
    assert "UNIFIED_DB=true" in content

    second = setup_env.ensure_hardened_env(env_file, write=True)
    assert second["written"] is False
    assert second["generated_keys"] == []

    audit = setup_env.audit_runtime_environment()
    assert "binaries" in audit and "packages" in audit


@pytest.mark.integration
def test_p0_unified_db_default_and_single_source_productivity(client):
    """P0: UNIFIED_DB defaults to True, dbunify covers all legacy DBs, and productivity custom agents use SQLite."""
    import config
    import dbunify

    assert config.UNIFIED_DB is True
    assert "auth.db" in dbunify.LEGACY_FILES
    assert "user_profile.db" in dbunify.LEGACY_FILES
    assert "graph_rag.db" in dbunify.LEGACY_FILES

    created = client.post(
        "/api/productivity/agents/custom",
        json={"name": "Tek Kaynak Ajanı", "instructions": "Türkçe ve net yanıtla.", "model": "qwen3.5:4b", "tools": ["calculator"]},
    )
    assert created.status_code == 200
    aid = created.json()["id"]

    # Must appear in BOTH /api/custom-agents (SQLite) AND /api/productivity/agents/custom!
    sql_list = client.get("/api/custom-agents?user_id=default").json()["agents"]
    prod_list = client.get("/api/productivity/agents/custom").json()["custom_agents"]
    assert any(a["agent_id"] == aid for a in sql_list)
    assert any(a["id"] == aid for a in prod_list)


@pytest.mark.e2e
def test_p1_code_editor_and_interactive_labs_ui():
    """P1: Rich offline code editor passes Node tests and hub.js mounts interactive visual labs."""
    node_bin = shutil.which("node")
    assert node_bin is not None
    proc = subprocess.run(
        [node_bin, "--test", "frontend/tests/code_editor.test.mjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    hub_src = (REPO_ROOT / "master" / "static" / "js" / "hub.js").read_text(encoding="utf-8")
    labs_src = (REPO_ROOT / "master" / "static" / "js" / "workspace_labs.js").read_text(encoding="utf-8")
    assert "renderInteractiveLabsTab" in hub_src
    assert "/api/notebooks" in labs_src
    assert "/api/education/flashcards" in labs_src
    assert "/api/memory/conflicts" in labs_src
    assert "/api/eval-studio/benchmark-run" in labs_src


@pytest.mark.integration
def test_p2_ann_index_pg_adapter_and_turkish_benchmark(client, monkeypatch):
    """P2: LSH ANN retrieves top-k, Postgres HA adapter detects DSN, and 300-sample Turkish benchmark runs."""
    from ha.pg_adapter import detect_ha_backend
    from rag.ann_index import RandomHyperplaneANN, probe_ann_backends

    backends = probe_ann_backends()
    assert backends["numpy_lsh_ann"] is True

    rng = np.random.default_rng(42)
    idx = RandomHyperplaneANN(dim=32, num_bits=10)
    target = rng.standard_normal(32).astype(np.float32)
    idx.add("target-doc", target)
    for i in range(150):
        idx.add(f"doc-{i}", rng.standard_normal(32).astype(np.float32))
    hits = idx.search(target, top_k=3)
    assert hits and hits[0][0] == "target-doc" and hits[0][1] > 0.99

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert detect_ha_backend()["active_backend"] == "sqlite_wal"
    monkeypatch.setenv("DATABASE_URL", "postgresql://dadp:pass@127.0.0.1:5432/dadp")
    assert detect_ha_backend()["postgres_configured"] is True

    run_res = client.post("/api/eval-studio/benchmark-run", json={"limit": 100})
    assert run_res.status_code == 200
    rb = run_res.json()
    assert rb["evaluated_count"] == 100
    assert rb["schema_pass_rate"] == 1.0
    assert len(rb["amdahl_speedup"]) == 4

    sum_res = client.get("/api/eval-studio/benchmark-summary")
    assert sum_res.status_code == 200
    assert sum_res.json()["dataset"] == "turkish_benchmark_v1.jsonl"


@pytest.mark.unit
@settings(max_examples=25)
@given(st.lists(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False), min_size=8, max_size=8))
def test_p2_ann_index_self_similarity_pbt(vec_vals: list[float]):
    """P2 Property-Based Test (Hypothesis): any non-zero vector added to ANN must match itself with similarity ~1.0."""
    from rag.ann_index import RandomHyperplaneANN

    arr = np.asarray(vec_vals, dtype=np.float32)
    if float(np.linalg.norm(arr)) < 1e-4:
        return
    idx = RandomHyperplaneANN(dim=8, num_bits=6)
    idx.add("self", arr)
    hits = idx.search(arr, top_k=1)
    assert hits[0][0] == "self"
    assert hits[0][1] >= 0.999
