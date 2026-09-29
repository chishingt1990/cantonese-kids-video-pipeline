import uuid
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.storage import contained_path, project_path
from app.services.audio_service import MediaPrerequisiteError
from app.services.render_service import (
    start_render_job, get_render_job, cancel_render_job, RenderBusyError,
)

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderRequest(BaseModel):
    project_data: dict


@router.post("/start")
def trigger_render(req: RenderRequest):
    try:
        job = start_render_job(req.project_data, uuid.uuid4().hex)
        return {"job_id": job["job_id"], "project_id": job["project_id"],
                "status": job["status"], "input_fingerprint": job["input_fingerprint"]}
    except RenderBusyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except MediaPrerequisiteError as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/status/{job_id}")
def check_status(job_id: str, project_id: str = None):
    try:
        return get_render_job(job_id, project_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/cancel/{job_id}")
def cancel(job_id: str):
    return {"job_id": job_id, "cancel_requested": cancel_render_job(job_id)}


@router.get("/video/{project_id}/{filename}")
def stream_video(project_id: str, filename: str):
    try:
        path = contained_path(project_path(project_id, "renders"), filename)
        manifest = path.with_name(path.name + ".json")
        if not filename.endswith(".mp4") or not path.is_file() or not manifest.is_file() or path.stat().st_size == 0:
            raise HTTPException(404, "Completed project video not found")
        try:
            artifact = json.loads(manifest.read_text(encoding="utf-8"))
            if artifact.get("status") != "done" or artifact.get("project_id") != project_id or artifact.get("video_filename") != filename:
                raise ValueError("Manifest does not describe this completed video")
        except (ValueError, AttributeError):
            raise HTTPException(404, "Completed project video not found")
        return FileResponse(path, media_type="video/mp4")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
