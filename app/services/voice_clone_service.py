"""Explicit parent-voice synthesis. Provider errors never select another voice."""
import asyncio
import base64
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

import requests

from app.config import load_settings
from app import storage
from app.storage import ROOT, PROJECTS_DIR, atomic_write_json, project_path, project_operation
from app.services.audio_service import (
    get_audio_duration, normalize_audio, run_blocking, scene_duration, run_media_command,
    require_media_tools, MAX_SCENE_SECONDS,
)

GEMINI_VOICES_URL = "https://generativelanguage.googleapis.com/v1beta/voices"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
TTS_MODEL = "gemini-3.8-flash-tts"
CONSENT_STATEMENT_EN_US = (
    "I am the owner of this voice and I consent to Google using this voice "
    "to create a synthetic voice model."
)
CONSENT_STATEMENT_ZH_CN = "我是此声音的拥有者并授权谷歌使用此声音创建语音合成模型"
_VOICES_LOCK = threading.RLock()


class VoiceCloneUnavailableError(RuntimeError):
    pass


class VoiceProfileError(ValueError):
    def __init__(self, code, message, http_status=400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def get_gemini_api_key():
    return (load_settings().gemini_api_key or "").strip()


def is_voice_clone_available():
    """Configuration only, not a successful capability/provider probe."""
    return bool(get_gemini_api_key())


def _require_api_key():
    key = get_gemini_api_key()
    if not key:
        raise VoiceCloneUnavailableError("Parent voice is not configured. No substitute voice was generated.")
    return key


def _headers(key):
    return {"x-goog-api-key": key, "Content-Type": "application/json"}


def _cloned_voices_path():
    # Default storage is ROOT, preserving the old registry in place. An explicitly
    # isolated DATA_DIR must never fall back to another installation's voice profiles.
    return storage.contained_path(storage.DATA_DIR, "config", "cloned_voices.json")


def list_cloned_voices():
    path = _cloned_voices_path()
    with _VOICES_LOCK:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, list) or any(not isinstance(v, dict) for v in data):
            raise ValueError("Stored voice profiles are invalid")
        return data


def save_cloned_voice(voice_id, name, sample, *, verified_metadata=None):
    record = {"voice_id": voice_id, "name": name, "sample": sample,
              "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if verified_metadata:
        record.update(verified_metadata)
    with _VOICES_LOCK:
        voices = [v for v in list_cloned_voices() if v.get("voice_id") != voice_id]
        voices.append(record)
        atomic_write_json(_cloned_voices_path(), voices)
    return record


def _stored_voice_id(voice_id):
    if not isinstance(voice_id, str) or not re.fullmatch(r"voice_[A-Za-z0-9_-]{1,94}", voice_id):
        raise VoiceProfileError("voice_id_invalid",
                                "Enter a stored voice_… ID from Google AI Studio, not a URL or voicekey_… key.")
    return voice_id


def _read_google_voices(path="", *, params=None):
    key = _require_api_key()
    try:
        response = requests.get(
            GEMINI_VOICES_URL + path, headers=_headers(key), params=params,
            timeout=(10, 30), allow_redirects=False,
        )
    except requests.exceptions.Timeout:
        raise VoiceProfileError("voice_lookup_timeout",
                                "Google voice lookup timed out. No voice was created or imported.", 504) from None
    except requests.exceptions.RequestException:
        raise VoiceProfileError("voice_lookup_unavailable",
                                "Could not reach Google Voices. No voice was created or imported.", 502) from None
    messages = {
        401: ("voice_lookup_authentication", "Google rejected the saved API key. Check Settings.", 401),
        403: ("voice_lookup_forbidden", "This API key cannot access the selected Google voice/project.", 403),
        404: ("voice_not_found", "No stored voice was found with that ID under the configured Google project.", 404),
        429: ("voice_lookup_rate_limited", "Google voice lookup is rate-limited. Try again later.", 429),
    }
    if response.status_code in messages:
        raise VoiceProfileError(*messages[response.status_code])
    if response.status_code != 200:
        raise VoiceProfileError("voice_lookup_unavailable", "Google Voices lookup failed; nothing was imported.", 502)
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except ValueError:
        raise VoiceProfileError("voice_response_invalid", "Google returned an unsupported voice response.", 502) from None


def _verified_profile(data, requested_id=None):
    voice_id = data.get("id") or data.get("voice_id")
    if not voice_id and isinstance(data.get("name"), str) and data["name"].startswith("voices/"):
        voice_id = data["name"][len("voices/"):]
    try:
        voice_id = _stored_voice_id(voice_id)
    except VoiceProfileError:
        raise VoiceProfileError("voice_response_invalid", "Google returned no supported stored voice ID.", 502) from None
    if requested_id is not None and voice_id != requested_id:
        raise VoiceProfileError("voice_response_mismatch", "Google returned a different voice ID; nothing was imported.", 502)
    if data.get("type") != "replicated":
        raise VoiceProfileError("voice_not_replicated", "Select an existing replicated voice, not a stock or prompted voice.")
    display_name = data.get("display_name", data.get("displayName", ""))
    if not isinstance(display_name, str) or len(display_name) > 500:
        raise VoiceProfileError("voice_response_invalid", "Google returned invalid voice metadata.", 502)
    return {"voice_id": voice_id, "provider": "google", "voice_type": "replicated",
            "provider_display_name": display_name}


def import_cloned_voice(voice_id, name="Dad"):
    voice_id = _stored_voice_id(voice_id)
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise VoiceProfileError("voice_name_invalid", "Give this local voice a name of 1–100 characters.")
    # Verify even when already saved; caller-supplied IDs are never trusted as profiles.
    verified = _verified_profile(_read_google_voices("/" + voice_id), voice_id)
    verified.update(verified_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    verification="google_voices_get", profile_verified=True,
                    capability_verified=False)
    record = save_cloned_voice(
        voice_id, name.strip(), "Imported existing Google replicated profile; no voice was created.",
        verified_metadata=verified,
    )
    return {"status": "imported", "voice": record,
            "warnings": ["Profile access/type verified. Speaker identity and Cantonese synthesis quality are not verified."]}


def discover_cloned_voices():
    data = _read_google_voices(params={"type": "replicated"})
    profiles = data.get("voices", [])
    if not isinstance(profiles, list) or len(profiles) > 200 or any(not isinstance(p, dict) for p in profiles):
        raise VoiceProfileError("voice_response_invalid", "Google returned an unsupported voice list.", 502)
    voices = [_verified_profile(p) for p in profiles if p.get("type") == "replicated"]
    return {"voices": voices, "source": "google", "imported": False,
            "has_more": bool(data.get("next_page_token") or data.get("nextPageToken")),
            "warnings": ["Discovery does not save a profile. Import a selected voice to verify it again."]}


def default_sample_path():
    return str(ROOT / "assets" / "audio_samples" / "dad_cantonese.mp3")


def _prepare_reference_wav(src_path, workdir):
    duration = get_audio_duration(src_path)
    if duration < 10:
        raise ValueError("Reference audio must contain at least 10 seconds")
    out_path = Path(workdir) / "reference_24k.wav"
    command = ["-nostdin", "-n", "-i", str(src_path)]
    if duration > 30:
        command += ["-ss", str((duration - 30) / 2), "-t", "30"]
    command += ["-vn", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out_path)]
    result = run_media_command("ffmpeg", command, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError("Reference audio conversion failed")
    return str(out_path)


def _prepare_consent_wav(src_path, workdir):
    if get_audio_duration(src_path) > 120:
        raise ValueError("Consent recording exceeds 120 seconds")
    out_path = Path(workdir) / "consent_24k.wav"
    result = run_media_command(
        "ffmpeg", ["-nostdin", "-n", "-i", str(src_path), "-vn", "-ar", "24000",
         "-ac", "1", "-c:a", "pcm_s16le", str(out_path)],
        capture_output=True, timeout=120,
    )
    if result.returncode:
        raise RuntimeError("Consent audio conversion failed")
    return str(out_path)


def _b64_file(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def create_cloned_voice(sample_path=None, consent_path=None, name="Dad"):
    api_key = _require_api_key()
    if not sample_path or not Path(sample_path).is_file():
        raise ValueError("Upload the selected adult speaker's reference recording")
    if not consent_path or not Path(consent_path).is_file():
        raise ValueError("The same adult speaker's consent recording is required")
    require_media_tools("ffmpeg", "ffprobe")
    workdir = PROJECTS_DIR.parent / "voice_work" / uuid.uuid4().hex
    workdir.mkdir(parents=True)
    try:
        ref_wav = _prepare_reference_wav(sample_path, workdir)
        consent_wav = _prepare_consent_wav(consent_path, workdir)
        payload = {"store": True, "voice": {
            "model": TTS_MODEL, "type": "replicated",
            "display_name": f"{name} - Cantonese Kids Studio",
            "replicated": {
                "source_audio": {"mime_type": "audio/wav", "data": _b64_file(ref_wav)},
                "consent_audio": {"mime_type": "audio/wav", "data": _b64_file(consent_wav)},
            },
        }}
        response = requests.post(GEMINI_VOICES_URL, headers=_headers(api_key), json=payload, timeout=180)
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"Voice creation failed (HTTP {response.status_code}); no voice was substituted")
        voice_id = _parse_voice_id(response.json(), "")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    save_cloned_voice(voice_id, name, "user-uploaded reference; temporary copy deleted")
    return {"status": "success", "voice_id": voice_id, "name": name}


def _parse_voice_id(data, raw_text=""):
    voice_id = data.get("id") or data.get("voice_id")
    if not voice_id and isinstance(data.get("name"), str):
        voice_id = data["name"].split("/")[-1]
    if not voice_id:
        voice_id = (data.get("replicated_voice") or {}).get("id")
    if not isinstance(voice_id, str) or not voice_id.startswith("voice"):
        raise RuntimeError("Provider returned no supported voice identifier")
    return voice_id


def _extract_audio_b64(payload):
    candidates = [
        item["data"] for step in payload.get("steps", []) or []
        for item in step.get("content", []) or []
        if isinstance(item, dict) and item.get("type") == "audio" and item.get("data")
    ]
    if not candidates and isinstance(payload.get("output_audio"), dict):
        candidates = [payload["output_audio"].get("data")]
    if len(candidates) != 1 or not candidates[0]:
        raise RuntimeError("Provider returned missing or multipart audio; refusing an incomplete narration")
    return candidates[0]


async def generate_cloned_tts(text, voice_id, output_wav_path,
                              style="warm and gentle, speaking slowly to young children in Hong Kong Cantonese",
                              *, max_seconds=None, timeout=120):
    if not text.strip() or not voice_id:
        raise ValueError("Narration text and selected parent voice are required")
    api_key = _require_api_key()
    require_media_tools("ffmpeg", "ffprobe")
    payload = {
        "model": TTS_MODEL,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": text,
            "annotations": [{"type": "speech_metadata", "style": style}],
        }]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice_id}]},
    }
    response = await run_blocking(
        requests.post, GEMINI_INTERACTIONS_URL, headers=_headers(api_key), json=payload, timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Parent voice synthesis failed (HTTP {response.status_code}); no substitute was generated")
    encoded = _extract_audio_b64(response.json())
    if not isinstance(encoded, str) or len(encoded) > 160 * 1024 * 1024:
        raise RuntimeError("Provider audio exceeds the supported response size")
    audio_bytes = base64.b64decode(encoded, validate=True)
    output = Path(output_wav_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_name(f"{uuid.uuid4().hex}.source")
    try:
        source.write_bytes(audio_bytes)
        await run_blocking(normalize_audio, source, output,
                           max_seconds=MAX_SCENE_SECONDS - 1.2 if max_seconds is None else max_seconds)
    finally:
        source.unlink(missing_ok=True)
    return str(output)


def synthesize_story_cloned_voice(text, voice_id, output_path, style):
    """One provider operation; an uncertain timeout is never automatically retried."""
    if not text.strip() or len(text) > 12000:
        raise ValueError("Whole-story narration must contain 1–12000 characters")
    if not any(v.get("voice_id") == voice_id for v in list_cloned_voices()):
        raise ValueError("Select a saved parent voice before generating narration")
    return asyncio.run(generate_cloned_tts(
        text, voice_id, str(output_path), style=style, max_seconds=1800, timeout=300,
    ))


def synthesize_scene_cloned_voice(scene_idx, text, voice_id, *, project_id, duration_sec=6):
    with project_operation(project_id):
        filename = f"{uuid.uuid4().hex}.wav"
        out_path = project_path(project_id, "audio", filename)
        asyncio.run(generate_cloned_tts(text, voice_id, str(out_path)))
        duration = get_audio_duration(str(out_path))
        return {
            "status": "success", "project_id": project_id, "scene_idx": scene_idx,
            "filename": filename, "audio_url": f"/api/audio/clip/{project_id}/{filename}",
            "duration": duration, "duration_sec": scene_duration(duration_sec, duration),
            "voice_id": voice_id, "cloned": True,
            "voice_provenance": {"kind": "cloned", "provider": "gemini", "voice_id": voice_id,
                                 "requested_language": "yue-HK"},
        }
