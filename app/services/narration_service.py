"""Project-owned, immutable narration takes and bounded background work."""
import copy
import difflib
import hashlib
import importlib.util
import json
import logging
import math
import os
import shutil
import threading
import time
import unicodedata
import uuid
import wave
from pathlib import Path

import requests

from app.storage import atomic_write_json as _atomic_write_json, project_lock, project_operation, project_path, validate_id
from app.services import project_service, voice_clone_service
from app.services.audio_service import get_audio_duration, require_media_tools

STYLES = {
    "calm": "A calm, gentle dad speaking slowly in natural Hong Kong Cantonese to toddlers.",
    "warm_playful": "A warm, playful dad speaking natural Hong Kong Cantonese to toddlers.",
    "excited": "A cheerful, encouraging dad speaking clear Hong Kong Cantonese, never shouting.",
}
_SLOT = threading.BoundedSemaphore(1)
_PROCESS_ID = uuid.uuid4().hex
_ACTIVE_JOBS = set()
_ACTIVE_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def atomic_write_json(path, value):
    # Windows readers/sync clients may briefly hold a handle across atomic replacement.
    for attempt in range(5):
        try:
            return _atomic_write_json(path, value)
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * 2 ** attempt)


class NarrationError(ValueError):
    def __init__(self, code, message, http_status=400):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _scenes(project):
    scenes = project.get("scenes") or []
    if not 1 <= len(scenes) <= 100:
        raise NarrationError("script_invalid", "Save a story with 1–100 spoken scenes first")
    numbers = [s.get("scene_number") for s in scenes]
    if len(set(numbers)) != len(numbers) or any(not isinstance(n, int) or n < 1 for n in numbers):
        raise NarrationError("script_invalid", "Scene numbers must be distinct positive integers")
    if any(not isinstance(s.get("cantonese"), str) or not _norm(s["cantonese"]) for s in scenes):
        raise NarrationError("script_invalid", "Every narration scene needs spoken Cantonese text")
    if sum(len(s["cantonese"]) + 2 for s in scenes) > 12000:
        raise NarrationError("script_invalid", "Whole-story narration exceeds 12000 characters")
    return scenes


def script_fingerprint(project, voice_id=None, style=None):
    options = project.get("voice_options") or {}
    if not isinstance(options, dict):
        raise NarrationError("voice_invalid", "Voice options must be an object")
    return _digest({
        "scenes": [{"scene_number": s["scene_number"], "cantonese": s["cantonese"].strip()}
                   for s in _scenes(project)],
        "voice_id": voice_id if voice_id is not None else options.get("voice_id"),
        "style": style if style is not None else options.get("style"),
    })


def narration_audio_path(project_id, take_id):
    validate_id(take_id)
    return project_path(project_id, "narration", take_id + ".wav")


def _manifest_path(project_id, take_id):
    validate_id(take_id)
    return project_path(project_id, "narration", take_id + ".json")


def _norm(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold()
                   if unicodedata.category(c)[0] in {"L", "N"})


def _saved_project(project_id, revision=None):
    project = project_service.get_project(project_id)
    if project is None:
        raise NarrationError("project_missing", "Save the project before generating narration", 404)
    if revision is not None and project.get("revision", 0) != revision:
        raise NarrationError("revision_conflict", "Project changed; reload before starting narration", 409)
    _scenes(project)
    return project


def _selected_voice(project, voice_id, style):
    if style not in STYLES:
        raise NarrationError("style_invalid", "Choose calm, warm_playful, or excited")
    options = project.get("voice_options") or {}
    if (options.get("use_cloned") is not True or options.get("voice_id") != voice_id
            or options.get("style") != style):
        raise NarrationError("voice_mismatch", "Save the selected parent voice and style first", 409)
    if not any(v.get("voice_id") == voice_id for v in voice_clone_service.list_cloned_voices()):
        raise NarrationError("voice_unknown", "Select a known saved parent voice")


def alignment_preflight():
    """Only an explicitly installed local Cantonese-capable model is accepted."""
    message = ("Local Cantonese alignment is unavailable. Install faster-whisper and set "
               "KIDS_STUDIO_WHISPER_MODEL to a local converted large-v3 model directory, "
               "or explicitly choose estimated timing before generating audio.")
    try:
        folder = Path(os.environ.get("KIDS_STUDIO_WHISPER_MODEL", ""))
        if not os.environ.get("KIDS_STUDIO_WHISPER_MODEL") or not folder.is_dir():
            raise ValueError()
        if importlib.util.find_spec("faster_whisper") is None:
            raise ValueError()
        if not (folder / "model.bin").is_file():
            raise ValueError()
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        tokenizer = json.loads((folder / "tokenizer.json").read_text(encoding="utf-8"))
        feature = json.loads((folder / "preprocessor_config.json").read_text(encoding="utf-8"))
        yue = next(t["id"] for t in tokenizer.get("added_tokens", [])
                   if t.get("content") == "<|yue|>")
        if (yue not in config.get("lang_ids", []) or not config.get("alignment_heads")
                or feature.get("feature_size") != 128):
            raise ValueError()
        return str(folder.resolve())
    except (OSError, ValueError, KeyError, StopIteration, ImportError):
        raise NarrationError("alignment_unavailable", message, 503) from None


def _load_model(path):
    from faster_whisper import WhisperModel
    return WhisperModel(path, device="cpu", compute_type="int8", local_files_only=True)


def _asr_words(model, path):
    segments, _ = model.transcribe(str(path), language="yue", word_timestamps=True,
                                   condition_on_previous_text=False)
    return [{"text": w.word.strip(), "start_sec": float(w.start), "end_sec": float(w.end),
             "probability": float(w.probability)}
            for seg in segments for w in (seg.words or []) if _norm(w.word)]


def align_words(scenes, words, duration):
    """Conservative normalized transcript coverage; never invent ASR timestamps."""
    script = "".join(_norm(s["cantonese"]) for s in scenes)
    transcript, char_words = "", []
    previous = 0.0
    for index, word in enumerate(words):
        start, end = word["start_sec"], word["end_sec"]
        probability = word.get("probability", 0)
        if (not all(math.isfinite(x) for x in (start, end, probability))
                or start < previous - 0.02 or not 0 <= start < end <= duration + 0.02
                or probability < 0.2):
            raise NarrationError("alignment_unreliable", "Speech timestamps/confidence are unreliable")
        previous = end
        normalized = _norm(word["text"])
        transcript += normalized
        char_words.extend([index] * len(normalized))
    if not words or sum(w.get("probability", 0) for w in words) / len(words) < 0.65:
        raise NarrationError("alignment_unreliable", "Speech recognition confidence is too low")
    mapping = {}
    for match in difflib.SequenceMatcher(None, script, transcript, autojunk=False).get_matching_blocks():
        for offset in range(match.size):
            mapping[match.a + offset] = match.b + offset
    if len(mapping) / max(len(script), len(transcript), 1) < 0.9:
        raise NarrationError("alignment_unreliable", "Recognized speech does not sufficiently match the saved story")
    result, offset, last_word = [], 0, -1
    for scene in scenes:
        length = len(_norm(scene["cantonese"]))
        matches = [mapping[i] for i in range(offset, offset + length) if i in mapping]
        if len(matches) / length < 0.85:
            raise NarrationError("alignment_unreliable", "A scene could not be confidently aligned")
        first, last = char_words[matches[0]], char_words[matches[-1]]
        if first <= last_word:
            raise NarrationError("alignment_unreliable", "Speech boundaries overlap between scenes")
        chosen = [{k: w[k] for k in ("text", "start_sec", "end_sec")}
                  for w in words[first:last + 1]]
        result.append({"scene_number": scene["scene_number"], "start_sec": chosen[0]["start_sec"],
                       "end_sec": chosen[-1]["end_sec"], "words": chosen})
        last_word, offset = last, offset + length
    for i in range(len(result) - 1):
        boundary = (result[i]["end_sec"] + result[i + 1]["start_sec"]) / 2
        result[i]["end_sec"] = result[i + 1]["start_sec"] = boundary
    result[0]["start_sec"], result[-1]["end_sec"] = 0.0, duration
    return result


def estimated_alignment(scenes, duration):
    lengths = [len(_norm(s["cantonese"])) for s in scenes]
    total, offset, result = sum(lengths), 0, []
    previous = 0.0
    for index, (scene, length) in enumerate(zip(scenes, lengths)):
        start = previous
        end = duration if index == len(scenes) - 1 else duration * (offset + length) / total
        words = [{"text": char, "start_sec": start + (end - start) * i / length,
                  "end_sec": start + (end - start) * (i + 1) / length}
                 for i, char in enumerate(_norm(scene["cantonese"]))]
        words[-1]["end_sec"] = end
        result.append({"scene_number": scene["scene_number"], "start_sec": start,
                       "end_sec": end, "words": words})
        offset += length
        previous = end
    return result


def load_manifest(project_id, take_id):
    path = _manifest_path(project_id, take_id)
    if not path.is_file():
        raise NarrationError("take_missing", "Narration take not found in this project", 404)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["project_id"] != project_id or manifest["take_id"] != take_id:
            raise ValueError()
        if file_digest(narration_audio_path(project_id, take_id)) != manifest["source_digest"]:
            raise ValueError()
        if manifest.get("alignment_digest") != _digest(manifest["scenes"]):
            raise ValueError()
        return manifest
    except (OSError, ValueError, KeyError, TypeError):
        raise NarrationError("take_corrupt", "Narration artifact is missing or changed; original project preserved") from None


def validate_narration(project):
    if not isinstance(project, dict):
        raise NarrationError("project_invalid", "Project snapshot must be an object")
    project_id = project.get("id") or project.get("episode_id")
    attachment = project.get("narration") or {}
    if not isinstance(attachment, dict):
        raise NarrationError("take_invalid", "Narration attachment must be an object")
    manifest = load_manifest(project_id, attachment.get("take_id", ""))
    options = project.get("voice_options") or {}
    if not isinstance(options, dict):
        raise NarrationError("voice_invalid", "Voice options must be an object")
    if (options.get("use_cloned") is not True or options.get("voice_id") != manifest["voice_id"]
            or options.get("style") != manifest["style"]
            or manifest["script_fingerprint"] != script_fingerprint(project)):
        raise NarrationError("narration_stale", "Narration no longer matches the story, selected voice or style", 409)
    if not 120 <= manifest["duration_sec"] <= 240:
        raise NarrationError("duration_out_of_range", "Narration must measure 120–240 seconds; revise and regenerate")
    if manifest["alignment_method"] not in {"asr", "estimated"}:
        raise NarrationError("needs_alignment", "Align this saved voice take before rendering", 409)
    if manifest["alignment_method"] == "estimated" and manifest.get("allow_estimated_alignment") is not True:
        raise NarrationError("alignment_unreliable", "Estimated timing was not explicitly approved")
    scenes = manifest["scenes"]
    if [s["scene_number"] for s in scenes] != [s["scene_number"] for s in _scenes(project)]:
        raise NarrationError("alignment_unreliable", "Narration scene map does not match the story")
    previous = 0.0
    for scene in scenes:
        start, end = scene["start_sec"], scene["end_sec"]
        if not (math.isfinite(start) and math.isfinite(end) and abs(start - previous) < 1e-6
                and start < end <= manifest["duration_sec"]):
            raise NarrationError("alignment_unreliable", "Narration timeline contains gaps or invalid boundaries")
        word_end = start
        for word in scene["words"]:
            a, b = word["start_sec"], word["end_sec"]
            if not (math.isfinite(a) and math.isfinite(b) and a >= word_end - 0.02
                    and start <= a < b <= end + 0.02 and isinstance(word["text"], str)):
                raise NarrationError("alignment_unreliable", "Narration word timestamps are invalid")
            word_end = b
        previous = end
    if abs(previous - manifest["duration_sec"]) > 1e-6:
        raise NarrationError("alignment_unreliable", "Narration timeline does not cover the audio")
    return manifest


def _job_path(project_id, job_id):
    validate_id(job_id)
    return project_path(project_id, "narration_jobs", job_id + ".json")


def get_job(project_id, job_id):
    path = _job_path(project_id, job_id)
    if not path.is_file():
        raise NarrationError("job_missing", "Narration job not found in this project", 404)
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("project_id") != project_id or job.get("job_id") != job_id:
        raise NarrationError("job_missing", "Narration job not found", 404)
    with _ACTIVE_LOCK:
        active = (project_id, job_id) in _ACTIVE_JOBS
    if job["status"] in {"queued", "running"} and (job.get("process_id") != _PROCESS_ID or not active):
        job.update(status="error", error_code="interrupted",
                   error="Narration was interrupted; provider outcome may be uncertain. It was not resubmitted.")
    if (job["status"] == "error" and job.get("take_id")
            and (not job.get("narration") or job.get("error_code") == "interrupted")):
        _recover_take(job)
    if job.get("narration"):
        current = project_service.get_project(project_id)
        try:
            job["stale"] = (not current or script_fingerprint(current) != job["narration"]["script_fingerprint"]
                            or (current.get("voice_options") or {}).get("use_cloned") is not True)
        except (ValueError, KeyError, TypeError):
            job["stale"] = True
    return {key: value for key, value in job.items() if key not in {"process_id", "binding"}}


def _base_manifest(job, duration, digest):
    project_id, take_id = job["project_id"], job["take_id"]
    return {
        "project_id": project_id, "take_id": take_id,
        "audio_url": f"/api/narration/audio/{project_id}/{take_id}",
        "duration_sec": duration, **job["binding"], "source_digest": digest,
        "alignment_method": "none", "scenes": [], "warnings": [],
        "source_revision": job["source_revision"], "alignment_digest": _digest([]),
    }


def _recover_take(job):
    """Recover completed local audio, never reissue an uncertain paid operation."""
    project_id, take_id = job["project_id"], job["take_id"]
    try:
        with project_lock(project_id):
            manifest_path = _manifest_path(project_id, take_id)
            if manifest_path.is_file():
                manifest = load_manifest(project_id, take_id)
            else:
                audio = narration_audio_path(project_id, take_id)
                with wave.open(str(audio), "rb") as stream:
                    if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 44100):
                        return
                    frames = stream.getnframes()
                    count = 0
                    while block := stream.readframes(44100):
                        count += len(block)
                    if not frames or count != frames * 2 or frames / 44100 > 1800:
                        return
                manifest = _base_manifest(job, frames / 44100, file_digest(audio))
                manifest["warnings"].append("Audio recovered after interruption; alignment must be reviewed.")
                atomic_write_json(manifest_path, manifest)
            job["narration"] = manifest
            if 120 <= manifest["duration_sec"] <= 240:
                job.update(status="needs_alignment", error_code="needs_alignment",
                           error="Saved voice take recovered. Retry alignment; no synthesis is needed.")
            else:
                job.update(error_code="duration_out_of_range",
                           error="Saved voice take recovered but does not measure 120–240 seconds.")
            atomic_write_json(_job_path(project_id, job["job_id"]), job)
    except (OSError, ValueError, KeyError, TypeError, wave.Error, EOFError):
        # Partial/undecodable audio stays untouched; its provider outcome remains uncertain.
        return


def start_job(project_id, revision, voice_id=None, style=None,
              allow_estimated_alignment=False, take_id=None):
    with project_lock(project_id):
        project = copy.deepcopy(_saved_project(project_id, revision))
        source = load_manifest(project_id, take_id) if take_id else None
        if source:
            voice_id, style = source["voice_id"], source["style"]
        _selected_voice(project, voice_id, style)
        fingerprint = script_fingerprint(project, voice_id, style)
        if source and source["script_fingerprint"] != fingerprint:
            raise NarrationError("narration_stale", "This take belongs to an older story or voice selection", 409)
        model_path = None
        try:
            model_path = alignment_preflight()
        except NarrationError:
            if not allow_estimated_alignment:
                raise
        require_media_tools("ffmpeg", "ffprobe")
        if not source:
            voice_clone_service._require_api_key()
        if not _SLOT.acquire(blocking=False):
            raise NarrationError("narration_busy", "A narration job is already running; wait for its result", 409)
        lease = project_operation(project_id)
        entered = False
        job = None
        try:
            lease.__enter__()
            entered = True
            job_id = uuid.uuid4().hex
            job = {"job_id": job_id, "project_id": project_id, "status": "queued",
                   "source_revision": revision, "process_id": _PROCESS_ID}
            atomic_write_json(_job_path(project_id, job_id), job)
            with _ACTIVE_LOCK:
                _ACTIVE_JOBS.add((project_id, job_id))
            _launch_worker((
                job, project, voice_id, style, fingerprint, model_path,
                allow_estimated_alignment, source, lease))
        except Exception:
            try:
                if job is not None:
                    job.update(status="error", error_code="startup_failed",
                               error="Narration worker could not start; no automatic retry was made.")
                    atomic_write_json(_job_path(project_id, job["job_id"]), job)
            finally:
                if job is not None:
                    with _ACTIVE_LOCK:
                        _ACTIVE_JOBS.discard((project_id, job["job_id"]))
                if entered:
                    lease.__exit__(None, None, None)
                _SLOT.release()
            raise
    return {"job_id": job_id, "project_id": project_id}


def _launch_worker(args):
    threading.Thread(target=_worker, args=args, daemon=True).start()


def _worker(job, project, voice_id, style, fingerprint, model_path, allow_estimated, source, lease):
    project_id = job["project_id"]
    path = _job_path(project_id, job["job_id"])
    take_id = uuid.uuid4().hex
    manifest = None
    try:
        job["status"] = "running"
        job["take_id"] = take_id
        job["binding"] = {"script_fingerprint": fingerprint, "voice_id": voice_id, "style": style,
                          "allow_estimated_alignment": allow_estimated,
                          "script_scenes": [{"scene_number": s["scene_number"], "cantonese": s["cantonese"].strip()}
                                            for s in _scenes(project)]}
        atomic_write_json(path, job)
        model = None
        if model_path:
            try:
                model = _load_model(model_path)
            except Exception:
                if not allow_estimated:
                    raise NarrationError("alignment_unavailable", "Local alignment model could not load; no synthesis requested", 503)
        output = narration_audio_path(project_id, take_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        if source:
            shutil.copyfile(narration_audio_path(project_id, source["take_id"]), output)
        else:
            voice_clone_service.synthesize_story_cloned_voice(
                "\n\n".join(s["cantonese"].strip() for s in _scenes(project)),
                voice_id, output, STYLES[style])
        duration = get_audio_duration(str(output))
        manifest = _base_manifest(job, duration, file_digest(output))
        if source:
            manifest["source_take_id"] = source["take_id"]
        # Recover the paid take even if alignment, duration validation, or the process fails.
        atomic_write_json(_manifest_path(project_id, take_id), manifest)
        job["narration"] = manifest
        atomic_write_json(path, job)
        if not 120 <= duration <= 240:
            raise NarrationError("duration_out_of_range",
                                 f"Narration measured {duration:.1f}s; required 120–240s. "
                                 "The take is preserved for listening. Revise the story; no silence was added.")
        try:
            if model is None:
                raise NarrationError("alignment_unavailable", "Local Cantonese alignment is unavailable")
            manifest["scenes"] = align_words(_scenes(project), _asr_words(model, output), duration)
            manifest["alignment_method"] = "asr"
            manifest["warnings"].append("Audio-derived ASR timestamps are estimates, not guaranteed exact.")
        except Exception:
            if not allow_estimated:
                job.update(status="needs_alignment", error_code="alignment_unreliable",
                           error="Voice take preserved. Local alignment failed; retry alignment without resynthesis.")
            else:
                manifest["scenes"] = estimated_alignment(_scenes(project), duration)
                manifest["alignment_method"] = "estimated"
                manifest["warnings"].append("Estimated character-proportional timing; not speech-aligned.")
        manifest["alignment_digest"] = _digest(manifest["scenes"])
        atomic_write_json(_manifest_path(project_id, take_id), manifest)
        if job["status"] != "needs_alignment":
            validate_narration(dict(project, narration=manifest))
            job["status"] = "done"
    except NarrationError as exc:
        job.update(status="error", error_code=exc.code, error=str(exc))
    except requests.exceptions.Timeout:
        job.update(status="error", error_code="provider_outcome_unknown",
                   error="Provider timed out; outcome and charge may be uncertain. No automatic retry was made.")
    except Exception:
        job.update(status="error", error_code="narration_failed",
                   error="Narration failed; no substitute voice or automatic provider retry was used.")
    finally:
        try:
            atomic_write_json(path, job)
        except OSError:
            logger.exception("Could not persist narration completion; status recovery will inspect the saved take")
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE_JOBS.discard((project_id, job["job_id"]))
            try:
                lease.__exit__(None, None, None)
            finally:
                _SLOT.release()
