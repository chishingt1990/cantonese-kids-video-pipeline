import asyncio
import math
import os
import shutil
import subprocess
import wave
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np

from app.storage import contained_path, project_path, project_is_busy, project_operation, validate_id

MAX_SCENE_SECONDS = 120
MAX_EPISODE_SECONDS = 1800
media_operation = project_operation


def media_binary(name):
    return os.environ.get(f"KIDS_STUDIO_{name.upper()}", name)


class MediaPrerequisiteError(RuntimeError):
    pass


def missing_media_tool(name):
    return MediaPrerequisiteError(
        f"{name} executable is unavailable. Install FFmpeg (including ffprobe) and add its bin "
        f"directory to PATH, or set KIDS_STUDIO_{name.upper()} to the full executable path."
    )


def require_media_tools(*names):
    for name in names:
        if not shutil.which(media_binary(name)):
            raise missing_media_tool(name)


def run_media_command(name, arguments, **kwargs):
    try:
        return subprocess.run([media_binary(name), *arguments], **kwargs)
    except FileNotFoundError as exc:
        raise missing_media_tool(name) from exc


def project_media_busy(project_id):
    """Compatibility alias; storage owns the deletion-lease registry."""
    return project_is_busy(project_id)


async def run_blocking(function, *args, **kwargs):
    """Do not release a worker's input files until that worker has really stopped."""
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()
        raise


def get_audio_duration(file_path: str) -> float:
    """Probe containers as well as PCM WAV; invalid audio is never silent success."""
    if not Path(file_path).is_file():
        raise ValueError("Audio file is missing")
    try:
        with wave.open(str(file_path), "rb") as wf:
            duration = wf.getnframes() / float(wf.getframerate())
    except (wave.Error, EOFError):
        result = run_media_command(
            "ffprobe", ["-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise ValueError("Audio could not be decoded by ffprobe")
        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise ValueError("Audio duration is unavailable") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio must have a positive finite duration")
    return duration


def scene_duration(requested=6, audio_duration=0) -> float:
    requested = float(requested)
    audio_duration = float(audio_duration)
    if not math.isfinite(requested) or requested <= 0:
        raise ValueError("Scene duration must be positive and finite")
    if not math.isfinite(audio_duration) or audio_duration < 0:
        raise ValueError("Audio duration must be finite and nonnegative")
    required = max(requested, audio_duration + 1.2 if audio_duration > 0 else 0)
    duration = math.ceil(required * 30) / 30
    if duration > MAX_SCENE_SECONDS:
        raise ValueError(f"Scene exceeds {MAX_SCENE_SECONDS} seconds")
    return duration


def normalize_audio(source, destination, *, max_seconds=None):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Audio outputs are immutable; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = get_audio_duration(str(source))
    if max_seconds is not None and duration > max_seconds:
        raise ValueError(f"Recording exceeds {max_seconds} seconds")
    try:
        result = run_media_command(
            "ffmpeg", ["-nostdin", "-n", "-i", str(source), "-vn",
             "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(destination)],
            capture_output=True, timeout=120,
        )
        if result.returncode:
            raise RuntimeError("FFmpeg audio normalization failed")
        return get_audio_duration(str(destination))
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def resolve_project_audio(project_id, audio_url):
    """Only immutable audio URLs from this project are valid render inputs."""
    validate_id(project_id)
    parsed = urlsplit(audio_url)
    parts = unquote(parsed.path).split("/")
    if parsed.scheme or parsed.netloc or len(parts) != 6 or parts[:4] != ["", "api", "audio", "clip"]:
        raise ValueError("Audio must be a project-scoped studio clip URL")
    if parts[4] != project_id:
        raise ValueError("Audio belongs to a different project")
    filename = parts[5]
    if not filename.endswith(".wav") or Path(filename).name != filename or "\\" in filename:
        raise ValueError("Invalid audio filename")
    path = contained_path(project_path(project_id, "audio"), filename)
    if not path.is_file():
        raise ValueError("Referenced project audio is missing; regenerate or record it")
    return path


def mix_narration_with_bgm(narration_path, output_path, *, enabled=True, volume=0.025):
    """Preserve every narration sample; optionally add a quiet synthesized plucked bed."""
    output = Path(output_path)
    if output.exists():
        raise ValueError("Mixed narration outputs are immutable")
    if not isinstance(enabled, bool) or not math.isfinite(volume) or not 0 <= volume <= 0.05:
        raise ValueError("Synthesized backing volume must be between 0 and 0.05")
    sr = 44100
    with wave.open(str(narration_path), "rb") as stream:
        if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (sr, 1, 2):
            raise ValueError("Narration audio must be normalized 44.1kHz mono PCM16 WAV")
        frames = stream.getnframes()
        if not 0 < frames <= MAX_EPISODE_SECONDS * sr:
            raise ValueError("Narration duration is invalid")
        raw = stream.readframes(frames)
        if len(raw) != frames * 2:
            raise ValueError("Narration WAV is incomplete")
    if enabled and volume:
        from scipy.ndimage import uniform_filter1d
        narration = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        bed = np.zeros(frames, dtype=np.float32)
        chords = ((261.63, 329.63, 392.0), (196.0, 246.94, 293.66),
                  (220.0, 261.63, 329.63), (174.61, 220.0, 261.63))
        chord_frames = 2 * sr
        for offset in range(0, frames, chord_frames):
            count = min(chord_frames, frames - offset)
            seconds = np.arange(count, dtype=np.float32) / sr
            decay = np.exp(-6 * (seconds % 0.5))
            for frequency in chords[(offset // chord_frames) % len(chords)]:
                bed[offset:offset + count] += (volume / 3) * np.sin(2 * np.pi * frequency * seconds) * decay
        envelope = uniform_filter1d(np.abs(narration), size=round(.08 * sr))
        duck = np.where(envelope > .01, .25, 1.0).astype(np.float32)
        duck = uniform_filter1d(duck, size=round(.15 * sr))
        mixed = narration + bed * duck
        peak = float(np.max(np.abs(mixed)))
        if peak > .98:
            mixed *= .98 / peak
        raw = np.round(np.clip(mixed, -1, .999969) * 32768).astype(np.int16).tobytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = output.open("xb")
    try:
        with handle:
            with wave.open(handle, "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(sr)
                stream.writeframes(raw)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"path": str(output), "duration_sec": frames / sr,
            "backing": "synthesized_plucked" if enabled and volume else "none",
            "warnings": []}


def mix_scene_audio(voice_paths: list, durations: list, output_master_path: str):
    """Mix validated normalized scene clips without truncating narration."""
    if len(voice_paths) != len(durations) or not durations:
        raise ValueError("Audio paths and durations must describe the same nonempty timeline")
    if any(not math.isfinite(float(d)) or d <= 0 for d in durations):
        raise ValueError("Invalid scene duration")
    total_duration = sum(durations)
    if total_duration > MAX_EPISODE_SECONDS:
        raise ValueError("Episode exceeds maximum duration")
    sr = 44100
    scene_samples = [round(d * sr) for d in durations]
    total_samples = sum(scene_samples)
    master = np.zeros(total_samples, dtype=np.float32)
    chords = [[261.63, 329.63, 392.00], [196.00, 246.94, 293.66],
              [220.00, 261.63, 329.63], [174.61, 220.00, 261.63]]
    bgm = np.zeros(total_samples, dtype=np.float32)
    chord_len = int(2.0 * sr)
    for i in range(0, total_samples, chord_len):
        sub_len = min(chord_len, total_samples - i)
        sub_t = np.arange(sub_len) / sr
        for note in chords[(i // chord_len) % len(chords)]:
            bgm[i:i + sub_len] += 0.04 * np.sin(2 * np.pi * note * sub_t) * np.exp(-1.5 * (sub_t % 0.5))
    duck_mask = np.ones(total_samples, dtype=np.float32)
    cur_idx = 0
    for v_path, dur_samples in zip(voice_paths, scene_samples):
        if v_path is not None:
            with wave.open(str(v_path), "rb") as wf:
                if (wf.getframerate(), wf.getnchannels(), wf.getsampwidth()) != (sr, 1, 2):
                    raise ValueError("Scene audio must be normalized 44.1kHz mono PCM16 WAV")
                arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            if len(arr) > dur_samples:
                raise ValueError("Narration exceeds scene duration")
            master[cur_idx:cur_idx + len(arr)] += arr
            duck_mask[cur_idx:cur_idx + len(arr)] = 0.25
        cur_idx += dur_samples
    from scipy.ndimage import uniform_filter1d
    final_mix = master + bgm * uniform_filter1d(duck_mask, size=int(0.5 * sr))
    peak = np.max(np.abs(final_mix))
    if peak > 0.95:
        final_mix = final_mix / peak * 0.95
    Path(output_master_path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_master_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((final_mix * 32767.0).astype(np.int16).tobytes())
