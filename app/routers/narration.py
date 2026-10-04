"""Narration endpoints: record-your-voice flow.

Parents record in the app or upload a phone recording. Every recording is
auto-cleaned (denoise + level) on the way in. Transcription + alignment turn
what was actually said into timed karaoke captions.
"""
import os
import shutil
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services import narration_service

router = APIRouter(prefix="/api/narration", tags=["narration"])


def _audio_url(project_id: str) -> str:
    return f"/api/narration/audio/{project_id}"


@router.post("/upload")
async def upload_narration(project_id: str = Form(...),
                           audio_file: UploadFile = File(...)):
    """Upload one finished recording (e.g. a phone m4a). Auto-cleaned."""
    tmp = narration_service.narration_path(project_id) + ".upload_raw"
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(audio_file.file, f)
        res = narration_service.save_uploaded_narration(project_id, tmp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    res["audio_url"] = _audio_url(project_id)
    return res


@router.post("/take")
async def upload_take(project_id: str = Form(...),
                      audio_file: UploadFile = File(...)):
    """Upload one take of a multi-take recording session. Auto-cleaned."""
    tmp = narration_service.narration_path(project_id) + ".take_raw"
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(audio_file.file, f)
        res = narration_service.add_narration_take(project_id, tmp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return res


@router.get("/takes/{project_id}")
def get_takes(project_id: str):
    return {"takes": narration_service.list_narration_takes(project_id)}


@router.delete("/take/{project_id}/{index}")
def remove_take(project_id: str, index: int):
    try:
        return narration_service.delete_narration_take(project_id, index)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FinalizeRequest(BaseModel):
    project_id: str


@router.post("/takes/finalize")
def finalize_takes(req: FinalizeRequest):
    """Join recorded takes with crossfades into the final narration."""
    try:
        res = narration_service.finalize_narration_takes(req.project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    res["audio_url"] = _audio_url(req.project_id)
    return res


@router.post("/transcribe")
def transcribe(req: FinalizeRequest):
    """Transcribe the final narration: what did the parent actually say?"""
    audio_path = narration_service.narration_path(req.project_id)
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=404,
            detail="No narration yet — record or upload your voice first.",
        )
    try:
        return narration_service.transcribe_narration(audio_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SectionIn(BaseModel):
    scene_number: int
    cantonese: str


class AlignRequest(BaseModel):
    project_id: str
    sections: List[SectionIn]


@router.post("/align")
def align_narration(req: AlignRequest):
    """Map each script section onto the narration; captions come from the
    transcript (what was actually said), timed to the real voice."""
    audio_path = narration_service.narration_path(req.project_id)
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=404,
            detail="No narration yet — record or upload your voice first.",
        )
    try:
        return narration_service.align_narration(
            audio_path, [s.model_dump() for s in req.sections]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/{project_id}")
def get_narration_audio(project_id: str):
    path = narration_service.narration_path(project_id)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/wav")
    return {"error": "Narration not found"}
