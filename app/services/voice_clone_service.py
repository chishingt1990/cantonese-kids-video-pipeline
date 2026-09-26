"""
Parent-voice cloning via the Google Gemini API voice replication
(gemini-3.8-flash-tts).

Flow:
  1. Parent provides two clips from the SAME adult speaker, recorded on the
     same mic in a quiet room:
       - reference clip: 10-30s of clean natural speech
         (defaults to assets/audio_samples/dad_cantonese.mp3, trimmed to 30s)
       - consent clip: the speaker reciting Google's mandatory consent
         statement VERBATIM in a supported language. en-US example:
         "I am the owner of this voice and I consent to Google using this
          voice to create a synthetic voice model."
         NOTE: Cantonese is NOT in Google's consent-statement locale list, so
         the consent clip should use English (en-US) or the zh-CN Mandarin
         version. This does not affect narration language.
  2. Backend converts both clips to 24kHz mono 16-bit WAV, base64-encodes them,
     and POSTs to https://generativelanguage.googleapis.com/v1beta/voices
     (store=True, persistent voice profile). The returned voice_... id is
     persisted to config/cloned_voices.json.
  3. Scene narration is synthesized via POST /v1beta/interactions with
     model gemini-3.8-flash-tts and the voice id, then normalized to
     16-bit 44.1kHz mono WAV (same contract as tts_service).

Uses the same Gemini key as the rest of the studio (load_settings(), seeded
from GEMINI_API_KEY) -- no extra key needed. ~$0.81/hour of generated audio
at 2026 pricing, so effectively free at this volume.

Graceful degradation: if no Gemini key is configured, every public function
raises VoiceCloneUnavailableError (or returns available=False) so callers can
fall back to the built-in edge-tts path. Nothing here crashes the app.

Endpoint shapes follow the official voice-replication docs as of 2026-09-24:
https://ai.google.dev/gemini-api/docs/voice-replication
The API is days old; response parsing is deliberately defensive.
"""
import os
import json
import time
import base64
import subprocess
import tempfile
import asyncio

import requests

from app.config import load_settings
from app.services.audio_service import get_audio_duration

GEMINI_VOICES_URL = "https://generativelanguage.googleapis.com/v1beta/voices"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
TTS_MODEL = "gemini-3.8-flash-tts"

# Verbatim consent statements from the official docs. The speaker must recite
# ONE of these word-for-word in the consent clip. Cantonese is not listed.
CONSENT_STATEMENT_EN_US = (
    "I am the owner of this voice and I consent to Google using this voice "
    "to create a synthetic voice model."
)
CONSENT_STATEMENT_ZH_CN = (
    "我是此声音的拥有者并授权谷歌使用此声音创建语音合成模型"
)


class VoiceCloneUnavailableError(RuntimeError):
    """Raised when voice cloning was requested but cannot run (no Gemini key)."""


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def get_gemini_api_key() -> str:
    """The studio's Gemini key (Settings UI, seeded from GEMINI_API_KEY)."""
    try:
        return (load_settings().gemini_api_key or "").strip()
    except Exception:
        return ""


def is_voice_clone_available() -> bool:
    """True only when a Gemini API key is configured."""
    return bool(get_gemini_api_key())


def _require_api_key() -> str:
    api_key = get_gemini_api_key()
    if not api_key:
        raise VoiceCloneUnavailableError(
            "Gemini voice cloning is not configured. "
            "Add your Gemini API key in the studio Settings page "
            "(or set GEMINI_API_KEY in your .env file) to enable it. "
            "Falling back to the built-in Cantonese AI voices."
        )
    return api_key


def _headers(api_key: str) -> dict:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


def _cloned_voices_path() -> str:
    return os.path.join(_project_root(), "config", "cloned_voices.json")


def list_cloned_voices() -> list:
    """Previously created clone records: [{voice_id, name, created_at, sample}]."""
    path = _cloned_voices_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_cloned_voice(voice_id: str, name: str, sample: str) -> dict:
    record = {
        "voice_id": voice_id,
        "name": name,
        "sample": sample,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    voices = [v for v in list_cloned_voices() if v.get("voice_id") != voice_id]
    voices.append(record)
    path = _cloned_voices_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(voices, f, indent=2, ensure_ascii=False)
    return record


def default_sample_path() -> str:
    return os.path.join(_project_root(), "assets", "audio_samples", "dad_cantonese.mp3")


def _prepare_reference_wav(src_path: str, workdir: str) -> str:
    """
    Converts the reference sample to Google's recommended format (24kHz mono
    16-bit WAV) and trims to a 10-30s window when longer than 30s.
    """
    out_path = os.path.join(workdir, "reference_24k.wav")
    try:
        duration = float(get_audio_duration(src_path) or 0)
    except Exception:
        duration = 0
    cmd = ["ffmpeg", "-y", "-i", src_path]
    if duration > 30:
        start = max(0.0, (duration - 30.0) / 2.0)  # center 30s window
        cmd += ["-ss", f"{start:.2f}", "-t", "30"]
    cmd += ["-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", out_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(
            f"FFmpeg reference-audio conversion failed: "
            f"{res.stderr.decode('utf-8', errors='ignore')[:300]}"
        )
    return out_path


def _prepare_consent_wav(src_path: str, workdir: str) -> str:
    """Converts the consent clip to 24kHz mono 16-bit WAV (no trimming)."""
    out_path = os.path.join(workdir, "consent_24k.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", src_path,
        "-ar", "24000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        out_path,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(
            f"FFmpeg consent-audio conversion failed: "
            f"{res.stderr.decode('utf-8', errors='ignore')[:300]}"
        )
    return out_path


def _b64_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_cloned_voice(
    sample_path: str = None,
    consent_path: str = None,
    name: str = "Dad",
) -> dict:
    """
    Creates a Gemini replicated voice from a parent voice sample + consent clip.
    Returns {"status": "success", "voice_id": ..., "name": ...}.
    Raises VoiceCloneUnavailableError when no Gemini key is configured,
    ValueError when the consent clip is missing (Google requires it).
    """
    api_key = _require_api_key()
    sample_path = sample_path or default_sample_path()
    if not os.path.exists(sample_path):
        raise FileNotFoundError(f"Voice sample not found: {sample_path}")
    if not consent_path or not os.path.exists(consent_path):
        raise ValueError(
            "A consent recording is required by Google. Record the same speaker "
            "saying, word for word: "
            f'"{CONSENT_STATEMENT_EN_US}"'
        )

    workdir = tempfile.mkdtemp(prefix="voice_clone_")
    try:
        ref_wav = _prepare_reference_wav(sample_path, workdir)
        consent_wav = _prepare_consent_wav(consent_path, workdir)

        payload = {
            "store": True,
            "voice": {
                "model": TTS_MODEL,
                "type": "replicated",
                "display_name": f"{name} - Cantonese Kids Studio",
                "replicated": {
                    "source_audio": {"mime_type": "audio/wav", "data": _b64_file(ref_wav)},
                    "consent_audio": {"mime_type": "audio/wav", "data": _b64_file(consent_wav)},
                },
            },
        }
        resp = requests.post(
            GEMINI_VOICES_URL, headers=_headers(api_key), json=payload, timeout=180
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gemini voice creation failed ({resp.status_code}): {resp.text[:300]}"
            )
        voice_id = _parse_voice_id(resp.json(), resp.text)
    finally:
        for p in (os.path.join(workdir, "reference_24k.wav"),
                  os.path.join(workdir, "consent_24k.wav")):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        try:
            os.rmdir(workdir)
        except Exception:
            pass

    save_cloned_voice(voice_id, name, sample_path)
    return {"status": "success", "voice_id": voice_id, "name": name}


def _parse_voice_id(data, raw_text: str) -> str:
    """Defensive parse of the voices.create response (brand-new API)."""
    voice_id = None
    if isinstance(data, dict):
        voice_id = data.get("id") or data.get("voice_id")
        if not voice_id and isinstance(data.get("name"), str):
            # REST-style resource name, e.g. "voices/voice_abc123"
            voice_id = data["name"].split("/")[-1]
        replicated = data.get("replicated_voice") or {}
        if not voice_id and isinstance(replicated, dict):
            voice_id = replicated.get("id")
    if not voice_id or not str(voice_id).startswith("voice"):
        raise RuntimeError(
            f"Gemini did not return a voice id (expected 'voice_...'): {raw_text[:300]}"
        )
    return voice_id


def _extract_audio_b64(payload: dict) -> str:
    """Defensive parse of the interactions response (brand-new API)."""
    candidates = []
    for step in payload.get("steps", []) or []:
        for item in step.get("content", []) or []:
            if isinstance(item, dict) and item.get("type") == "audio" and item.get("data"):
                candidates.append(item["data"])
    if not candidates:
        out = payload.get("output_audio")
        if isinstance(out, dict) and out.get("data"):
            candidates.append(out["data"])
    if not candidates:
        raise RuntimeError(
            f"Gemini TTS returned no audio data: {json.dumps(payload)[:300]}"
        )
    return candidates[-1]


async def generate_cloned_tts(
    text: str,
    voice_id: str,
    output_wav_path: str = None,
    style: str = "warm and gentle, speaking slowly to young children",
) -> str:
    """
    Renders Cantonese text with a Gemini replicated voice and normalizes to
    16-bit 44.1kHz mono WAV (same contract as tts_service.generate_cantonese_tts).
    Raises VoiceCloneUnavailableError when no Gemini key is configured.

    NOTE: Cantonese narration with a replicated voice is not explicitly
    confirmed in Google's voice-replication docs (they list 100+ TTS
    languages); test the first render and listen before publishing.
    """
    api_key = _require_api_key()

    if not output_wav_path:
        output_wav_path = os.path.join(
            _project_root(), "assets", "outputs", "audio_clips", "temp_cloned_tts.wav"
        )
    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)

    payload = {
        "model": TTS_MODEL,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [
                            {"type": "speech_metadata", "style": style}
                        ],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice_id}]},
    }
    resp = requests.post(
        GEMINI_INTERACTIONS_URL,
        headers=_headers(api_key),
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Gemini TTS failed ({resp.status_code}): {resp.text[:300]}"
        )

    audio_bytes = base64.b64decode(_extract_audio_b64(resp.json()))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav.write(audio_bytes)
        tmp_wav_path = tmp_wav.name

    try:
        # Normalize to 16-bit 44.1kHz mono WAV for the studio mixing pipeline.
        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_wav_path,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_wav_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(
                f"FFmpeg audio conversion failed: "
                f"{res.stderr.decode('utf-8', errors='ignore')[:300]}"
            )
        return output_wav_path
    finally:
        if os.path.exists(tmp_wav_path):
            try:
                os.remove(tmp_wav_path)
            except Exception:
                pass


def synthesize_scene_cloned_voice(scene_idx: int, text: str, voice_id: str) -> dict:
    """Synchronous wrapper for a scene's cloned-voice narration (mirrors tts_service)."""
    out_path = os.path.join(
        _project_root(), "assets", "outputs", "audio_clips",
        f"scene_{scene_idx:02d}_voice.wav",
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            generate_cloned_tts(text, voice_id, output_wav_path=out_path)
        )
    finally:
        loop.close()

    duration = get_audio_duration(out_path)
    return {
        "status": "success",
        "scene_idx": scene_idx,
        "filename": f"scene_{scene_idx:02d}_voice.wav",
        "path": out_path,
        "duration": duration,
        "voice_id": voice_id,
        "cloned": True,
    }
