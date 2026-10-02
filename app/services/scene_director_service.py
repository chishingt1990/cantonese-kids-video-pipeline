import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.services.ai_service import generate_ai_text
from app.services.sticker_service import (
    STICKER_CATALOG,
    RELEASE_PROPS,
    get_or_render_sticker,
    normalize_sticker_info,
)
from app.services import family_catalog

logger = logging.getLogger(__name__)

PRESET_BACKGROUNDS = [
    "living_room", "nursery", "kitchen", "park", "beach",
    "playroom", "reading_nook", "dining", "bathroom", "mountains",
    "playground", "farm_field", "duck_pond", "backyard_garden",
    "art_room", "supermarket"
]

CHARACTER_POSES = {
    "levi": ["default", "sad", "waving", "pointing", "running", "arms_out_hug", "stretching", "eating", "sleeping", "jumping", "dancing", "brushing_teeth"],
    "luca": ["default", "waving", "clapping", "holding_toy", "eating", "sleeping", "jumping", "dancing", "brushing_teeth"],
    "dad": ["default", "sitting", "kneeling", "teaching", "waving", "drinking"],
    "mom": ["default", "kneeling_hug", "holding_fruit", "teaching"],
    "dog": ["default", "playing_ball", "running", "eating_banana"],
    "grandparents_paternal": ["default", "drinking_tea"],
    "grandparents_maternal": ["default", "waving"],
    "auntie_cousins": ["default", "waving"]
}

# Merge the family-expansion v3 catalog so new individual relative IDs and
# contact-sprite IDs survive director validation instead of silently collapsing
# to "default". New mom/dad poses extend the parents' allowlist in place so
# existing poses stay first in the list.
for _new_cid, _new_poses in family_catalog.individual_poses().items():
    _existing = CHARACTER_POSES.get(_new_cid, [])
    _merged = list(_existing)
    for _pose in _new_poses:
        if _pose not in _merged:
            _merged.append(_pose)
    CHARACTER_POSES[_new_cid] = _merged
for _contact in family_catalog.contact_sprites():
    # Contact sprites are a single composite; only "default" is valid so director
    # plans cannot ask for a pose that would collapse the composite.
    CHARACTER_POSES.setdefault(_contact["id"], ["default"])

# Reviewed bottom anchors for the new full-canvas 520px toddler exports.
STARTER_POSE_Y = {"jumping": 800 / 1080 * 100, "dancing": 880 / 1080 * 100, "brushing_teeth": 880 / 1080 * 100}
STARTER_BADGES = {s["id"]: s for s in STICKER_CATALOG if s["id"] in {
    "badge_routine_brush_teeth", "badge_routine_wash_hands", "badge_routine_eat",
    "badge_play_together_v1", "badge_take_turns_v1", "badge_bedtime_sleep",
}}


def _starter_action(text: str) -> Optional[str]:
    """Match concrete actions without treating 'jumpers' or 'dancefloor' as poses."""
    text = text.lower()
    if "刷牙" in text or re.search(r"\bbrush(?:ing|es|ed)?\s+(?:(?:my|your|his|her|our|their|the)\s+)?teeth\b", text):
        return "brushing_teeth"
    if any(word in text for word in ("跳舞", "舞蹈")) or re.search(r"\bdanc(?:e|es|ed|ing)\b", text):
        return "dancing"
    if any(word in text for word in ("跳起", "跳一跳", "跳跳", "蹦跳")) or re.search(r"\b(?:jump(?:s|ed|ing)?|hop(?:s|ped|ping)?)\b", text):
        return "jumping"
    return None


def _starter_badge(sticker_id: str) -> Dict[str, Any]:
    badge = dict(STARTER_BADGES[sticker_id])
    badge.update(content=badge["chinese"], x_percent=50.0, y_percent=22.0,
                 scale=1.0, rotation_deg=0.0, layer=2)
    return badge


def _expanded_prop(text: str) -> Optional[Dict[str, Any]]:
    for prop in sorted(RELEASE_PROPS, key=lambda p: len(p["english"]), reverse=True):
        if not prop["release_addition"]:
            continue
        english = re.escape(prop["english"].lower()).replace(r"\ ", r"\s+")
        if prop["chinese"] in text or re.search(r"\b" + english + r"s?\b", text.lower()):
            return prop
    return None


# Single source of truth for scale standards (matching 1080p canvas & render)
SCALE_STANDARDS = {
    "adult": 1.0,   # Base height 760px (~70% of 1080p)
    "toddler": 1.0, # Base height 520px (~48% of 1080p)
    "pet": 1.0      # Base height 320px (~30% of 1080p)
}

DIRECTOR_SYSTEM_PROMPT = """You are an award-winning Visual Scene Director for Cantonese preschool television (for toddlers age 1-3).
Your job is to read a scene script (dialogue, action cues, and moral lesson) and produce a mathematically precise 16:9 staging layout.

STAGE COORDINATE RULES:
- 16:9 Canvas coordinates are percentages from 0.0 to 100.0.
- Standard ground floor plane for character feet is y_percent = 88.0.
- Characters interacting must face each other: A character on the left (x < 50) facing right has flip = false. A character on the right (x > 50) facing left has flip = true.
- Characters scale: Adults = 1.0, Toddlers = 1.0, Dog = 1.0.
- Educational stickers: Limit to 1-2 high-impact items. Place stickers in upper safe zones (y_percent between 18.0 and 32.0, x_percent between 18.0 and 82.0). NEVER place stickers below y_percent = 72.0 (reserved for subtitles).
- Choose poses ONLY from available catalog:
  - levi: default, sad, waving, pointing, running, arms_out_hug, stretching, eating, sleeping, jumping, dancing, brushing_teeth
  - luca: default, waving, clapping, holding_toy, eating, sleeping, jumping, dancing, brushing_teeth
  - dad: default, sitting, kneeling, teaching, waving, drinking
  - mom: default, kneeling_hug, holding_fruit, teaching
  - dog: default, playing_ball, running, eating_banana
  - grandparents_paternal: default, drinking_tea
  - grandparents_maternal: default, waving
  - auntie_cousins: default, waving
- Choose background_id from: living_room, nursery, kitchen, park, beach, playroom, reading_nook, dining, bathroom, mountains, playground, farm_field, duck_pond, backyard_garden, art_room, supermarket.
- New twin action layouts: jumping uses y_percent 74.074 (airborne); dancing and brushing_teeth use 81.481. Use scale 1.0 and preserve reference hair direction (flip=false) unless the scene explicitly requires otherwise. Do not show dancing/jumping while brushing teeth. Prefer bathroom for toothbrushing and playroom for indoor dance.
- Prefer the approved word badges with their exact labels:
  badge_routine_brush_teeth: 刷牙 / BRUSH TEETH; badge_routine_wash_hands: 洗手 / WASH HANDS;
  badge_routine_eat: 食飯 / MEALTIME; badge_play_together_v1: 一齊玩 / PLAY TOGETHER;
  badge_take_turns_v1: 輪住玩 / TAKE TURNS; badge_bedtime_sleep: 瞓覺 / SLEEP.

Return ONLY a valid JSON object matching this schema:
{
  "background_id": "living_room",
  "characters": [
    {"name": "levi", "pose": "default", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": false, "layer": 1},
    {"name": "luca", "pose": "waving", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": true, "layer": 1}
  ],
  "stickers": [
    {"id": "badge_thank_you", "type": "word", "content": "多謝", "english": "Thank you", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2}
  ]
}
"""
DIRECTOR_SYSTEM_PROMPT += "\nApproved illustrated prop and shape IDs (reuse these PNGs, do not invent replacements):\n" + "\n".join(
    f"- {prop['id']} ({prop.get('category', 'props')}): {prop['chinese']} / {prop['english']}" for prop in RELEASE_PROPS
)

# Family-expansion v3 vocabulary (approved 2026-10-02). Appended rather than
# rewriting DIRECTOR_SYSTEM_PROMPT so the existing twin/parent/legacy pose
# listings above remain the canonical baseline for the prompt.
_family_lines = ["", "Approved family-expansion v3 characters and poses (keep existing group IDs available too):"]
for _cid, _poses in sorted(family_catalog.individual_poses().items()):
    _family_lines.append(f"- {_cid}: {', '.join(_poses)}")
_contact_entries = family_catalog.contact_sprites()
if _contact_entries:
    _family_lines.append(
        "Contact composite sprites (pose must be \"default\"; do NOT also stage the inner "
        "members separately, the sprite already contains both participants):"
    )
    for _entry in _contact_entries:
        _members = " + ".join(_entry["members"])
        _family_lines.append(f"- {_entry['id']}  ({_members}, action={_entry['action']})")
DIRECTOR_SYSTEM_PROMPT += "\n".join(_family_lines) + "\n"

def direct_single_scene(scene: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Uses LLM visual reasoning to direct a scene, with an instant deterministic heuristic fallback."""
    user_prompt = f"""Direct this preschool scene:
Scene Number: {scene.get('scene_number', 1)}
Title: {scene.get('title', '')}
Speaker: {scene.get('speaker', 'Dad')}
Cantonese Dialogue: {scene.get('cantonese', '')}
English: {scene.get('english', '')}
Target Vocab: {scene.get('vocab_highlight', '')}
Moral Lesson: {context.get('moral_lesson', '') if context else ''}
Current Background: {scene.get('background', 'living_room')}

Produce the complete JSON staging plan.
"""
    try:
        raw_response = generate_ai_text(user_prompt, DIRECTOR_SYSTEM_PROMPT)
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        data = json.loads(cleaned.strip())
        plan = _validate_and_sanitize_plan(data, scene)
        return plan
    except Exception as e:
        logger.warning(f"LLM visual director failed or busy ({e}). Employing deterministic heuristic director.")
        return _heuristic_fallback_director(scene, context)

def _validate_and_sanitize_plan(plan: Dict[str, Any], original_scene: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes coordinates, bounds, scale, and ensures asset catalog validity."""
    bg = plan.get("background_id", original_scene.get("background", "living_room"))
    if bg not in PRESET_BACKGROUNDS:
        bg = "living_room"
    
    chars = plan.get("characters", [])
    if not chars:
        return _heuristic_fallback_director(original_scene)

    # Composite contact sprites each already contain two or three family members.
    # When a plan contains multiple contacts whose members overlap (e.g.
    # ``contact_dad_luca_hug`` and ``contact_dad_cousin_younger_handholding``
    # both include dad), rendering both would draw the shared member twice.
    # Resolution rule: first valid contact wins; later contacts whose member
    # set intersects any already-kept contact are dropped. Then any standalone
    # member of a retained contact is also dropped so no inner participant is
    # drawn alongside its composite. This mirrors the pre-release rule of
    # resolving plan conflicts in document order (same ordering used by the
    # heuristic director when it stages multiple characters).
    kept_contact_members: set = set()
    kept_contacts: list = []
    filtered_chars: list = []
    for c in chars:
        name = c.get("name", "")
        if family_catalog.is_contact_id(name):
            members = set(family_catalog.contact_members(name) or [])
            if members & kept_contact_members:
                # Overlapping composite; skip to avoid double-rendering the
                # shared member.
                continue
            kept_contact_members |= members
            kept_contacts.append(name)
            filtered_chars.append(c)
        else:
            filtered_chars.append(c)
    # Second pass: drop standalone entries whose IDs are already shown inside
    # a retained contact composite. Non-member characters pass through.
    if kept_contact_members:
        filtered_chars = [
            c for c in filtered_chars
            if family_catalog.is_contact_id(c.get("name", ""))
            or c.get("name") not in kept_contact_members
        ]
    chars = filtered_chars
    plan["characters"] = chars
    if not chars:
        return _heuristic_fallback_director(original_scene)

    # Enforce multi-character dynamic slot separation
    n = len(chars)
    slots = _get_stage_slots(n)
    for i, c in enumerate(chars):
        c_name = c.get("name", "levi")
        valid_poses = CHARACTER_POSES.get(c_name, ["default"])
        if c.get("pose") not in valid_poses:
            c["pose"] = "default"
        
        # Clamp x_percent or assign slot if overlapping
        if "x_percent" not in c or c["x_percent"] is None:
            c["x_percent"] = slots[i]
        c["x_percent"] = max(8.0, min(92.0, float(c["x_percent"])))
        default_y = STARTER_POSE_Y.get(c["pose"], 88.0) if c_name in ("levi", "luca") else 88.0
        c["y_percent"] = max(60.0, min(92.0, float(c.get("y_percent", default_y))))
        c["scale"] = max(0.6, min(1.5, float(c.get("scale", 1.0))))
        c["flip"] = bool(c.get("flip", c["x_percent"] > 50))
        c["layer"] = int(c.get("layer", 1))

    # Validate stickers
    stickers = plan.get("stickers", [])
    valid_stickers = []
    for s in stickers:
        s = normalize_sticker_info(s)
        s_id = s.get("id")
        if s_id in STARTER_BADGES:
            # Keep plan coordinates, but never relabel an approved cached image.
            badge = STARTER_BADGES[s_id]
            s.update(type="word", content=badge["chinese"], chinese=badge["chinese"],
                     english=badge["english"], color_theme=badge["color_theme"])
        # Ensure sticker exists in catalog or render
        get_or_render_sticker(s)
        s["x_percent"] = max(10.0, min(90.0, float(s.get("x_percent", 50.0))))
        s["y_percent"] = max(15.0, min(68.0, float(s.get("y_percent", 24.0)))) # Above subtitles
        s["scale"] = max(0.6, min(1.5, float(s.get("scale", 1.0))))
        s["rotation_deg"] = max(-25.0, min(25.0, float(s.get("rotation_deg", 0.0))))
        s["layer"] = int(s.get("layer", 2))
        valid_stickers.append(s)

    return {
        "background": bg,
        "characters": chars,
        "stickers": valid_stickers
    }

def _get_stage_slots(n: int) -> List[float]:
    """Generates golden-ratio balanced horizontal slots so characters never overlap."""
    if n <= 1:
        return [50.0]
    elif n == 2:
        return [34.0, 66.0]
    elif n == 3:
        return [22.0, 50.0, 78.0]
    elif n == 4:
        return [16.0, 38.0, 62.0, 84.0]
    else:
        step = 80.0 / max(1, n - 1)
        return [10.0 + i * step for i in range(n)]

def _heuristic_fallback_director(scene: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic, instant rule-based visual staging for offline states."""
    text = (scene.get("cantonese", "") + " " + scene.get("english", "") + " " + scene.get("title", "") + " " + scene.get("speaker", "")).lower()
    vocab = scene.get("vocab_highlight", "")

    # 1. Background Selection: Preserve existing preset if valid
    bg = scene.get("background", "living_room")
    if bg not in PRESET_BACKGROUNDS:
        if any(k in text for k in ["art", "draw", "paint", "easel", "crayon", "畫畫", "彩色"]):
            bg = "art_room"
        elif any(k in text for k in ["supermarket", "grocery", "market", "shop", "cart", "買嘢", "超市", "市場"]):
            bg = "supermarket"
        elif any(k in text for k in ["playground", "swing", "slide", "滑梯", "鞦韆"]):
            bg = "playground"
        elif any(k in text for k in ["duck", "pond", "lake", "鴨仔", "水池"]):
            bg = "duck_pond"
        elif any(k in text for k in ["farm", "sheep", "sunflower", "田", "農場"]):
            bg = "farm_field"
        elif any(k in text for k in ["mountain", "hill", "hike", "野花", "山"]):
            bg = "mountains"
        elif any(k in text for k in ["dining", "dim sum", "tea", "yum cha", "飲茶", "點心"]):
            bg = "dining"
        elif any(k in text for k in ["backyard", "garden", "flower", "vegetable", "花園", "後院"]):
            bg = "backyard_garden"
        elif any(k in text for k in ["park", "lawn", "outside", "公園"]):
            bg = "park"
        elif any(k in text for k in ["beach", "sand", "sea", "ocean", "沙灘"]):
            bg = "beach"
        elif any(k in text for k in ["eat", "banana", "apple", "breakfast", "meal", "kitchen", "high chair", "食", "香蕉", "蘋果", "早餐"]):
            bg = "kitchen"
        elif any(k in text for k in ["sleep", "bed", "crib", "night", "star", "dream", "瞓", "晚安", "星"]):
            bg = "nursery"
        elif any(k in text for k in ["bath", "bubble", "wash", "沖涼"]):
            bg = "bathroom"
        elif any(k in text for k in ["book", "story", "read", "睇書"]):
            bg = "reading_nook"
        elif any(k in text for k in ["toy", "block", "car", "playroom", "玩", "積木"]):
            bg = "playroom"
        else:
            bg = "living_room"

    # 2. Four-Tier Pedagogical Milestone Parser
    chars: List[Dict[str, Any]] = []
    stickers: List[Dict[str, Any]] = []
    
    has_dog = any(k in text for k in ["dog", "spitz", "puppy", "波波", "狗"])
    has_dad = any(k in text for k in ["dad", "father", "爸爸"])
    has_mom = any(k in text for k in ["mom", "mother", "媽媽"])
    has_grandparents = any(k in text for k in ["grandpa", "grandma", "爺爺", "嫲嫲", "公公", "婆婆"])

    # Milestone Domain Detectors
    is_sadness = any(k in text for k in ["sad", "cry", "tear", "frown", "disappoint", "fly away", "lost", "掉", "唔開心", "喊", "飛走", "眼淚", "心痛", "安慰"])
    is_celebration = any(k in text for k in ["hooray", "cheer", "celebrate", "clap", "well done", "clever", "smart", "成功", "好叻", "拍手", "讚", "太棒"])
    is_hygiene = any(k in text for k in ["brush", "teeth", "wash", "hand", "bath", "soap", "bubble", "towel", "刷牙", "洗手", "沖涼", "抹手", "乾淨"])
    is_dim_sum = any(k in text for k in ["dim sum", "dumpling", "tea", "steamer", "har gow", "siu mai", "egg tart", "點心", "蝦餃", "燒賣", "蛋撻", "飲茶", "蒸籠"])
    is_mealtime = any(k in text for k in ["eat", "banana", "apple", "strawberry", "watermelon", "cookie", "milk", "fruit", "snack", "hungry", "bowl", "spoon", "breakfast", "meal", "yummy", "食", "水果", "早餐", "好味", "西瓜", "士多啤梨", "曲奇"])
    is_vehicle = any(k in text for k in ["bus", "car", "truck", "plane", "airplane", "train", "fire truck", "校巴", "車", "飛機", "火車", "消防車"])
    is_animal = any(k in text for k in ["duck", "cat", "kitty", "bunny", "rabbit", "frog", "鴨仔", "貓咪", "兔仔", "青蛙"])
    is_blocks = any(k in text for k in ["block", "tower", "stack", "abc", "積木", "搭積木"])
    is_art = any(k in text for k in ["art", "draw", "crayon", "paint", "rainbow", "畫畫", "蠟筆", "彩虹"])
    is_drawing_reading = any(k in text for k in ["book", "read", "story", "睇書", "講故事"])
    is_bedtime = any(k in text for k in ["sleep", "bed", "night", "star", "moon", "dream", "lullaby", "瞓", "晚安", "瞓覺", "發夢", "星星", "月亮"])
    is_hugging = any(k in text for k in ["hug", "arms", "love", "comfort", "cuddle", "抱抱", "我愛你"])
    is_waving = any(k in text for k in ["hello", "good morning", "hi", "bye", "goodbye", "早晨", "揮手", "你好", "拜拜"])
    action = _starter_action(text)
    expanded_prop = _expanded_prop(text)
    # Hygiene takes precedence over movement; sadness retains its existing priority.
    if is_hygiene and action != "brushing_teeth":
        action = None

    # 1. Emotional Disruption & Comfort Domain (Sadness, Lost Item, Empathy)
    if is_sadness:
        # Luca is crying or Levi is sad
        chars.append({"name": "luca", "pose": "crying", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 28.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "comforting_hug", "scale": 1.0, "x_percent": 28.0, "y_percent": 86.0, "flip": False, "layer": 1})
        else:
            chars.append({"name": "levi", "pose": "arms_out_hug", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
            
        stickers.append({"id": "prop_comfort_hearts", "type": "icon", "content": "comfort_hearts", "x_percent": 50.0, "y_percent": 38.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_calm_down", "type": "word", "content": "深呼吸", "english": "Deep Breath & Hug", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif action:
        if scene.get("background") not in PRESET_BACKGROUNDS:
            bg = "bathroom" if action == "brushing_teeth" else "playroom"
        for name, x in (("levi", 34.0), ("luca", 66.0)):
            chars.append({"name": name, "pose": action, "scale": 1.0, "x_percent": x,
                          "y_percent": STARTER_POSE_Y[action], "flip": False, "layer": 1})
        badge_id = "badge_routine_brush_teeth" if action == "brushing_teeth" else "badge_play_together_v1"
        stickers.append(_starter_badge(badge_id))

    # 2. Celebration & Milestone Domain (Scene 6 or Praises)
    elif is_celebration:
        chars.append({"name": "levi", "pose": "cheering", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "cheering", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dad:
            chars.append({"name": "dad", "pose": "clapping", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_mom:
            chars.append({"name": "mom", "pose": "clapping", "scale": 1.0, "x_percent": 84.0, "y_percent": 86.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "dancing_paw", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
            
        stickers.append({"id": "prop_sparkle_cluster", "type": "icon", "content": "sparkle_cluster", "x_percent": 50.0, "y_percent": 38.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_well_done", "type": "word", "content": "好叻仔！", "english": "Well Done!", "color_theme": "emerald", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif expanded_prop and not is_hygiene:
        if scene.get("background") not in PRESET_BACKGROUNDS:
            bg = {"animals": "park", "vehicles": "park", "fruit_vegetables": "kitchen",
                  "food_snacks": "kitchen", "foodfruit": "kitchen", "everyday_props": "playroom",
                  "toys": "playroom", "shapes": "playroom"}.get(expanded_prop["category"], "playroom")
        chars.extend([
            {"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 28.0, "y_percent": 81.481, "flip": False, "layer": 1},
            {"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 72.0, "y_percent": 81.481, "flip": True, "layer": 1},
        ])
        sticker = dict(expanded_prop)
        sticker.update(x_percent=50.0, y_percent=30.0, scale=1.0, rotation_deg=0.0, layer=2)
        stickers.append(sticker)

    # 3. Vehicle & Transport Domain
    elif is_vehicle:
        chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "cheering", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "running", "scale": 1.0, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        
        v_prop = "prop_bus" if "bus" in text or "校巴" in text else ("prop_fire_truck" if "fire" in text or "消防" in text else ("prop_airplane" if "plane" in text or "飛機" in text else ("prop_train" if "train" in text or "火車" in text else "prop_toy_car")))
        stickers.append({"id": v_prop, "type": "icon", "content": v_prop.replace("prop_", ""), "x_percent": 50.0, "y_percent": 76.0, "scale": 1.15, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_vehicle", "type": "word", "content": "好快好得意", "english": "Zoom Zoom!", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 4. Animal Friends Domain
    elif is_animal:
        chars.append({"name": "levi", "pose": "thinking", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "pointing", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "sitting_attentive", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
        
        a_prop = "prop_duckling" if "duck" in text or "鴨仔" in text else ("prop_kitty_cat" if "cat" in text or "貓" in text else ("prop_bunny" if "bunny" in text or "rabbit" in text or "兔" in text else "prop_frog"))
        stickers.append({"id": a_prop, "type": "icon", "content": a_prop.replace("prop_", ""), "x_percent": 50.0, "y_percent": 76.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_animals", "type": "word", "content": "可愛小動物", "english": "Cute Animals", "color_theme": "emerald", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 5. Art, Drawing & Colors Domain
    elif is_art:
        chars.append({"name": "levi", "pose": "holding_book", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        stickers.append({"id": "prop_crayons", "type": "icon", "content": "crayons", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "prop_rainbow", "type": "icon", "content": "rainbow", "x_percent": 80.0, "y_percent": 25.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_colors", "type": "word", "content": "美麗色彩", "english": "Colorful Art", "color_theme": "rose", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 6. Hygiene Domain (Bathroom Routine)
    elif is_hygiene:
        chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 36.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "teaching", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "teaching", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        
        stickers.append({"id": "prop_toothbrush_blue", "type": "icon", "content": "toothbrush_blue", "x_percent": 42.0, "y_percent": 74.0, "scale": 0.85, "rotation_deg": -15.0, "layer": 3})
        stickers.append({"id": "prop_soap_bubbles", "type": "icon", "content": "soap_bubbles", "x_percent": 72.0, "y_percent": 30.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_hygiene", "type": "word", "content": "一齊刷牙", "english": "Brush Teeth Together", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 7. Mealtime & Dim Sum Domain
    elif is_dim_sum or (is_mealtime and has_grandparents):
        gp_name = "grandparents_paternal" if any(k in text for k in ["爺爺", "嫲嫲"]) else "grandparents_maternal"
        chars.append({"name": gp_name, "pose": "drinking_tea", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        chars.append({"name": "levi", "pose": "eating", "scale": 1.0, "x_percent": 58.0, "y_percent": 88.0, "flip": False, "layer": 2})
        chars.append({"name": "luca", "pose": "eating", "scale": 1.0, "x_percent": 78.0, "y_percent": 88.0, "flip": True, "layer": 2})
        stickers.append({"id": "prop_dim_sum_basket", "type": "icon", "content": "dim_sum_basket", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_dim_sum", "type": "word", "content": "飲茶食點心", "english": "Yummy Dim Sum", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif is_mealtime:
        if has_mom:
            chars.append({"name": "mom", "pose": "holding_bowl", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "sitting", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        chars.append({"name": "levi", "pose": "eating", "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
        chars.append({"name": "luca", "pose": "eating", "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        if has_dog or "banana" in text:
            chars.append({"name": "dog", "pose": "eating_banana", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
        
        m_prop = "prop_strawberry" if "strawberry" in text or "士多啤梨" in text else ("prop_watermelon_slice" if "watermelon" in text or "西瓜" in text else ("prop_cookie" if "cookie" in text or "餅" in text else "prop_fruit_plate"))
        stickers.append({"id": m_prop, "type": "icon", "content": m_prop.replace("prop_", ""), "x_percent": 50.0, "y_percent": 78.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_mealtime", "type": "word", "content": "好美味！", "english": "So Yummy!", "color_theme": "gold", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 8. Play, Cognitive & Blocks Domain
    elif is_blocks:
        chars.append({"name": "levi", "pose": "sitting_floor", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "sitting_floor", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "sitting_attentive", "scale": 1.0, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        
        stickers.append({"id": "prop_block_tower", "type": "icon", "content": "block_tower", "x_percent": 50.0, "y_percent": 80.0, "scale": 1.15, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_play_together", "type": "word", "content": "輪流玩", "english": "Take Turns & Share", "color_theme": "purple", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif is_drawing_reading:
        if has_dad:
            chars.append({"name": "dad", "pose": "teaching", "scale": 1.0, "x_percent": 30.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "holding_book", "scale": 1.0, "x_percent": 56.0, "y_percent": 88.0, "flip": True, "layer": 2})
            chars.append({"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 74.0, "y_percent": 88.0, "flip": True, "layer": 2})
        else:
            chars.append({"name": "levi", "pose": "holding_book", "scale": 1.0, "x_percent": 36.0, "y_percent": 88.0, "flip": False, "layer": 1})
            chars.append({"name": "luca", "pose": "pointing", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        stickers.append({"id": "prop_picture_book", "type": "icon", "content": "picture_book", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_reading", "type": "word", "content": "睇故事書", "english": "Storybook Time", "color_theme": "rose", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 9. Bedtime & Sleep Domain
    elif is_bedtime:
        chars.append({"name": "levi", "pose": "sleeping", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "sleeping", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "kneeling", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "curled_sleeping", "scale": 0.9, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        stickers.append({"id": "prop_star", "type": "icon", "content": "star", "x_percent": 80.0, "y_percent": 26.0, "scale": 1.1, "rotation_deg": 10.0, "layer": 2})
        stickers.append({"id": "badge_goodnight", "type": "word", "content": "晚安早抖", "english": "Sweet Dreams", "color_theme": "indigo", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 10. Hugging, Love & Manners (Default Warm Preschool Staging)
    else:
        if has_dad:
            chars.append({"name": "dad", "pose": "kneeling", "scale": 1.0, "x_percent": 26.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "thinking"), "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
            chars.append({"name": "luca", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        elif has_mom:
            chars.append({"name": "mom", "pose": "waving" if is_waving else "kneeling_hug", "scale": 1.0, "x_percent": 26.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else "default", "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
            chars.append({"name": "luca", "pose": "waving", "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        else:
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
            chars.append({"name": "luca", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        
        if has_dog:
            chars.append({"name": "dog", "pose": "sitting_attentive", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})

        if is_hugging:
            stickers.append({"id": "prop_comfort_hearts", "type": "icon", "content": "comfort_hearts", "x_percent": 50.0, "y_percent": 42.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
            stickers.append({"id": "badge_big_hug", "type": "word", "content": "抱抱", "english": "Big Warm Hug", "color_theme": "pink", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
        elif is_waving or any(k in text for k in ["good morning", "早晨"]):
            stickers.append({"id": "badge_good_morning", "type": "word", "content": "早晨", "english": "Good morning", "color_theme": "gold", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
        elif vocab:
            stickers.append({"id": f"badge_vocab_{vocab[:6]}", "type": "word", "content": vocab, "english": "Learn", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})

    # Use approved labels for explicit lesson cues, without replacing emotion badges.
    if not is_sadness:
        badge_id = None
        if any(word in text for word in ("洗手",)) or re.search(r"\bwash(?:ing)?\s+(?:(?:your|my|our|their|his|her|the)\s+)?hands\b", text):
            badge_id = "badge_routine_wash_hands"
        elif "輪住玩" in text or "輪流玩" in text or re.search(r"\btak(?:e|ing)\s+turns\b", text):
            badge_id = "badge_take_turns_v1"
        elif "一齊玩" in text or re.search(r"\bplay(?:ing)?\s+together\b", text):
            badge_id = "badge_play_together_v1"
        elif "食飯" in text or re.search(r"\bmealtime\b", text):
            badge_id = "badge_routine_eat"
        elif "瞓覺" in text or re.search(r"\b(?:sleep|sleeping|bedtime)\b", text):
            badge_id = "badge_bedtime_sleep"
        if badge_id and action != "brushing_teeth":
            stickers = [s for s in stickers if s.get("type") != "word"]
            stickers.append(_starter_badge(badge_id))

    return {
        "background": bg,
        "characters": chars,
        "stickers": stickers
    }

def auto_direct_entire_project(project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Batch directs all scenes in an episode project."""
    scenes = project_data.get("scenes", [])
    directed_scenes = []
    context = {
        "title": project_data.get("title_cantonese", ""),
        "theme": project_data.get("theme", ""),
        "age_group": project_data.get("age_group", "1-2"),
        "moral_lesson": project_data.get("moral_lesson", "")
    }

    for idx, s in enumerate(scenes):
        s_copy = dict(s)
        s_copy["scene_number"] = idx + 1
        plan = direct_single_scene(s_copy, context)
        s_copy["background"] = plan["background"]
        s_copy["characters"] = plan["characters"]
        s_copy["stickers"] = plan["stickers"]
        directed_scenes.append(s_copy)

    return directed_scenes

def apply_copilot_tweak(current_scene: Dict[str, Any], instruction: str) -> Dict[str, Any]:
    """Applies an instant natural language tweak to the active scene."""
    inst_lower = instruction.lower()
    updated = dict(current_scene)
    chars = [dict(c) for c in updated.get("characters", [])]
    stickers = [dict(s) for s in updated.get("stickers", [])]

    # 1. Background tweaks
    if any(k in inst_lower for k in ["art", "painting", "easel", "畫畫"]):
        updated["background"] = "art_room"
    elif any(k in inst_lower for k in ["supermarket", "grocery", "market", "超市", "市場"]):
        updated["background"] = "supermarket"
    elif any(k in inst_lower for k in ["mountain", "hill", "wildflower", "山", "花"]):
        updated["background"] = "mountains"
    elif any(k in inst_lower for k in ["beach", "ocean", "sandcastle", "沙灘", "海"]):
        updated["background"] = "beach"
    elif any(k in inst_lower for k in ["park", "garden", "lawn", "picnic", "公園", "草地"]):
        updated["background"] = "park"
    elif any(k in inst_lower for k in ["dining", "dim sum", "tea", "飯廳", "點心"]):
        updated["background"] = "dining"
    elif any(k in inst_lower for k in ["kitchen", "high chair", "廚房"]):
        updated["background"] = "kitchen"
    elif any(k in inst_lower for k in ["nursery", "bedroom", "star", "night", "房", "瞓"]):
        updated["background"] = "nursery"
    elif any(k in inst_lower for k in ["playroom", "toy room", "toys", "玩具"]):
        updated["background"] = "playroom"
    elif any(k in inst_lower for k in ["reading", "bookshelf", "story", "睇書"]):
        updated["background"] = "reading_nook"
    elif any(k in inst_lower for k in ["bath", "bubble", "duck", "沖涼"]):
        updated["background"] = "bathroom"
    elif any(k in inst_lower for k in ["living room", "sofa", "couch", "客廳"]):
        updated["background"] = "living_room"

    # 2. Character presence & poses
    # Add or pose dog
    if any(k in inst_lower for k in ["dog", "spitz", "波波", "狗"]):
        dog_char = next((c for c in chars if c["name"] == "dog"), None)
        dog_pose = "eating_banana" if any(k in inst_lower for k in ["banana", "香蕉", "eat"]) else ("dancing_paw" if any(k in inst_lower for k in ["dance", "cheer", "jump"]) else ("curled_sleeping" if any(k in inst_lower for k in ["sleep", "nap"]) else "sitting_attentive"))
        if not dog_char:
            chars.append({"name": "dog", "pose": dog_pose, "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
        else:
            dog_char["pose"] = dog_pose

    # Levi pose tweak
    if "levi" in inst_lower or "哥哥" in inst_lower or "brother" in inst_lower:
        levi_char = next((c for c in chars if c["name"] == "levi"), None)
        if levi_char:
            if any(k in inst_lower for k in ["banana", "香蕉", "eat", "食"]):
                levi_char["pose"] = "eating"
            elif any(k in inst_lower for k in ["think", "curious", "諗", "思考"]):
                levi_char["pose"] = "thinking"
            elif any(k in inst_lower for k in ["cheer", "hooray", "celebrate", "開心", "好叻"]):
                levi_char["pose"] = "cheering"
            elif any(k in inst_lower for k in ["sad", "cry", "tear", "唔開心", "喊"]):
                levi_char["pose"] = "sad"
            elif any(k in inst_lower for k in ["book", "read", "story", "睇書"]):
                levi_char["pose"] = "holding_book"
            elif any(k in inst_lower for k in ["sit", "floor", "mat", "坐"]):
                levi_char["pose"] = "sitting_floor"
            elif any(k in inst_lower for k in ["hug", "arms", "抱抱"]):
                levi_char["pose"] = "arms_out_hug"
            elif any(k in inst_lower for k in ["wave", "hello", "揮手"]):
                levi_char["pose"] = "waving"
            elif any(k in inst_lower for k in ["sleep", "yawn", "stretch", "瞓"]):
                levi_char["pose"] = "sleeping"

    # Luca pose tweak
    if "luca" in inst_lower or "細佬" in inst_lower:
        luca_char = next((c for c in chars if c["name"] == "luca"), None)
        if luca_char:
            if any(k in inst_lower for k in ["banana", "fruit", "eat", "食"]):
                luca_char["pose"] = "eating"
            elif any(k in inst_lower for k in ["cry", "sad", "tear", "喊", "唔開心"]):
                luca_char["pose"] = "crying"
            elif any(k in inst_lower for k in ["cheer", "hooray", "celebrate", "好叻"]):
                luca_char["pose"] = "cheering"
            elif any(k in inst_lower for k in ["point", "look", "睇下", "指"]):
                luca_char["pose"] = "pointing"
            elif any(k in inst_lower for k in ["hug", "arms", "抱抱"]):
                luca_char["pose"] = "arms_out_hug"
            elif any(k in inst_lower for k in ["sit", "floor", "mat", "坐"]):
                luca_char["pose"] = "sitting_floor"
            elif any(k in inst_lower for k in ["clap", "拍手"]):
                luca_char["pose"] = "clapping"
            elif any(k in inst_lower for k in ["wave", "hello", "揮手"]):
                luca_char["pose"] = "waving"
            elif any(k in inst_lower for k in ["sleep", "瞓"]):
                luca_char["pose"] = "sleeping"

    # 3. Sticker tweaks
    action = _starter_action(inst_lower)
    if action:
        for c in chars:
            name = c.get("name")
            if name in ("levi", "luca") and (name in inst_lower or ("哥哥" if name == "levi" else "細佬") in inst_lower):
                c["pose"] = action
                c.setdefault("y_percent", STARTER_POSE_Y[action])

    if any(k in inst_lower for k in ["thank you", "多謝"]):
        if not any(s.get("id") == "badge_thank_you" for s in stickers):
            stickers.append({"id": "badge_thank_you", "type": "word", "content": "多謝", "english": "Thank you", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
    elif any(k in inst_lower for k in ["please", "唔該"]):
        if not any(s.get("id") == "badge_please" for s in stickers):
            stickers.append({"id": "badge_please", "type": "word", "content": "唔該", "english": "Please", "color_theme": "emerald", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
    elif any(k in inst_lower for k in ["banana", "香蕉"]):
        if not any(s.get("id") == "prop_banana" for s in stickers):
            stickers.append({"id": "prop_banana", "type": "icon", "content": "banana", "x_percent": 78.0, "y_percent": 25.0, "scale": 1.1, "rotation_deg": 8.0, "layer": 2})
    elif any(k in inst_lower for k in ["bus", "school bus", "校巴"]):
        if not any(s.get("id") == "prop_bus" for s in stickers):
            stickers.append({"id": "prop_bus", "type": "icon", "content": "bus", "x_percent": 50.0, "y_percent": 76.0, "scale": 1.15, "rotation_deg": 0.0, "layer": 3})
    elif any(k in inst_lower for k in ["car", "toy car", "車"]):
        if not any(s.get("id") == "prop_toy_car" for s in stickers):
            stickers.append({"id": "prop_toy_car", "type": "icon", "content": "toy_car", "x_percent": 22.0, "y_percent": 26.0, "scale": 1.1, "rotation_deg": -5.0, "layer": 2})
    elif any(k in inst_lower for k in ["abc", "blocks", "block", "積木"]):
        if not any(s.get("id") == "block_a" for s in stickers):
            stickers.append({"id": "block_a", "type": "letter", "content": "A", "color_theme": "rose", "x_percent": 20.0, "y_percent": 24.0, "scale": 1.0, "rotation_deg": -6.0, "layer": 2})

    updated["characters"] = chars
    updated["stickers"] = stickers
    return updated
