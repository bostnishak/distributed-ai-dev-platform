"""Master agent service: web UI, REST API, agent registry and requirements decomposition."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import agents_api
import assistant
import config
import db
import llm
import projects_api


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    projects_api.recover_interrupted()
    yield


app = FastAPI(title="Distributed AI Software Development Platform - Master", lifespan=lifespan)
app.include_router(agents_api.router)
app.include_router(projects_api.router)
app.include_router(assistant.router)
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
