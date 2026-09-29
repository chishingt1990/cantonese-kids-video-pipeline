import json
import logging
import re
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.services.ai_service import generate_ai_text
from app.services.sticker_service import STICKER_CATALOG, get_or_render_sticker
from app.services import asset_manifest as assets

logger = logging.getLogger(__name__)

_WORD_FORMS = {
    "read": ("reading",), "teach": ("teaches", "teaching"), "eat": ("eats", "eating"),
    "cry": ("crying", "cries"), "cheer": ("cheering",), "celebrate": ("celebrating",),
    "clap": ("clapping",), "point": ("pointing",), "think": ("thinking",),
    "sleep": ("sleeping",), "wave": ("waving",), "hug": ("hugging",),
    "sit": ("sitting",), "wash": ("washing",), "brush": ("brushing",),
    "draw": ("drawing",), "paint": ("painting",), "stack": ("stacking",),
    "toy": ("toys",), "block": ("blocks",), "book": ("books", "storybook"),
}


def _has(text, *words):
    for word in words:
        pattern = "(?:" + "|".join(re.escape(w) for w in (word, *_WORD_FORMS.get(word, ()))) + ")"
        if word.isascii():
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            prefix = text[max(0, match.start() - 24):match.start()].lower()
            if re.search(r"(?:not|no|don't|do not|without)(?:\s+add)?\s+(?:the\s+)?$", prefix):
                continue
            if not word.startswith(("唔", "冇")) and prefix.endswith(("唔", "冇")):
                continue
            return True
    return False


def _number(value, low, high):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Scene coordinates must be finite")
    return max(low, min(high, value))

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
- Choose character names, poses and background_id ONLY from the authoritative catalogue appended below.
- Preserve the current background unless explicitly instructed otherwise.

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
        catalogue = json.dumps({"poses": assets.get_character_poses(),
                               "backgrounds": [b["id"] for b in assets.list_backgrounds()]})
        raw_response = generate_ai_text(user_prompt, DIRECTOR_SYSTEM_PROMPT + "\nCurrent authoritative catalogue:\n" + catalogue)
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        data = json.loads(cleaned.strip())
        plan = _validate_and_sanitize_plan(data, scene)
        plan["direction_method"] = "ai"
        return plan
    except Exception as e:
        logger.warning(f"LLM visual director failed or busy ({e}). Employing deterministic heuristic director.")
        plan = _heuristic_fallback_director(scene, context)
        plan["direction_method"] = "deterministic_fallback"
        plan.setdefault("warnings", []).append("AI direction unavailable or invalid; deterministic staging used.")
        return plan

def _validate_and_sanitize_plan(plan: Dict[str, Any], original_scene: Dict[str, Any], allow_empty=False) -> Dict[str, Any]:
    """Sanitizes coordinates, bounds, scale, and ensures asset catalog validity."""
    bg = plan.get("background_id", plan.get("background", original_scene.get("background", "living_room")))
    if str(original_scene.get("background", "")).startswith("custom_"):
        bg = original_scene["background"]
    assets.resolve_background(bg)
    
    chars = [dict(c) for c in plan.get("characters", [])]
    if not chars and not allow_empty:
        raise ValueError("A directed scene requires characters")
    available = assets.get_character_poses()

    # Enforce multi-character dynamic slot separation
    n = len(chars)
    slots = _get_stage_slots(n)
    for i, c in enumerate(chars):
        c_name = c.get("name")
        if c_name not in available:
            raise ValueError(f"Unknown character: {c_name}")
        assets.resolve_sprite(c_name, c.get("pose", "default"))
        
        # Clamp x_percent or assign slot if overlapping
        if "x_percent" not in c or c["x_percent"] is None:
            c["x_percent"] = slots[i]
        c["x_percent"] = _number(c["x_percent"], 8, 92)
        c["y_percent"] = _number(c.get("y_percent", 88.0), 60, 92)
        c["scale"] = _number(c.get("scale", 1.0), .6, 1.5)
        if "flip" in c and not isinstance(c["flip"], bool):
            raise ValueError("Character flip must be boolean")
        c["flip"] = c.get("flip", c["x_percent"] > 50)
        c["layer"] = int(c.get("layer", 1))

    # Validate stickers
    stickers = plan.get("stickers", [])
    valid_stickers = []
    for original in stickers:
        s = dict(original)
        s["id"] = Path(get_or_render_sticker(s)).stem
        s["x_percent"] = _number(s.get("x_percent", 50.0), 10, 90)
        s["y_percent"] = _number(s.get("y_percent", 24.0), 15, 68)
        s["scale"] = _number(s.get("scale", 1.0), .6, 1.5)
        s["rotation_deg"] = _number(s.get("rotation_deg", 0.0), -25, 25)
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
    bg = scene.get("background")
    if bg not in {b["id"] for b in assets.list_backgrounds()}:
        if _has(text, "art", "draw", "paint", "easel", "crayon", "畫畫", "彩色"):
            bg = "art_room"
        elif _has(text, "supermarket", "grocery", "market", "shop", "cart", "買嘢", "超市", "市場"):
            bg = "supermarket"
        elif _has(text, "playground", "swing", "slide", "滑梯", "鞦韆"):
            bg = "playground"
        elif _has(text, "duck", "pond", "lake", "鴨仔", "水池"):
            bg = "duck_pond"
        elif _has(text, "farm", "sheep", "sunflower", "田", "農場"):
            bg = "farm_field"
        elif _has(text, "mountain", "hill", "hike", "野花", "山"):
            bg = "mountains"
        elif _has(text, "dining", "dim sum", "tea", "yum cha", "飲茶", "點心"):
            bg = "dining"
        elif _has(text, "backyard", "garden", "flower", "vegetable", "花園", "後院"):
            bg = "backyard_garden"
        elif _has(text, "park", "lawn", "outside", "公園"):
            bg = "park"
        elif _has(text, "beach", "sand", "sea", "ocean", "沙灘"):
            bg = "beach"
        elif _has(text, "eat", "banana", "apple", "breakfast", "meal", "kitchen", "high chair", "食", "香蕉", "蘋果", "早餐"):
            bg = "kitchen"
        elif _has(text, "sleep", "bed", "crib", "night", "star", "dream", "瞓", "晚安", "星"):
            bg = "nursery"
        elif _has(text, "bath", "bubble", "wash", "沖涼"):
            bg = "bathroom"
        elif _has(text, "book", "story", "read", "睇書"):
            bg = "reading_nook"
        elif _has(text, "toy", "block", "car", "playroom", "玩", "積木"):
            bg = "playroom"
        else:
            bg = "living_room"

    # 2. Four-Tier Pedagogical Milestone Parser
    chars: List[Dict[str, Any]] = []
    stickers: List[Dict[str, Any]] = []
    
    has_dog = _has(text, "dog", "spitz", "puppy", "波波", "狗")
    has_dad = _has(text, "dad", "father", "爸爸")
    has_mom = _has(text, "mom", "mother", "媽媽")
    has_grandparents = _has(text, "grandpa", "grandma", "爺爺", "嫲嫲", "公公", "婆婆")

    # Milestone Domain Detectors
    is_sadness = _has(text, "sad", "cry", "tear", "frown", "disappoint", "fly away", "lost", "掉", "唔開心", "喊", "飛走", "眼淚", "心痛", "安慰")
    is_celebration = _has(text, "hooray", "cheer", "celebrate", "clap", "well done", "clever", "smart", "成功", "好叻", "拍手", "讚", "太棒")
    is_hygiene = _has(text, "brush", "teeth", "wash", "hand", "bath", "soap", "bubble", "towel", "刷牙", "洗手", "沖涼", "抹手", "乾淨")
    is_dim_sum = _has(text, "dim sum", "dumpling", "tea", "steamer", "har gow", "siu mai", "egg tart", "點心", "蝦餃", "燒賣", "蛋撻", "飲茶", "蒸籠")
    is_mealtime = _has(text, "eat", "banana", "apple", "strawberry", "watermelon", "cookie", "milk", "fruit", "snack", "hungry", "bowl", "spoon", "breakfast", "meal", "yummy", "食", "水果", "早餐", "好味", "西瓜", "士多啤梨", "曲奇")
    is_vehicle = _has(text, "bus", "car", "truck", "plane", "airplane", "train", "fire truck", "校巴", "車", "飛機", "火車", "消防車")
    is_animal = _has(text, "duck", "cat", "kitty", "bunny", "rabbit", "frog", "鴨仔", "貓咪", "兔仔", "青蛙")
    is_blocks = _has(text, "block", "blocks", "tower", "stack", "abc", "積木", "搭積木")
    is_art = _has(text, "art", "draw", "crayon", "paint", "rainbow", "畫畫", "蠟筆", "彩虹")
    is_drawing_reading = _has(text, "book", "read", "story", "睇書", "講故事")
    is_bedtime = _has(text, "sleep", "bed", "night", "star", "moon", "dream", "lullaby", "瞓", "晚安", "瞓覺", "發夢", "星星", "月亮")
    is_hugging = _has(text, "hug", "arms", "love", "comfort", "cuddle", "抱抱", "我愛你")
    is_waving = _has(text, "hello", "good morning", "hi", "bye", "goodbye", "早晨", "揮手", "你好", "拜拜")

    # 1. Emotional Disruption & Comfort Domain (Sadness, Lost Item, Empathy)
    if is_sadness:
        sad_child = "levi" if _has(text, "levi", "哥哥") and not _has(text, "luca", "細佬") else "luca"
        chars.append({"name": sad_child, "pose": "sad" if sad_child == "levi" else "crying", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 28.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "comforting_hug", "scale": 1.0, "x_percent": 28.0, "y_percent": 86.0, "flip": False, "layer": 1})
        else:
            chars.append({"name": "luca" if sad_child == "levi" else "levi", "pose": "arms_out_hug", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
            
        stickers.append({"id": "prop_comfort_hearts", "type": "icon", "content": "comfort_hearts", "x_percent": 50.0, "y_percent": 38.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_calm_down", "type": "word", "content": "深呼吸", "english": "Deep Breath & Hug", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

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

    # 3. Vehicle & Transport Domain
    elif is_vehicle:
        chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "cheering", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "running", "scale": 1.0, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        
        v_prop = "prop_bus" if _has(text, "bus", "校巴") else ("prop_fire_truck" if _has(text, "fire", "消防") else ("prop_airplane" if _has(text, "plane", "airplane", "飛機") else ("prop_train" if _has(text, "train", "火車") else "prop_toy_car")))
        stickers.append({"id": v_prop, "type": "icon", "content": v_prop.replace("prop_", ""), "x_percent": 50.0, "y_percent": 76.0, "scale": 1.15, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_vehicle", "type": "word", "content": "好快好得意", "english": "Zoom Zoom!", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 4. Animal Friends Domain
    elif is_animal:
        chars.append({"name": "levi", "pose": "thinking", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "pointing", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "sitting_attentive", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
        
        a_prop = "prop_duckling" if _has(text, "duck", "鴨仔") else ("prop_kitty_cat" if _has(text, "cat", "kitty", "貓") else ("prop_bunny" if _has(text, "bunny", "rabbit", "兔") else "prop_frog"))
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
        if has_grandparents:
            gp_name = "grandparents_paternal" if any(k in text for k in ["爺爺", "嫲嫲"]) else "grandparents_maternal"
            chars.append({"name": gp_name, "pose": "drinking_tea", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad or has_mom:
            chars.append({"name": "dad" if has_dad else "mom", "pose": "drinking" if has_dad else "holding_bowl",
                          "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
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
        elif _has(text, "bye", "goodbye", "拜拜"):
            stickers.append({"id": "badge_goodbye", "type": "word", "content": "拜拜", "english": "Goodbye", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0})
        elif _has(text, "good morning", "早晨"):
            stickers.append({"id": "badge_good_morning", "type": "word", "content": "早晨", "english": "Good morning", "color_theme": "gold", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
        elif is_waving:
            stickers.append({"id": "badge_hello", "type": "word", "content": "你好", "english": "Hello", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0})
        elif vocab:
            stickers.append({"id": f"badge_vocab_{vocab[:6]}", "type": "word", "content": vocab, "english": "Learn", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})

    warnings = []
    available = assets.get_character_poses()
    for char in chars:
        pose = char["pose"]
        if pose not in available.get(char["name"], []):
            alternatives = {"sitting_floor": "playing_blocks", "drinking_tea": "default"}
            replacement = alternatives.get(pose, "default")
            if replacement not in available.get(char["name"], []):
                raise ValueError(f"No approved sprite for {char['name']}/{pose}")
            char["pose"] = replacement
            warnings.append(f"{char['name']}: requested {pose} unavailable; using {replacement}.")
    plan = _validate_and_sanitize_plan({"background": bg, "characters": chars, "stickers": stickers}, scene)
    plan["warnings"] = warnings
    return plan

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
        s_copy["direction_method"] = plan.get("direction_method", "deterministic_fallback")
        s_copy["warnings"] = plan.get("warnings", [])
        directed_scenes.append(s_copy)

    return directed_scenes

def apply_copilot_tweak(current_scene: Dict[str, Any], instruction: str) -> Dict[str, Any]:
    """Apply supported deterministic edits; retain unrecognized intent as a warning."""
    inst_lower = instruction.lower()
    updated = dict(current_scene)
    chars = [dict(c) for c in updated.get("characters", [])]
    stickers = [dict(s) for s in updated.get("stickers", [])]
    aliases = {
        "levi": ("levi", "哥哥", "big brother"), "luca": ("luca", "細佬", "little brother"),
        "dad": ("dad", "爸爸"), "mom": ("mom", "媽媽"), "dog": ("dog", "spitz", "波波", "狗"),
        "grandparents_paternal": ("爺爺", "嫲嫲"), "grandparents_maternal": ("公公", "婆婆"),
        "auntie_cousins": ("姑媽", "表哥"),
    }
    targets = [cid for cid, words in aliases.items() if _has(inst_lower, *words)]
    removal = _has(inst_lower, "remove", "delete", "移除", "刪除")
    changed = False
    if removal:
        chars = [c for c in chars if c.get("name") not in targets]
        changed = bool(targets)
    else:
        from app.services.background_generator import _latest_match, SETTING_WORDS
        background = _latest_match(inst_lower, SETTING_WORDS)
        if background:
            updated["background"] = background
            changed = True
        pose_rules = [
            (("sad", "cry", "tear", "唔開心", "喊"), "sad"),
            (("banana", "fruit", "eat", "食"), "eating"),
            (("think", "curious", "諗", "思考"), "thinking"),
            (("cheer", "hooray", "celebrate", "開心", "好叻"), "cheering"),
            (("book", "read", "story", "睇書"), "holding_book"),
            (("point", "look", "指"), "pointing"),
            (("sit", "floor", "mat", "坐"), "playing_blocks"),
            (("hug", "arms", "抱抱"), "arms_out_hug"),
            (("clap", "拍手"), "clapping"),
            (("wave", "hello", "揮手"), "waving"),
            (("sleep", "nap", "瞓"), "sleeping"),
        ]
        available = assets.get_character_poses()
        for cid in targets:
            character = next((c for c in chars if c["name"] == cid), None)
            if character is None:
                if not _has(inst_lower, "add", "include", "加入", "加埋"):
                    continue
                character = {"name": cid, "pose": "default", "x_percent": 50, "y_percent": 88}
                chars.append(character)
                changed = True
            pose = next((pose for words, pose in pose_rules if _has(inst_lower, *words)), None)
            pose = {("luca", "sad"): "crying", ("dog", "eating"): "eating_banana",
                    ("dog", "sleeping"): "curled_sleeping", ("dog", "playing_blocks"): "sitting_attentive",
                    ("dad", "arms_out_hug"): "comforting_hug", ("mom", "arms_out_hug"): "kneeling_hug"}.get((cid, pose), pose)
            if pose:
                if pose not in available[cid]:
                    raise ValueError(f"No approved {cid} pose for {pose}")
                character["pose"] = pose
                changed = True
        additions = [
            (("thank you", "多謝"), {"id": "badge_thank_you", "type": "word", "content": "多謝", "english": "Thank you"}),
            (("please", "唔該"), {"id": "badge_please", "type": "word", "content": "唔該", "english": "Please"}),
            (("banana", "香蕉"), {"id": "prop_banana", "type": "icon", "content": "banana"}),
            (("bus", "校巴"), {"id": "prop_bus", "type": "icon", "content": "bus"}),
            (("toy car", "car", "車"), {"id": "prop_toy_car", "type": "icon", "content": "toy_car"}),
            (("abc", "blocks", "積木"), {"id": "block_a", "type": "letter", "content": "A"}),
        ]
        for words, sticker in additions:
            if _has(inst_lower, *words):
                if not any(s.get("content") == sticker["content"] and s.get("type") == sticker["type"] for s in stickers):
                    stickers.append(sticker)
                changed = True
                break
    plan = _validate_and_sanitize_plan(
        {"background": updated.get("background", "living_room"), "characters": chars, "stickers": stickers},
        {}, allow_empty=True)
    updated.update(plan)
    updated["direction_method"] = "deterministic_edit"
    updated["warnings"] = [] if changed else ["No supported edit recognized; staging unchanged."]
    return updated
