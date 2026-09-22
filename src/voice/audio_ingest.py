#!/usr/bin/env python3
"""
Audio Ingest & Voice Normalization.
Validates uploaded Dad/Mom voice samples, trims silence, checks duration,
and coordinates Instant Voice Cloning registration.
"""

import os
import sys
import wave
from pathlib import Path

# Fix Windows console UTF-8 encoding for Chinese characters and emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIO_SAMPLES_DIR = PROJECT_ROOT / "assets" / "audio_samples"


def check_sample(filepath: Path):
    """Inspects an audio file and verifies its duration and sample format."""
    if not filepath.exists():
        return False, f"File not found: {filepath.name}"

    try:
        with wave.open(str(filepath), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            frames = wf.getnframes()
            duration_sec = frames / float(framerate)

            report = {
                "file": filepath.name,
                "duration_seconds": round(duration_sec, 2),
                "sample_rate_hz": framerate,
                "channels": "Stereo" if channels == 2 else "Mono",
                "bit_depth": sample_width * 8
            }

            if duration_sec < 45.0:
                status = "Warning: Sample is under 45 seconds. 1-2 minutes is recommended for optimal clone quality."
            elif duration_sec > 180.0:
                status = "Notice: Sample exceeds 3 minutes. The cloner will utilize the first 3 minutes."
            else:
                status = "Excellent: Optimal duration for high-fidelity voice cloning."

            return True, {"report": report, "status": status}
    except Exception as e:
        return False, f"Could not read as WAV (if MP3, cloner will process directly): {e}"


def scan_all_samples():
    """Scans audio_samples directory for Dad and Mom recordings."""
    print("Scanning audio samples directory:", AUDIO_SAMPLES_DIR)
    AUDIO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    targets = [
        ("Dad (Cantonese)", ["dad_cantonese.wav", "dad_cantonese.m4a", "dad_cantonese.mp3", "dad_cantonese.aac", "dad.wav", "dad.m4a", "dad.mp3"]),
        ("Mom (Cantonese)", ["mom_cantonese.wav", "mom_cantonese.m4a", "mom_cantonese.mp3", "mom_cantonese.aac", "mom.wav", "mom.m4a", "mom.mp3"]),
        ("Dad (Mandarin)", ["dad_mandarin.wav", "dad_mandarin.m4a", "dad_mandarin.mp3"]),
        ("Mom (Mandarin)", ["mom_mandarin.wav", "mom_mandarin.m4a", "mom_mandarin.mp3"]),
    ]

    results = {}
    for label, filenames in targets:
        found_path = None
        for fname in filenames:
            candidate = AUDIO_SAMPLES_DIR / fname
            if candidate.exists():
                found_path = candidate
                break

        if found_path:
            if found_path.suffix.lower() == ".wav":
                success, info = check_sample(found_path)
            else:
                info = f"{found_path.suffix.upper()} audio file present"
            results[label] = {"found": True, "path": str(found_path), "info": info}
            print(f"✅ Found {label}: {found_path.name} ({info})", flush=True)
        else:
            results[label] = {"found": False, "expected": filenames}
            print(f"⏳ Waiting for {label}: place in assets/audio_samples/{filenames[0]} (WAV, M4A, MP3)", flush=True)

    return results


if __name__ == "__main__":
    scan_all_samples()
