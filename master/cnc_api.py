"""REST API for CNC Technical Drawing Ballooning & Quality Control (AS9102 / ISO 2768)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

import cnc_ballooning as cnc
import config

router = APIRouter(prefix="/api/cnc", tags=["cnc"])

SUPPORTED_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".docx", ".xlsx", ".xlsm", ".dxf")


def _jobs_dir() -> Path:
    d = config.CNC_JOBS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _job_dir(job_id: str) -> Path:
    safe_id = "".join(c for c in job_id if c.isalnum() or c in ("-", "_"))
    if not safe_id or safe_id != job_id:
        raise HTTPException(status_code=400, detail="Geçersiz iş kimliği.")
    return _jobs_dir() / safe_id


def _load_job(job_id: str) -> dict[str, Any]:
    meta_path = _job_dir(job_id) / "job.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Balonlama işi bulunamadı.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _save_job(job_id: str, data: dict[str, Any]) -> None:
    d = _job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "job.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_all_outputs(job_dir: Path, base_img: Image.Image, balloons: list[cnc.BalloonItem], metadata: dict[str, str]) -> None:
    base_img.save(job_dir / "original.png", format="PNG")
    ballooned_img = cnc.render_ballooned_image(base_img, balloons, metadata)
    ballooned_png = job_dir / "ballooned.png"
    ballooned_img.save(ballooned_png, format="PNG")
    cnc.export_ballooned_pdf(ballooned_img, balloons, metadata, job_dir / "ballooned.pdf")
    cnc.export_excel_report(balloons, metadata, job_dir / "report.xlsx")
    cnc.export_word_report(ballooned_png, balloons, metadata, job_dir / "report.docx")


@router.get("/jobs")
async def list_cnc_jobs():
    """List all CNC ballooning jobs, newest first."""
    jobs = []
    for p in _jobs_dir().iterdir():
        meta_path = p / "job.json"
        if meta_path.is_file():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                jobs.append({
                    "id": data["id"],
                    "filename": data.get("filename", ""),
                    "created_at": data.get("created_at", ""),
                    "engine_used": data.get("engine_used", ""),
                    "metadata": data.get("metadata", {}),
                    "balloon_count": len(data.get("balloons", [])),
                })
            except Exception:
                continue
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"jobs": jobs}


@router.get("/jobs/{id}")
async def get_cnc_job(id: str):
    """Return full details and balloon list for a single CNC job."""
    return _load_job(id)


@router.post("/balloon")
async def create_balloon_job(
    file: UploadFile = File(...),  # noqa: B008
    part_number: str = Form(""),
    part_name: str = Form(""),
    material: str = Form(""),
    revision: str = Form("A"),
    standard: str = Form("ISO 2768-mK"),
    model: str = Form(""),
):
    """Upload a CNC technical drawing (PDF, Image, DOCX, XLSX) and run automated ballooning."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş.")
    lower = file.filename.lower()
    if not lower.endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen format. Desteklenenler: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    raw = await file.read()
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dosya boyutu çok büyük (maks 20 MB).")

    try:
        base_img, balloons, extracted_meta, engine_used = await cnc.process_drawing(
            file.filename, raw, model_override=model or None, use_vlm=True
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Teknik çizim işlenemedi: {exc}") from exc

    meta = {
        "part_number": part_number.strip() or extracted_meta.get("part_number") or "",
        "part_name": part_name.strip() or extracted_meta.get("part_name") or Path(file.filename).stem,
        "material": material.strip() or extracted_meta.get("material") or "",
        "revision": revision.strip() or extracted_meta.get("revision") or "A",
        "standard": standard.strip() or extracted_meta.get("standard") or "ISO 2768-mK",
    }

    job_id = f"cnc-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / f"source{Path(file.filename).suffix.lower()}").write_bytes(raw)
    _generate_all_outputs(jdir, base_img, balloons, meta)

    job_data = {
        "id": job_id,
        "filename": file.filename,
        "created_at": datetime.now(UTC).isoformat(),
        "engine_used": engine_used,
        "metadata": meta,
        "balloons": [b.to_dict() for b in balloons],
        "manufacturing_plan": cnc.build_cnc_manufacturing_plan(balloons, meta),
    }
    _save_job(job_id, job_data)
    return job_data


class UpdateBalloonsRequest(BaseModel):
    metadata: dict[str, str] | None = None
    balloons: list[dict[str, Any]]


@router.put("/jobs/{id}/balloons")
async def update_job_balloons(id: str, body: UpdateBalloonsRequest):
    """Update/edit/add/remove balloons and re-render PNG, PDF, Excel, and Word outputs."""
    job = _load_job(id)
    jdir = _job_dir(id)
    orig_path = jdir / "original.png"
    if not orig_path.exists():
        raise HTTPException(status_code=404, detail="Orijinal çizim görüntüsü bulunamadı.")

    meta = job.get("metadata", {})
    if body.metadata:
        meta.update(body.metadata)

    updated: list[cnc.BalloonItem] = []
    for idx, raw_b in enumerate(body.balloons, start=1):
        x_pct = float(raw_b.get("x_pct", 50.0))
        y_pct = float(raw_b.get("y_pct", 50.0))
        nominal = raw_b.get("nominal")
        tol_p = raw_b.get("tol_plus")
        tol_m = raw_b.get("tol_minus")
        min_l = raw_b.get("min_limit")
        max_l = raw_b.get("max_limit")
        if nominal is not None and tol_p is not None and max_l is None:
            max_l = round(float(nominal) + float(tol_p), 4)
        if nominal is not None and tol_m is not None and min_l is None:
            min_l = round(float(nominal) + float(tol_m), 4)
        item = cnc.BalloonItem(
            balloon_no=idx,
            raw_text=str(raw_b.get("raw_text", "")),
            category=str(raw_b.get("category", "Lineer Ölçü")),
            nominal=float(nominal) if nominal not in (None, "") else None,
            unit=str(raw_b.get("unit", "mm")),
            tol_plus=float(tol_p) if tol_p not in (None, "") else None,
            tol_minus=float(tol_m) if tol_m not in (None, "") else None,
            min_limit=float(min_l) if min_l not in (None, "") else None,
            max_limit=float(max_l) if max_l not in (None, "") else None,
            fit_class=str(raw_b.get("fit_class", "")),
            quantity=int(raw_b.get("quantity", 1) or 1),
            gage=str(raw_b.get("gage", "Dijital Kumpas")),
            criticality=str(raw_b.get("criticality", "Majör")),
            notes=str(raw_b.get("notes", "")),
            x_pct=max(2.0, min(98.0, x_pct)),
            y_pct=max(2.0, min(96.0, y_pct)),
            w_pct=float(raw_b.get("w_pct", 4.0)),
            h_pct=float(raw_b.get("h_pct", 2.0)),
            zone=str(raw_b.get("zone") or cnc.compute_zone(x_pct, y_pct)),
        )
        cnc.enrich_cnc_engineering_fields(item)
        updated.append(item)

    base_img = Image.open(orig_path).convert("RGB")
    _generate_all_outputs(jdir, base_img, updated, meta)

    job["metadata"] = meta
    job["balloons"] = [b.to_dict() for b in updated]
    job["manufacturing_plan"] = cnc.build_cnc_manufacturing_plan(updated, meta)
    job["updated_at"] = datetime.now(UTC).isoformat()
    _save_job(id, job)
    return job


@router.get("/jobs/{id}/file/{kind}")
async def download_cnc_file(id: str, kind: str):
    """Download original.png, ballooned.png, ballooned.pdf, report.xlsx, or report.docx."""
    allowed = {
        "original": ("original.png", "image/png"),
        "ballooned.png": ("ballooned.png", "image/png"),
        "ballooned.pdf": ("ballooned.pdf", "application/pdf"),
        "report.xlsx": (
            "report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "report.docx": (
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    }
    if kind not in allowed:
        raise HTTPException(status_code=404, detail="Bilinmeyen dosya türü.")
    fname, media = allowed[kind]
    path = _job_dir(id) / fname
    if not path.exists():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    headers = {"Cache-Control": "no-cache"}
    if kind in ("ballooned.pdf", "report.xlsx", "report.docx"):
        headers["Content-Disposition"] = f'attachment; filename="{id}-{fname}"'
    return FileResponse(path, media_type=media, headers=headers)


@router.post("/demo")
async def create_cnc_demo():
    """Generate a realistic CNC Bearing Housing Flange PDF drawing and run full ballooning on it."""
    job_id = "demo-flange-fln2026"
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)
    pdf_path = jdir / "source.pdf"
    cnc.generate_sample_cnc_drawing_pdf(pdf_path)

    raw = pdf_path.read_bytes()
    base_img, balloons, meta, engine_used = await cnc.process_drawing(
        "FLN-2026-042_Bearing_Housing_Flange.pdf", raw, use_vlm=False
    )
    _generate_all_outputs(jdir, base_img, balloons, meta)

    job_data = {
        "id": job_id,
        "filename": "FLN-2026-042_Bearing_Housing_Flange.pdf",
        "created_at": datetime.now(UTC).isoformat(),
        "engine_used": engine_used,
        "metadata": meta,
        "balloons": [b.to_dict() for b in balloons],
        "manufacturing_plan": cnc.build_cnc_manufacturing_plan(balloons, meta),
    }
    _save_job(job_id, job_data)
    return job_data


class EvaluateMeasurementsRequest(BaseModel):
    measurements: dict[int, list[float]]


@router.post("/jobs/{id}/evaluate-measurements")
async def evaluate_job_measurements(id: str, body: EvaluateMeasurementsRequest):
    """Evaluate CMM or operator measurements for a ballooned job and compute Cp/Cpk."""
    job = _load_job(id)
    balloons = [
        cnc.BalloonItem(**{k: v for k, v in b.items() if k in cnc.BalloonItem.__dataclass_fields__})
        for b in job.get("balloons", [])
    ]
    report = cnc.evaluate_cmm_measurements(balloons, body.measurements)
    job["cmm_evaluation"] = report
    _save_job(id, job)
    return report
