#!/usr/bin/env python3
"""
Master Orchestration CLI for the Personalized Cantonese & Mandarin Educational Video Pipeline.
Runs pipeline stages:
  1. auth: Verifies or establishes Google OAuth for Photos and YouTube
  2. styles: Lists and configures selected cartoon style
  3. voice-check: Validates Dad & Mom audio samples
  4. script: Displays and validates lesson scripts with Jyutping / Pinyin
  5. run-lesson: Coordinates end-to-end generation of a video lesson
"""

import os
import sys
import yaml
import argparse
from pathlib import Path

# Fix Windows console UTF-8 encoding for Chinese characters and emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.voice.audio_ingest import scan_all_samples


def load_config():
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_status():
    config = load_config()
    print("=" * 70)
    print("🎬 Cantonese & Mandarin Kids Video Pipeline - Status Overview")
    print("=" * 70)
    print(f"Target Audience: {config['project']['target_audience']}")
    print(f"Active Locale:   {config['project']['default_locale']}")
    print(f"Selected Style:  {config['visual_styles']['selected_style']}")
    print("-" * 70)

    # Check OAuth token
    token_path = PROJECT_ROOT / config['paths']['token_path']
    if token_path.exists():
        print("🔑 Google OAuth:   ✅ Authorized (token cached)")
    else:
        print("🔑 Google OAuth:   ⏳ Pending (Run: python src/auth/google_oauth.py)")

    # Check audio samples
    print("\n🎙️ Audio Samples Status:")
    scan_all_samples()

    # Check lessons
    lessons_dir = PROJECT_ROOT / "src" / "script" / "lessons"
    lessons = list(lessons_dir.glob("*.yaml"))
    print(f"\n📖 Available Lessons: {len(lessons)}")
    for l in lessons:
        print(f"  - {l.stem}")
    print("=" * 70)


def cmd_lesson(lesson_id: str, locale: str = "yue-Hant-HK"):
    config = load_config()
    lesson_file = PROJECT_ROOT / "src" / "script" / "lessons" / f"{lesson_id}.yaml"
    if not lesson_file.exists():
        print(f"Error: Lesson file not found: {lesson_file}")
        return

    with open(lesson_file, "r", encoding="utf-8") as f:
        lesson = yaml.safe_load(f)

    is_mandarin = locale.startswith("cmn") or locale.startswith("zh")
    print("=" * 70)
    print(f"Episode: {lesson['title_cantonese']} ({lesson['title_english']})")
    print(f"Target Duration: {lesson['duration_target_seconds']}s | Mode: {'Mandarin' if is_mandarin else 'Cantonese'}")
    print("=" * 70)

    for idx, scene in enumerate(lesson["scenes"], 1):
        speaker = scene["speaker"].upper()
        text = scene["mandarin_text"] if is_mandarin else scene["cantonese_text"]
        phonetic = scene["pinyin"] if is_mandarin else scene["jyutping"]
        vocab = scene.get("focus_vocab")

        print(f"\n[Scene {idx:02d}] ({scene['duration_sec']}s) Background: {scene['background']}")
        print(f"  Speaker: {speaker}")
        print(f"  Action:  {scene['action']}")
        print(f"  Dialogue: {text}")
        print(f"  Phonetics: {phonetic}")
        if vocab:
            if isinstance(vocab, list):
                words = ", ".join([f"{v['word']} ({v['meaning']})" for v in vocab])
            else:
                words = f"{vocab['word']} ({vocab['meaning']})"
            print(f"  Focus Vocab: {words}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kids Video Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show pipeline configuration and assets status")

    lesson_parser = subparsers.add_parser("preview-lesson", help="Preview lesson script")
    lesson_parser.add_argument("--id", default="lesson_01_meeting_family", help="Lesson ID")
    lesson_parser.add_argument("--locale", default="yue-Hant-HK", help="yue-Hant-HK or cmn-Hans-CN")

    args = parser.parse_args()

    if args.command == "preview-lesson":
        cmd_lesson(args.id, args.locale)
    else:
        cmd_status()
