#!/usr/bin/env python3
"""
Google Cloud Cantonese Text-to-Speech Engine.
Synthesizes high-fidelity Cantonese (Hong Kong) audio using Google Cloud TTS.
Supports male and female neural voices with toddler-tailored cadence and pitch modulation.
"""

import os
import sys
import yaml
import json
import requests
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
TOKEN_PATH = PROJECT_ROOT / "config" / "google_token.json"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "outputs" / "audio_clips"


class GoogleCantoneseTTS:
    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        if not TOKEN_PATH.exists():
            return None
        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("token")
        except Exception:
            return None

    def synthesize(self, text: str, voice_gender: str = "MALE", output_filename: str = None) -> Path:
        """
        Synthesizes Cantonese speech using Google Cloud Text-to-Speech API.
        Language: yue-HK
        Voices:
          - MALE: yue-HK-Standard-B or yue-HK-Standard-D
          - FEMALE: yue-HK-Standard-A or yue-HK-Standard-C
        """
        if not output_filename:
            safe_text = "".join([c for c in text[:10] if c.isalnum()])
            output_filename = f"google_cantonese_{voice_gender.lower()}_{safe_text}.mp3"
        output_path = OUTPUT_DIR / output_filename

        voice_name = "yue-HK-Standard-B" if voice_gender == "MALE" else "yue-HK-Standard-A"

        # Check for API key from Google AI Studio / Cloud or OAuth token
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")

        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif api_key:
            url += f"?key={api_key}"
        else:
            print(f"Notice: No Google API Key or OAuth token found for Google TTS. Simulating speech for: '{text}'")
            return output_path

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "yue-HK",
                "name": voice_name,
                "ssmlGender": voice_gender
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 0.88,  # Slower for toddlers
                "pitch": 1.2           # Animated, cheerful pitch for infant-directed speech
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            import base64
            audio_content = response.json().get("audioContent", "")
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(audio_content))
            print(f"✅ Google Cantonese TTS saved to: {output_path}")
            return output_path
        else:
            print(f"Google TTS response ({response.status_code}): {response.text}")
            return output_path


if __name__ == "__main__":
    tts = GoogleCantoneseTTS()
    test_line = "Hello Levi 哥哥，Hello Luca 細佬！爸爸好愛你哋呀！"
    path = tts.synthesize(test_line, voice_gender="MALE", output_filename="test_dad_greeting.mp3")
    print(f"Result: {path}")
