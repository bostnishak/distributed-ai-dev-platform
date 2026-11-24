"""Wave 3A Verification Suite: EPK-03 (Orgs/RBAC/IDOR), EPK-04 (OpenAPI contracts & typegen), EPK-25 (Field crypto/RTBF), EPK-26 (PBT/Fault injection)."""

from __future__ import annotations

import base64
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api_schemas
import app as master_app
import user_profile as up
from auth import orgs as auth_orgs
from auth import service as auth_service
from privacy import field_crypto

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_epk03_orgs_invites_rbac_and_idor_enforcement():
    """EPK-03 (PKA-21..30): Org creation, single-use invite redemption, RBAC checks, and session A->B IDOR block."""
    client = TestClient(master_app.app)
    slug = f"team-{secrets.token_hex(4)}"

    r_create = client.post("/api/auth/orgs", json={"name": "Yazılım Ekibi", "slug": slug, "owner_id": "ali"})
    assert r_create.status_code == 200, r_create.text
    org_id = r_create.json()["org"]["id"]

    # Duplicate slug must fail cleanly (fault injection)
    r_dup = client.post("/api/auth/orgs", json={"name": "Kopya", "slug": slug, "owner_id": "ali"})
    assert r_dup.status_code == 400

    # Non-member cannot list members
    r_denied = client.get(f"/api/auth/orgs/{org_id}/members", params={"user_id": "veli"})
    assert r_denied.status_code == 403

    # Owner issues single-use invite
    r_inv = client.post(
        f"/api/auth/orgs/{org_id}/invites",
        json={"role": "member", "email": "veli@local", "ttl_hours": 24, "invited_by": "ali"},
    )
    assert r_inv.status_code == 200, r_inv.text
    token = r_inv.json()["invite"]["invite_token"]

    # Veli redeems invite
    r_acc = client.post("/api/auth/orgs/invites/accept", json={"invite_token": token, "user_id": "veli"})
    assert r_acc.status_code == 200
    assert r_acc.json()["role"] == "member"

    # Re-using the same single-use invite must fail
    r_reuse = client.post("/api/auth/orgs/invites/accept", json={"invite_token": token, "user_id": "ayse"})
    assert r_reuse.status_code == 400

    # Member can list members, cannot issue invites
    r_mem = client.get(f"/api/auth/orgs/{org_id}/members", params={"user_id": "veli"})
    assert r_mem.status_code == 200
    assert len(r_mem.json()["members"]) == 2
    r_forbid_inv = client.post(
        f"/api/auth/orgs/{org_id}/invites",
        json={"role": "viewer", "invited_by": "veli"},
    )
    assert r_forbid_inv.status_code == 403

    # RBAC matrix check
    assert client.post("/api/auth/orgs/rbac/check", json={"role": "viewer", "action": "read"}).json()["allowed"] is True
    assert client.post("/api/auth/orgs/rbac/check", json={"role": "viewer", "action": "write"}).json()["allowed"] is False

    # Authenticated session A->B IDOR spoofing must return 403
    auth_service.init_auth_db()
    uname = f"u_{secrets.token_hex(4)}"
    u = auth_service.create_user(uname, "Guclu!2026Sifre", role="member")
    _, signed = auth_service.create_session(u["id"], client_ip="127.0.0.1")
    client.cookies.set(auth_service.SESSION_COOKIE_NAME, signed)
    r_idor = client.get("/api/auth/orgs", params={"user_id": "ali"})
    assert r_idor.status_code == 403


def test_epk04_openapi_contracts_and_js_typegen():
    """EPK-04 (PKA-31..40): Every OpenAPI route has description+schema and gen_api_types.py produces valid JS."""
    report = api_schemas.validate_openapi_contracts(master_app.app)
    assert report["ok"] is True, f"Contract violations: {report}"
    assert report["total_operations"] >= 240
    assert report["schema_count"] >= 20

    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_api_types.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "api_types.js" in res.stdout
    out_js = REPO_ROOT / "master" / "static" / "js" / "api_types.js"
    assert out_js.is_file()
    chk = subprocess.run(["node", "--check", str(out_js)], capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr


def test_epk25_field_crypto_tamper_malware_scan_and_rtbf_proof():
    """EPK-25 (PKC-43..52): Authenticated field crypto roundtrip + tamper fail + EICAR scan + RTBF proof."""
    client = TestClient(master_app.app)

    # Round-trip Turkish/Unicode payloads via API
    secret_text = "TCKN: 12345678901 · Şifreli Müşteri Notu €100"
    enc_res = client.post("/api/privacy/encrypt", json={"plaintext": secret_text})
    assert enc_res.status_code == 200
    ct = enc_res.json()["ciphertext"]
    assert ct.startswith("v1:") and secret_text not in ct

    dec_res = client.post("/api/privacy/decrypt", json={"ciphertext": ct})
    assert dec_res.status_code == 200
    assert dec_res.json()["plaintext"] == secret_text

    # Fault injection: tampering a single byte in ciphertext must fail HMAC check
    raw = bytearray(base64.urlsafe_b64decode(ct[3:]))
    raw[-1] ^= 0xFF
    tampered = "v1:" + base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
    assert client.post("/api/privacy/decrypt", json={"ciphertext": tampered}).status_code == 400

    # Wrong key must also fail
    with pytest.raises(ValueError):
        field_crypto.decrypt_field(ct, key_override=b"0" * 32)

    # Malware scanner catches EICAR and passes benign text
    eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    r_bad = client.post("/api/privacy/scan-file", json={"filename": "eicar.txt", "content": eicar})
    assert r_bad.status_code == 200 and r_bad.json()["clean"] is False
    r_ok = client.post("/api/privacy/scan-file", json={"filename": "clean.txt", "content": "Merhaba dünya"})
    assert r_ok.status_code == 200 and r_ok.json()["clean"] is True

    # RTBF cryptographic erasure proof
    uid = f"rtbf_{secrets.token_hex(4)}"
    up.init_db()
    up.record_usage(uid, "conv1", "qwen3.5:4b", "genel", 10, 20, 50, False)
    up.add_fact(uid, "preference", "Kahve severim")
    r_wipe = client.post(f"/api/privacy/rtbf/{uid}")
    assert r_wipe.status_code == 200, r_wipe.text
    proof = r_wipe.json()
    assert proof["ok"] is True
    assert proof["residual_hits"] == 0
    assert uid not in proof["user_hash"]
    assert len(proof["receipt_hmac"]) == 64

    r_list = client.get(f"/api/privacy/rtbf/{uid}/proofs")
    assert r_list.status_code == 200
    assert any(p["proof_id"] == proof["proof_id"] for p in r_list.json()["proofs"])


def test_epk26_property_based_crypto_and_rbac_invariants():
    """EPK-26 (PKC-53..62): Property-based fuzzing across field crypto & RBAC role/action lattice."""
    samples = ["a", "Türkçe ğüşıöçĞÜŞİÖÇ", "line1\nline2\n" * 50, '{"k": [1, 2, 3]}', "x" * 4096]
    for sample in samples:
        c1 = field_crypto.encrypt_field(sample)
        c2 = field_crypto.encrypt_field(sample)
        assert c1 != c2  # semantic security (fresh nonce each call)
        assert field_crypto.decrypt_field(c1) == sample
        assert field_crypto.decrypt_field(c2) == sample

    # RBAC monotonicity: owner >= admin >= member >= viewer
    actions = ["read", "write", "invite", "manage_members", "manage_settings", "delete_org", "admin"]
    for act in actions:
        if auth_orgs.check_rbac_permission("viewer", act):
            assert auth_orgs.check_rbac_permission("member", act)
        if auth_orgs.check_rbac_permission("member", act):
            assert auth_orgs.check_rbac_permission("admin", act)
        if auth_orgs.check_rbac_permission("admin", act):
            assert auth_orgs.check_rbac_permission("owner", act)
