#!/usr/bin/env python3
"""
Voice Cloning Pipeline.
Connects to ElevenLabs Voice Cloning API to register Dad's recorded Cantonese audio,
creates the cloned voice profile, and caches the Voice ID in config/config.yaml.
"""

import os
import sys
import yaml
import requests
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
AUDIO_SAMPLES_DIR = PROJECT_ROOT / "assets" / "audio_samples"


def get_api_key():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Check environment variable first, then config
    api_key = os.environ.get("ELEVENLABS_API_KEY") or config.get("voice", {}).get("api_key", "")
    return api_key, config


def clone_dad_voice(sample_filename="dad_cantonese.wav"):
    api_key, config = get_api_key()
    sample_path = AUDIO_SAMPLES_DIR / sample_filename

    if not sample_path.exists():
        # Check alternative extensions
        for ext in [".wav", ".m4a", ".mp3", ".webm"]:
            alt = AUDIO_SAMPLES_DIR / f"dad_cantonese{ext}"
            if alt.exists():
                sample_path = alt
                break

    if not sample_path.exists():
        print(f"❌ Error: Audio sample not found at {sample_path}")
        return None

    file_size_kb = sample_path.stat().st_size / 1024
    print(f"🎙️ Found Dad's Audio Sample: {sample_path.name} ({file_size_kb:.1f} KB)")

    if not api_key:
        print("\n" + "=" * 70)
        print("🔑 ACTION NEEDED: ElevenLabs API Key")
        print("=" * 70)
        print("To complete voice cloning training, provide your ElevenLabs API Key.")
        print("You can get a free key at: https://elevenlabs.io/ (Profile -> API Keys)")
        print("\nYou can either:")
        print("1. Set it in your terminal: $env:ELEVENLABS_API_KEY='your_api_key'")
        print("2. Or add it to config/config.yaml under voice.api_key")
        print("=" * 70)
        return None

    print("🚀 Registering Dad's voice clone with ElevenLabs API...")
    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": api_key}

    # Determine MIME type
    suffix = sample_path.suffix.lower()
    mime_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg"
    }
    content_type = mime_map.get(suffix, "audio/wav")

    with open(sample_path, "rb") as f:
        files = {
            "files": (sample_path.name, f, content_type)
        }
        data = {
            "name": "Dad (Chi Shing) - Cantonese Parentese",
            "description": "Warm, animated parentese Cantonese voice for twin boys educational videos",
            "labels": '{"accent": "Hong Kong", "language": "yue", "gender": "male", "target": "kids"}'
        }
        response = requests.post(url, headers=headers, data=data, files=files)

    if response.status_code == 200:
        result = response.json()
        voice_id = result.get("voice_id")
        print(f"🎉 Voice clone created successfully! Voice ID: {voice_id}")

        # Update config.yaml
        config["voice"]["clones"]["dad_cantonese"]["voice_id"] = voice_id
        # Also map mom to dad's voice profile as requested
        config["voice"]["clones"]["mom_cantonese"]["voice_id"] = voice_id

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        print(f"Updated {CONFIG_PATH} with Voice ID.")
        return voice_id
    else:
        print(f"❌ Voice cloning request failed ({response.status_code}): {response.text}")
        return None


if __name__ == "__main__":
    clone_dad_voice()
