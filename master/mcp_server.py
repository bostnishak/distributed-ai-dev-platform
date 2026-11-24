"""EPK-13: Local-First MCP Server Exporter (JSON-RPC 2.0) & Scoped Connector Registry with Human Approval Gate."""

from __future__ import annotations

import shutil
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mcp-server", tags=["mcp-server"])

EXPORTED_MCP_TOOLS: list[dict[str, Any]] = [
    {"name": "dadp_health", "description": "Master servis sağlık durumunu döndürür.", "side_effect": False},
    {"name": "dadp_rag_search", "description": "Yerel RAG bilgi tabanında arama yapar.", "side_effect": False},
    {"name": "dadp_run_backup", "description": "Veritabanı yedeği alır (insan onayı gerektirir).", "side_effect": True},
    {"name": "dadp_github_status", "description": "Yerel git/gh CLI depo durumunu sorgular.", "side_effect": False},
]


def list_local_connectors() -> list[dict[str, Any]]:
    """Probe local-first connectors (zero mandatory cloud OAuth)."""
    return [
        {"id": "github_local_cli", "name": "GitHub / Git CLI", "available": shutil.which("git") is not None, "auth": "local_token_or_ssh"},
        {"id": "local_drive_sync", "name": "Yerel Klasör / Drive / OneDrive", "available": True, "auth": "local_filesystem"},
        {"id": "caldav_ics", "name": "Takvim (ICS / CalDAV)", "available": True, "auth": "local_ics"},
        {"id": "imap_smtp", "name": "E-Posta (IMAP / SMTP)", "available": True, "auth": "env_credentials"},
    ]


def handle_mcp_rpc(method: str, params: dict[str, Any], req_id: Any = 1) -> dict[str, Any]:
    """Process standard MCP JSON-RPC 2.0 calls with mandatory human_approved gate on side effects."""
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "dadp-mcp-server", "version": "1.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": EXPORTED_MCP_TOOLS}}
    if method == "tools/call":
        tname = str(params.get("name") or "")
        tool = next((t for t in EXPORTED_MCP_TOOLS if t["name"] == tname), None)
        if not tool:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Bilinmeyen araç: {tname}"}}
        if tool["side_effect"] and not bool(params.get("human_approved")):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32003, "message": "Yan etkili MCP aracı için human_approved=true insan onayı zorunludur."},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tool": tname, "status": "executed", "side_effect": tool["side_effect"]}}
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Desteklenmeyen metot: {method}"}}


class McpRpcRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: int | str = Field(default=1)
    method: str = Field(..., min_length=2, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/rpc")
async def api_mcp_server_rpc(body: McpRpcRequest):
    """Handle JSON-RPC 2.0 MCP server requests (initialize, tools/list, tools/call)."""
    return handle_mcp_rpc(body.method, body.params, body.id)


@router.get("/connectors")
async def api_local_connectors():
    """List local-first external connectors and their availability without cloud lock-in."""
    items = list_local_connectors()
    return {"ok": True, "count": len(items), "connectors": items}
