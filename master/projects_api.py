"""Projects API: submit a requirements document, analyze it in the background, read the plan."""

import asyncio
import logging
import time

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

import config
import db
import decompose
import llm
from extract import REQUIREMENT_EXTENSIONS, UnsupportedFileError, extract_text

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

# The master model runs on one machine; parallel analyses would only slow each other.
_analysis_slot = asyncio.Semaphore(1)

# Indirection so tests can replace the model call with a fake.
llm_chat = llm.chat_structured

INTERRUPTED_MESSAGE = "Master yeniden başlatıldığı için analiz yarıda kaldı. Yeniden analiz edebilirsiniz."


async def run_analysis(project_id: int) -> None:
    async with _analysis_slot:
        project = db.get_project(project_id)
        if project is None or project["status"] != "analyzing":
            return
        started = time.monotonic()
        try:
            result = await decompose.analyze_document(project["document"], chat=llm_chat)
            tasks = decompose.build_task_plan(result.spec)
        except (decompose.AnalysisError, llm.LLMError) as exc:
            db.mark_failed(project_id, str(exc))
            return
        except Exception as exc:  # keep the project out of a stuck "analyzing" state
            log.exception("Analysis of project %s failed", project_id)
            db.mark_failed(project_id, f"Beklenmeyen hata: {exc!r}")
            return
        db.save_decomposition(
            project_id,
            result.spec.model_dump(),
            tasks,
            analysis_model=config.MASTER_MODEL,
            analysis_seconds=round(time.monotonic() - started, 1),
            chunk_count=result.chunk_count,
        )


def recover_interrupted() -> int:
    return db.fail_interrupted_analyses(INTERRUPTED_MESSAGE)


def _project_or_404(project_id: int) -> dict:
    project = db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return project


@router.post("", status_code=202)
async def create_project(
    background: BackgroundTasks,
    name: str = Form(..., min_length=1, max_length=120),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),  # noqa: B008 (standard FastAPI pattern)
):
    has_file = file is not None and bool(file.filename)
    has_text = bool(text and text.strip())
    if has_file == has_text:
        raise HTTPException(status_code=422, detail="Ya metin yapıştırın ya da bir dosya yükleyin (ikisi birden değil).")

    source_filename = None
    if has_file:
        raw = await file.read(config.MAX_UPLOAD_BYTES + 1)
        if len(raw) > config.MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Dosya 5 MB sınırını aşıyor.")
        try:
            document = extract_text(file.filename, raw)
        except UnsupportedFileError as exc:
            raise HTTPException(
                status_code=415,
                detail=f"Desteklenmeyen dosya türü. Desteklenenler: {', '.join(REQUIREMENT_EXTENSIONS)}",
            ) from exc
        source_filename = file.filename
    else:
        document = text

    document = decompose.normalize_document(document)
    if not document:
        raise HTTPException(status_code=422, detail="Dokümandan metin çıkarılamadı.")
    if len(document) > config.MAX_DOCUMENT_CHARS:
        raise HTTPException(status_code=413, detail="Doküman çok uzun (en fazla 300.000 karakter).")

    project_id = db.create_project(name.strip(), document, source_filename)
    background.add_task(run_analysis, project_id)
    return {"id": project_id, "status": "analyzing"}


@router.get("")
def list_projects():
    return db.list_projects()


@router.get("/{project_id}")
def get_project(project_id: int):
    project = _project_or_404(project_id)
    project["tasks"] = db.list_tasks(project_id)
    return project


@router.post("/{project_id}/reanalyze", status_code=202)
def reanalyze(project_id: int, background: BackgroundTasks):
    project = _project_or_404(project_id)
    if project["status"] == "analyzing":
        raise HTTPException(status_code=409, detail="Bu proje zaten analiz ediliyor.")
    db.mark_analyzing(project_id)
    background.add_task(run_analysis, project_id)
    return {"id": project_id, "status": "analyzing"}


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int):
    project = _project_or_404(project_id)
    if project["status"] == "analyzing":
        raise HTTPException(status_code=409, detail="Analiz sürerken proje silinemez.")
    db.delete_project(project_id)
