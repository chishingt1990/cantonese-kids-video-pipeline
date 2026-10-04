"""Narration-first endpoints: one script -> one TTS request -> auto-alignment.

All routes are additive; the classic per-scene audio flow is untouched.
"""
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services import narration_service

router = APIRouter(prefix="/api/narration", tags=["narration"])


class SynthesizeRequest(BaseModel):
    project_id: str
    voice_id: str
    full_text: str
    style: Optional[str] = None


@router.post("/synthesize")
def synthesize_narration(req: SynthesizeRequest):
    """Render the FULL episode script with ONE cloned-voice TTS request."""
    try:
        res = narration_service.synthesize_narration(
            req.project_id, req.voice_id, req.full_text, req.style
        )
        res["audio_url"] = f"/api/narration/audio/{req.project_id}"
        return res
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
    """Map each script section onto the narration audio (word-level)."""
    audio_path = narration_service.narration_path(req.project_id)
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=404,
            detail="Narration audio not found — generate it first.",
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
