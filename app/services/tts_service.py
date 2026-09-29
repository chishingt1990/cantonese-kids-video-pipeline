import asyncio
import uuid
from pathlib import Path

import edge_tts

from app.storage import project_path, project_operation
from app.services.audio_service import normalize_audio, run_blocking, scene_duration, require_media_tools, MAX_SCENE_SECONDS

VOICE_MAP = {
    "dad": "zh-HK-WanLungNeural",
    "mom": "zh-HK-HiuMaanNeural",
    "child": "zh-HK-HiuGaaiNeural",
    "narrator": "zh-HK-HiuMaanNeural",
}


def speaker_persona(speaker, default_persona):
    if default_persona not in VOICE_MAP:
        raise ValueError("Choose an explicit supported stock voice")
    speaker = str(speaker or "").lower()
    if any(word in speaker for word in ("mom", "mother", "媽媽")):
        return "mom"
    if any(word in speaker for word in ("child", "brother", "baby", "levi", "luca", "哥哥", "細佬")):
        return "child"
    if "narrator" in speaker:
        return "narrator"
    if any(word in speaker for word in ("dad", "father", "爸爸")):
        return "dad"
    return default_persona


async def generate_cantonese_tts(text: str, persona: str, output_wav_path: str,
                                 rate: str = "-8%", pitch: str = "+3Hz") -> str:
    if persona not in VOICE_MAP:
        raise ValueError("Choose an explicit supported stock voice")
    if not text.strip():
        raise ValueError("Narration text is blank")
    require_media_tools("ffmpeg", "ffprobe")
    output = Path(output_wav_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_name(f"{uuid.uuid4().hex}.source.mp3")
    try:
        communicate = edge_tts.Communicate(text, VOICE_MAP[persona], rate=rate, pitch=pitch)
        await asyncio.wait_for(communicate.save(str(source)), timeout=120)
        await run_blocking(normalize_audio, source, output, max_seconds=MAX_SCENE_SECONDS - 1.2)
        return str(output)
    finally:
        source.unlink(missing_ok=True)


def synthesize_scene_voice(scene_idx: int, text: str, persona: str, *, project_id: str,
                           duration_sec: float = 6) -> dict:
    with project_operation(project_id):
        filename = f"{uuid.uuid4().hex}.wav"
        out_path = project_path(project_id, "audio", filename)
        asyncio.run(generate_cantonese_tts(text, persona, str(out_path)))
        from app.services.audio_service import get_audio_duration
        duration = get_audio_duration(str(out_path))
        return {
            "status": "success", "project_id": project_id, "scene_idx": scene_idx,
            "filename": filename, "audio_url": f"/api/audio/clip/{project_id}/{filename}",
            "duration": duration, "duration_sec": scene_duration(duration_sec, duration),
            "persona": persona, "cloned": False,
            "voice_provenance": {"kind": "stock", "provider": "edge", "persona": persona,
                                 "voice": VOICE_MAP[persona], "language": "yue-HK"},
        }
