"""Plan v3 Wave 3 OpenAPI contract tests: SMA/SMB (response schemas) & ACK/ACL (descriptions)."""

from __future__ import annotations

import pytest

import app as master_app

pytestmark = pytest.mark.contract


@pytest.mark.contract
def test_sma_smb_ack_acl_every_openapi_route_has_200_schema_and_description():
    """Every GET/POST/PUT/PATCH/DELETE operation in OpenAPI must expose a 200 JSON schema and description."""
    spec = master_app.app.openapi()
    missing_schema: list[str] = []
    missing_desc: list[str] = []

    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                continue
            ok_schema = op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema")
            if not ok_schema:
                missing_schema.append(f"{method.upper()} {path}")
            if not (op.get("description") or "").strip():
                missing_desc.append(f"{method.upper()} {path}")

    assert missing_schema == [], f"Routes without 200 response schema: {missing_schema[:10]}"
    assert missing_desc == [], f"Routes without description: {missing_desc[:10]}"

    # Ensure core typed schemas expose expected contract properties
    schemas = spec["components"]["schemas"]
    assert "status" in schemas["HealthResponse"]["properties"]
    assert "components" in schemas["ReadyResponse"]["properties"]
    assert "authenticated" in schemas["AuthResponse"]["properties"]
