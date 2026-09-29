import os
import re
import subprocess
import threading
import copy
import hashlib
import json
import math
import shutil
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.services.audio_service import (
    get_audio_duration, media_binary, require_media_tools, missing_media_tool,
    resolve_project_audio, MAX_SCENE_SECONDS, MAX_EPISODE_SECONDS,
)
from app.services.sticker_service import get_or_render_sticker
from app.services.asset_manifest import resolve_sprite, resolve_background
from app.storage import (
    validate_id, project_path, project_operation,
    atomic_write_json, media_input_fingerprint,
)

JOBS = {}
_CONTROLS = {}
_JOBS_LOCK = threading.RLock()
_RENDER_SLOT = threading.BoundedSemaphore(1)
MAX_JOB_SECONDS = 1800
FPS = 30


class RenderBusyError(RuntimeError):
    pass


class RenderCancelled(RuntimeError):
    pass


class RenderPolicyError(ValueError):
    def __init__(self, code, message, project_id, scene_numbers=None, input_fingerprint=None):
        super().__init__(message)
        self.code = code
        self.project_id = project_id
        self.scene_numbers = scene_numbers or []
        self.input_fingerprint = input_fingerprint


def _update_job(job_id, **fields):
    with _JOBS_LOCK:
        JOBS[job_id].update(fields)
        job = dict(JOBS[job_id])
        atomic_write_json(project_path(job["project_id"], "jobs", f"render_{job_id}.json"), job)


def get_render_job(job_id, project_id=None):
    validate_id(job_id)
    with _JOBS_LOCK:
        if job_id in JOBS:
            job = dict(JOBS[job_id])
            if project_id and project_id != job["project_id"]:
                raise ValueError("Render belongs to another project")
            return job
    if not project_id:
        return {"status": "not_found", "progress": 0,
                "error": "Supply project_id to retrieve a job after server restart"}
    path = project_path(project_id, "jobs", f"render_{job_id}.json")
    if not path.is_file():
        return {"status": "not_found", "progress": 0}
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("status") in ("queued", "rendering"):
        job.update(status="error", error="Render interrupted by server restart; start a new render")
        atomic_write_json(path, job)
    return job


def cancel_render_job(job_id):
    with _JOBS_LOCK:
        control = _CONTROLS.get(job_id)
        if not control or JOBS[job_id]["status"] not in ("queued", "rendering"):
            return False
        control["cancel"].set()
        proc = control.get("proc")
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        return True


def _asset(path):
    if not path.is_file():
        raise ValueError(f"Approved stage asset is missing: {path.name}")
    return path


def _stage_asset(resolver, *identifiers):
    try:
        return _asset(resolver(*identifiers))
    except FileNotFoundError as exc:
        raise ValueError(f"Approved stage asset is missing: {' / '.join(identifiers)}") from exc


def _load_narration(project_data):
    attachment = project_data.get("narration")
    if attachment is None or attachment == {}:
        return None, None
    if not isinstance(attachment, dict) or not attachment.get("take_id"):
        raise ValueError("Select a valid narration take before rendering")
    from app.services.narration_service import validate_narration, narration_audio_path
    manifest = copy.deepcopy(validate_narration(project_data))
    project_id = project_data.get("id") or project_data.get("episode_id")
    take_id = validate_id(manifest["take_id"])
    path = Path(narration_audio_path(project_id, take_id))
    if not path.resolve().is_relative_to(project_path(project_id, "narration")):
        raise ValueError("Narration take belongs to another project")
    return manifest, path


def _file_digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _narration_frame_spans(manifest, scene_numbers, fps=FPS):
    """Quantize absolute boundaries once; pauses stay on screen, never disappear."""
    duration = float(manifest["duration_sec"])
    if not math.isfinite(duration) or not 120 <= duration <= 240:
        raise ValueError("Narration must span 120–240 seconds")
    entries = manifest.get("scenes")
    if not isinstance(entries, list) or len(entries) != len(scene_numbers):
        raise ValueError("Narration scenes do not match the current visual script")
    if [entry.get("scene_number") for entry in entries] != scene_numbers:
        raise ValueError("Narration scene order does not match the current script")
    previous_end = 0.0
    for entry in entries:
        start, end = float(entry["start_sec"]), float(entry["end_sec"])
        if not all(math.isfinite(t) for t in (start, end)) or start < previous_end - 1e-6 or not 0 <= start < end <= duration:
            raise ValueError("Narration scene timestamps are invalid or overlapping")
        previous_end = end
        words = entry.get("words", [])
        if not isinstance(words, list) or len(words) > 10000:
            raise ValueError("Invalid narration word timings")
        previous_word_end = start
        for word in words:
            word_start, word_end = float(word["start_sec"]), float(word["end_sec"])
            if not isinstance(word.get("text"), str) or not word["text"].strip() or len(word["text"]) > 1000:
                raise ValueError("Invalid narration word text")
            if not all(math.isfinite(t) for t in (word_start, word_end)) or not start <= word_start < word_end <= end + .02 or word_start < previous_word_end - .02:
                raise ValueError("Narration word timestamps are invalid or overlapping")
            previous_word_end = word_end
    boundaries = [0] + [math.ceil(float(entry["start_sec"]) * fps - 1e-9) for entry in entries[1:]]
    boundaries.append(math.ceil(duration * fps - 1e-9))
    if any(end <= start for start, end in zip(boundaries, boundaries[1:])):
        raise ValueError("Narration scene boundaries are too close to render")
    return list(zip(boundaries, boundaries[1:]))


def _legacy_scene_timeline(project_id, scenes, scene_numbers):
    timeline, spans = [], []
    missing_spoken, unvoiced = [], []
    has_voice = False
    elapsed = 0.0
    previous_frame = 0
    for number, scene in zip(scene_numbers, scenes):
        duration = float(scene.get("duration_sec", 6))
        if not math.isfinite(duration) or not 0 < duration <= MAX_SCENE_SECONDS:
            raise ValueError("Invalid scene duration")
        url = scene.get("audio_url")
        path = resolve_project_audio(project_id, url) if url else None
        text = scene.get("cantonese", "")
        if not isinstance(text, str):
            raise ValueError("Invalid scene cantonese")
        audio_duration = get_audio_duration(str(path)) if path else 0
        if path and audio_duration + 1.2 > duration + 1e-6:
            raise ValueError(f"Scene {number} requires at least {audio_duration + 1.2:.2f} seconds")
        if not path:
            unvoiced.append(number)
            if text.strip():
                missing_spoken.append(number)
        else:
            has_voice = True
        scene["_audio_path"] = str(path) if path else None
        timeline.append({"scene_number": number, "start_sec": elapsed,
                         "end_sec": elapsed + duration, "words": []})
        elapsed += duration
        end_frame = math.ceil(elapsed * FPS - 1e-9)
        if end_frame <= previous_frame:
            raise ValueError("Scene is too short to render")
        spans.append((previous_frame, end_frame))
        previous_frame = end_frame
    if elapsed > MAX_EPISODE_SECONDS:
        raise ValueError("Episode exceeds maximum duration")
    return {"take_id": None, "duration_sec": elapsed, "scenes": timeline,
            "alignment_method": "estimated",
            "missing_narration_scenes": missing_spoken if has_voice else unvoiced,
            "warnings": ["Legacy scene-clip mode: caption timings are estimated."]}, spans


def _narration_audio_options(project_data):
    options = project_data.get("audio_options")
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ValueError("Audio options must be an object")
    enabled = options.get("bgm_enabled", True)
    volume = options.get("bgm_volume", .025)
    if not isinstance(enabled, bool) or isinstance(volume, bool) or not isinstance(volume, (int, float)):
        raise ValueError("Backing enabled must be boolean and volume numeric")
    if not math.isfinite(volume) or not 0 <= volume <= .05:
        raise ValueError("Backing volume must be between 0 and 0.05")
    return {"bgm_enabled": enabled, "bgm_volume": float(volume)}


def validate_render_snapshot(project_data, *, silent_legacy_confirmed=False):
    if not isinstance(silent_legacy_confirmed, bool):
        raise ValueError("silent_legacy_confirmed must be a boolean request field")
    if not isinstance(project_data, dict):
        raise ValueError("Project snapshot must be an object")
    snapshot = copy.deepcopy(project_data)
    project_id = validate_id(snapshot.get("id") or snapshot.get("episode_id") or "")
    if snapshot.get("id") and snapshot.get("episode_id") and snapshot["id"] != snapshot["episode_id"]:
        raise ValueError("Project identifiers disagree")
    project_file = project_path(project_id, "project.json")
    if not project_file.is_file():
        raise ValueError("Save the project before rendering")
    try:
        saved = json.loads(project_file.read_text(encoding="utf-8"))
        narration_first = snapshot.get("workflow") == "narration_first" or saved.get("workflow") == "narration_first"
    except (OSError, ValueError, AttributeError) as exc:
        raise ValueError("Saved project could not be verified before rendering") from exc
    scenes = snapshot.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 100:
        raise ValueError("Render requires 1–100 scenes")
    scene_numbers = [scene.get("scene_number", index) if isinstance(scene, dict) else None
                     for index, scene in enumerate(scenes, 1)]
    if any(isinstance(number, bool) or not isinstance(number, int) or number < 1 for number in scene_numbers) or len(set(scene_numbers)) != len(scene_numbers):
        raise ValueError("Scene numbers must be unique positive integers")
    manifest, narration_path = _load_narration(snapshot)
    if manifest is None:
        if narration_first:
            raise RenderPolicyError(
                "narration_required", "This narration-first project requires a current narration take; silent rendering is not allowed.",
                project_id)
        manifest, spans = _legacy_scene_timeline(project_id, scenes, scene_numbers)
        snapshot["_audio_mode"] = "scene_clips"
        snapshot["_narration_audio_path"] = None
        snapshot["_narration_audio_sha256"] = None
    else:
        spans = _narration_frame_spans(manifest, scene_numbers, fps=FPS)
        snapshot["_audio_mode"] = "narration"
        if not narration_path.is_file():
            raise ValueError("Validated narration audio is missing")
        if abs(get_audio_duration(str(narration_path)) - float(manifest["duration_sec"])) > 1 / FPS:
            raise ValueError("Narration WAV duration does not match its manifest")
        digest = _file_digest(narration_path)
        if manifest.get("source_digest") != digest:
            raise ValueError("Narration audio changed during validation")
        snapshot["_narration_audio_path"] = str(narration_path)
        snapshot["_narration_audio_sha256"] = digest
    if manifest.get("alignment_method") not in ("asr", "estimated"):
        raise ValueError("Narration alignment method must be asr or estimated")
    warnings = manifest.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(warning, str) for warning in warnings):
        raise ValueError("Narration warnings must be a list of strings")
    if manifest["alignment_method"] == "estimated":
        warning = "Word timing is estimated, not ASR-aligned."
        if warning not in warnings:
            warnings.append(warning)
        manifest["warnings"] = warnings
    if snapshot["_audio_mode"] == "narration":
        snapshot["narration"] = copy.deepcopy(manifest)
    snapshot["_narration"] = manifest
    missing_narration = manifest.get("missing_narration_scenes", [])
    snapshot["_silent_legacy_confirmed"] = bool(silent_legacy_confirmed and missing_narration)
    snapshot["_missing_narration_scenes"] = missing_narration
    snapshot["_audio_options"] = _narration_audio_options(snapshot) if snapshot["_audio_mode"] == "narration" else None
    snapshot["_total_frames"] = spans[-1][1]
    snapshot["_fps"] = FPS
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError("Each scene must be an object")
        for field in ("cantonese", "english", "jyutping", "vocab_highlight", "speaker"):
            if not isinstance(scene.get(field, ""), str) or len(scene.get(field, "")) > 10000:
                raise ValueError(f"Invalid scene {field}")
        scene["_start_frame"], scene["_end_frame"] = spans[index - 1]
        scene["_caption_mode"] = snapshot["_audio_mode"]
        scene["_fps"] = FPS
        scene["_narration_scene"] = copy.deepcopy(manifest["scenes"][index - 1])
        background = validate_id(scene.get("background", "living_room"))
        scene["_background_path"] = str(_stage_asset(resolve_background, background))
        for key, limit in (("characters", 30), ("stickers", 50)):
            items = scene.get(key, [])
            if not isinstance(items, list) or len(items) > limit:
                raise ValueError(f"Invalid scene {key}")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"Invalid {key} entry")
                for field, default, low, high in (
                    ("scale", 1, 0.1, 4), ("x_percent", 50, 0, 100),
                    ("y_percent", 88 if key == "characters" else 24, 0, 100),
                    ("rotation_deg", item.get("rotation", 0), -360, 360),
                    ("layer", 1, -100, 100),
                ):
                    value = float(item.get(field, default))
                    if not math.isfinite(value) or not low <= value <= high:
                        raise ValueError(f"Invalid {key} {field}")
                if key == "characters":
                    item["_sprite_path"] = str(_stage_asset(
                        resolve_sprite, item.get("name", "levi"), item.get("pose", "default")))
                else:
                    # Only a local deterministic sticker renderer is used here.
                    sticker = dict(item)
                    sticker["id"] = validate_id(item.get("id") or item.get("sticker_id") or "badge_thank_you")
                    for text_field in ("content", "chinese", "english", "letter", "number", "icon"):
                        if not isinstance(sticker.get(text_field, ""), str) or len(sticker.get(text_field, "")) > 200:
                            raise ValueError("Invalid sticker content")
                    item["_sticker_path"] = str(_asset(Path(get_or_render_sticker(sticker))))
    options = snapshot.get("subtitle_options", {})
    if not isinstance(options, dict) or not isinstance(snapshot.get("caption_options", {}), dict):
        raise ValueError("Invalid subtitle/caption options")
    for name, default in (("font_size_cn", 52), ("font_size_en", 26)):
        value = int(options.get(name, default))
        if not 12 <= value <= 96:
            raise ValueError("Font sizes must be between 12 and 96")
    if missing_narration and snapshot["_audio_mode"] == "scene_clips":
        if not silent_legacy_confirmed:
            raise RenderPolicyError(
                "silent_legacy_confirmation_required",
                "Confirm rendering without narration for the listed legacy scenes. Existing recordings and background music will be retained.",
                project_id, missing_narration, media_input_fingerprint(project_data))
        manifest["warnings"].append(
            "Confirmed rendering without narration for scene(s): " + ", ".join(map(str, missing_narration))
            + ". Existing recordings and background music are retained.")
    return project_id, snapshot


def _freeze_assets(snapshot, workdir):
    cache = {}
    def freeze(path):
        if path is None:
            return None
        if path not in cache:
            source = Path(path)
            destination = workdir / f"{len(cache):04d}{source.suffix}"
            shutil.copyfile(source, destination)
            cache[path] = str(destination)
        return cache[path]
    if snapshot["_audio_mode"] == "narration":
        snapshot["_narration_audio_path"] = freeze(snapshot["_narration_audio_path"])
        if _file_digest(snapshot["_narration_audio_path"]) != snapshot["_narration_audio_sha256"]:
            raise ValueError("Narration audio changed while capturing the render snapshot")
        atomic_write_json(workdir / "narration.json", snapshot["_narration"])
    for scene in snapshot["scenes"]:
        scene["_background_path"] = freeze(scene["_background_path"])
        if snapshot["_audio_mode"] == "scene_clips":
            scene["_audio_path"] = freeze(scene["_audio_path"])
        for char in scene.get("characters", []):
            char["_sprite_path"] = freeze(char["_sprite_path"])
        for sticker in scene.get("stickers", []):
            sticker["_sticker_path"] = freeze(sticker["_sticker_path"])
    return snapshot


def _narration_identity(snapshot):
    if snapshot["_audio_mode"] != "narration":
        return None
    return {key: snapshot["_narration"].get(key) for key in
            ("take_id", "source_digest", "script_fingerprint", "alignment_method", "alignment_digest")}


def get_font(size: int, bold: bool = False):
    candidates = [
        os.environ.get("KIDS_STUDIO_CJK_FONT", ""),
        r"C:\Windows\Fonts\msjhbd.ttc" if bold else r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    raise RuntimeError("Install a Cantonese-capable CJK font or set KIDS_STUDIO_CJK_FONT")


def _split_caption_lines(text: str, max_chars: int = 10) -> list:
    """Split a Cantonese line into short singable phrases at punctuation."""
    if max_chars < 1:
        raise ValueError("Caption width must be positive")
    parts = re.split(r'[，。！？；：、,.!?;:\s]+', text or "")
    return [part[i:i + max_chars] for part in parts for i in range(0, len(part), max_chars)]


def _legacy_caption_timeline(scene, font, max_chars):
    lines = _split_caption_lines(scene.get("cantonese", ""), max_chars)
    if not lines:
        return []
    fps = scene["_fps"]
    duration = (scene["_end_frame"] - scene["_start_frame"]) / fps
    audio_duration = get_audio_duration(scene["_audio_path"]) if scene.get("_audio_path") else None
    span = min(duration, audio_duration) if audio_duration else duration - .6
    span = max(1 / fps, span)
    total_chars = sum(len(line) for line in lines)
    time_sec = scene["_start_frame"] / fps
    cues = []
    for line in lines:
        line_duration = span * len(line) / total_chars
        words = [{"text": char, "start_sec": time_sec + line_duration * i / len(line),
                  "end_sec": time_sec + line_duration * (i + 1) / len(line)}
                 for i, char in enumerate(line)]
        widths = [font.getlength(char) for char in line]
        cues.append({"start": time_sec, "end": time_sec + line_duration,
                     "words": words, "widths": widths, "total_w": sum(widths),
                     "font": font, "legacy": True})
        time_sec += line_duration
    return cues


def _build_scene_caption_timeline(scene: dict, font, max_chars=10) -> list:
    """Use take word timestamps, or preserve explicitly estimated legacy phrases."""
    if scene.get("_caption_mode") == "scene_clips":
        return _legacy_caption_timeline(scene, font, max_chars)
    cues, group = [], []
    count = 0
    for word in scene["_narration_scene"].get("words", []):
        text = word["text"]
        if group and (count + len(text) > max_chars or word["start_sec"] - group[-1]["end_sec"] > 0.75):
            cues.append(group)
            group, count = [], 0
        group.append({"text": text, "start_sec": word["start_sec"], "end_sec": word["end_sec"]})
        count += len(text)
    if group:
        cues.append(group)
    result = []
    for words in cues:
        cue_font = font
        total_width = sum(cue_font.getlength(word["text"]) for word in words)
        if total_width > 1600:
            cue_font = font.font_variant(size=max(1, math.floor(font.size * 1600 / total_width)))
        widths = [cue_font.getlength(word["text"]) for word in words]
        result.append({
            "start": words[0]["start_sec"], "end": words[-1]["end_sec"],
            "words": words, "widths": widths, "total_w": sum(widths), "font": cue_font,
        })
    return result


def _word_state(word, absolute_time):
    if absolute_time < word["start_sec"]:
        return "upcoming"
    if absolute_time < word["end_sec"]:
        return "active"
    return "spoken"

def render_project_video(project_data: dict, job_id: str, output_path: str):
    proc = None
    log = None
    control = _CONTROLS[job_id]
    workdir = Path(control["workdir"])
    complete = threading.Event()
    def watchdog():
        if not complete.wait(MAX_JOB_SECONDS):
            control["timed_out"] = True
            cancel_render_job(job_id)
    threading.Thread(target=watchdog, daemon=True).start()
    try:
        _update_job(job_id, status="rendering", progress=0)
        if control["cancel"].is_set():
            raise RenderCancelled("Render cancelled")
        scenes = project_data.get("scenes", [])
        narration = project_data["_narration"]
        render_warnings = list(narration.get("warnings", []))
        total_duration = float(narration["duration_sec"])
        fps = project_data["_fps"]
        width, height = 1920, 1080
        total_frames = project_data["_total_frames"]
        if project_data["_audio_mode"] == "narration":
            audio_path = project_data["_narration_audio_path"]
            if _file_digest(audio_path) != project_data["_narration_audio_sha256"]:
                raise ValueError("Frozen narration audio changed before encoding")
            from app.services.audio_service import mix_narration_with_bgm
            options = project_data["_audio_options"]
            mixed_path = workdir / "narration_mix.wav"
            mixed = mix_narration_with_bgm(audio_path, mixed_path,
                                          enabled=options["bgm_enabled"], volume=options["bgm_volume"])
            if abs(get_audio_duration(str(mixed_path)) - get_audio_duration(str(audio_path))) > 1 / 44100:
                raise ValueError("Narration backing changed the audio duration")
            audio_path = mixed_path
            backing = mixed["backing"]
            render_warnings.extend(mixed.get("warnings", []))
        else:
            from app.services.audio_service import mix_scene_audio
            audio_path = workdir / "master.wav"
            mix_scene_audio([scene["_audio_path"] for scene in scenes],
                            [(scene["_end_frame"] - scene["_start_frame"]) / fps for scene in scenes],
                            str(audio_path))
            backing = "legacy_synthesized"
        render_audio_digest = _file_digest(audio_path)
        if control["cancel"].is_set():
            raise RenderCancelled("Render cancelled")
        
        # 2. Setup FFmpeg pipe
        ffmpeg_cmd = [
            media_binary("ffmpeg"), "-n",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
        ]
        
        ffmpeg_cmd.extend(["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
                           "-c:a", "aac", "-b:a", "192k", "-t", f"{total_duration:.9f}"])
            
        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "22",
            output_path
        ])
        
        log = (workdir / "ffmpeg.log").open("wb")
        try:
            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        except FileNotFoundError as exc:
            raise missing_media_tool("ffmpeg") from exc
        with _JOBS_LOCK:
            control["proc"] = proc
        
        # Subtitle Options & Fonts
        sub_opts = project_data.get("subtitle_options", {})
        font_size_cn = int(sub_opts.get("font_size_cn", 52))
        font_size_en = int(sub_opts.get("font_size_en", 26))
        pill_style = sub_opts.get("pill_style", "warm_cream")

        font_chinese = get_font(font_size_cn, bold=True)
        font_english = get_font(font_size_en, bold=False)
        font_vocab = get_font(36, bold=True)
        font_jyutping = get_font(30, bold=False)
        font_karaoke = get_font(64, bold=True)

        # Sing-along caption timelines (karaoke). Toggle lives in the Render
        # step; default ON. When off, rendering follows the original path.
        caption_opts = project_data.get("caption_options", {})
        singalong_enabled = caption_opts.get("enabled", True)
        caption_timelines = []
        if singalong_enabled:
            for _scene in scenes:
                caption_timelines.append(
                    _build_scene_caption_timeline(_scene, font_karaoke)
                )
        
        frame_idx = 0
        
        # Cache loaded backgrounds and character sprites
        bg_cache = {}
        sprite_cache = {}
        
        def load_bg(bg_file):
            if bg_file in bg_cache:
                return bg_cache[bg_file]
            with Image.open(bg_file) as source:
                im = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            bg_cache[bg_file] = im
            return im

        def load_sprite(path):
            if path in sprite_cache:
                return sprite_cache[path]
            with Image.open(path) as source:
                im = source.convert("RGBA")
            sprite_cache[path] = im
            return im
            
        for s_idx, scene in enumerate(scenes):
            bg_base = load_bg(scene["_background_path"])
            
            chars = scene.get("characters", [])
            cantonese = scene.get("cantonese", "")
            jyutping = scene.get("jyutping", "")
            english = scene.get("english", "")
            vocab = scene.get("vocab_highlight", "")
            speaker = (scene.get("speaker") or "").lower()
            
            scene_frames = scene["_end_frame"] - scene["_start_frame"]
            
            # Speaker bias for Ken Burns subtle camera pan
            speaker_bias_x = 0.0
            if "dad" in speaker or any(c.get("name") == "dad" and c.get("x_percent", 50) < 40 for c in chars):
                speaker_bias_x = -0.08
            elif "mom" in speaker or any(c.get("name") == "mom" and c.get("x_percent", 50) > 60 for c in chars):
                speaker_bias_x = 0.08

            for f in range(scene_frames):
                if control["cancel"].is_set():
                    raise RenderCancelled("Render cancelled")
                time_sec = f / fps
                t_norm = f / max(1, scene_frames - 1)
                
                # 1. Ken Burns Smooth Camera Motion (Smoothstep 1.0x -> 1.07x push-in)
                ease = t_norm * t_norm * (3.0 - 2.0 * t_norm)
                cam_scale = 1.0 + 0.07 * ease
                bg_w = int(width * cam_scale)
                bg_h = int(height * cam_scale)
                bg_zoomed = bg_base.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
                crop_x = int((bg_w - width) * (0.5 + speaker_bias_x))
                crop_y = int((bg_h - height) * 0.5)
                crop_x = max(0, min(crop_x, bg_w - width))
                crop_y = max(0, min(crop_y, bg_h - height))
                frame = bg_zoomed.crop((crop_x, crop_y, crop_x + width, crop_y + height)).convert("RGB")

                # 2. Ukulele 116 BPM Downbeat Rhythmic Bounce & Squash
                # 116 BPM ~= 1.9333 Hz
                phase_bpm = 2.0 * np.pi * 1.9333 * time_sec
                bob_y = int(-abs(np.sin(phase_bpm / 2.0)) * 6.0)
                squash_y = 1.0 + 0.016 * np.sin(phase_bpm)
                squash_x = 1.0 / np.sqrt(max(0.7, squash_y))

                # 3. Build Unified Z-Sorted Render Queue
                render_queue = []
                for c in chars:
                    render_queue.append({
                        "type": "char",
                        "layer": int(c.get("layer", 1)),
                        "y": float(c.get("y_percent", 82.0)),
                        "data": c
                    })
                for s in scene.get("stickers", []):
                    render_queue.append({
                        "type": "sticker",
                        "layer": int(s.get("layer", 2)),
                        "y": float(s.get("y_percent", 24.0)),
                        "data": s
                    })
                render_queue.sort(key=lambda item: (item["layer"], item["y"]))

                for item in render_queue:
                    if item["type"] == "char":
                        c = item["data"]
                        c_name = c.get("name", "levi")
                        c_pose = c.get("pose", "default")
                        c_pos = c.get("position", "center")
                        sp = load_sprite(c["_sprite_path"])
                        if sp:
                            if c_name in ["dad", "mom", "grandparents_paternal", "grandparents_maternal", "auntie_cousins"]:
                                base_h = round(height * 0.72)
                            elif c_name in ["dog", "family_dog", "spitz"]:
                                base_h = round(height * 0.30)
                            else:
                                base_h = round(height * 0.50)
                            
                            c_scale = float(c.get("scale", 1.0))
                            target_h = int(base_h * c_scale * squash_y)
                            aspect = sp.width / sp.height
                            target_w = int(target_h * aspect * squash_x)
                            resized_sp = sp.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            
                            if c.get("flip"):
                                resized_sp = resized_sp.transpose(Image.FLIP_LEFT_RIGHT)

                            # Active Speaker Head Nod / Tilt
                            if c_name in speaker:
                                tilt_deg = float(1.8 * np.sin(2.0 * np.pi * 2.2 * time_sec))
                                resized_sp = resized_sp.rotate(tilt_deg, expand=True, resample=Image.Resampling.BICUBIC)
                                
                            if "x_percent" in c:
                                x = int(width * (float(c["x_percent"]) / 100.0) - resized_sp.width / 2)
                            elif c_pos == "left":
                                x = int(width * 0.30 - resized_sp.width / 2)
                            elif c_pos == "right":
                                x = int(width * 0.70 - resized_sp.width / 2)
                            else:
                                x = int(width * 0.50 - resized_sp.width / 2)
                                
                            if "y_percent" in c:
                                ground_y = int(height * (float(c["y_percent"]) / 100.0))
                            else:
                                ground_y = round(height * 0.88)
                            y = ground_y - resized_sp.height + bob_y
                            frame.paste(resized_sp, (x, y), resized_sp)

                    elif item["type"] == "sticker":
                        s = item["data"]
                        # 4. Elastic Squash-and-Stretch Pop-In Entrance
                        f_enter = int(fps * 0.35)
                        if f >= f_enter:
                            if f < f_enter + 18:
                                tau = (f - f_enter) / 18.0
                                # Damped harmonic spring: shoots up to 1.28x then settles
                                s_spring = 1.0 - np.exp(-7.0 * tau) * np.cos(14.0 * tau) + 0.35 * np.exp(-9.0 * tau) * np.sin(14.0 * tau)
                                pop_mult = max(0.01, float(s_spring))
                            else:
                                pop_mult = 1.0
                                
                            try:
                                st_path = s["_sticker_path"]
                                if st_path and os.path.exists(st_path):
                                    st_img = load_sprite(st_path)
                                    s_scale = float(s.get("scale", 1.0)) * pop_mult
                                    st_w = int(st_img.width * s_scale)
                                    st_h = int(st_img.height * s_scale)
                                    if st_w > 4 and st_h > 4:
                                        resized_st = st_img.resize((st_w, st_h), Image.Resampling.LANCZOS)
                                        # Secondary gentle floating
                                        float_y = int(4.0 * np.sin(2.0 * np.pi * 0.5 * time_sec))
                                        base_rot = float(s.get("rotation_deg", s.get("rotation", 0.0)))
                                        rot = base_rot + float(2.0 * np.cos(2.0 * np.pi * 0.4 * time_sec))
                                        if abs(rot) > 0.5:
                                            resized_st = resized_st.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                                        sx = int(width * (float(s.get("x_percent", 50.0)) / 100.0) - resized_st.width / 2)
                                        sy = int(height * (float(s.get("y_percent", 24.0)) / 100.0) - resized_st.height / 2) + float_y
                                        frame.paste(resized_st, (sx, sy), resized_st)
                            except Exception as exc:
                                raise RuntimeError("Approved sticker could not be rendered") from exc

                # 5. Forefront Subtitle Pill with Soft Fade In / Fade Out
                alpha_sub = min(1.0, f / 8.0)
                if f > scene_frames - 8:
                    alpha_sub = min(alpha_sub, max(0.0, (scene_frames - f) / 8.0))
                    
                if alpha_sub > 0.05:
                    box_y = height - 170 # 910px
                    sub_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    s_draw = ImageDraw.Draw(sub_overlay)
                    s_draw.rounded_rectangle([190, box_y + 8, width - 190, height - 22], radius=28, fill=(0, 0, 0, int(60 * alpha_sub)))
                    sub_overlay = sub_overlay.filter(ImageFilter.GaussianBlur(10))
                    frame.paste(sub_overlay, (0, 0), sub_overlay)

                    draw = ImageDraw.Draw(frame)
                    if pill_style == "translucent_dark":
                        pill_fill = (25, 25, 30, int(220 * alpha_sub))
                        pill_outline = (255, 255, 255, int(80 * alpha_sub))
                        text_cn_color = (255, 255, 255)
                        text_en_color = (220, 220, 220)
                    elif pill_style == "pastel_amber":
                        pill_fill = (255, 251, 235, int(245 * alpha_sub))
                        pill_outline = (245, 158, 11, int(220 * alpha_sub))
                        text_cn_color = (120, 53, 15)
                        text_en_color = (180, 83, 9)
                    else:  # warm_cream (default)
                        pill_fill = (255, 255, 255, int(240 * alpha_sub))
                        pill_outline = (245, 158, 11, int(180 * alpha_sub))
                        text_cn_color = (40, 35, 30)
                        text_en_color = (100, 100, 100)

                    draw.rounded_rectangle([200, box_y, width - 200, height - 30], radius=24, fill=pill_fill, outline=pill_outline, width=2)
                    
                    # Bilingual Subtitles (Clean Spoken Cantonese + English)
                    draw.text((width // 2, box_y + 22), cantonese, fill=text_cn_color, font=font_chinese, anchor="mt")
                    draw.text((width // 2, box_y + 82), english, fill=text_en_color, font=font_english, anchor="mt")
                    
                    # Top Vocab badge
                    if vocab:
                        left_occupied = any(float(c.get("x_percent", 50)) < 28 for c in chars)
                        if left_occupied:
                            draw.rounded_rectangle([width - 380, 50, width - 60, 140], radius=16, fill=(255, 248, 235), outline=(245, 158, 11), width=3)
                            draw.text((width - 220, 95), f"★ {vocab}", fill=(180, 83, 9), font=font_vocab, anchor="mm")
                        else:
                            draw.rounded_rectangle([60, 50, 380, 140], radius=16, fill=(255, 248, 235), outline=(245, 158, 11), width=3)
                            draw.text((220, 95), f"★ {vocab}", fill=(180, 83, 9), font=font_vocab, anchor="mm")

                # 5b. Sing-along karaoke captions (toddler-friendly, burned in).
                # Drawn above the subtitle pill; skipped entirely when toggled off.
                if singalong_enabled and s_idx < len(caption_timelines):
                    cues = caption_timelines[s_idx]
                    absolute_time = frame_idx / fps
                    active = next(
                        (c for c in cues if c["start"] <= absolute_time < c["end"]),
                        None,
                    )
                    if active:
                        cue_font = active["font"]
                        fade_seconds = .15 if active.get("legacy") else .05
                        fade = min(
                            1.0,
                            (absolute_time - active["start"]) / fade_seconds,
                            (active["end"] - absolute_time) / fade_seconds,
                        )
                        if fade > 0.05:
                            k_draw = ImageDraw.Draw(frame, "RGBA")
                            cy = 748  # sits above the subtitle pill
                            cx = width // 2 - active["total_w"] / 2
                            try:
                                _bbox = cue_font.getbbox("".join(word["text"] for word in active["words"]))
                                line_h = _bbox[3] - _bbox[1]
                            except Exception:
                                line_h = 64
                            # Soft backdrop for readability
                            k_draw.rounded_rectangle(
                                [cx - 36, cy - 22, cx + active["total_w"] + 36, cy + line_h + 22],
                                radius=32,
                                fill=(30, 20, 12, int(110 * fade)),
                            )
                            # Only words whose own absolute interval is active glow amber.
                            x = cx
                            for i, word in enumerate(active["words"]):
                                state = _word_state(word, absolute_time)
                                if active.get("legacy") and state == "spoken":
                                    state = "active"
                                color = {"active": (255, 176, 32), "spoken": (230, 205, 150),
                                         "upcoming": (255, 251, 235)}[state]
                                fill = (*color, int(255 * fade))
                                k_draw.text(
                                    (x, cy), word["text"], font=cue_font, fill=fill,
                                    stroke_width=3,
                                    stroke_fill=(40, 25, 10, int(220 * fade)),
                                    anchor="lt",
                                )
                                x += active["widths"][i]
                
                # Pipe to ffmpeg
                proc.stdin.write(frame.tobytes())
                frame_idx += 1
                
                if frame_idx % 30 == 0:
                    _update_job(job_id, progress=min(99, int((frame_idx / total_frames) * 100)))
        
        if frame_idx != total_frames:
            raise RuntimeError("Rendered frame count does not cover the complete narration timeline")
        proc.stdin.close()
        _verify_encoder_output(proc, output_path)
        with _JOBS_LOCK:
            if control["cancel"].is_set():
                raise RenderCancelled("Render cancelled")
            job = JOBS[job_id]
            artifact = {
                "status": "done", "project_id": job["project_id"],
                "filename": Path(output_path).name,
                "video_filename": Path(output_path).name,
                "video_url": f"/api/render/video/{job['project_id']}/{Path(output_path).name}",
                "input_fingerprint": job["input_fingerprint"],
                "caption_timing": narration["alignment_method"] if singalong_enabled else "disabled",
                "alignment_method": narration["alignment_method"],
                "audio_mode": project_data["_audio_mode"],
                "warnings": render_warnings,
                "narration_take_id": narration["take_id"],
                "narration_identity": _narration_identity(project_data),
                "narration_audio_sha256": project_data["_narration_audio_sha256"],
                "render_audio_sha256": render_audio_digest,
                "audio_options": project_data["_audio_options"],
                "backing": backing,
                "silent_legacy_confirmed": project_data["_silent_legacy_confirmed"],
                "missing_narration_scenes": project_data["_missing_narration_scenes"],
                "duration_sec": total_duration,
                "frame_count": total_frames,
                "fps": fps,
                "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            atomic_write_json(Path(str(output_path) + ".json"), artifact)
            _update_job(job_id, **artifact, progress=100)
    except Exception as e:
        cancelled = control["cancel"].is_set()
        message = "Render exceeded the 30-minute limit" if control.get("timed_out") else (
            "Render cancelled" if cancelled else str(e))
        _update_job(job_id, status="cancelled" if cancelled and not control.get("timed_out") else "error",
                    error=message)
    finally:
        complete.set()
        try:
            if proc is not None:
                try:
                    if proc.poll() is None:
                        proc.kill()
                    proc.wait(timeout=10)
                finally:
                    if proc.stdin and not proc.stdin.closed:
                        try:
                            proc.stdin.close()
                        except OSError:
                            pass
            if log is not None:
                log.close()
            if JOBS[job_id]["status"] != "done":
                Path(output_path).unlink(missing_ok=True)
                Path(str(output_path) + ".json").unlink(missing_ok=True)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
            with _JOBS_LOCK:
                _CONTROLS.pop(job_id, None)
            try:
                operation = control.pop("operation", None)
                if operation is not None:
                    operation.__exit__(None, None, None)
            finally:
                _RENDER_SLOT.release()


def _verify_encoder_output(proc, output_path):
    result = proc.wait(timeout=60)
    if result != 0:
        raise RuntimeError(f"FFmpeg failed with exit code {result}")
    path = Path(output_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("FFmpeg produced no usable output")


def start_render_job(project_data: dict, job_id: str, *, silent_legacy_confirmed=False):
    validate_id(job_id)
    if not _RENDER_SLOT.acquire(blocking=False):
        raise RenderBusyError("Another render is active; wait or cancel it before starting another")
    workdir = None
    operation = None
    operation_entered = False
    started = False
    try:
        require_media_tools("ffmpeg")
        with _JOBS_LOCK:
            if job_id in JOBS:
                raise ValueError("Render identifier already exists")
        original = copy.deepcopy(project_data)
        project_id = validate_id(original.get("id") or original.get("episode_id") or "")
        operation = project_operation(project_id)
        operation.__enter__()
        operation_entered = True
        project_id, snapshot = validate_render_snapshot(original, silent_legacy_confirmed=silent_legacy_confirmed)
        original["id"] = original["episode_id"] = project_id
        if snapshot["_audio_mode"] == "narration":
            original["narration"] = copy.deepcopy(snapshot["narration"])
        filename = f"episode_{job_id}.mp4"
        output_path = project_path(project_id, "renders", filename)
        if output_path.exists():
            raise ValueError("Render output already exists")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        workdir = project_path(project_id, "renders", f".job_{job_id}")
        workdir.mkdir()
        snapshot = _freeze_assets(snapshot, workdir)
        fingerprint = media_input_fingerprint(original)
        atomic_write_json(Path(str(output_path) + ".input.json"), original)
        if snapshot["_audio_mode"] == "narration":
            atomic_write_json(Path(str(output_path) + ".narration.json"), snapshot["_narration"])
        with _JOBS_LOCK:
            # Disk records remain available through project-scoped status queries.
            for old in list(JOBS):
                if len(JOBS) < 100:
                    break
                if old not in _CONTROLS:
                    JOBS.pop(old)
            JOBS[job_id] = {"job_id": job_id, "project_id": project_id,
                            "status": "queued", "progress": 0, "error": None,
                            "input_fingerprint": fingerprint,
                            "narration_take_id": snapshot["_narration"]["take_id"],
                            "narration_identity": _narration_identity(snapshot),
                            "alignment_method": snapshot["_narration"]["alignment_method"],
                            "audio_mode": snapshot["_audio_mode"],
                            "audio_options": snapshot["_audio_options"],
                            "silent_legacy_confirmed": snapshot["_silent_legacy_confirmed"],
                            "missing_narration_scenes": snapshot["_missing_narration_scenes"],
                            "warnings": snapshot["_narration"].get("warnings", []),
                            "duration_sec": snapshot["_narration"]["duration_sec"],
                            "frame_count": snapshot["_total_frames"], "fps": FPS}
            _CONTROLS[job_id] = {"cancel": threading.Event(), "proc": None, "workdir": str(workdir),
                                "operation": operation}
        _update_job(job_id)
        thread = threading.Thread(target=render_project_video,
                                  args=(snapshot, job_id, str(output_path)), daemon=True)
        thread.start()
        started = True
        return get_render_job(job_id)
    except Exception:
        if started:
            raise
        if workdir is not None:
            shutil.rmtree(workdir, ignore_errors=True)
        with _JOBS_LOCK:
            _CONTROLS.pop(job_id, None)
            JOBS.pop(job_id, None)
        try:
            if operation_entered:
                operation.__exit__(None, None, None)
        finally:
            _RENDER_SLOT.release()
        raise
