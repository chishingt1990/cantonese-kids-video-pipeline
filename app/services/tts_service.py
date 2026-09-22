import os
import subprocess
import tempfile
import asyncio
import edge_tts
from app.services.audio_service import get_audio_duration

VOICE_MAP = {
    "dad": "zh-HK-WanLungNeural",
    "mom": "zh-HK-HiuMaanNeural",
    "child": "zh-HK-HiuGaaiNeural",
    "narrator": "zh-HK-HiuMaanNeural"
}

async def generate_cantonese_tts(
    text: str,
    persona: str = "dad",
    output_wav_path: str = None,
    rate: str = "-8%",
    pitch: str = "+3Hz"
) -> str:
    """
    Generates high quality Cantonese speech using Edge-TTS neural voices,
    and normalizes to 16-bit 44.1kHz mono WAV for audio mixing.
    """
    voice = VOICE_MAP.get(persona.lower(), "zh-HK-WanLungNeural")
    
    if not output_wav_path:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_wav_path = os.path.join(project_root, "assets", "outputs", "audio_clips", "temp_tts.wav")
    
    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
        tmp_mp3_path = tmp_mp3.name

    try:
        # 1. Synthesize with edge-tts
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(tmp_mp3_path)
        
        # 2. Convert to standard 16-bit 44.1kHz mono WAV using ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_mp3_path,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio conversion failed: {res.stderr.decode('utf-8', errors='ignore')}")
            
        return output_wav_path
    finally:
        if os.path.exists(tmp_mp3_path):
            try:
                os.remove(tmp_mp3_path)
            except Exception:
                pass

def synthesize_scene_voice(scene_idx: int, text: str, persona: str = "dad") -> dict:
    """Synchronous wrapper for synthesizing a scene's Cantonese voice."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    filename = f"scene_{scene_idx:02d}_voice.wav"
    out_path = os.path.join(project_root, "assets", "outputs", "audio_clips", filename)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(generate_cantonese_tts(text, persona=persona, output_wav_path=out_path))
    finally:
        loop.close()
        
    duration = get_audio_duration(out_path)
    return {
        "status": "success",
        "scene_idx": scene_idx,
        "filename": filename,
        "path": out_path,
        "duration": duration,
        "persona": persona
    }
