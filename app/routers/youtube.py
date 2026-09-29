import html
import json
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from pydantic import BaseModel, Field

from app.services import youtube_service, project_service
from app.services.ai_service import GenerationError
from app.storage import project_path, project_lock, media_input_fingerprint
from app.models import ProjectData, YoutubeMetadata, PrivacyStatus

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class GenerateMetadataRequest(BaseModel):
    project_data: ProjectData


class UploadVideoRequest(YoutubeMetadata):
    project_id: str
    video_filename: str = Field(min_length=1, max_length=255)
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    privacy_status: PrivacyStatus = "private"
    made_for_kids: bool = True
    selected_frame: Optional[str] = None


def rendered_artifact(project_id):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    rendered = project.get("rendered_video") or {}
    filename = rendered.get("filename", "")
    if not filename or any(c in filename for c in "/\\"):
        raise HTTPException(409, "Render this project before publishing.")
    fingerprint = media_input_fingerprint(project)
    if rendered.get("input_fingerprint") != fingerprint:
        raise HTTPException(409, "The render is stale. Render the saved project again before publishing.")
    path = project_path(project_id, "renders", filename)
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise HTTPException(409, "The project's rendered video is missing.")
    try:
        manifest = json.loads(project_path(project_id, "renders", filename + ".json").read_text(encoding="utf-8"))
        if manifest.get("status") != "done" or manifest.get("project_id") != project_id or manifest.get("video_filename") != filename or manifest.get("input_fingerprint") != fingerprint:
            raise ValueError()
        inputs = json.loads(project_path(project_id, "renders", filename + ".input.json").read_text(encoding="utf-8"))
        if media_input_fingerprint(inputs) != fingerprint:
            raise ValueError()
    except (ValueError, OSError, AttributeError):
        raise HTTPException(409, "Completed render manifest or input snapshot is missing or does not match this project.")
    return project, path, fingerprint


@router.get("/status")
def get_status():
    try:
        return youtube_service.get_channel_info()
    except youtube_service.YoutubeError as exc:
        raise HTTPException(502, str(exc))


@router.get("/auth/start")
def start_auth(request: Request):
    if not request.state.studio_session:
        raise HTTPException(403, "Open the studio session first.")
    try:
        return RedirectResponse(youtube_service.get_auth_url(str(request.url_for("auth_callback")), request.state.studio_session))
    except (youtube_service.YoutubeError, youtube_service.OAuthStateError) as exc:
        raise HTTPException(400, str(exc))


@router.get("/auth/callback")
def auth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None, state: str = ""):
    redirect_uri = str(request.url_for("auth_callback"))
    try:
        if error or not code:
            youtube_service.consume_oauth_state(state, request.state.studio_session, redirect_uri)
            return HTMLResponse(f"<h3>Authentication failed: {html.escape((error or 'No code returned')[:300])}</h3>", status_code=400)
        youtube_service.exchange_code_for_token(code, redirect_uri, state, request.state.studio_session)
        return HTMLResponse("""<h3>YouTube channel connected.</h3><p>You can close this window.</p>
<script>if(window.opener)window.opener.postMessage('yt_connected',location.origin);window.close();</script>""")
    except (youtube_service.OAuthStateError, youtube_service.YoutubeError) as exc:
        return HTMLResponse(f"<h3>{html.escape(str(exc))}</h3>", status_code=400)


@router.post("/disconnect")
def disconnect():
    youtube_service.disconnect_channel()
    return {"connected": False, "status": "local_credentials_removed"}


@router.post("/generate-metadata")
def generate_metadata(req: GenerateMetadataRequest):
    try:
        return youtube_service.generate_ai_metadata(req.project_data.model_dump(mode="json"))
    except GenerationError as exc:
        raise HTTPException(502, str(exc))


@router.get("/scene-frames/{project_id}")
def get_scene_frames(project_id: str):
    with project_lock(project_id):
        _, path, _ = rendered_artifact(project_id)
        return {"frames": youtube_service.extract_scene_frames(project_id, str(path))}


@router.get("/frame/{project_id}/{frame_name}")
def serve_frame(project_id: str, frame_name: str):
    if any(c in frame_name for c in "/\\") or not frame_name.endswith(".jpg"):
        raise HTTPException(400, "Invalid frame filename")
    path = project_path(project_id, "frames", frame_name)
    if not path.is_file():
        raise HTTPException(404, "Frame not found")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/upload")
def start_upload(req: UploadVideoRequest):
    with project_lock(req.project_id):
        _, path, fingerprint = rendered_artifact(req.project_id)
        if req.video_filename != path.name or req.input_fingerprint != fingerprint:
            raise HTTPException(409, "The selected render no longer matches this saved project. Review and confirm the current render.")
        thumbnail = None
        if req.selected_frame:
            prefix = f"/api/youtube/frame/{req.project_id}/"
            if not req.selected_frame.startswith(prefix):
                raise HTTPException(400, "Thumbnail must belong to this project")
            filename = req.selected_frame[len(prefix):]
            if any(c in filename for c in "/\\%?#") or not filename.endswith(".jpg"):
                raise HTTPException(400, "Invalid thumbnail filename")
            thumbnail = project_path(req.project_id, "frames", filename)
            if not thumbnail.is_file():
                raise HTTPException(400, "Selected thumbnail is missing")
        if sum(len(tag) for tag in req.tags) + max(0, len(req.tags) - 1) > 500:
            raise HTTPException(422, "YouTube tags exceed the total length limit")
        job_id = f"yt_up_{uuid.uuid4().hex}"
        try:
            youtube_service.start_youtube_upload(job_id, str(path), req.title, req.description, req.tags, req.privacy_status, req.made_for_kids, str(thumbnail) if thumbnail else None, project_id=req.project_id, input_fingerprint=fingerprint)
        except youtube_service.YoutubeError as exc:
            raise HTTPException(409, str(exc))
        return {"status": "started", "job_id": job_id}


@router.get("/upload-status/{job_id}")
def get_upload_status(job_id: str):
    job = youtube_service.get_upload_job(job_id)
    if not job:
        raise HTTPException(404, "Upload job not found")
    return job
