"""Operations layer: request ids, metrics, error tracking, size limit and the admin/readiness endpoints.

``install(app)`` adds one pure-ASGI middleware (it does not buffer, so server-sent events keep streaming) and
the router below. The middleware gives each request an id (``X-Request-ID``), counts and times it under its
route *template*, records unhandled exceptions, and refuses bodies above ``MAX_REQUEST_BYTES`` (OPS-18).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import suppress
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

import config
import db_doctor
import dbconn
import erd
import error_tracker
import events_log
import features
import logging_setup
import maintenance
import memory_maintenance
import metrics
import portability
import process_utils
import readiness
import search_index
from access_control import require_local_or_admin

log = logging.getLogger(__name__)
_VALID_ID = re.compile(r"^[A-Za-z0-9_.-]{8,64}$")


class BodyTooLarge(Exception):
    pass


class ObservabilityMiddleware:
    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        offered = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = offered if _VALID_ID.match(offered) else uuid.uuid4().hex[:16]
        token = logging_setup.request_id_var.set(request_id)
        started = time.perf_counter()
        state = {"status": 500, "started": False}
        received = {"bytes": 0}
        declared = headers.get(b"content-length", b"")

        async def limited_receive():
            message = await receive()
            if message["type"] == "http.request":
                received["bytes"] += len(message.get("body", b""))
                if received["bytes"] > self.max_body_bytes:
                    raise BodyTooLarge
            return message

        async def tracking_send(message):
            if message["type"] == "http.response.start":
                state["started"] = True
                state["status"] = message["status"]
                message = {**message, "headers": [*message.get("headers", []), (b"x-request-id", request_id.encode())]}
            await send(message)

        try:
            if declared.isdigit() and int(declared) > self.max_body_bytes:
                raise BodyTooLarge
            await self.app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            metrics.inc("http_requests_rejected_total", reason="body_too_large")
            if not state["started"]:
                state["status"] = 413
                await JSONResponse(
                    {"detail": f"İstek gövdesi {self.max_body_bytes} bayt sınırını aşıyor."},
                    status_code=413, headers={"x-request-id": request_id},
                )(scope, receive, send)
        except Exception as exc:
            error_tracker.record(exc, getattr(scope.get("route"), "path", None), request_id)
            log.exception("yakalanmamış hata", extra={"path": scope.get("path")})
            raise
        finally:
            route = getattr(scope.get("route"), "path", None) or "unmatched"
            method = scope.get("method", "?")
            metrics.inc("http_requests_total", method=method, route=route, status=str(state["status"]))
            metrics.observe("http_request_duration_seconds", time.perf_counter() - started, method=method, route=route)
            logging_setup.request_id_var.reset(token)


router = APIRouter(tags=["ops"])


def _trusted(request: Request) -> bool:
    try:
        require_local_or_admin(request)
    except HTTPException:
        return False
    return True


@router.get("/ready")
async def ready(request: Request):
    """200 when the service can work, 503 when a critical part is missing. Details only for trusted callers."""
    result = await readiness.check_all()
    body = result if _trusted(request) else {"status": result["status"]}
    return JSONResponse(body, status_code=503 if result["status"] == "down" else 200)


@router.get("/metrics", dependencies=[Depends(require_local_or_admin)])
async def prometheus_metrics():
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@router.get("/api/admin/errors", dependencies=[Depends(require_local_or_admin)])
async def recent_errors(limit: int = Query(50, ge=1, le=200)):
    return {"errors": error_tracker.recent(limit)}


class FlagBody(BaseModel):
    enabled: bool
    owner: str | None = None


@router.get("/api/admin/features", dependencies=[Depends(require_local_or_admin)])
async def list_features(owner: str | None = None):
    return {"features": features.snapshot(owner)}


@router.put("/api/admin/features/{name}", dependencies=[Depends(require_local_or_admin)])
async def change_feature(name: str, body: FlagBody):
    try:
        features.set_flag(name, body.enabled, owner=body.owner)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"bilinmeyen özellik: {name}") from exc
    return {"name": name, "enabled": features.is_enabled(name, body.owner)}


@router.get("/api/admin/events", dependencies=[Depends(require_local_or_admin)])
async def operational_events(
    event_type: str | None = None, agent_id: str | None = None, project_id: int | None = None,
    since: str | None = None, until: str | None = None,
    limit: int = Query(50, ge=1, le=events_log.MAX_PAGE), offset: int = Query(0, ge=0),
):
    with dbconn.connection(config.DB_PATH) as conn:
        return {"events": events_log.query(conn, event_type, agent_id, project_id, since, until, limit, offset)}


@router.get("/api/admin/maintenance", dependencies=[Depends(require_local_or_admin)])
async def maintenance_state():
    return maintenance.status()


@router.get("/api/admin/db-doctor", dependencies=[Depends(require_local_or_admin)])
async def admin_db_doctor():
    findings = db_doctor.diagnose(Path(config.DB_PATH))
    return {
        "ok": not any(f.severity == "error" for f in findings),
        "findings": [{"severity": f.severity, "check": f.check, "detail": f.detail} for f in findings],
    }


@router.get("/api/admin/erd", dependencies=[Depends(require_local_or_admin)])
async def admin_erd():
    with dbconn.connection(config.DB_PATH) as conn:
        return PlainTextResponse(erd.render(conn), media_type="text/markdown; charset=utf-8")


@router.get("/api/admin/data-services", dependencies=[Depends(require_local_or_admin)])
async def admin_data_services(query: str = Query(default="")):
    return {
        "portability_format": portability.FORMAT,
        "memory_consolidation_available": callable(memory_maintenance.consolidate),
        "sample_tokens": search_index.tokens(query) if query else [],
        "supervisors": process_utils.all_supervisor_statuses(),
    }


def install(app) -> None:
    logging_setup.configure(
        level=getattr(config, "LOG_LEVEL", "INFO"),
        json_output=getattr(config, "LOG_JSON", True),
        log_file=Path(dbconn.data_dir()) / "logs" / "master.log",
    )
    app.add_middleware(ObservabilityMiddleware, max_body_bytes=getattr(config, "MAX_REQUEST_BYTES", 64 * 1024 * 1024))
    app.include_router(router)


def startup() -> None:
    features.ensure_registered()
    maintenance.start_background(float(getattr(config, "MAINTENANCE_INTERVAL_SECONDS", 3600)))


def shutdown() -> None:
    with suppress(Exception):
        maintenance.stop_background()
