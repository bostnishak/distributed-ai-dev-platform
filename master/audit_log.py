"""SEC-15: AS9100 & ISO 27001 Immutable SHA-256 Hash-Chained Audit Trail + Admin Verification API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from access_control import require_local_or_admin
from enterprise_security_mcp import AuditTrail

router = APIRouter(prefix="/api/admin/audit", tags=["audit"])


@router.get("/verify", dependencies=[Depends(require_local_or_admin)])
async def verify_audit_chain():
    """Cryptographically verify the entire SHA-256 hash chain and pinpoint any tampered line."""
    trail = AuditTrail()
    return trail.verify_chain_detailed()


@router.get("/events", dependencies=[Depends(require_local_or_admin)])
async def list_audit_events(limit: int = Query(50, ge=1, le=500)):
    """Return recent tamper-evident audit events (most recent first)."""
    trail = AuditTrail()
    events = trail.read_events()
    return {"total": len(events), "valid": trail.verify_chain(), "events": list(reversed(events[-limit:]))}


__all__ = ["AuditTrail", "router"]
