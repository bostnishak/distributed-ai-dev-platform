"""External MCP (Model Context Protocol) Connector Manager & FastAPI Router.

Allows users to connect external MCP servers using a server URL and API Key / Bearer Token:
- Persists connectors in local SQLite (`mcp_connectors` table in `config.DB_PATH`).
- Masks API keys in all API responses so secrets are never leaked to the UI.
- Real JSON-RPC 2.0 over HTTP / Streamable-HTTP (SSE) client supporting:
  `initialize`, `tools/list`, and `tools/call`.
- Exposes `/api/mcp/connectors` CRUD + `/discover` + `/call` endpoints.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_mcp_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_connectors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                api_key TEXT NOT NULL DEFAULT '',
                auth_header TEXT NOT NULL DEFAULT 'Authorization',
                auth_prefix TEXT NOT NULL DEFAULT 'Bearer ',
                description TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                tools_json TEXT NOT NULL DEFAULT '[]',
                last_status TEXT NOT NULL DEFAULT 'Henüz test edilmedi',
                last_checked_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )


def _mask_key(raw: str) -> str:
    k = (raw or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return "*" * len(k)
    return f"{k[:4]}...{k[-4:]}"


def _row_to_public(row: sqlite3.Row) -> dict[str, Any]:
    try:
        tools = json.loads(row["tools_json"] or "[]")
    except json.JSONDecodeError:
        tools = []
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "has_api_key": bool((row["api_key"] or "").strip()),
        "api_key_masked": _mask_key(row["api_key"]),
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
    auth_header: str = "Authorization",
    auth_prefix: str = "Bearer ",
    description: str = "",
) -> dict[str, Any]:
    init_mcp_db()
    clean_name = (name or "").strip()[:60]
    clean_url = (url or "").strip()[:300]
    if not clean_name or not clean_url.startswith(("http://", "https://")):
        raise ValueError("Geçerli bir bağlayıcı adı ve http(s):// ile başlayan MCP URL girin.")
    cid = f"mcp-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO mcp_connectors (id, name, url, api_key, auth_header, auth_prefix, description, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                cid,
                clean_name,
                clean_url,
                (api_key or "").strip(),
                (auth_header or "Authorization").strip()[:40],
                auth_prefix if auth_prefix is not None else "Bearer ",
                (description or "").strip()[:240],
                now,
            ),
        )
        row = conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (cid,)).fetchone()
    return _row_to_public(row)


def update_connector(connector_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    init_mcp_db()
    row = _get_raw_connector(connector_id)
    if not row:
        raise KeyError("MCP bağlayıcı bulunamadı.")
    name = str(patch["name"]).strip()[:60] if "name" in patch and patch["name"] is not None else row["name"]
    url = str(patch["url"]).strip()[:300] if "url" in patch and patch["url"] is not None else row["url"]
    api_key = str(patch["api_key"]).strip() if patch.get("api_key") else row["api_key"]
    enabled = int(bool(patch["enabled"])) if "enabled" in patch and patch["enabled"] is not None else row["enabled"]
    desc = str(patch["description"]).strip()[:240] if "description" in patch and patch["description"] is not None else row["description"]
    with _connect() as conn:
        conn.execute(
            "UPDATE mcp_connectors SET name=?, url=?, api_key=?, enabled=?, description=? WHERE id=?",
            (name, url, api_key, enabled, desc, connector_id),
        )
        updated = conn.execute("SELECT * FROM mcp_connectors WHERE id = ?", (connector_id,)).fetchone()
    return _row_to_public(updated)


def delete_connector(connector_id: str) -> bool:
    init_mcp_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM mcp_connectors WHERE id = ?", (connector_id,))
    return cur.rowcount > 0


def _build_headers(row: sqlite3.Row) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    key = (row["api_key"] or "").strip()
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
    url: str,
    headers: dict[str, str],
    method: str,
    params: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
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
    now = datetime.now(UTC).isoformat()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            _, sid = await _rpc_request(
                client,
                row["url"],
                headers,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "cm6453-local-ai", "version": "2.0"},
                },
            )
            tools_resp, _ = await _rpc_request(client, row["url"], headers, "tools/list", {}, session_id=sid)
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
    except Exception as exc:
        err_status = f"Bağlantı hatası: {str(exc)[:140]}"
        with _connect() as conn:
            conn.execute(
                "UPDATE mcp_connectors SET last_status=?, last_checked_at=? WHERE id=?",
                (err_status, now, connector_id),
            )
        return {"ok": False, "error": err_status}


async def call_connector_tool(connector_id: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a live MCP tools/call on the connected external server using its stored API key."""
    row = _get_raw_connector(connector_id)
    if not row:
        raise KeyError("MCP bağlayıcı bulunamadı.")
    if not row["enabled"]:
        raise ValueError("Bu MCP bağlayıcısı pasif durumda.")
    headers = _build_headers(row)
    async with httpx.AsyncClient(timeout=30.0) as client:
        _, sid = await _rpc_request(
            client,
            row["url"],
            headers,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cm6453-local-ai", "version": "2.0"},
            },
        )
        res, _ = await _rpc_request(
            client,
            row["url"],
            headers,
            "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
            session_id=sid,
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


# ---------------------------------------------------------------- FastAPI routes

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


@router.post("/connectors")
async def api_create_connector(req: MCPCreateReq):
    try:
        conn = create_connector(req.name, req.url, req.api_key, req.auth_header, req.auth_prefix, req.description)
        return {"connector": conn}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/connectors/{connector_id}")
async def api_update_connector(connector_id: str, req: MCPUpdateReq):
    try:
        conn = update_connector(connector_id, req.model_dump(exclude_none=True))
        return {"connector": conn}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/connectors/{connector_id}")
async def api_delete_connector(connector_id: str):
    if not delete_connector(connector_id):
        raise HTTPException(status_code=404, detail="MCP bağlayıcı bulunamadı.")
    return {"deleted": True}


@router.post("/connectors/{connector_id}/discover")
async def api_discover_connector(connector_id: str):
    try:
        return await discover_connector_tools(connector_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/connectors/{connector_id}/call")
async def api_call_connector(connector_id: str, req: MCPCallReq):
    try:
        return await call_connector_tool(connector_id, req.tool_name, req.arguments)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP çağrısı başarısız: {exc}") from exc
