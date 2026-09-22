import os
import uuid
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.render_service import start_render_job, JOBS

router = APIRouter(prefix="/api/render", tags=["render"])

class RenderRequest(BaseModel):
    project_data: dict

@router.post("/start")
def trigger_render(req: RenderRequest):
    job_id = str(uuid.uuid4())[:8]
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    out_file = os.path.join(project_root, "assets", "outputs", f"episode_{job_id}.mp4")
    
    start_render_job(req.project_data, job_id, out_file)
    return {"job_id": job_id, "status": "started"}

@router.get("/status/{job_id}")
def check_status(job_id: str):
    job = JOBS.get(job_id, {"status": "not_found", "progress": 0})
    return job

@router.get("/video/{filename}")
def stream_video(filename: str):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(project_root, "assets", "outputs", filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4")
    return {"error": "Not found"}
