"""SEC-11..SEC-24 Comprehensive Security Hardening Test Suite (`pytest -m security`)."""

from __future__ import annotations

import ast
import io
import json
import logging
import re
import zipfile
from pathlib import Path

import pytest
import pyzipper
from fastapi.testclient import TestClient

import app as master_app
import backup_manager
import config
import db
import log_sanitizer
import mcp_connector
import preview_server
import sandbox
import secret_store
import user_profile
from audit_log import AuditTrail

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = REPO_ROOT / "master"

pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# SEC-11: Encrypted secrets (Fernet) + excluded from backups + key rotation
# ---------------------------------------------------------------------------

def test_sec11_encrypted_secrets_not_plaintext_not_in_backup_and_rotatable(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    monkeypatch.setattr(config, "SECRET_KEY", "initial-master-key-for-sec11-test")

    secret_val = "sk-super-secret-mcp-token-9988776655"
    conn = mcp_connector.create_connector(
        name="Secure MCP",
        url="https://mcp.example.com/rpc",
        api_key=secret_val,
    )
    assert conn["has_api_key"] is True
    assert secret_val not in conn["api_key_masked"]

    # 1. Plaintext secret must NOT appear in platform.db OR secrets.db on disk
    assert secret_val.encode("utf-8") not in (tmp_path / "platform.db").read_bytes()
    assert secret_val.encode("utf-8") not in (tmp_path / "secrets.db").read_bytes()

    # 2. Encrypted backup ZIP must NOT contain secrets.db or plaintext secret
    backup_bytes = backup_manager.create_enterprise_backup_zip(data_dir=tmp_path, password="BackupPass!123")
    with pyzipper.AESZipFile(io.BytesIO(backup_bytes), "r") as zf:
        zf.setpassword(b"BackupPass!123")
        names = zf.namelist()
        assert not any("secrets.db" in n or ".master.key" in n for n in names)
        for name in names:
            assert secret_val.encode("utf-8") not in zf.read(name)

    # 3. Master key rotation re-encrypts stored secrets and preserves decryption
    rotated = secret_store.rotate_master_key(
        new_secret_key="rotated-master-key-v2-sec11",
        old_secret_key="initial-master-key-for-sec11-test",
    )
    assert rotated >= 1
    assert secret_store.get_secret(f"mcp:{conn['id']}:api_key") == secret_val
    assert secret_val.encode("utf-8") not in (tmp_path / "secrets.db").read_bytes()


# ---------------------------------------------------------------------------
# SEC-12: Password-encrypted AES-256 backup + SHA-256 verification + restore
# ---------------------------------------------------------------------------

def test_sec12_encrypted_backup_requires_password_and_restores_verified(tmp_path: Path, monkeypatch):
    src_dir = tmp_path / "src_data"
    src_dir.mkdir()
    (src_dir / "sample.txt").write_text("Önemli Türkçe veri ğüşiöç", encoding="utf-8")
    (src_dir / "secrets.db").write_bytes(b"MUST_NEVER_BE_BACKED_UP")
    monkeypatch.setattr(config, "DATA_DIR", src_dir)
    monkeypatch.setattr(config, "SECRET_KEY", "sec12-key")

    enc_zip = backup_manager.create_enterprise_backup_zip(data_dir=src_dir, password="CorrectPassword!42")

    # Cannot be opened without password
    with pytest.raises((RuntimeError, zipfile.BadZipFile)):
        with pyzipper.AESZipFile(io.BytesIO(enc_zip), "r") as zf:
            zf.read("backup/BACKUP_MANIFEST.json")

    # Wrong password via REST endpoint returns HTTP 400
    client = TestClient(master_app.app)
    restore_dir = tmp_path / "restored"
    monkeypatch.setattr(config, "DATA_DIR", restore_dir)
    bad_resp = client.post(
        "/api/admin/backup/restore",
        files={"file": ("backup.zip", enc_zip, "application/zip")},
        data={"password": "WrongPassword"},
    )
    assert bad_resp.status_code == 400

    # Correct password restores and verifies SHA-256 checksums
    ok_resp = client.post(
        "/api/admin/backup/restore",
        files={"file": ("backup.zip", enc_zip, "application/zip")},
        data={"password": "CorrectPassword!42"},
    )
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["verified_sha256"] is True
    assert body["restored_count"] >= 1
    assert (restore_dir / "sample.txt").read_text(encoding="utf-8") == "Önemli Türkçe veri ğüşiöç"
    assert not (restore_dir / "secrets.db").exists()


# ---------------------------------------------------------------------------
# SEC-13 & SEC-14: Container sandbox flags + AST test forbidding shell=True/Popen in routes
# ---------------------------------------------------------------------------

def test_sec13_sandbox_docker_args_are_fully_hardened(tmp_path: Path):
    args = sandbox.build_docker_run_args(tmp_path, command=["python", "-V"])
    joined = " ".join(args)
    assert "--user 10001:10001" in joined
    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--cap-drop ALL" in joined
    assert "no-new-privileges:true" in joined
    assert "--pids-limit 64" in joined
    assert "--memory" in joined and "--cpus" in joined
    assert "seccomp=" in joined


def test_sec14_no_shell_true_or_host_popen_in_any_api_route_module():
    """AST security gate: NO HTTP route module may invoke shell=True or subprocess.Popen."""
    route_files = [
        *MASTER_DIR.glob("*_api.py"),
        MASTER_DIR / "assistant.py",
        MASTER_DIR / "app.py",
        MASTER_DIR / "backup_manager.py",
        MASTER_DIR / "mcp_connector.py",
    ]
    violations: list[str] = []
    for path in route_files:
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        violations.append(f"{path.name}:{node.lineno}: shell=True forbidden")
                if isinstance(node.func, ast.Attribute) and node.func.attr == "Popen":
                    violations.append(f"{path.name}:{node.lineno}: subprocess.Popen forbidden in route module")
    assert violations == [], f"SEC-14 AST violations: {violations}"


# ---------------------------------------------------------------------------
# SEC-15: Wired AuditTrail + tamper line pinpoint via GET /api/admin/audit/verify
# ---------------------------------------------------------------------------

def test_sec15_audit_trail_detects_tampered_line(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    trail = AuditTrail(log_path=tmp_path / "audit_chain.jsonl")
    trail.append_event("admin", "BACKUP_CREATED", {"size": 100})
    trail.append_event("admin", "SETTINGS_UPDATED", {"theme": "dark"})
    trail.append_event("admin", "AGENT_KEY_REVOKED", {"agent_id": "uye1"})

    client = TestClient(master_app.app)
    v_ok = client.get("/api/admin/audit/verify")
    assert v_ok.status_code == 200
    assert v_ok.json()["valid"] is True
    assert v_ok.json()["total_entries"] == 3

    # Manually tamper line 2 payload
    lines = (tmp_path / "audit_chain.jsonl").read_text(encoding="utf-8").splitlines()
    rec2 = json.loads(lines[1])
    rec2["payload"]["theme"] = "TAMPERED"
    lines[1] = json.dumps(rec2)
    (tmp_path / "audit_chain.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    v_bad = client.get("/api/admin/audit/verify")
    assert v_bad.status_code == 200
    data = v_bad.json()
    assert data["valid"] is False
    assert data["corrupted_line"] == 2


# ---------------------------------------------------------------------------
# SEC-16: Security headers, cross-origin POST rejection, and CSRF double-submit
# ---------------------------------------------------------------------------

def test_sec16_headers_cross_origin_block_and_csrf():
    client = TestClient(master_app.app)
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "default-src 'self'" in r_root.headers.get("content-security-policy", "")
    assert r_root.headers.get("x-content-type-options") == "nosniff"
    assert r_root.headers.get("x-frame-options") == "DENY"
    assert r_root.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "cm6453_csrf" in r_root.cookies

    # Cross-origin POST must be rejected with 403
    r_xorigin = client.post(
        "/api/user/profiles",
        json={"display_name": "Evil"},
        headers={"Origin": "https://attacker.example"},
    )
    assert r_xorigin.status_code == 403

    # Missing X-CSRF-Token when cookie is set must be rejected with 403
    r_no_csrf = client.post("/api/user/profiles", json={"display_name": "NoCsrf"})
    assert r_no_csrf.status_code == 403


# ---------------------------------------------------------------------------
# SEC-17: Preview origin isolation (sandbox CSP + second origin app with no /api)
# ---------------------------------------------------------------------------

def test_sec17_preview_origin_isolation(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path)
    ws = tmp_path / "sec17-ws"
    ws.mkdir()
    (ws / "index.html").write_text("<html><body><script>fetch('/api/projects')</script></body></html>", encoding="utf-8")

    # 1. Main app preview enforces sandbox CSP (opaque origin)
    main_client = TestClient(master_app.app)
    r_main = main_client.get("/api/studio/workspaces/sec17-ws/preview/index.html")
    assert r_main.status_code == 200
    csp = r_main.headers.get("content-security-policy", "")
    assert "sandbox" in csp and "connect-src 'none'" in csp

    # 2. Isolated second-origin preview app serves file with zero cookies and zero /api routes
    prev_client = TestClient(preview_server.preview_app)
    r_prev = prev_client.get("/preview/sec17-ws/index.html")
    assert r_prev.status_code == 200
    assert "sandbox" in r_prev.headers.get("content-security-policy", "")
    assert len(r_prev.cookies) == 0
    assert prev_client.get("/api/projects").status_code == 404


# ---------------------------------------------------------------------------
# SEC-18: Per-agent keys, task ownership (403), revocation (401), rotation
# ---------------------------------------------------------------------------

def test_sec18_per_agent_key_ownership_and_revocation(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sec18.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "AGENT_TOKEN", "bootstrap-token-sec18")
    db.init_db()

    client = TestClient(master_app.app)
    boot_hdr = {"Authorization": "Bearer bootstrap-token-sec18"}

    reg_a = client.post(
        "/api/agents/register",
        json={"agent_id": "agent-a", "member_name": "A", "model": "qwen3.5:4b", "capabilities": ["completion"]},
        headers=boot_hdr,
    )
    reg_b = client.post(
        "/api/agents/register",
        json={"agent_id": "agent-b", "member_name": "B", "model": "qwen3.5:4b", "capabilities": ["completion"]},
        headers=boot_hdr,
    )
    assert reg_a.status_code == 200 and reg_b.status_code == 200
    key_a = reg_a.json()["agent_key"]
    key_b = reg_b.json()["agent_key"]
    assert key_a.startswith("agt_") and key_b.startswith("agt_") and key_a != key_b

    # Create a task assigned exclusively to agent-b
    pid = db.create_project("SEC18", "doc", None)
    with db.connect() as conn:
        tid = conn.execute(
            "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status) "
            "VALUES (?, 'T1', 1, 'backend', 'Task', 'Desc', '{}', 'planned')",
            (pid,),
        ).lastrowid
    db.assign_task(tid, "agent-b", {"reason": "test"})

    # Agent A attempting to submit result for Agent B's task MUST get 403
    r_forbid = client.post(
        f"/api/tasks/{tid}/result",
        json={"status": "done", "output": "Spoofed output " * 5},
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert r_forbid.status_code == 403

    # Agent B submitting result for its own task succeeds (200)
    r_ok = client.post(
        f"/api/tasks/{tid}/result",
        json={"status": "done", "output": "Legitimate output " * 5},
        headers={"Authorization": f"Bearer {key_b}"},
    )
    assert r_ok.status_code == 200

    # Revoke Agent A -> heartbeat and re-registration must fail with 401
    assert client.post("/api/agents/agent-a/revoke-key").status_code == 200
    assert client.post(
        "/api/agents/agent-a/heartbeat",
        json={"status": "idle"},
        headers={"Authorization": f"Bearer {key_a}"},
    ).status_code == 401
    assert client.post(
        "/api/agents/register",
        json={"agent_id": "agent-a", "member_name": "A", "model": "qwen3.5:4b", "capabilities": ["completion"]},
        headers=boot_hdr,
    ).status_code == 401


# ---------------------------------------------------------------------------
# SEC-21 & SEC-23: Physical Right to Erasure (VACUUM/WAL) & Log PII/Secret Redaction
# ---------------------------------------------------------------------------

def test_sec21_and_sec23_physical_erasure_and_log_redaction(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    canary = "UNIQUE_USER_CANARY_99118822"
    user_profile.upsert_saved_chat(
        "erase-u",
        "c-erase",
        canary,
        1700000000000,
        [{"role": "user", "text": f"Gizli metin {canary}"}],
    )
    user_profile.add_fact("erase-u", "preference", f"Not {canary}")

    # Verify wipe_data physically removes canary from SQLite DB & WAL files
    user_profile.wipe_data("erase-u", "all")
    for db_file in tmp_path.glob("*.db*"):
        assert canary.encode("utf-8") not in db_file.read_bytes(), f"Canary still present in {db_file.name}"

    # Verify log filter masks tokens, TCKN, IBAN, phone, and email
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(log_sanitizer.SecretAndPIIRedactingFilter())
    test_log = logging.getLogger("sec23_test_logger")
    test_log.setLevel(logging.INFO)
    test_log.handlers = [handler]
    test_log.info(
        "Authorization: Bearer agt_deadbeef1234567890abcdef TCKN=12345678901 "
        "IBAN=TR330006100519786457841326 Tel=05321234567 Mail=ali@example.com tskey-auth-abcdef123456"
    )
    logged = buf.getvalue()
    for secret_str in ("agt_deadbeef1234567890abcdef", "12345678901", "TR330006100519786457841326", "05321234567", "ali@example.com", "tskey-auth-abcdef123456"):
        assert secret_str not in logged


# ---------------------------------------------------------------------------
# SEC-19, SEC-20, SEC-24: CI Scans, Gitleaks Rules, Network Binding & Firewall Docs
# ---------------------------------------------------------------------------

def test_sec19_sec20_sec24_configs_and_policies():
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for token in ("pip-audit", "cyclonedx", "trivy", "gitleaks", "pytest -m security"):
        assert token in ci_text

    gl_text = (REPO_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    assert "tskey-" in gl_text and "AGENT_TOKEN" in gl_text and "AIza" in gl_text
    assert re.search(r"tskey-(?:auth|api|client)-[A-Za-z0-9\-_]{10,}", "tskey-auth-kFakeKey1234567890")

    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8000:8000" in compose_text

    dev_ps1 = (REPO_ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")
    assert "127.0.0.1" in dev_ps1 and "tailscale ip -4" in dev_ps1

    fw_doc = (REPO_ROOT / "docs" / "security" / "network-firewall.md").read_text(encoding="utf-8")
    assert "RemoteAddress 100.64.0.0/10" in fw_doc and "-Profile Private" in fw_doc
