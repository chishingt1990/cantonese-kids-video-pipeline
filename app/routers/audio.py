import os
import subprocess
import time
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.tts_service import synthesize_scene_voice
from app.services.audio_service import mix_scene_audio, get_audio_duration

router = APIRouter(prefix="/api/audio", tags=["audio"])

class SceneTTSRequest(BaseModel):
    scene_idx: int
    text: str
    persona: str = "dad"

class BulkTTSRequest(BaseModel):
    scenes: List[dict]
    default_persona: str = "dad"

@router.get("/clip/{filename}")
def get_audio_clip(filename: str):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(project_root, "assets", "outputs", "audio_clips", filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/wav")
    return {"error": "Clip not found"}

@router.get("/master")
def get_master_audio():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(project_root, "assets", "outputs", "episode_01_master_audio.wav")
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/wav")
    return {"error": "Master audio not found"}

def _remix_master_audio():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    audio_clips_dir = os.path.join(project_root, "assets", "outputs", "audio_clips")
    master_audio_path = os.path.join(project_root, "assets", "outputs", "episode_01_master_audio.wav")
    voice_paths = []
    durations = []
    for s_idx in range(1, 15):
        clip = os.path.join(audio_clips_dir, f"scene_{s_idx:02d}_voice.wav")
        if os.path.exists(clip):
            voice_paths.append(clip)
            durations.append(max(6.0, get_audio_duration(clip) + 1.2))
        elif s_idx > 1 and not voice_paths:
            continue
        elif voice_paths:
            break
    if voice_paths:
        try:
            mix_scene_audio(voice_paths, durations, master_audio_path)
            return True
        except Exception as e:
            print(f"Master audio remix notice: {e}")
    return False

@router.post("/tts/scene")
def generate_single_scene_tts(req: SceneTTSRequest):
    """Generate high quality Cantonese voiceover for a single scene."""
    try:
        res = synthesize_scene_voice(req.scene_idx, req.text, persona=req.persona)
        res["audio_url"] = f"/api/audio/clip/{res['filename']}?t={int(time.time()*1000)}"
        _remix_master_audio()
        res["master_audio_url"] = f"/api/audio/master?t={int(time.time()*1000)}"
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts/all")
def generate_all_scenes_tts(req: BulkTTSRequest):
    """Generate Cantonese voiceovers for all scenes in the episode and remixes the master audio."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    audio_clips_dir = os.path.join(project_root, "assets", "outputs", "audio_clips")
    os.makedirs(audio_clips_dir, exist_ok=True)
    
    results = []
    voice_paths = []
    durations = []
    
    for idx, s in enumerate(req.scenes):
        scene_idx = s.get("scene_number", idx + 1)
        text = s.get("cantonese", "")
        speaker = s.get("speaker", "Dad").lower()
        persona = "mom" if "mom" in speaker or "mother" in speaker else ("child" if "brother" in speaker or "baby" in speaker or "levi" in speaker or "luca" in speaker else req.default_persona)
        
        if text.strip():
            res = synthesize_scene_voice(scene_idx, text, persona=persona)
            res["audio_url"] = f"/api/audio/clip/{res['filename']}?t={int(time.time()*1000)}"
            results.append(res)
            v_path = res["path"]
            voice_paths.append(v_path)
            dur = max(res["duration"] + 1.2, float(s.get("duration_sec", 6)))
            durations.append(dur)
        else:
            filename = f"scene_{scene_idx:02d}_voice.wav"
            v_path = os.path.join(audio_clips_dir, filename)
            voice_paths.append(v_path if os.path.exists(v_path) else None)
            durations.append(float(s.get("duration_sec", 6)))

    # Automatically re-mix master audio with soft ukulele BGM
    master_audio_path = os.path.join(project_root, "assets", "outputs", "episode_01_master_audio.wav")
    try:
        mix_scene_audio(voice_paths, durations, master_audio_path)
    except Exception as e:
        print(f"Warning: master audio mix failed: {e}")
        
    return {
        "status": "success",
        "generated_count": len(results),
        "scenes": results,
        "master_audio_url": f"/api/audio/master?t={int(time.time()*1000)}"
    }

@router.post("/upload_scene")
async def upload_scene_voice(
    scene_idx: int = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    Receives recorded microphone audio (from browser WebM/WAV)
    and transcodes to clean 16-bit 44.1kHz mono PCM WAV via FFmpeg.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    out_dir = os.path.join(project_root, "assets", "outputs", "audio_clips")
    os.makedirs(out_dir, exist_ok=True)
    
    temp_raw = os.path.join(out_dir, f"temp_upload_{scene_idx}.raw")
    filename = f"scene_{scene_idx:02d}_voice.wav"
    final_path = os.path.join(out_dir, filename)
    
    contents = await audio_file.read()
    with open(temp_raw, "wb") as f:
        f.write(contents)
        
    try:
        # Transcode any browser audio container to true 44.1kHz PCM s16 WAV
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_raw,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            final_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        if os.path.exists(temp_raw):
            try:
                os.remove(temp_raw)
            except Exception:
                pass
                
    dur = get_audio_duration(final_path)
    _remix_master_audio()
    return {
        "status": "saved",
        "path": final_path,
        "scene_idx": scene_idx,
        "duration": dur,
        "audio_url": f"/api/audio/clip/{filename}?t={int(time.time()*1000)}",
        "master_audio_url": f"/api/audio/master?t={int(time.time()*1000)}"
    }
