import uuid
from typing import List, Literal

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.storage import PROJECTS_DIR, contained_path, project_path, project_operation, validate_id
from app.services.tts_service import synthesize_scene_voice, speaker_persona
from app.services.audio_service import normalize_audio, run_blocking, scene_duration, MediaPrerequisiteError, MAX_SCENE_SECONDS
from app.services.voice_clone_service import (
    is_voice_clone_available, list_cloned_voices, create_cloned_voice,
    synthesize_scene_cloned_voice, VoiceCloneUnavailableError,
)

router = APIRouter(prefix="/api/audio", tags=["audio"])
StockPersona = Literal["dad", "mom", "child", "narrator"]
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class SceneTTSRequest(BaseModel):
    project_id: str
    scene_idx: int = Field(ge=1, le=100)
    text: str = Field(max_length=10000)
    persona: StockPersona
    duration_sec: float = Field(default=6, gt=0, le=MAX_SCENE_SECONDS)


class BulkTTSRequest(BaseModel):
    project_id: str
    scenes: List[dict] = Field(min_length=1, max_length=100)
    default_persona: StockPersona


class ClonedSceneTTSRequest(BaseModel):
    project_id: str
    scene_idx: int = Field(ge=1, le=100)
    text: str = Field(max_length=10000)
    voice_id: str = Field(min_length=1, max_length=200)
    duration_sec: float = Field(default=6, gt=0, le=MAX_SCENE_SECONDS)


class ClonedBulkTTSRequest(BaseModel):
    project_id: str
    scenes: List[dict] = Field(min_length=1, max_length=100)
    voice_id: str = Field(min_length=1, max_length=200)


def _require_project(project_id):
    try:
        validate_id(project_id)
        if not project_path(project_id, "project.json").is_file():
            raise HTTPException(404, "Save the project before generating audio")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _error(exc):
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, VoiceCloneUnavailableError):
        return HTTPException(503, str(exc))
    if isinstance(exc, MediaPrerequisiteError):
        return HTTPException(503, str(exc))
    if isinstance(exc, (ValueError, TypeError)):
        return HTTPException(400, str(exc))
    return HTTPException(502, "Audio operation failed; no substitute voice was generated")


def _blank(project_id, scene_idx, duration):
    return {"status": "success", "project_id": project_id, "scene_idx": scene_idx,
            "audio_url": None, "duration": 0, "duration_sec": scene_duration(duration),
            "voice_provenance": {"kind": "none"}, "cloned": False}


@router.get("/clip/{project_id}/{filename}")
def get_audio_clip(project_id: str, filename: str):
    try:
        validate_id(project_id)
        path = contained_path(project_path(project_id, "audio"), filename)
        if not filename.endswith(".wav") or not path.is_file():
            raise HTTPException(404, "Clip not found")
        return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=31536000, immutable"})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/tts/scene")
def generate_single_scene_tts(req: SceneTTSRequest):
    _require_project(req.project_id)
    try:
        if not req.text.strip():
            return _blank(req.project_id, req.scene_idx, req.duration_sec)
        with project_operation(req.project_id):
            return synthesize_scene_voice(req.scene_idx, req.text, req.persona,
                                          project_id=req.project_id, duration_sec=req.duration_sec)
    except Exception as exc:
        raise _error(exc) from exc


def _bulk(req, cloned=False):
    _require_project(req.project_id)
    planned = []
    seen = set()
    try:
        for idx, scene in enumerate(req.scenes, 1):
            scene_idx = scene.get("scene_number", idx)
            if isinstance(scene_idx, bool) or not isinstance(scene_idx, int) or not 1 <= scene_idx <= 100 or scene_idx in seen:
                raise ValueError("Scene numbers must be unique integers between 1 and 100")
            seen.add(scene_idx)
            text = scene.get("cantonese") or ""
            if not isinstance(text, str) or len(text) > 10000:
                raise ValueError("Invalid narration text")
            duration = scene_duration(scene.get("duration_sec", 6))
            planned.append((scene_idx, text, duration, scene.get("speaker")))
        results = []
        for scene_idx, text, duration, speaker in planned:
            if not text.strip():
                result = _blank(req.project_id, scene_idx, duration)
            elif cloned:
                result = synthesize_scene_cloned_voice(
                    scene_idx, text, req.voice_id, project_id=req.project_id, duration_sec=duration)
            else:
                result = synthesize_scene_voice(
                    scene_idx, text, speaker_persona(speaker, req.default_persona),
                    project_id=req.project_id, duration_sec=duration)
            results.append(result)
        return {"status": "success", "project_id": req.project_id, "scenes": results,
                "generated_count": sum(bool(r["audio_url"]) for r in results),
                "cloned": cloned and any(bool(r["audio_url"]) for r in results)}
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/tts/all")
def generate_all_scenes_tts(req: BulkTTSRequest):
    _require_project(req.project_id)
    with project_operation(req.project_id):
        return _bulk(req)


async def _save_upload(upload, destination):
    contents = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not contents or len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Recording must be nonempty and at most 25 MB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    await run_blocking(destination.write_bytes, contents)


@router.post("/upload_scene")
async def upload_scene_voice(project_id: str = Form(...), scene_idx: int = Form(...),
                             duration_sec: float = Form(6), audio_file: UploadFile = File(...)):
    _require_project(project_id)
    if not 1 <= scene_idx <= 100:
        raise HTTPException(400, "Invalid scene number")
    filename = f"{uuid.uuid4().hex}.wav"
    output = project_path(project_id, "audio", filename)
    source = output.with_suffix(".upload")
    try:
        requested = scene_duration(duration_sec)
        with project_operation(project_id):
            await _save_upload(audio_file, source)
            duration = await run_blocking(normalize_audio, source, output, max_seconds=MAX_SCENE_SECONDS - 1.2)
            return {"status": "saved", "project_id": project_id, "scene_idx": scene_idx,
                    "duration": duration, "duration_sec": scene_duration(requested, duration),
                    "audio_url": f"/api/audio/clip/{project_id}/{filename}",
                    "voice_provenance": {"kind": "recorded"}}
    except Exception as exc:
        raise _error(exc) from exc
    finally:
        source.unlink(missing_ok=True)


@router.get("/voice-clone/status")
def voice_clone_status():
    return {"available": is_voice_clone_available(), "capability_verified": False,
            "voices": list_cloned_voices()}


@router.post("/voice-clone/create")
async def voice_clone_create(name: str = Form("Dad"), audio_file: UploadFile = File(...),
                             consent_file: UploadFile = File(...)):
    workdir = PROJECTS_DIR.parent / "voice_uploads" / uuid.uuid4().hex
    sample = workdir / "reference.upload"
    consent = workdir / "consent.upload"
    try:
        if not is_voice_clone_available():
            raise VoiceCloneUnavailableError("Configure the parent-voice provider first")
        await _save_upload(audio_file, sample)
        await _save_upload(consent_file, consent)
        return await run_blocking(create_cloned_voice, str(sample), str(consent), name)
    except Exception as exc:
        raise _error(exc) from exc
    finally:
        sample.unlink(missing_ok=True)
        consent.unlink(missing_ok=True)
        if workdir.exists():
            workdir.rmdir()


@router.post("/voice-clone/synthesize")
def synthesize_single_scene_cloned(req: ClonedSceneTTSRequest):
    _require_project(req.project_id)
    try:
        if not req.text.strip():
            return _blank(req.project_id, req.scene_idx, req.duration_sec)
        with project_operation(req.project_id):
            return synthesize_scene_cloned_voice(req.scene_idx, req.text, req.voice_id,
                                                 project_id=req.project_id, duration_sec=req.duration_sec)
    except Exception as exc:
        raise _error(exc) from exc


@router.post("/voice-clone/synthesize-all")
def synthesize_all_scenes_cloned(req: ClonedBulkTTSRequest):
    _require_project(req.project_id)
    with project_operation(req.project_id):
        return _bulk(req, cloned=True)
