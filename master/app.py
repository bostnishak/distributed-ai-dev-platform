"""Master agent service: web UI, REST API, agent registry and requirements decomposition."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import agents_api
import assistant
import audit_log
import auth
import backup_manager
import cnc_api
import config
import contract_check
import db
import distributed
import domains
import factory
import games
import gateway
import hallucination
import llm
import log_sanitizer
import mcp_connector
import memory_api
import ml_ops
import ops
import orchestrator
import output_api
import perf_api
import preview_server
import projects_api
import rag
import scheduler
import security_middleware
import studio_api
import studios
import tasks_api
import user_api
import ux_api


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_sanitizer.install_log_redaction()
    db.init_db()
    auth.init_auth_db()
    gateway.init_gateway_db()
    orchestrator.init_orchestrator_db()
    hallucination.init_hallucination_db()
    ml_ops.init_ml_db()
    distributed.init_distributed_db()
    projects_api.recover_interrupted()
    tasks_api.start_lease_expiry()
    scheduler.start_dag_scheduler()
    preview_server.start_preview_server_background()
    ops.startup()
    yield
    ops.shutdown()


app = FastAPI(title="Distributed AI Software Development Platform - Master", lifespan=lifespan)
app.add_middleware(security_middleware.SecurityHeadersAndCSRFMiddleware)
ops.install(app)
app.include_router(agents_api.router)
app.include_router(auth.router)
app.include_router(projects_api.router)
app.include_router(assistant.router)
app.include_router(tasks_api.router)
app.include_router(output_api.router)
app.include_router(perf_api.router)
app.include_router(cnc_api.router)
app.include_router(studio_api.router)
app.include_router(user_api.router)
app.include_router(memory_api.router)
app.include_router(mcp_connector.router)
app.include_router(backup_manager.router)
app.include_router(audit_log.router)
app.include_router(gateway.router)
app.include_router(orchestrator.router)
app.include_router(rag.router)
app.include_router(hallucination.router)
app.include_router(ml_ops.router)
app.include_router(studios.router)
app.include_router(factory.router)
app.include_router(games.router)
app.include_router(domains.router)
app.include_router(distributed.router)
app.include_router(ux_api.router)


@app.get("/api/admin/contract-check")
async def api_contract_check():
    """PB-40: Check frontend fetch() calls against backend routes."""
    return contract_check.run_check(app)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.middleware("http")
async def revalidate_ui_files(request: Request, call_next):
    # Browsers otherwise keep serving an old copy of the UI after an update.
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/master/status")
async def master_status():
    return await llm.status()


@app.get("/")
async def ui():
    return FileResponse(config.STATIC_DIR / "index.html")
