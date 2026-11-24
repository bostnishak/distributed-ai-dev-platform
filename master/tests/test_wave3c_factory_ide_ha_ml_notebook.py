"""Wave 3C Verification Suite: EPK-05 (Factory Templates), EPK-06 (IDE LSP/DAP/Diff), EPK-10 & EPK-30 (HA/Idempotency), EPK-31 (ML Gate), EPK-32 (Accounting/Quotas), EPK-33 (Notebooks)."""

from __future__ import annotations

import secrets

from fastapi.testclient import TestClient

import app as master_app


def test_epk05_eight_verified_factory_templates_and_repair_plan():
    """EPK-05 (PKA-41..50): All 8 production starter templates pass AST/security verification + repair plan."""
    client = TestClient(master_app.app)
    r_list = client.get("/api/factory/verified-templates")
    assert r_list.status_code == 200
    tpls = r_list.json()["templates"]
    assert len(tpls) == 8

    for t in tpls:
        r_v = client.post(f"/api/factory/verified-templates/{t['id']}/verify", json={"errors": []})
        assert r_v.status_code == 200 and r_v.json()["ok"] is True

    # Repair plan maps syntax/import failures cleanly
    r_rep = client.post(
        "/api/factory/verified-templates/fastapi_service/verify",
        json={"errors": ["SyntaxError: invalid syntax line 4", "ModuleNotFoundError: foo"]},
    )
    assert len(r_rep.json()["repair_plan"]) == 2
    assert r_rep.json()["repair_plan"][0]["strategy"] == "ast_syntax_repair"
    assert client.post("/api/factory/verified-templates/nonexistent/verify").status_code == 404


def test_epk06_ide_lsp_dap_and_multifile_diff():
    """EPK-06 (PKA-51..60, KOD-08): LSP syntax+security diagnostics, DAP breakpoint validation & multi-file diff."""
    client = TestClient(master_app.app)

    r_lsp = client.post("/api/ide/lsp/diagnostics", json={"language": "python", "code": "def f(x):\n    return eval(x)\n"})
    assert r_lsp.status_code == 200
    assert any(s["name"] == "f" for s in r_lsp.json()["symbols"])
    assert any(d["code"] == "S307" for d in r_lsp.json()["diagnostics"])

    r_syn = client.post("/api/ide/lsp/diagnostics", json={"language": "python", "code": "def broken(:\n"})
    assert any(d["severity"] == "error" for d in r_syn.json()["diagnostics"])

    r_dap = client.post("/api/ide/dap/session", json={"code": "a = 1\nb = a + 2\n", "breakpoints": [1, 99]})
    assert r_dap.status_code == 200
    bps = {b["line"]: b["verified"] for b in r_dap.json()["verified_breakpoints"]}
    assert bps[1] is True and bps[99] is False

    r_diff = client.post(
        "/api/ide/diff/multi",
        json={"files": [{"path": "x.py", "before": "a = 1\n", "after": "a = 2\nb = 3\n"}]},
    )
    assert r_diff.status_code == 200 and r_diff.json()["total_added"] == 2


def test_epk10_epk30_ha_leader_lease_failover_and_idempotency():
    """EPK-10 & EPK-30 (PKA-91..PKB-01, PKC-93..PKD-03, OPR-02): Leader lease, drain failover & zero duplicate commits."""
    client = TestClient(master_app.app)
    lkey = f"ha-{secrets.token_hex(4)}"

    r1 = client.post("/api/ha/lease", json={"node_id": "master-a", "lease_key": lkey, "ttl_s": 30})
    assert r1.status_code == 200 and r1.json()["acquired"] is True and r1.json()["term"] == 1

    # Second node cannot steal active lease
    r2 = client.post("/api/ha/lease", json={"node_id": "master-b", "lease_key": lkey, "ttl_s": 30})
    assert r2.status_code == 200 and r2.json()["acquired"] is False

    # Drain master-a -> master-b fails over cleanly with term=2
    assert client.post("/api/ha/drain/master-a", params={"lease_key": lkey}).json()["drained"] is True
    r3 = client.post("/api/ha/lease", json={"node_id": "master-b", "lease_key": lkey, "ttl_s": 30})
    assert r3.json()["acquired"] is True and r3.json()["term"] == 2 and r3.json().get("failover") is True

    # Status includes Amdahl speedup matrix
    st = client.get("/api/ha/status", params={"lease_key": lkey}).json()
    assert st["leader"] == "master-b" and len(st["speedup_matrix"]) == 4

    # Idempotent task result commit prevents duplicates on chaos retry
    ikey = f"idem-{secrets.token_hex(6)}"
    c1 = client.post("/api/ha/idempotency/commit", json={"idempotency_key": ikey, "task_id": "t1", "agent_id": "uye1", "payload": "done"}).json()
    c2 = client.post("/api/ha/idempotency/commit", json={"idempotency_key": ikey, "task_id": "t1", "agent_id": "uye1", "payload": "done"}).json()
    assert c1["duplicate"] is False and c2["duplicate"] is True and c1["result_hash"] == c2["result_hash"]


def test_epk31_ml_promotion_eval_gate_and_rollback():
    """EPK-31 (PKD-04..13): Promotion rejected below threshold, allowed above, rollback reverts to 0%."""
    client = TestClient(master_app.app)
    mid = f"model-{secrets.token_hex(4)}"

    r_rej = client.post(f"/api/ml/models/{mid}/promote", json={"eval_score": 0.62, "min_threshold": 0.80, "canary_pct": 10})
    assert r_rej.status_code == 400

    r_ok = client.post(f"/api/ml/models/{mid}/promote", json={"eval_score": 0.91, "min_threshold": 0.80, "canary_pct": 25})
    assert r_ok.status_code == 200 and r_ok.json()["stage"] == "canary" and r_ok.json()["canary_pct"] == 25

    r_rb = client.post(f"/api/ml/models/{mid}/rollback", json={"reason": "latency_spike"})
    assert r_rb.status_code == 200 and r_rb.json()["stage"] == "rolled_back" and r_rb.json()["canary_pct"] == 0


def test_epk32_accounting_energy_ledger_and_429_quota_enforcement():
    """EPK-32 (PKD-14..23): Token/latency/Wh energy ledger and hard daily quota 429 rejection."""
    client = TestClient(master_app.app)
    uid = f"acc_{secrets.token_hex(4)}"

    assert client.put(f"/api/accounting/quotas/{uid}", json={"daily_token_limit": 500, "daily_energy_wh_limit": 50.0, "hard_enforce": True}).status_code == 200
    r1 = client.post("/api/accounting/record", json={"user_id": uid, "model": "qwen3.5:4b", "tokens_in": 150, "tokens_out": 200, "latency_ms": 600})
    assert r1.status_code == 200 and r1.json()["energy_wh"] > 0

    # Exceeding daily token limit must return structured 429
    r_over = client.post("/api/accounting/record", json={"user_id": uid, "model": "qwen3.5:4b", "tokens_in": 200, "tokens_out": 200, "latency_ms": 400})
    assert r_over.status_code == 429

    rep = client.get(f"/api/accounting/report/{uid}").json()
    assert rep["tokens_total"] == 350 and rep["calls"] == 1


def test_epk33_stateful_notebook_safe_execution_and_ipynb_roundtrip():
    """EPK-33 (PKD-24..33): Stateful notebook CRUD, safe AST cell runner (blocks imports), and .ipynb v4 round-trip."""
    client = TestClient(master_app.app)
    uid = f"nb_{secrets.token_hex(4)}"

    r_create = client.post(
        "/api/notebooks",
        json={
            "user_id": uid,
            "title": "Hesaplama Defteri",
            "cells": [
                {"cell_type": "code", "source": "a = 6\nb = 7\nprint('sonuc:', a * b)\na * b"},
                {"cell_type": "code", "source": "import os"},
            ],
        },
    )
    assert r_create.status_code == 200
    nb_id = r_create.json()["notebook_id"]

    # Safe cell executes cleanly
    r_run0 = client.post(f"/api/notebooks/{nb_id}/run", json={"user_id": uid, "cell_index": 0})
    assert r_run0.status_code == 200 and r_run0.json()["ok"] is True
    assert r_run0.json()["output"]["result"] == 42
    assert "sonuc: 42" in r_run0.json()["output"]["stdout"]

    # Unsafe import statement is blocked by AST guard
    r_run1 = client.post(f"/api/notebooks/{nb_id}/run", json={"user_id": uid, "cell_index": 1})
    assert r_run1.status_code == 200 and r_run1.json()["ok"] is False

    # Export .ipynb v4.5 and re-import
    r_exp = client.get(f"/api/notebooks/{nb_id}/export.ipynb", params={"user_id": uid})
    assert r_exp.status_code == 200 and r_exp.json()["nbformat"] == 4
    r_imp = client.post("/api/notebooks/import-ipynb", json={"user_id": uid, "ipynb": r_exp.json()})
    assert r_imp.status_code == 200 and len(r_imp.json()["cells"]) == 2
