#!/usr/bin/env python3
"""
Cantonese & Mandarin Infant-Directed TTS Engine.
Synthesizes speech using cloned voices or neural fallback with toddler-tailored pacing,
expressive pitch variations, and pause tags between vocabulary words.
"""

import os
import sys
import yaml
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


class TTSEngine:
    def __init__(self, config_path=CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.model_id = self.config["voice"].get("model_id", "eleven_multilingual_v2")
        self.voice_settings = self.config["voice"].get("voice_settings", {
            "stability": 0.55,
            "similarity_boost": 0.85,
            "style": 0.35,
            "use_speaker_boost": True
        })

    def synthesize(self, text: str, voice_profile_key: str = "dad_cantonese", output_filename: str = None) -> Path:
        """
        Synthesizes Cantonese or Mandarin audio for a given lesson line.
        """
        clones = self.config["voice"].get("clones", {})
        profile = clones.get(voice_profile_key, {})
        voice_id = profile.get("voice_id") or os.environ.get("DEFAULT_VOICE_ID", "")

        output_dir = PROJECT_ROOT / "assets" / "outputs" / "audio_clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        if not output_filename:
            safe_text = "".join([c for c in text[:10] if c.isalnum()])
            output_filename = f"{voice_profile_key}_{safe_text}.mp3"
        output_path = output_dir / output_filename

        if not self.api_key or not voice_id:
            print(f"Notice: ElevenLabs API Key or Voice ID not set. Generating mock audio timing marker for: '{text}'")
            # Create a placeholder silent audio or log for testing
            output_path.write_bytes(b"MOCK_MP3_AUDIO_HEADER" + b"\x00" * 4096)
            return output_path

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": self.voice_settings
        }

        print(f"Synthesizing [{voice_profile_key}]: {text}")
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Audio saved to: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"ElevenLabs TTS failed ({response.status_code}): {response.text}")


if __name__ == "__main__":
    engine = TTSEngine()
    test_line = "Hello 兩個BB！今日爸爸同你哋一齊玩啦！"
    path = engine.synthesize(test_line)
    print(f"Test generated at: {path}")
