"""Wave 3E Verification Suite: EPK-11, EPK-12, EPK-13, EPK-16, EPK-17, EPK-23, EPK-24, EPK-27, EPK-28, EPK-29, EPK-34."""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as master_app

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_epk11_versioned_custom_agents_and_rollback():
    """EPK-11 (PKB-02..11, AJN-01/06): Create custom assistant v1->v2 and roll back cleanly to v1."""
    client = TestClient(master_app.app)
    uid = f"cag_{secrets.token_hex(4)}"

    r1 = client.post("/api/custom-agents", json={"user_id": uid, "name": "Mimari Uzman", "instructions": "v1 talimat", "allowed_tools": ["rag"]})
    assert r1.status_code == 200 and r1.json()["version"] == 1
    aid = r1.json()["agent_id"]

    r2 = client.post("/api/custom-agents", json={"agent_id": aid, "user_id": uid, "name": "Mimari Uzman", "instructions": "v2 talimat", "allowed_tools": ["rag", "lint"]})
    assert r2.status_code == 200 and r2.json()["version"] == 2

    r_rb = client.post(f"/api/custom-agents/{aid}/rollback", json={"user_id": uid, "target_version": 1})
    assert r_rb.status_code == 200 and r_rb.json()["instructions"] == "v1 talimat"


def test_epk12_signed_webhooks_and_cron_validator():
    """EPK-12 (PKB-12..21): Constant-time HMAC webhook sign/verify + 5-field cron validator."""
    client = TestClient(master_app.app)
    payload = '{"event":"build.ok"}'
    sec = "super-secret-2026"

    r_sign = client.post("/api/automation/webhooks/sign", json={"event_type": "build.ok", "target_url": "http://127.0.0.1:9000/h", "payload": payload, "secret": sec})
    assert r_sign.status_code == 200
    sig = r_sign.json()["signature"]

    assert client.post("/api/automation/webhooks/verify", json={"payload": payload, "secret": sec, "signature": sig}).json()["verified"] is True
    assert client.post("/api/automation/webhooks/verify", json={"payload": payload + "!", "secret": sec, "signature": sig}).json()["verified"] is False

    assert client.post("/api/automation/cron/validate", json={"expression": "0 9 * * 1-5"}).json()["valid"] is True
    assert client.post("/api/automation/cron/validate", json={"expression": "99 9 * * *"}).json()["valid"] is False


def test_epk13_mcp_server_rpc_and_human_approval_gate():
    """EPK-13 (PKB-22..31): JSON-RPC 2.0 MCP server + mandatory human approval gate on side effects + local connectors."""
    client = TestClient(master_app.app)
    assert client.post("/api/mcp-server/rpc", json={"method": "initialize"}).json()["result"]["serverInfo"]["name"] == "dadp-mcp-server"
    assert len(client.post("/api/mcp-server/rpc", json={"method": "tools/list"}).json()["result"]["tools"]) >= 4

    # Side-effect tool blocked without human_approved=True
    r_blk = client.post("/api/mcp-server/rpc", json={"method": "tools/call", "params": {"name": "dadp_run_backup"}}).json()
    assert "error" in r_blk and r_blk["error"]["code"] == -32003

    r_ok = client.post("/api/mcp-server/rpc", json={"method": "tools/call", "params": {"name": "dadp_run_backup", "human_approved": True}}).json()
    assert r_ok["result"]["status"] == "executed"
    assert client.get("/api/mcp-server/connectors").json()["count"] >= 4


def test_epk17_epk23_epk24_otel_openai_compat_pwa_and_updater():
    """EPK-17, EPK-23, EPK-24: OTel OTLP spans, OpenAI /v1/* endpoints, PWA manifest, and SemVer/SHA-256 updater."""
    client = TestClient(master_app.app)

    r_sp = client.post("/api/telemetry/otel/spans", json={"name": "rag.search", "duration_ms": 18.4, "status": "OK"})
    assert r_sp.status_code == 200 and r_sp.json()["span"]["traceparent"].startswith("00-")
    assert client.get("/api/telemetry/otel/spans").json()["span_count"] >= 1

    assert client.get("/v1/models").json()["object"] == "list"
    r_chat = client.post("/v1/chat/completions", json={"model": "dadp-local", "messages": [{"role": "user", "content": "12 * 12"}]})
    assert r_chat.status_code == 200 and "144" in r_chat.json()["choices"][0]["message"]["content"]

    r_emb = client.post("/v1/embeddings", json={"model": "dadp-embed-local", "input": ["merhaba", "dünya"]})
    assert r_emb.status_code == 200 and len(r_emb.json()["data"]) == 2 and len(r_emb.json()["data"][0]["embedding"]) == 64

    pwa = json.loads((REPO_ROOT / "master" / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert pwa["display"] == "standalone"

    assert client.get("/api/admin/update/status", params={"available_version": "3.0.0"}).json()["update_available"] is True
    sample = "dadp-release-artifact"
    h = hashlib.sha256(sample.encode()).hexdigest()
    assert client.post("/api/admin/update/verify-release", json={"payload": sample, "expected_sha256": h}).json()["verified"] is True


def test_epk28_epk29_notifications_quiet_hours_and_signed_marketplace():
    """EPK-28 & EPK-29: Notification quiet hours suppression + HMAC-signed marketplace with permission approval."""
    client = TestClient(master_app.app)

    r_ch = client.post("/api/notifications/channels", json={"kind": "discord", "name": "Ops Alert", "quiet_start_hour": 22, "quiet_end_hour": 7})
    assert r_ch.status_code == 200
    cid = r_ch.json()["channel_id"]

    # Suppressed during quiet hour 23 UTC, dispatched at 14 UTC
    assert client.post("/api/notifications/dispatch", json={"channel_id": cid, "title": "Alert", "message": "Disk 90%", "hour_utc": 23}).json()["dispatched"] is False
    assert client.post("/api/notifications/dispatch", json={"channel_id": cid, "title": "Alert", "message": "Disk 90%", "hour_utc": 14}).json()["dispatched"] is True

    pid = f"pkg-{secrets.token_hex(4)}"
    r_pub = client.post("/api/marketplace/publish", json={"package_id": pid, "name": "CNC Tool", "version": "1.0.0", "kind": "tool", "permissions": ["cnc.read"]})
    assert r_pub.status_code == 200 and len(r_pub.json()["signature_hmac"]) == 64

    # Install rejected without explicit permission approval
    assert client.post("/api/marketplace/install", json={"package_id": pid, "approved_permissions": False}).status_code == 403
    r_inst = client.post("/api/marketplace/install", json={"package_id": pid, "approved_permissions": True})
    assert r_inst.status_code == 200 and r_inst.json()["installed"] is True
    assert client.delete(f"/api/marketplace/items/{pid}").json()["installed"] is False


def test_epk16_epk27_epk34_i18n_and_mv3_browser_extension():
    """EPK-16, EPK-27, EPK-34: 5-language i18n file + MV3 browser extension sidePanel/contextMenus/consent."""
    i18n_src = (REPO_ROOT / "master" / "static" / "js" / "i18n.js").read_text(encoding="utf-8")
    for lang in ("'tr'", "'en'", "'de'", "'fr'", "'ar'"):
        assert lang in i18n_src
    assert "getTextDirection" in i18n_src

    ext_dir = REPO_ROOT / "extensions" / "browser"
    manifest = json.loads((ext_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert "sidePanel" in manifest["permissions"] and "contextMenus" in manifest["permissions"]
    assert all("127.0.0.1" in hp or "localhost" in hp for hp in manifest["host_permissions"])
    assert (ext_dir / "background.js").is_file()
    sidepanel = (ext_dir / "sidepanel.html").read_text(encoding="utf-8")
    assert 'id="consent"' in sidepanel
