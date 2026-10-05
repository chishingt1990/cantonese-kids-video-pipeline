"""Lesson Studio endpoints: the engine behind the 15-20 video library.

Flow:
  1. POST /api/lesson/timing   (upload parent's recording -> phrase timeline)
  2. POST /api/lesson/plan     (timeline + template + items -> scene plan)
  3. POST /api/lesson/render   (scene plan + timeline -> MP4, preview or full)

The parent reviews the timeline and scene plan between steps — the
preview-then-approve loop.
"""
import os
import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from app.services import lesson_timing_service, lesson_templates
from app.services.lesson_render_service import render_lesson

router = APIRouter(prefix="/api/lesson", tags=["lesson"])


def _lesson_dir(project_id: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    d = os.path.join(root, "assets", "outputs", "lessons",
                     "".join(c for c in project_id
                             if c.isalnum() or c in "-_") or "lesson")
    os.makedirs(d, exist_ok=True)
    return d


def _lesson_audio(project_id: str) -> str:
    return os.path.join(_lesson_dir(project_id), "audio.wav")


@router.get("/templates")
def get_templates():
    """List the four lesson formats."""
    return {"templates": lesson_templates.list_templates()}


@router.post("/timing")
async def lesson_timing(project_id: str = Form(...),
                        audio_file: UploadFile = File(...),
                        max_gap: float = Form(0.6),
                        target_count: Optional[int] = Form(None),
                        trim: float = Form(0.0)):
    """Upload the parent's recording -> phrase timeline with display tokens.

    target_count: tune phrase splitting to hit this many phrases
    (e.g. 56 for a 7x8 verse song). trim: cut lead-in silence (seconds).
    """
    tmp = _lesson_audio(project_id) + ".upload_raw"
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(audio_file.file, f)
        # Transcode to clean WAV via the narration service's helper.
        from app.services.narration_service import _transcode_to_wav
        _transcode_to_wav(tmp, _lesson_audio(project_id))
        tc = int(target_count) if target_count else None
        timeline = lesson_timing_service.build_timeline(
            _lesson_audio(project_id), max_gap=float(max_gap),
            target_count=tc, trim=float(trim))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return timeline


class PlanRequest(BaseModel):
    phrases: list
    template_id: str
    items: list = []
    opts: dict = {}


@router.post("/plan")
def lesson_plan(req: PlanRequest):
    """Phrases + template + items -> scene plan for review."""
    try:
        scenes = lesson_templates.build_scenes(req.template_id, req.phrases,
                                               req.items, req.opts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "template_id": req.template_id,
            "scene_count": len(scenes), "scenes": scenes}


class RenderRequest(BaseModel):
    project_id: str
    scenes: list
    caption_lines: list = []
    preview: bool = True
    tail: float = 1.5


@router.post("/render")
def lesson_render(req: RenderRequest):
    """Render the scene plan -> MP4. preview=True for a fast timing check."""
    audio = _lesson_audio(req.project_id)
    if not os.path.exists(audio):
        raise HTTPException(status_code=400,
                            detail="No lesson audio. POST /api/lesson/timing first.")
    job_id = uuid.uuid4().hex[:8]
    kind = "preview" if req.preview else "full"
    out = os.path.join(_lesson_dir(req.project_id),
                       f"lesson_{kind}_{job_id}.mp4")
    # caption_lines default to the phrases-as-lines when not supplied.
    caption_lines = req.caption_lines or []
    try:
        res = render_lesson(req.scenes, caption_lines, audio, out,
                            {"preview": req.preview, "tail": req.tail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    res["job_id"] = job_id
    res["video_url"] = (f"/api/lesson/video/{req.project_id}/"
                        f"{os.path.basename(out)}")
    return res


@router.get("/video/{project_id}/{filename}")
def lesson_video(project_id: str, filename: str):
    path = os.path.join(_lesson_dir(project_id), filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4")
    return {"error": "Not found"}
