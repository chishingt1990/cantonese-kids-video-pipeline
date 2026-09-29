from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.services import narration_service as narration
from app.services.audio_service import MediaPrerequisiteError, require_media_tools
from app.services.voice_clone_service import (
    VoiceCloneUnavailableError, VoiceProfileError, import_cloned_voice, discover_cloned_voices,
    is_voice_clone_available, list_cloned_voices,
)

router = APIRouter(prefix="/api/narration", tags=["narration"])


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=0)
    voice_id: str = Field(min_length=1, max_length=200)
    style: Literal["calm", "warm_playful", "excited"]
    allow_estimated_alignment: bool = False


class AlignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=0)
    take_id: str = Field(min_length=1, max_length=100)
    allow_estimated_alignment: bool = False


class ImportVoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    voice_id: str = Field(min_length=1, max_length=100)
    name: str = Field(default="Dad", min_length=1, max_length=100)


def _error(exc):
    if isinstance(exc, (narration.NarrationError, VoiceProfileError)):
        return HTTPException(exc.http_status, {"code": exc.code, "message": str(exc)})
    if isinstance(exc, (MediaPrerequisiteError, VoiceCloneUnavailableError)):
        return HTTPException(503, {"code": "prerequisite_missing", "message": str(exc)})
    if isinstance(exc, ValueError):
        return HTTPException(400, {"code": "invalid_request", "message": str(exc)})
    return HTTPException(500, {"code": "narration_failed", "message": "Narration operation failed safely"})


@router.post("/voices/import")
def import_voice(req: ImportVoiceRequest):
    try:
        return import_cloned_voice(req.voice_id, req.name)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/voices/discover")
def discover_voices():
    try:
        return discover_cloned_voices()
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/capabilities")
def capabilities():
    """Report local prerequisites without a provider call or model download."""
    try:
        voices = [{
            "voice_id": item["voice_id"], "name": item.get("name", "Saved parent voice"),
            "profile_verified": item.get("profile_verified", False),
        } for item in list_cloned_voices()]
        provider_configured = is_voice_clone_available()
        alignment_available, alignment_message = True, ""
        try:
            narration.alignment_preflight()
        except narration.NarrationError as exc:
            alignment_available, alignment_message = False, str(exc)
        media_available, media_message = True, ""
        try:
            require_media_tools("ffmpeg", "ffprobe")
        except MediaPrerequisiteError as exc:
            media_available, media_message = False, str(exc)
        return {
            "voices": voices, "provider_configured": provider_configured,
            "styles": list(narration.STYLES),
            "capability_verified": False,
            "alignment_available": alignment_available, "alignment_message": alignment_message,
            "media_available": media_available, "media_message": media_message,
        }
    except (OSError, ValueError) as exc:
        raise _error(exc) from exc


@router.post("/start", status_code=202)
def start(req: StartRequest):
    try:
        return narration.start_job(**req.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/align", status_code=202)
def align(req: AlignRequest):
    try:
        return narration.start_job(**req.model_dump())
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/status/{job_id}")
def status(job_id: str, project_id: str):
    try:
        return narration.get_job(project_id, job_id)
    except Exception as exc:
        raise _error(exc) from exc


@router.get("/audio/{project_id}/{take_id}")
def audio(project_id: str, take_id: str):
    try:
        narration.load_manifest(project_id, take_id)
        return FileResponse(narration.narration_audio_path(project_id, take_id), media_type="audio/wav",
                            headers={"Cache-Control": "private, max-age=31536000, immutable"})
    except Exception as exc:
        raise _error(exc) from exc
