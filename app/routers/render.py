import uuid
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, StrictBool

from app.storage import contained_path, project_path
from app.services.audio_service import MediaPrerequisiteError
from app.services.narration_service import NarrationError
from app.services.render_service import (
    start_render_job, get_render_job, cancel_render_job, RenderBusyError, RenderPolicyError,
)

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderRequest(BaseModel):
    project_data: dict
    silent_legacy_confirmed: StrictBool = False


@router.post("/start")
def trigger_render(req: RenderRequest):
    try:
        job = start_render_job(req.project_data, uuid.uuid4().hex,
                               silent_legacy_confirmed=req.silent_legacy_confirmed)
        return {"job_id": job["job_id"], "project_id": job["project_id"],
                "status": job["status"], "input_fingerprint": job["input_fingerprint"],
                "narration_take_id": job["narration_take_id"],
                "narration_identity": job["narration_identity"],
                "audio_mode": job["audio_mode"],
                "audio_options": job["audio_options"],
                "silent_legacy_confirmed": job["silent_legacy_confirmed"],
                "missing_narration_scenes": job["missing_narration_scenes"],
                "alignment_method": job["alignment_method"], "warnings": job["warnings"],
                "duration_sec": job["duration_sec"], "frame_count": job["frame_count"], "fps": job["fps"]}
    except RenderBusyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RenderPolicyError as exc:
        return JSONResponse(status_code=409, content={
            "detail": str(exc), "error_code": exc.code, "project_id": exc.project_id,
            "scene_numbers": exc.scene_numbers, "input_fingerprint": exc.input_fingerprint})
    except MediaPrerequisiteError as exc:
        raise HTTPException(503, str(exc)) from exc
    except NarrationError as exc:
        raise HTTPException(exc.http_status, str(exc)) from exc
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
