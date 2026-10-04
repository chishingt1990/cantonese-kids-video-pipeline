"""Narration-first pipeline (record-your-voice edition).

The parent records the narration themselves — in the app or by uploading a
phone recording — instead of using a cloned voice. Every recording is
AUTO-CLEANED (denoise + level) with no button needed.

Flow:
  1. save_uploaded_narration() / add_narration_take() + finalize_narration_takes()
     -> one clean narration WAV
  2. transcribe_narration() -> transcript + per-word timestamps
  3. align_narration() -> each script section mapped onto the transcript.
     Captions come from what was ACTUALLY said (the transcript), timed to
     the real voice — never from the script alone.
"""
import os
import re
import subprocess
import difflib

from app.services.audio_service import get_audio_duration, auto_clean_voice


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


NARRATION_DIR = os.path.join(_project_root(), "assets", "outputs", "narration")


def _safe_id(project_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", project_id or "project")


def narration_path(project_id: str) -> str:
    os.makedirs(NARRATION_DIR, exist_ok=True)
    return os.path.join(NARRATION_DIR, f"{_safe_id(project_id)}_narration.wav")


def takes_dir(project_id: str) -> str:
    d = os.path.join(NARRATION_DIR, f"{_safe_id(project_id)}_takes")
    os.makedirs(d, exist_ok=True)
    return d


def _transcode_to_wav(src_path: str, dst_path: str) -> str:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src_path,
         "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", dst_path],
        check=True,
    )
    return dst_path


# ---------------------------------------------------------------------------
# Recording intake: single upload, or multi-take recording.
# ---------------------------------------------------------------------------

def save_uploaded_narration(project_id: str, src_path: str) -> dict:
    """Take one uploaded recording, auto-clean it, store as the narration."""
    out_path = narration_path(project_id)
    auto_clean_voice(src_path, out_path)
    return {
        "status": "success",
        "project_id": project_id,
        "path": out_path,
        "filename": os.path.basename(out_path),
        "duration": get_audio_duration(out_path),
        "recorded": True,
    }


def add_narration_take(project_id: str, src_path: str) -> dict:
    """Save one recorded take (auto-cleaned). Returns the take list."""
    d = takes_dir(project_id)
    existing = sorted(f for f in os.listdir(d) if f.startswith("take_"))
    idx = len(existing) + 1
    dst = os.path.join(d, f"take_{idx:02d}.wav")
    auto_clean_voice(src_path, dst)
    return {"status": "success", "take_index": idx,
            "takes": list_narration_takes(project_id)}


def list_narration_takes(project_id: str) -> list:
    d = takes_dir(project_id)
    takes = []
    for f in sorted(os.listdir(d) if os.path.isdir(d) else []):
        if f.startswith("take_") and f.endswith(".wav"):
            p = os.path.join(d, f)
            takes.append({"index": int(f[5:7]), "filename": f,
                          "duration": round(get_audio_duration(p), 2)})
    return takes


def delete_narration_take(project_id: str, index: int) -> dict:
    d = takes_dir(project_id)
    target = os.path.join(d, f"take_{int(index):02d}.wav")
    if os.path.exists(target):
        os.remove(target)
    # Renumber remaining takes so indices stay 1..N.
    remaining = sorted(f for f in os.listdir(d)
                       if f.startswith("take_") and f.endswith(".wav"))
    for i, f in enumerate(remaining, 1):
        want = f"take_{i:02d}.wav"
        if f != want:
            os.rename(os.path.join(d, f), os.path.join(d, want))
    return {"status": "success", "takes": list_narration_takes(project_id)}


def finalize_narration_takes(project_id: str) -> dict:
    """Join all takes with short crossfades into the final narration WAV."""
    takes = list_narration_takes(project_id)
    if not takes:
        raise ValueError("No takes recorded yet.")
    d = takes_dir(project_id)
    out_path = narration_path(project_id)
    if len(takes) == 1:
        src = os.path.join(d, takes[0]["filename"])
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                        "-c", "copy", out_path], check=True)
    else:
        inputs = []
        for t in takes:
            inputs += ["-i", os.path.join(d, t["filename"])]
        # Chain acrossfades: [0][1]xf -> [a1]; [a1][2]xf -> [a2]; ...
        fc, last = [], "0:a"
        for i in range(1, len(takes)):
            out = f"[a{i}]"
            fc.append(f"[{last}][{i}:a]acrossfade=d=0.4:c1=tri:c2=tri{out}")
            last = out
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", *inputs,
             "-filter_complex", ";".join(fc), "-map", last,
             "-ar", "44100", "-c:a", "pcm_s16le", out_path],
            check=True,
        )
    return {
        "status": "success",
        "project_id": project_id,
        "path": out_path,
        "filename": os.path.basename(out_path),
        "duration": get_audio_duration(out_path),
        "takes_joined": len(takes),
        "recorded": True,
    }


# ---------------------------------------------------------------------------
# Transcription: what did the parent ACTUALLY say?
# ---------------------------------------------------------------------------

def _whisper_words(audio_path: str):
    """Word-level timestamps via faster-whisper. Raises if unavailable."""
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    # "zh" covers Cantonese speech well; "yue" is not a valid whisper tag.
    segments, _ = model.transcribe(audio_path, language="zh",
                                   word_timestamps=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            txt = (w.word or "").strip()
            if txt:
                words.append({"w": txt, "start": float(w.start),
                              "end": float(w.end)})
    if not words:
        raise RuntimeError("Whisper returned no words.")
    return words, segments


def transcribe_narration(audio_path: str) -> dict:
    """Transcribe the narration. Returns text + segments + word timestamps."""
    words, segments = _whisper_words(audio_path)
    text = "".join(w["w"] for w in words)
    return {
        "status": "success",
        "text": text,
        "segments": [
            {"text": s.text, "start": round(s.start, 2),
             "end": round(s.end, 2)} for s in segments
        ],
        "words": words,
        "duration": get_audio_duration(audio_path),
    }


# ---------------------------------------------------------------------------
# Alignment: map each script section onto the transcript. Captions come from
# the transcript slice (what was actually said), timed to the real voice.
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[\s，。！？；：、,.!?;:'\"「」『』（）()\[\]…—–\-]+")


def _norm(s: str) -> str:
    return _PUNCT_RE.sub("", s or "")


def _align_with_words(words, sections):
    """Char-level alignment of script sections onto the transcript.

    Returns (sections_out, words) on success, else (None, words).
    Each section gains caption_text: the transcript slice actually spoken.
    """
    transcript = "".join(w["w"] for w in words)
    if not transcript:
        return None, words
    char_to_word = []
    for i, w in enumerate(words):
        char_to_word.extend([i] * len(w["w"]))

    out = []
    search_from = 0
    for sec in sections:
        needle = _norm(sec.get("cantonese"))
        if not needle:
            return None, words
        idx = transcript.find(needle, search_from)
        if idx == -1:
            window = transcript[search_from: search_from + len(needle) + 40]
            sm = difflib.SequenceMatcher(None, window, needle, autojunk=False)
            eq = [oc for oc in sm.get_opcodes() if oc[0] == "equal"]
            matched = sum(oc[2] - oc[1] for oc in eq)
            if not eq or matched < max(4, len(needle) // 2):
                return None, words
            idx = search_from + eq[0][1]
            end_idx = min(search_from + eq[-1][2], len(char_to_word))
        else:
            end_idx = min(idx + len(needle), len(char_to_word))
        w0 = char_to_word[idx]
        w1 = char_to_word[end_idx - 1]
        out.append({
            "scene_number": sec.get("scene_number"),
            "start": round(words[w0]["start"], 3),
            "end": round(words[w1]["end"], 3),
            # What was ACTUALLY said in this window (caption source).
            "caption_text": transcript[idx:end_idx],
        })
        search_from = end_idx
    return out, words


def _align_proportional(sections, total_duration):
    """Fallback: split time by character count when Whisper is unavailable."""
    lens = [max(1, len(_norm(s.get("cantonese")))) for s in sections]
    total = max(1, sum(lens))
    out, t = [], 0.0
    for s, ln in zip(sections, lens):
        d = total_duration * ln / total
        out.append({
            "scene_number": s.get("scene_number"),
            "start": round(t, 3),
            "end": round(t + d, 3),
            "caption_text": s.get("cantonese") or "",
        })
        t += d
    return out


def align_narration(audio_path: str, sections) -> dict:
    """Align script sections to the narration audio.

    sections: [{scene_number, cantonese}, ...]
    Returns {"sections": [...with caption_text...], "words": [...],
             "method": "whisper"|"proportional", "duration": float}
    """
    sections = [s for s in (sections or []) if (s.get("cantonese") or "").strip()]
    if not sections:
        raise ValueError("No sections to align.")
    duration = get_audio_duration(audio_path)

    words = []
    method = "proportional"
    aligned = None
    try:
        words, _ = _whisper_words(audio_path)
        aligned, words = _align_with_words(words, sections)
        if aligned:
            method = "whisper"
    except Exception as e:
        print(f"Narration align: whisper unavailable ({e}), using proportional fallback.")

    if not aligned:
        aligned = _align_proportional(sections, duration)
        words = []

    return {
        "status": "success",
        "method": method,
        "duration": duration,
        "sections": aligned,
        "words": words,
    }
