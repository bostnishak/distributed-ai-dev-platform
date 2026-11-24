"""EPK-17: Lightweight OpenTelemetry (OTLP JSON) Span Recorder & Performance Budget Reporter."""

from __future__ import annotations

import secrets
from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/telemetry/otel", tags=["telemetry-otel"])

_SPANS: deque[dict[str, Any]] = deque(maxlen=500)


def record_otel_span(name: str, duration_ms: float, status: str = "OK", attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    trace_id = secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "traceparent": f"00-{trace_id}-{span_id}-01",
        "name": name.strip()[:120],
        "durationMs": round(max(0.0, float(duration_ms)), 2),
        "status": status,
        "attributes": attributes or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _SPANS.append(span)
    return span


def export_otlp_payload(limit: int = 50) -> dict[str, Any]:
    items = list(_SPANS)[-max(1, min(limit, 500)) :]
    avg_ms = round(sum(s["durationMs"] for s in items) / max(1, len(items)), 2) if items else 0.0
    return {
        "ok": True,
        "format": "otlp-json-v1",
        "resource": {"service.name": "dadp-master"},
        "span_count": len(items),
        "avg_duration_ms": avg_ms,
        "spans": items,
    }


class OtelSpanRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    duration_ms: float = Field(default=12.5, ge=0.0, le=600000.0)
    status: str = Field(default="OK", max_length=32)
    attributes: dict[str, Any] = Field(default_factory=dict)


@router.get("/spans")
async def api_get_otel_spans(limit: int = 50):
    """Export recorded spans in OTLP JSON format with average latency summary."""
    return export_otlp_payload(limit)


@router.post("/spans")
async def api_record_otel_span(body: OtelSpanRequest):
    """Record a new W3C traceparent OpenTelemetry span."""
    return {"ok": True, "span": record_otel_span(body.name, body.duration_ms, body.status, body.attributes)}
