"""Master agent service: web UI, REST API, agent registry and requirements decomposition."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import accounting
import agents_api
import api_schemas
import assistant
import audit_log
import auth
import automation
import backup_manager
import cnc_api
import config
import contract_check
import cronjobs
import custom_agents
import db
import distributed
import domains
import education
import education_and_domains
import eval_studio
import factory
import games
import gateway
import ha
import hallucination
import ide
import llm
import log_sanitizer
import marketplace
import mcp_connector
import mcp_server
import media
import memory_api
import memory_conflicts
import ml_ops
import multimodal
import notebook
import notifications
import openai_compat
import ops
import orchestrator
import output_api
import perf_api
import preview_server
import privacy
import productivity_api
import projects_api
import rag
import scheduler
import security_extensions
import security_middleware
import studio_api
import studios
import tasks_api
import telemetry_otel
import updater
import user_api
import ux_api
from auth import orgs as auth_orgs
from domains import engineering_bench as domains_eng
from domains import kb_service as domains_kb
from factory import verified_templates as factory_verified
from hallucination import numeric_check as hallucination_numeric
from ml_ops import promotion as ml_promotion
from rag import advanced as rag_advanced
from rag import crawler as rag_crawler
from studios import leakage_guard as studios_leakage
from studios import render_qa as studios_render_qa


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_sanitizer.install_log_redaction()
    db.init_db()
    auth.init_auth_db()
    auth_orgs.init_orgs_db()
    privacy.init_privacy_db()
    rag_crawler.init_web_archive_db()
    eval_studio.init_eval_studio_db()
    memory_conflicts.init_memory_conflicts_db()
    ha.init_ha_db()
    ml_promotion.init_ml_promotions_db()
    accounting.init_accounting_db()
    notebook.init_notebooks_db()
    education.init_education_db()
    custom_agents.init_custom_agents_db()
    automation.init_webhooks_db()
    notifications.init_notifications_db()
    marketplace.init_marketplace_db()
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
    cron_task = asyncio.create_task(cronjobs.loop(productivity_api.assistant_runner))
    yield
    cron_task.cancel()
    ops.shutdown()


app = FastAPI(title="Distributed AI Software Development Platform - Master", lifespan=lifespan)
app.add_middleware(security_middleware.SecurityHeadersAndCSRFMiddleware)
ops.install(app)
app.include_router(agents_api.router)
app.include_router(auth.router)
app.include_router(auth_orgs.router)
app.include_router(privacy.router)
app.include_router(projects_api.router)
app.include_router(assistant.router)
app.include_router(tasks_api.router)
app.include_router(output_api.router)
app.include_router(perf_api.router)
app.include_router(cnc_api.router)
app.include_router(studio_api.router)
app.include_router(user_api.router)
app.include_router(memory_api.router)
app.include_router(memory_conflicts.router)
app.include_router(mcp_connector.router)
app.include_router(backup_manager.router)
app.include_router(audit_log.router)
app.include_router(gateway.router)
app.include_router(orchestrator.router)
app.include_router(rag.router)
app.include_router(rag_crawler.router)
app.include_router(rag_advanced.router)
app.include_router(hallucination.router)
app.include_router(hallucination_numeric.router)
app.include_router(eval_studio.router)
app.include_router(ml_ops.router)
app.include_router(ml_promotion.router)
app.include_router(studios.router)
app.include_router(studios_render_qa.router)
app.include_router(studios_leakage.router)
app.include_router(multimodal.router)
app.include_router(education.router)
app.include_router(media.router)
app.include_router(factory.router)
app.include_router(factory_verified.router)
app.include_router(ide.router)
app.include_router(ha.router)
app.include_router(accounting.router)
app.include_router(notebook.router)
app.include_router(games.router)
app.include_router(domains.router)
app.include_router(domains_kb.router)
app.include_router(domains_eng.router)
app.include_router(distributed.router)
app.include_router(ux_api.router)
app.include_router(security_extensions.router)
app.include_router(education_and_domains.router)
app.include_router(productivity_api.router)
app.include_router(custom_agents.router)
app.include_router(automation.router)
app.include_router(mcp_server.router)
app.include_router(telemetry_otel.router)
app.include_router(openai_compat.router)
app.include_router(updater.router)
app.include_router(notifications.router)
app.include_router(marketplace.router)


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
    """Return master service liveness status."""
    return {"status": "ok"}


@app.get("/api/master/status")
async def master_status():
    """Return master LLM provider connectivity and active model status."""
    return await llm.status()


@app.get("/")
async def ui():
    """Serve the single-page web application shell."""
    return FileResponse(config.STATIC_DIR / "index.html")


api_schemas.attach_openapi_contracts(app)
