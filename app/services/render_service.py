import os
import re
import subprocess
import threading
import copy
import json
import math
import shutil
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.services.audio_service import (
    mix_scene_audio, get_audio_duration, resolve_project_audio, MAX_EPISODE_SECONDS,
    MAX_SCENE_SECONDS, media_binary, require_media_tools, missing_media_tool,
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


class RenderBusyError(RuntimeError):
    pass


class RenderCancelled(RuntimeError):
    pass


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


def validate_render_snapshot(project_data):
    if not isinstance(project_data, dict):
        raise ValueError("Project snapshot must be an object")
    snapshot = copy.deepcopy(project_data)
    project_id = validate_id(snapshot.get("id") or snapshot.get("episode_id") or "")
    if snapshot.get("id") and snapshot.get("episode_id") and snapshot["id"] != snapshot["episode_id"]:
        raise ValueError("Project identifiers disagree")
    if not project_path(project_id, "project.json").is_file():
        raise ValueError("Save the project before rendering")
    scenes = snapshot.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 100:
        raise ValueError("Render requires 1–100 scenes")
    total = 0
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError("Each scene must be an object")
        duration = float(scene.get("duration_sec", 6))
        if not math.isfinite(duration) or not 0 < duration <= MAX_SCENE_SECONDS:
            raise ValueError("Invalid scene duration")
        duration = math.ceil(duration * 30) / 30
        total += duration
        for field in ("cantonese", "english", "jyutping", "vocab_highlight", "speaker"):
            if not isinstance(scene.get(field, ""), str) or len(scene.get(field, "")) > 10000:
                raise ValueError(f"Invalid scene {field}")
        audio_url = scene.get("audio_url")
        if audio_url:
            path = resolve_project_audio(project_id, audio_url)
            audio_duration = get_audio_duration(str(path))
            if audio_duration + 1.2 > duration + 1e-6:
                raise ValueError(f"Scene {index} requires at least {math.ceil(audio_duration + 1.2)} seconds for its narration")
            scene["_audio_path"] = str(path)
        elif scene.get("cantonese", "").strip():
            raise ValueError(f"Scene {index} has narration text but no approved audio")
        else:
            scene["_audio_path"] = None
        scene["duration_sec"] = duration
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
    if total > MAX_EPISODE_SECONDS:
        raise ValueError("Episode exceeds maximum duration")
    options = snapshot.get("subtitle_options", {})
    if not isinstance(options, dict) or not isinstance(snapshot.get("caption_options", {}), dict):
        raise ValueError("Invalid subtitle/caption options")
    for name, default in (("font_size_cn", 52), ("font_size_en", 26)):
        value = int(options.get(name, default))
        if not 12 <= value <= 96:
            raise ValueError("Font sizes must be between 12 and 96")
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
    for scene in snapshot["scenes"]:
        for key in ("_audio_path", "_background_path"):
            scene[key] = freeze(scene[key])
        for char in scene.get("characters", []):
            char["_sprite_path"] = freeze(char["_sprite_path"])
        for sticker in scene.get("stickers", []):
            sticker["_sticker_path"] = freeze(sticker["_sticker_path"])
    return snapshot

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


# ---------------------------------------------------------------------------
# Sing-along karaoke captions.
# Each scene's Cantonese line is split into short singable phrases. Timing
# prefers the real narration (scene <-> audio-clip pairing the pipeline
# already produces); when a clip's duration is unknown we fall back to
# distributing phrases evenly across the scene duration, weighted by length.
# ---------------------------------------------------------------------------

def _split_caption_lines(text: str, max_chars: int = 10) -> list:
    """Split a Cantonese line into short singable phrases at punctuation."""
    if max_chars < 1:
        raise ValueError("Caption width must be positive")
    parts = re.split(r'[，。！？；：、,.!?;:\s]+', text or "")
    return [part[i:i + max_chars] for part in parts for i in range(0, len(part), max_chars)]


def _build_scene_caption_timeline(scene: dict, project_root: str, font) -> list:
    """
    Returns a list of caption cues for one scene:
    [{"start", "end", "chars", "widths", "total_w"}].
    """
    text = (scene.get("cantonese") or "").strip()
    if not text:
        return []
    lines = _split_caption_lines(text)
    if not lines:
        return []

    duration = float(scene.get("duration_sec", 6))

    # Prefer real narration timing: resolve this scene's voice clip and read
    # its actual duration, clamped to the scene length.
    audio_dur = get_audio_duration(scene["_audio_path"]) if scene.get("_audio_path") else None

    if audio_dur and audio_dur > 0:
        span = min(duration, audio_dur)
    else:
        span = duration - 0.6
    span = max(1 / 30, span)

    lead_in = 0.0
    total_chars = max(1, sum(len(l) for l in lines))
    timeline = []
    t = lead_in
    for line in lines:
        line_dur = span * (len(line) / total_chars)
        chars = list(line)
        try:
            widths = [font.getlength(ch) for ch in chars]
        except Exception:
            widths = [font.size * 0.9] * len(chars)
        timeline.append({
            "start": t,
            "end": t + line_dur,
            "chars": chars,
            "widths": widths,
            "total_w": sum(widths),
        })
        t += line_dur
    return timeline

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
        total_duration = sum(s.get("duration_sec", 6) for s in scenes)
        fps = 30
        width, height = 1920, 1080
        total_frames = sum(round(s["duration_sec"] * fps) for s in scenes)
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 1. Dynamically gather scene voice recordings and mix master audio with ukulele BGM
        voice_paths = [s["_audio_path"] for s in scenes]
        durations = [s["duration_sec"] for s in scenes]
        audio_path = workdir / "master.wav"
        mix_scene_audio(voice_paths, durations, str(audio_path))
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
        
        ffmpeg_cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-b:a", "192k"])
            
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
                    _build_scene_caption_timeline(_scene, project_root, font_karaoke)
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
            
            scene_duration = scene.get("duration_sec", 6)
            scene_frames = round(scene_duration * fps)
            
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
                    scene_elapsed = f / fps
                    active = next(
                        (c for c in cues if c["start"] <= scene_elapsed < c["end"]),
                        None,
                    )
                    if active:
                        fade = min(
                            1.0,
                            (scene_elapsed - active["start"]) / 0.15,
                            (active["end"] - scene_elapsed) / 0.15,
                        )
                        if fade > 0.05:
                            n_chars = len(active["chars"])
                            progress = (scene_elapsed - active["start"]) / max(
                                0.001, active["end"] - active["start"]
                            )
                            lit_count = progress * n_chars

                            k_draw = ImageDraw.Draw(frame, "RGBA")
                            cy = 748  # sits above the subtitle pill
                            cx = width // 2 - active["total_w"] / 2
                            try:
                                _bbox = font_karaoke.getbbox("".join(active["chars"]))
                                line_h = _bbox[3] - _bbox[1]
                            except Exception:
                                line_h = 64
                            # Soft backdrop for readability
                            k_draw.rounded_rectangle(
                                [cx - 36, cy - 22, cx + active["total_w"] + 36, cy + line_h + 22],
                                radius=32,
                                fill=(30, 20, 12, int(110 * fade)),
                            )
                            # Karaoke: sung chars glow amber, upcoming chars stay cream
                            x = cx
                            for i, ch in enumerate(active["chars"]):
                                sung = i < lit_count
                                fill = (
                                    (255, 176, 32, int(255 * fade))
                                    if sung
                                    else (255, 251, 235, int(255 * fade))
                                )
                                k_draw.text(
                                    (x, cy), ch, font=font_karaoke, fill=fill,
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
                "caption_timing": "estimated" if singalong_enabled else "disabled",
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


def start_render_job(project_data: dict, job_id: str):
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
        project_id, snapshot = validate_render_snapshot(original)
        original["id"] = original["episode_id"] = project_id
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
        with _JOBS_LOCK:
            # Disk records remain available through project-scoped status queries.
            for old in list(JOBS):
                if len(JOBS) < 100:
                    break
                if old not in _CONTROLS:
                    JOBS.pop(old)
            JOBS[job_id] = {"job_id": job_id, "project_id": project_id,
                            "status": "queued", "progress": 0, "error": None,
                            "input_fingerprint": fingerprint}
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
