"""Lesson templates: scene choreography for the four lesson formats.

The timing engine (lesson_timing_service) produces phrases; templates turn
phrases + a list of items into a scene plan for the renderer
(lesson_render_service).

Scene format (JSON-safe):
  {
    "start": 0.0, "end": 5.2,
    "background": "farm_barn",          # bg_<name>.png
    "stickers": [
      {"src": "prop_cow.png",           # assets/stickers/<src>
       "keyframes": [[0.0, 50, 82, 460], [1.0, 50, 82, 460]],
       # each keyframe: [t_frac, x_pct, y_pct, height_px]
       "fade_in": 0.3, "fade_out": 0.3}
    ],
    "characters": [                     # optional family, pinned poses
      {"src": "dad_pointing_right.png", "x_pct": 11, "y_base_pct": 96,
       "h_px": 600}
    ],
    "badge_image": "word_niu.png",      # optional, top-center w/ fade
    "transition_in": "cut" | "fade" | "slide",
  }

Item format:
  {"sticker": "prop_cow.png", "badge": "word_niu.png",
   "name_zh": "牛", "name_en": "cow"}
"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sticker(src, x_pct, y_pct, h_px, fade_in=0.3, fade_out=0.3,
             keyframes=None):
    kf = keyframes or [[0.0, x_pct, y_pct, h_px], [1.0, x_pct, y_pct, h_px]]
    return {"src": src, "keyframes": kf,
            "fade_in": fade_in, "fade_out": fade_out}


def _phrase_span(phrases, a, b):
    """Start/end covering phrases[a:b]."""
    return phrases[a]["start"], phrases[b - 1]["end"]


# ---------------------------------------------------------------------------
# 1. Verse Song (Old MacDonald pattern)
# ---------------------------------------------------------------------------
# N verses x P phrases. Per verse, 7 scenes:
#   family-only -> 1 animal -> CLOSE -> hard-cut FAR -> far -> 3 animals
#   -> family-only. Badge on while the animal is the focus.
# The two "sound" phrases each split in two (midpoint by default; pass
# split_fracs to fine-tune, e.g. [0.5, 0.6]).

def verse_song_scenes(phrases, items, opts=None):
    o = opts or {}
    ppv = int(o.get("phrases_per_verse", 8))
    bg = o.get("background", "farm_barn")
    family = o.get("family", True)
    split_fracs = o.get("split_fracs", [0.5, 0.6])
    n_verses = len(phrases) // ppv
    scenes = []
    for v in range(n_verses):
        base = v * ppv
        vp = phrases[base:base + ppv]
        item = items[v] if v < len(items) else {}
        sticker = item.get("sticker", "")
        badge = item.get("badge")
        fam = _family_chars() if family else []

        def sc(a, b, stickers, badge_on, transition="fade"):
            s, e = _phrase_span(vp, a, b)
            scenes.append({
                "start": round(s, 2), "end": round(e, 2),
                "background": bg, "stickers": stickers,
                "characters": fam,
                "badge_image": badge if badge_on else None,
                "transition_in": transition,
            })

        sc(0, 2, [], False)                                            # opening
        sc(2, 4, [_sticker(sticker, 50, 82, 460)], True)                # animal
        p4 = vp[4]                                                     # sounds line 1
        m1 = p4["start"] + (p4["end"] - p4["start"]) * split_fracs[0]
        scenes.append({"start": round(p4["start"], 2), "end": round(m1, 2),
                       "background": bg,
                       "stickers": [_sticker(sticker, 47, 88, 520)],
                       "characters": fam, "badge_image": badge,
                       "transition_in": "fade"})                        # CLOSE
        scenes.append({"start": round(m1, 2), "end": round(p4["end"], 2),
                       "background": bg,
                       "stickers": [_sticker(sticker, 79, 80, 300)],
                       "characters": fam, "badge_image": badge,
                       "transition_in": "cut"})                         # FAR (hard cut)
        p5 = vp[5]                                                     # sounds line 2
        m2 = p5["start"] + (p5["end"] - p5["start"]) * split_fracs[1]
        scenes.append({"start": round(p5["start"], 2), "end": round(m2, 2),
                       "background": bg,
                       "stickers": [_sticker(sticker, 79, 80, 300)],
                       "characters": fam, "badge_image": badge,
                       "transition_in": "fade"})
        scenes.append({"start": round(m2, 2), "end": round(p5["end"], 2),
                       "background": bg,
                       "stickers": [_sticker(sticker, 46, 68, 310),
                                    _sticker(sticker, 64, 84, 430),
                                    _sticker(sticker, 90, 74, 250)],
                       "characters": fam, "badge_image": badge,
                       "transition_in": "fade"})                        # 3 animals
        sc(6, 8, [], False)                                            # closing
    return scenes


def _family_chars():
    return [
        {"src": "dad_pointing_right.png", "x_pct": 11, "y_base_pct": 96,
         "h_px": 600},
        {"src": "mom_pointing_right.png", "x_pct": 21, "y_base_pct": 96,
         "h_px": 560},
        {"src": "levi_eyes_fixed.png", "x_pct": 13, "y_base_pct": 96,
         "h_px": 260},
        {"src": "luca_eyes_fixed.png", "x_pct": 18.5, "y_base_pct": 96,
         "h_px": 260},
    ]


# ---------------------------------------------------------------------------
# 2. Vocab Parade ("here are the fruits!")
# ---------------------------------------------------------------------------
# Phrases: [intro..., (item phrases)..., outro...].
# Each item gets one scene: sticker appears big, badge on, karaoke names it.

def vocab_parade_scenes(phrases, items, opts=None):
    o = opts or {}
    bg = o.get("background", "living_room")
    family = o.get("family", True)
    intro_n = int(o.get("intro_phrases", 1))
    outro_n = int(o.get("outro_phrases", 1))
    per_item = int(o.get("phrases_per_item", 1))
    fam = _family_chars() if family else []
    scenes = []
    idx = 0

    def add(a, b, stickers, badge, transition="fade"):
        s, e = _phrase_span(phrases, a, b)
        scenes.append({"start": round(s, 2), "end": round(e, 2),
                       "background": bg, "stickers": stickers,
                       "characters": fam,
                       "badge_image": badge,
                       "transition_in": transition})

    if intro_n:
        add(0, intro_n, [], None)
        idx = intro_n
    for item in items:
        n = per_item
        a, b = idx, min(idx + n, len(phrases) - outro_n)
        if a >= b:
            break
        add(a, b, [_sticker(item["sticker"], 55, 78, 520,
                            keyframes=[[0.0, 55, 78, 380],
                                       [0.35, 55, 78, 520],
                                       [1.0, 55, 78, 520]])],
            item.get("badge"))
        idx = b
    if outro_n and idx < len(phrases):
        # Finale: all items small across the scene.
        n = len(items)
        stickers = []
        for i, item in enumerate(items):
            x = 20 + (60 * i / max(1, n - 1)) if n > 1 else 50
            stickers.append(_sticker(item["sticker"], x, 70, 260))
        add(idx, len(phrases), stickers, None)
    return scenes


# ---------------------------------------------------------------------------
# 3. Routine / behavior ("brush your teeth", "share with friends")
# ---------------------------------------------------------------------------
# Like a vocab parade, but each step shows a character pose + a lesson badge.

def routine_scenes(phrases, items, opts=None):
    o = opts or {}
    bg = o.get("background", "bathroom")
    intro_n = int(o.get("intro_phrases", 1))
    outro_n = int(o.get("outro_phrases", 1))
    per_item = int(o.get("phrases_per_item", 1))
    scenes = []
    idx = 0

    def add(a, b, stickers, characters, badge, transition="fade"):
        s, e = _phrase_span(phrases, a, b)
        scenes.append({"start": round(s, 2), "end": round(e, 2),
                       "background": bg, "stickers": stickers,
                       "characters": characters,
                       "badge_image": badge,
                       "transition_in": transition})

    if intro_n:
        add(0, intro_n, [], _family_chars(), None)
        idx = intro_n
    for item in items:
        a, b = idx, min(idx + per_item, len(phrases) - outro_n)
        if a >= b:
            break
        chars = [{"src": item["pose"], "x_pct": 50, "y_base_pct": 96,
                  "h_px": item.get("h_px", 620)}] if item.get("pose") else []
        stickers = ([_sticker(item["sticker"], 72, 70, 340)]
                    if item.get("sticker") else [])
        add(a, b, stickers, chars, item.get("badge"))
        idx = b
    if outro_n and idx < len(phrases):
        add(idx, len(phrases), [], _family_chars(),
            items[-1].get("badge") if items else None)
    return scenes


# ---------------------------------------------------------------------------
# 4. Concepts (counting, colors)
# ---------------------------------------------------------------------------
# Like a vocab parade; each item carries a "concept_value" (e.g. "3", "紅色")
# drawn as a big badge so the concept lands visually.

def concepts_scenes(phrases, items, opts=None):
    o = opts or {}
    o = dict(o or {})
    # Concept value becomes the badge image when no badge is given.
    scenes = vocab_parade_scenes(phrases, items, o)
    return scenes


TEMPLATES = {
    "verse_song": {
        "name": "Verse Song",
        "description": "Repeating verses like Old MacDonald: family intro, "
                       "animal appears close then far, three-animal finale.",
        "builder": verse_song_scenes,
    },
    "vocab_parade": {
        "name": "Vocab Parade",
        "description": "Name each thing as it appears big: fruits, vehicles, "
                       "animals, toys. Finale shows everything together.",
        "builder": vocab_parade_scenes,
    },
    "routine": {
        "name": "Routine / Behavior",
        "description": "Step-by-step with character poses and lesson badges: "
                       "brush teeth, share, bedtime.",
        "builder": routine_scenes,
    },
    "concepts": {
        "name": "Concepts",
        "description": "Counting, colors, shapes: each item lands with its "
                       "concept value front and center.",
        "builder": concepts_scenes,
    },
}


def build_scenes(template_id: str, phrases: list, items: list,
                 opts: dict = None) -> list:
    """Build a scene plan from a template. Raises on unknown template."""
    t = TEMPLATES.get(template_id)
    if not t:
        raise ValueError(f"Unknown template '{template_id}'. "
                         f"Choose from: {', '.join(TEMPLATES)}")
    return t["builder"](phrases, items, opts or {})


def list_templates() -> list:
    return [{"id": tid, "name": t["name"], "description": t["description"]}
            for tid, t in TEMPLATES.items()]
