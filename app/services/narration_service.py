"""Narration-first pipeline.

Instead of one TTS request per scene, the whole episode script is rendered
with a SINGLE TTS request (one narration track). Scenes are then mapped onto
the narration via automatic word-level alignment, so pictures land on the
right words and karaoke captions get true timings.

Flow:
  1. build_narration_text(scenes) -> one continuous script
  2. synthesize_narration(...)      -> ONE cloned-voice TTS request -> narration WAV
  3. align_narration(...)           -> per-section (start, end) + word timestamps
"""
import os
import re
import asyncio
import difflib

from app.services.audio_service import get_audio_duration
from app.services.voice_clone_service import (
    generate_cloned_tts,
    VoiceCloneUnavailableError,
)


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


NARRATION_DIR = os.path.join(_project_root(), "assets", "outputs", "narration")

DEFAULT_STYLE = "warm and gentle dad speaking Cantonese to his toddlers, natural and playful"


def narration_path(project_id: str) -> str:
    os.makedirs(NARRATION_DIR, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", project_id or "project")
    return os.path.join(NARRATION_DIR, f"{safe}_narration.wav")


def build_narration_text(scenes) -> str:
    """Join every scene's Cantonese line into one continuous narration script."""
    parts = []
    for s in scenes or []:
        t = (s.get("cantonese") or "").strip()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def synthesize_narration(project_id: str, voice_id: str, full_text: str,
                         style: str = None) -> dict:
    """Render the FULL script with ONE cloned-voice TTS request.

    Returns dict with status/path/duration. Raises VoiceCloneUnavailableError
    when no Gemini key is configured.
    """
    if not (full_text or "").strip():
        raise ValueError("Narration text is empty.")
    out_path = narration_path(project_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            generate_cloned_tts(full_text, voice_id,
                                output_wav_path=out_path,
                                style=style or DEFAULT_STYLE)
        )
    finally:
        loop.close()

    duration = get_audio_duration(out_path)
    return {
        "status": "success",
        "project_id": project_id,
        "path": out_path,
        "filename": os.path.basename(out_path),
        "duration": duration,
        "voice_id": voice_id,
        "cloned": True,
    }


# ---------------------------------------------------------------------------
# Alignment: map each script section onto the narration audio.
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[\s，。！？；：、,.!?;:'\"「」『』（）()\[\]…—–\-]+")


def _norm(s: str) -> str:
    return _PUNCT_RE.sub("", s or "")


def _whisper_words(audio_path: str):
    """Word-level timestamps via faster-whisper. Raises if unavailable."""
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, language="yue",
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
    return words


def _align_with_words(words, sections):
    """Char-level sequential alignment of section texts onto the transcript.

    Returns (sections_out, None) on success, or (None, None) to signal the
    caller should use the proportional fallback.
    """
    transcript = "".join(w["w"] for w in words)
    if not transcript:
        return None, None
    # char index -> word index
    char_to_word = []
    for i, w in enumerate(words):
        char_to_word.extend([i] * len(w["w"]))

    out = []
    search_from = 0
    for sec in sections:
        needle = _norm(sec.get("cantonese"))
        if not needle:
            return None, None
        idx = transcript.find(needle, search_from)
        if idx == -1:
            # Fuzzy fallback: align via opcode spans so small insertions /
            # deletions in the transcription don't break the mapping.
            window = transcript[search_from: search_from + len(needle) + 40]
            sm = difflib.SequenceMatcher(None, window, needle, autojunk=False)
            eq = [oc for oc in sm.get_opcodes() if oc[0] == "equal"]
            matched = sum(oc[2] - oc[1] for oc in eq)
            if not eq or matched < max(4, len(needle) // 2):
                return None, None
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
        })
        t += d
    return out


def align_narration(audio_path: str, sections) -> dict:
    """Align script sections to the narration audio.

    sections: [{scene_number, cantonese}, ...]
    Returns {"sections": [...], "words": [...], "method": "whisper"|"proportional",
             "duration": float}
    """
    sections = [s for s in (sections or []) if (s.get("cantonese") or "").strip()]
    if not sections:
        raise ValueError("No sections to align.")
    duration = get_audio_duration(audio_path)

    words = []
    method = "proportional"
    aligned = None
    try:
        words = _whisper_words(audio_path)
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
