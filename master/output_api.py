"""Project output download as a ZIP archive (PB-32).

Every completed task's files (or raw output) are packaged into a single ZIP that the user
can download from the project detail page.
"""

import io
import json
import re
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

import db

router = APIRouter(tags=["output"])


def _project_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


@router.get("/api/projects/{project_id}/output.zip")
def download_output(project_id: int):
    """Download all completed task outputs for a project as a ZIP archive."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    tasks = db.list_tasks(project_id)
    done_tasks = [t for t in tasks if t["status"] == "done" and t.get("result")]

    if not done_tasks:
        raise HTTPException(status_code=404, detail="Henüz tamamlanmış görev yok.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for task in done_tasks:
            folder = f"{task['key']}_{task['type']}"
            files: list[dict] = []
            if task.get("files"):
                try:
                    files = json.loads(task["files"])
                except (json.JSONDecodeError, TypeError):
                    files = []

            if files:
                for f in files:
                    path = f.get("path", "output.txt")
                    # Normalise absolute paths so they don't escape the archive.
                    path = path.lstrip("/").replace("..", "")
                    zf.writestr(f"{folder}/{path}", f.get("content", ""))
            elif task.get("result"):
                zf.writestr(f"{folder}/output.txt", task["result"])

    buf.seek(0)
    filename = f"{_project_slug(project['name'])}-output.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/projects/{project_id}/output")
def get_output_summary(project_id: int):
    """Return a summary of completed task outputs (for the UI)."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    tasks = db.list_tasks(project_id)
    total = len([t for t in tasks if t["type"] != "requirements"])
    done = [t for t in tasks if t["status"] == "done" and t["type"] != "requirements"]
    in_progress = [t for t in tasks if t["assigned_to"] and t["status"] == "planned"]
    blocked = [t for t in tasks if t["status"] == "blocked"]

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "tasks_total": total,
        "tasks_done": len(done),
        "tasks_in_progress": len(in_progress),
        "tasks_blocked": len(blocked),
        "has_output": len(done) > 0,
    }
