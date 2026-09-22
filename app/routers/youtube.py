import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from pydantic import BaseModel

from app.services import youtube_service, project_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

class GenerateMetadataRequest(BaseModel):
    project_data: Dict[str, Any]

class UploadVideoRequest(BaseModel):
    project_id: str
    title: str
    description: str
    tags: List[str]
    privacy_status: str = "unlisted"
    made_for_kids: bool = True
    selected_frame: Optional[str] = None

@router.get("/status")
def get_status():
    """Checks YouTube connection status and channel details."""
    return youtube_service.get_channel_info()

@router.get("/auth/start")
def start_auth(request: Request):
    """Initiates OAuth 2.0 flow with local redirect."""
    redirect_uri = str(request.url_for("auth_callback"))
    # In local testing behind proxy, ensure http://
    if redirect_uri.startswith("https://localhost") or redirect_uri.startswith("https://127.0.0.1"):
        redirect_uri = redirect_uri.replace("https://", "http://", 1)
    try:
        url = youtube_service.get_auth_url(redirect_uri)
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/auth/callback")
def auth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handles OAuth redirect from Google."""
    if error or not code:
        return HTMLResponse(
            f"<html><body><h3>Authentication failed: {error or 'No code returned'}</h3><button onclick='window.close()'>Close</button></body></html>"
        )
    redirect_uri = str(request.url_for("auth_callback"))
    if redirect_uri.startswith("https://localhost") or redirect_uri.startswith("https://127.0.0.1"):
        redirect_uri = redirect_uri.replace("https://", "http://", 1)
        
    success = youtube_service.exchange_code_for_token(code, redirect_uri)
    if success:
        return HTMLResponse("""
        <html>
          <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #fffbeb;">
            <h2 style="color: #047857;">🎉 YouTube Channel Connected!</h2>
            <p>You can now publish episodes directly from Kids Video Studio.</p>
            <script>
              if (window.opener) {
                window.opener.postMessage('yt_connected', '*');
              }
              setTimeout(function() { window.close(); }, 1500);
            </script>
          </body>
        </html>
        """)
    else:
        return HTMLResponse("<html><body><h3>Failed to save credentials. Please try again.</h3><button onclick='window.close()'>Close</button></body></html>")

@router.post("/disconnect")
def disconnect():
    """Revokes local OAuth credentials."""
    success = youtube_service.disconnect_channel()
    return {"connected": not success}

@router.post("/generate-metadata")
def generate_metadata(req: GenerateMetadataRequest):
    """Uses Gemini to generate high-SEO Cantonese preschool YouTube metadata and chapters."""
    return youtube_service.generate_ai_metadata(req.project_data)

@router.get("/scene-frames/{project_id}")
def get_scene_frames(project_id: str):
    """Extracts candidate thumbnail frames from the project's rendered video."""
    proj = project_service.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project_root = Path(__file__).resolve().parent.parent.parent
    rendered_vid = proj.get("rendered_video", {}).get("filename")
    if not rendered_vid:
        # Fallback to standard output paths
        v_candidates = [
            project_root / "assets" / "outputs" / f"episode_{project_id}.mp4",
            project_root / "assets" / "outputs" / "episode_01_meeting_family.mp4"
        ]
        video_path = None
        for vc in v_candidates:
            if vc.exists():
                video_path = str(vc)
                break
    else:
        video_path = str(project_root / "assets" / "outputs" / rendered_vid)
        
    if not video_path or not os.path.exists(video_path):
        return {"frames": []}
        
    frames = youtube_service.extract_scene_frames(project_id, video_path)
    return {"frames": frames}

@router.get("/frame/{project_id}/{frame_name}")
def serve_frame(project_id: str, frame_name: str):
    """Serves extracted video frame thumbnail image."""
    project_root = Path(__file__).resolve().parent.parent.parent
    frame_path = project_root / "projects" / project_id / "frames" / frame_name
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(str(frame_path), media_type="image/jpeg")

@router.post("/upload")
def start_upload(req: UploadVideoRequest):
    """Kicks off a background upload of the rendered video to YouTube."""
    proj = project_service.get_project(req.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project_root = Path(__file__).resolve().parent.parent.parent
    rendered_vid = proj.get("rendered_video", {}).get("filename")
    video_path = None
    if rendered_vid:
        v_test = project_root / "assets" / "outputs" / rendered_vid
        if v_test.exists():
            video_path = str(v_test)
            
    if not video_path:
        for fname in [f"episode_{req.project_id}.mp4", "episode_01_meeting_family.mp4"]:
            candidate = project_root / "assets" / "outputs" / fname
            if candidate.exists():
                video_path = str(candidate)
                break
                
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="No rendered video file found for this project. Please render first in Step 5.")

    thumb_path = None
    if req.selected_frame:
        fname = os.path.basename(req.selected_frame)
        f_candidate = project_root / "projects" / req.project_id / "frames" / fname
        if f_candidate.exists():
            thumb_path = str(f_candidate)

    job_id = f"yt_up_{uuid.uuid4().hex[:8]}"
    youtube_service.start_youtube_upload(
        job_id=job_id,
        video_path=video_path,
        title=req.title,
        description=req.description,
        tags=req.tags,
        privacy_status=req.privacy_status,
        made_for_kids=req.made_for_kids,
        thumbnail_path=thumb_path
    )

    return {"status": "started", "job_id": job_id}

@router.get("/upload-status/{job_id}")
def get_upload_status(job_id: str):
    """Polls YouTube upload progress."""
    job = youtube_service.UPLOAD_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job
