"""External MCP (Model Context Protocol) Connector Manager & FastAPI Router (SEC-11 hardened).

- Persists connector metadata in local SQLite (`mcp_connectors` table in `config.DB_PATH`).
- NEVER stores plaintext API keys in `platform.db`: all API keys are encrypted with Fernet
  inside `secret_store` (`secrets.db`) which is excluded from backups and exports (SEC-11).
- Real JSON-RPC 2.0 over HTTP / Streamable-HTTP (SSE) client supporting:
  `initialize`, `tools/list`, and `tools/call`.
- Exposes `/api/mcp/connectors` CRUD + `/discover` + `/call` endpoints with local/admin guards & audit logging.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
import dbconn
import policy
import secret_store
from access_control import require_local_or_admin
from audit_log import AuditTrail
from prompt_loader import load_prompt

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(config.DB_PATH)


def _secret_name(connector_id: str) -> str:
    return f"mcp:{connector_id}:api_key"


def init_mcp_db() -> None:
    with _connect() as conn:
        conn.execute(load_prompt("b4_mcp_schema.txt"))
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(mcp_connectors)").fetchall()}
        if "api_key_masked" not in cols:
            conn.execute("ALTER TABLE mcp_connectors ADD COLUMN api_key_masked TEXT NOT NULL DEFAULT ''")
        # Auto-migrate any legacy plaintext api_key rows into encrypted secret_store
        legacy_rows = conn.execute("SELECT id, api_key FROM mcp_connectors WHERE api_key != ''").fetchall()
        for r in legacy_rows:
            raw_k = str(r["api_key"] or "").strip()
            if raw_k:
                secret_store.set_secret(_secret_name(r["id"]), raw_k)
                conn.execute(
                    "UPDATE mcp_connectors SET api_key = '', api_key_masked = ? WHERE id = ?",
                    (secret_store.mask_secret(raw_k), r["id"]),
                )


def _row_to_public(row: sqlite3.Row) -> dict[str, Any]:
    try:
        tools = json.loads(row["tools_json"] or "[]")
    except json.JSONDecodeError:
        tools = []
    masked = row["api_key_masked"] if "api_key_masked" in row.keys() else ""
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "has_api_key": bool(masked),
        "api_key_masked": masked,
        "auth_header": row["auth_header"],
        "auth_prefix": row["auth_prefix"],
        "description": row["description"],
        "enabled": bool(row["enabled"]),
        "tools": tools if isinstance(tools, list) else [],
        "last_status": row["last_status"],
        "last_checked_at": row["last_checked_at"],
        "created_at": row["created_at"],
    }


def list_connectors() -> list[dict[str, Any]]:
    init_mcp_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM mcp_connectors ORDER BY created_at DESC").fetchall()
    return [_row_to_public(r) for r in rows]


def _get_raw_connector(connector_id: str) -> sqlite3.Row | None:
    init_mcp_db()
    with _connect() as conn:
        return conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (connector_id,)).fetchone()


def create_connector(
    name: str,
    url: str,
    api_key: str = "",
    **options: Any,
) -> dict[str, Any]:
    auth_header: str = options.get("auth_header", "Authorization")
    auth_prefix: str | None = options.get("auth_prefix", "Bearer ")
    description: str = options.get("description", "")
    init_mcp_db()
    clean_name = (name or "").strip()[:60]
    clean_url = (url or "").strip()[:300]
    if not clean_name or not clean_url.startswith(("http://", "https://")):
        raise ValueError("Geçerli bir bağlayıcı adı ve http(s):// ile başlayan MCP URL girin.")
    cid = f"mcp-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    raw_key = (api_key or "").strip()
    masked = secret_store.mask_secret(raw_key) if raw_key else ""
    if raw_key:
        secret_store.set_secret(_secret_name(cid), raw_key)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO mcp_connectors (id, name, url, api_key, api_key_masked, auth_header, auth_prefix, description, enabled, created_at)
            VALUES (?, ?, ?, '', ?, ?, ?, ?, 1, ?)
            """,
            (
                cid,
                clean_name,
                clean_url,
                masked,
                (auth_header or "Authorization").strip()[:40],
                auth_prefix if auth_prefix is not None else "Bearer ",
                (description or "").strip()[:240],
                now,
            ),
        )
        row = conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (cid,)).fetchone()
    AuditTrail().append_event(
        actor="admin",
        action="MCP_CONNECTOR_CREATED",
        payload={"connector_id": cid, "name": clean_name, "url": clean_url, "has_api_key": bool(raw_key)},
    )
    return _row_to_public(row)


def update_connector(connector_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    init_mcp_db()
    row = _get_raw_connector(connector_id)
    if not row:
        raise KeyError("MCP bağlayıcı bulunamadı.")
    name = str(patch["name"]).strip()[:60] if "name" in patch and patch["name"] is not None else row["name"]
    url = str(patch["url"]).strip()[:300] if "url" in patch and patch["url"] is not None else row["url"]
    masked = row["api_key_masked"]
    if patch.get("api_key"):
        raw_key = str(patch["api_key"]).strip()
        secret_store.set_secret(_secret_name(connector_id), raw_key)
        masked = secret_store.mask_secret(raw_key)
    enabled = int(bool(patch["enabled"])) if "enabled" in patch and patch["enabled"] is not None else row["enabled"]
    desc = str(patch["description"]).strip()[:240] if "description" in patch and patch["description"] is not None else row["description"]
    with _connect() as conn:
        conn.execute(
            "UPDATE mcp_connectors SET name=?, url=?, api_key='', api_key_masked=?, enabled=?, description=? WHERE id=?",
            (name, url, masked, enabled, desc, connector_id),
        )
        updated = conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (connector_id,)).fetchone()
    AuditTrail().append_event(
        actor="admin",
        action="MCP_CONNECTOR_UPDATED",
        payload={"connector_id": connector_id, "enabled": bool(enabled)},
    )
    return _row_to_public(updated)


def delete_connector(connector_id: str) -> bool:
    init_mcp_db()
    secret_store.delete_secret(_secret_name(connector_id))
    with _connect() as conn:
        cur = conn.execute("DELETE FROM mcp_connectors WHERE id = ?", (connector_id,))
    if cur.rowcount > 0:
        AuditTrail().append_event(
            actor="admin",
            action="MCP_CONNECTOR_DELETED",
            payload={"connector_id": connector_id},
        )
        return True
    return False


def _build_headers(row: sqlite3.Row) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    key = secret_store.get_secret(_secret_name(row["id"])).strip()
    if key:
        hdr = (row["auth_header"] or "Authorization").strip()
        pref = row["auth_prefix"] or ""
        headers[hdr] = f"{pref}{key}" if pref and not key.startswith(pref) else key
    return headers


def _parse_mcp_response(resp: httpx.Response) -> dict[str, Any]:
    ct = (resp.headers.get("content-type") or "").lower()
    text = resp.text.strip()
    if "text/event-stream" in ct or text.startswith("data:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk.startswith("{"):
                    try:
                        return json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
    return resp.json()


async def _rpc_request(
    client: httpx.AsyncClient,
    endpoint: tuple[str, dict[str, str]],
    method: str,
    params: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    url, headers = endpoint
    req_headers = dict(headers)
    if session_id:
        req_headers["Mcp-Session-Id"] = session_id
    payload = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex[:8],
        "method": method,
        "params": params or {},
    }
    resp = await client.post(url, headers=req_headers, json=payload)
    resp.raise_for_status()
    new_sid = resp.headers.get("mcp-session-id") or session_id
    return _parse_mcp_response(resp), new_sid


async def discover_connector_tools(connector_id: str) -> dict[str, Any]:
    """Perform live MCP JSON-RPC 2.0 initialize + tools/list handshake and persist discovered tools."""
    row = _get_raw_connector(connector_id)
    if not row:
        raise KeyError("MCP bağlayıcı bulunamadı.")
    headers = _build_headers(row)
    endpoint = (row["url"], headers)
    now = datetime.now(UTC).isoformat()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            _, sid = await _rpc_request(
                client,
                endpoint,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "cm6453-local-ai", "version": "2.0"},
                },
            )
            tools_resp, _ = await _rpc_request(client, endpoint, "tools/list", {}, session_id=sid)
            raw_tools = (tools_resp.get("result") or {}).get("tools") or []
            tools = [
                {
                    "name": str(t.get("name") or ""),
                    "description": str(t.get("description") or "")[:240],
                    "inputSchema": t.get("inputSchema") or {},
                }
                for t in raw_tools
                if isinstance(t, dict) and t.get("name")
            ]
            status = f"Bağlandı ({len(tools)} araç)"
            with _connect() as conn:
                conn.execute(
                    "UPDATE mcp_connectors SET tools_json=?, last_status=?, last_checked_at=? WHERE id=?",
                    (json.dumps(tools, ensure_ascii=False), status, now, connector_id),
                )
                updated = conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (connector_id,)).fetchone()
            return {"ok": True, "connector": _row_to_public(updated)}
    except (httpx.HTTPError, sqlite3.Error, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        err_status = f"Bağlantı hatası: {str(exc)[:140]}"
        with _connect() as conn:
            conn.execute(
                "UPDATE mcp_connectors SET last_status=?, last_checked_at=? WHERE id=?",
                (err_status, now, connector_id),
            )
        return {"ok": False, "error": err_status}


async def call_connector_tool(connector_id: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a live MCP tools/call on the connected external server using its encrypted API key."""
    row = _get_raw_connector(connector_id)
    if not row:
        raise KeyError("MCP bağlayıcı bulunamadı.")
    if not row["enabled"]:
        raise ValueError("Bu MCP bağlayıcısı pasif durumda.")
    gate = policy.check("mcp_call", payload=json.dumps(arguments or {}, ensure_ascii=False))
    if not gate.allowed:
        raise ValueError(gate.reason)
    headers = _build_headers(row)
    endpoint = (row["url"], headers)
    async with httpx.AsyncClient(timeout=30.0) as client:
        _, sid = await _rpc_request(
            client,
            endpoint,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cm6453-local-ai", "version": "2.0"},
            },
        )
        res, _ = await _rpc_request(
            client,
            endpoint,
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
            session_id=sid,
        )
    AuditTrail().append_event(
        actor="user",
        action="MCP_TOOL_CALLED",
        payload={"connector_id": connector_id, "tool_name": tool_name, "ok": "error" not in res},
    )
    if "error" in res:
        return {"ok": False, "error": res["error"]}
    return {"ok": True, "result": res.get("result")}


def list_enabled_tools_summary() -> list[dict[str, Any]]:
    out = []
    for c in list_connectors():
        if not c["enabled"]:
            continue
        for t in c["tools"]:
            out.append({
                "connector_id": c["id"],
                "connector_name": c["name"],
                "tool_name": t["name"],
                "description": t.get("description") or "",
            })
    return out


class MCPCreateReq(BaseModel):
    name: str
    url: str
    api_key: str = ""
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    description: str = ""


class MCPUpdateReq(BaseModel):
    name: str | None = None
    url: str | None = None
    api_key: str | None = None
    enabled: bool | None = None
    description: str | None = None


class MCPCallReq(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


@router.get("/connectors")
async def api_list_connectors():
    return {"connectors": list_connectors()}


@router.post("/connectors", dependencies=[Depends(require_local_or_admin)])
async def api_create_connector(req: MCPCreateReq):
    try:
        conn = create_connector(
            req.name,
            req.url,
            req.api_key,
            auth_header=req.auth_header,
            auth_prefix=req.auth_prefix,
            description=req.description,
        )
        return {"connector": conn}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/connectors/{connector_id}", dependencies=[Depends(require_local_or_admin)])
async def api_update_connector(connector_id: str, req: MCPUpdateReq):
    try:
        conn = update_connector(connector_id, req.model_dump(exclude_none=True))
        return {"connector": conn}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/connectors/{connector_id}", dependencies=[Depends(require_local_or_admin)])
async def api_delete_connector(connector_id: str):
    if not delete_connector(connector_id):
        raise HTTPException(status_code=404, detail="MCP bağlayıcı bulunamadı.")
    return {"deleted": True}


@router.post("/connectors/{connector_id}/discover", dependencies=[Depends(require_local_or_admin)])
async def api_discover_connector(connector_id: str):
    try:
        return await discover_connector_tools(connector_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/connectors/{connector_id}/call", dependencies=[Depends(require_local_or_admin)])
async def api_call_connector(connector_id: str, req: MCPCallReq):
    try:
        return await call_connector_tool(connector_id, req.tool_name, req.arguments)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP çağrısı başarısız: {exc}") from exc
