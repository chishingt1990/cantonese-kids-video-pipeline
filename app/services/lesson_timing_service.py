"""Lesson timing engine: turn a parent's recording into timed karaoke phrases.

This is the generalized version of the hand-built Old MacDonald pipeline
(Oct 2026). The flow:

  1. Whisper word timestamps (via narration_service._whisper_words).
  2. clean_tokens(): merge whisper's Latin fragments ("M"+"u" -> "Mu").
  3. segment_phrases(): split the token stream into sung/spoken phrases on
     silences. Optionally tunes the silence threshold to hit a target count
     (e.g. 56 phrases for a 7x8 verse song).

Output phrase format (JSON-safe):
  {"start": 12.3, "end": 15.1, "text": "老麥當勞有個農場",
   "words": [(12.3, "老"), (12.5, "麥"), ...]}

Templates in lesson_templates.py consume these phrases; the renderer in
lesson_render_service.py draws them as karaoke.
"""
import re

CJK = re.compile(r'[\u4e00-\u9fff]')


def get_words(audio_path: str) -> list:
    """Whisper word-level timestamps. Raises if faster-whisper is missing."""
    from app.services.narration_service import _whisper_words
    words, _segments = _whisper_words(audio_path)
    out = []
    for w in words:
        t = (w.get("w") or w.get("text") or "").strip()
        if not t:
            continue
        out.append({"text": t,
                    "start": float(w["start"]),
                    "end": float(w["end"])})
    return out


def clean_tokens(words: list) -> list:
    """Merge whisper's Latin fragments into display tokens.

    Whisper often splits sung English into fragments ("M"+"u", "O"+"ink").
    Consecutive Latin fragments separated by a tiny gap are joined.
    CJK characters are already single tokens and pass through untouched.
    """
    tokens = []
    cur_text, cur_start, cur_end = None, None, None

    def flush():
        nonlocal cur_text, cur_start, cur_end
        if cur_text:
            tokens.append({"text": cur_text,
                           "start": round(cur_start, 2),
                           "end": round(cur_end, 2)})
        cur_text, cur_start, cur_end = None, None, None

    for w in words:
        t, s, e = w["text"], w["start"], w["end"]
        latin = not CJK.search(t)
        mergeable = (latin and cur_text is not None
                     and not CJK.search(cur_text)
                     and s - cur_end < 0.20)
        if mergeable:
            cur_text += t
            cur_end = e
        else:
            flush()
            cur_text, cur_start, cur_end = t, s, e
    flush()

    # Guarantee strictly increasing start times for the karaoke renderer.
    for i in range(1, len(tokens)):
        if tokens[i]["start"] <= tokens[i - 1]["start"]:
            tokens[i]["start"] = round(tokens[i - 1]["start"] + 0.05, 2)
            if tokens[i]["end"] <= tokens[i]["start"]:
                tokens[i]["end"] = round(tokens[i]["start"] + 0.05, 2)
    return tokens


def _split_on_gap(tokens: list, gap: float) -> list:
    phrases, cur = [], [tokens[0]]
    for prev, tok in zip(tokens, tokens[1:]):
        if tok["start"] - prev["end"] > gap:
            phrases.append(cur)
            cur = [tok]
        else:
            cur.append(tok)
    phrases.append(cur)
    return phrases


def segment_phrases(tokens: list, max_gap: float = 0.6,
                    target_count: int = None) -> list:
    """Split tokens into phrases on silences.

    max_gap: a silence longer than this starts a new phrase (seconds).
    target_count: if given, the gap threshold is tuned (binary search) to get
    as close as possible to this many phrases. Useful for verse songs where
    the structure is known (e.g. 7 verses x 8 phrases = 56).
    """
    if not tokens:
        return []
    phrases = _split_on_gap(tokens, max_gap)
    if target_count and len(phrases) != target_count:
        lo, hi, best = 0.10, 3.0, phrases
        for _ in range(14):
            mid = (lo + hi) / 2
            cand = _split_on_gap(tokens, mid)
            if len(cand) == target_count:
                best = cand
                break
            # Bigger gap -> fewer phrases.
            if len(cand) > target_count:
                lo = mid
            else:
                hi = mid
            if abs(len(cand) - target_count) < abs(len(best) - target_count):
                best = cand
        phrases = best
    out = []
    for p in phrases:
        out.append({
            "start": p[0]["start"],
            "end": p[-1]["end"],
            "text": "".join(t["text"] for t in p),
            "words": [(t["start"], t["text"]) for t in p],
        })
    return out


def build_timeline(audio_path: str, max_gap: float = 0.6,
                   target_count: int = None, trim: float = 0.0) -> dict:
    """Full pipeline: audio file -> phrase timeline with display tokens.

    trim: seconds to cut off the front (e.g. lead-in silence before singing).
    """
    words = get_words(audio_path)
    if trim:
        words = [{"text": w["text"],
                  "start": max(0.0, w["start"] - trim),
                  "end": w["end"] - trim}
                 for w in words if w["end"] > trim]
    tokens = clean_tokens(words)
    phrases = segment_phrases(tokens, max_gap=max_gap,
                              target_count=target_count)
    duration = tokens[-1]["end"] if tokens else 0.0
    return {
        "status": "success",
        "phrases": phrases,
        "phrase_count": len(phrases),
        "token_count": len(tokens),
        "duration": round(duration, 2),
    }
