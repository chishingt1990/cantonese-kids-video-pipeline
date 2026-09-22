import json
import logging
from typing import Dict, Any, List, Optional
from app.services.ai_service import generate_ai_text
from app.services.sticker_service import STICKER_CATALOG, get_or_render_sticker

logger = logging.getLogger(__name__)

PRESET_BACKGROUNDS = [
    "living_room", "nursery", "kitchen", "park", "beach",
    "playroom", "reading_nook", "dining", "bathroom", "mountains",
    "playground", "farm_field", "duck_pond", "backyard_garden"
]

CHARACTER_POSES = {
    "levi": ["default", "waving", "sleeping", "eating", "stretching", "arms_out_hug", "pointing", "running"],
    "luca": ["default", "waving", "sleeping", "eating", "clapping", "holding_toy"],
    "dad": ["default", "kneeling", "waving", "drinking", "sitting", "teaching"],
    "mom": ["default", "kneeling_hug", "holding_fruit", "teaching"],
    "dog": ["default", "running", "playing_ball", "eating_banana"],
    "grandparents_paternal": ["default", "drinking_tea"],
    "grandparents_maternal": ["default", "waving"],
    "auntie_cousins": ["default", "waving"]
}

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
  - levi: default, waving, sleeping, eating, stretching, arms_out_hug, pointing, running
  - luca: default, waving, sleeping, eating, clapping, holding_toy
  - dad: default, kneeling, waving, drinking, sitting, teaching
  - mom: default, kneeling_hug, holding_fruit, teaching
  - dog: default, running, playing_ball, eating_banana
  - grandparents_paternal: default, drinking_tea
  - grandparents_maternal: default, waving
  - auntie_cousins: default, waving
- Choose background_id from: living_room, nursery, kitchen, park, beach, playroom, reading_nook, dining, bathroom, mountains, playground, farm_field, duck_pond, backyard_garden.

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
        c["y_percent"] = max(60.0, min(92.0, float(c.get("y_percent", 88.0))))
        c["scale"] = max(0.6, min(1.5, float(c.get("scale", 1.0))))
        c["flip"] = bool(c.get("flip", c["x_percent"] > 50))
        c["layer"] = int(c.get("layer", 1))

    # Validate stickers
    stickers = plan.get("stickers", [])
    valid_stickers = []
    for s in stickers:
        s_id = s.get("id")
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
    text = (scene.get("cantonese", "") + " " + scene.get("english", "") + " " + scene.get("title", "")).lower()
    vocab = scene.get("vocab_highlight", "")

    # 1. Background Selection
    bg = scene.get("background", "living_room")
    if bg not in PRESET_BACKGROUNDS:
        if any(k in text for k in ["playground", "swing", "slide", "滑梯", "鞦韆"]):
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
    is_hygiene = any(k in text for k in ["brush", "teeth", "wash", "hand", "bath", "soap", "bubble", "towel", "刷牙", "洗手", "沖涼", "抹手", "乾淨"])
    is_dim_sum = any(k in text for k in ["dim sum", "dumpling", "tea", "steamer", "點心", "蝦餃", "飲茶", "蒸籠"])
    is_mealtime = any(k in text for k in ["eat", "banana", "apple", "fruit", "snack", "hungry", "bowl", "spoon", "breakfast", "meal", "yummy", "食", "水果", "早餐", "好味"])
    is_blocks = any(k in text for k in ["block", "tower", "stack", "abc", "積木", "搭積木"])
    is_drawing_reading = any(k in text for k in ["book", "read", "story", "crayon", "draw", "睇書", "講故事", "畫畫"])
    is_toy_play = any(k in text for k in ["toy", "car", "play", "share", "turn", "玩", "玩具車", "輪流"])
    is_bedtime = any(k in text for k in ["sleep", "bed", "night", "star", "moon", "dream", "lullaby", "瞓", "晚安", "瞓覺", "發夢", "星星", "月亮"])
    is_hugging = any(k in text for k in ["hug", "arms", "love", "comfort", "cuddle", "抱抱", "我愛你", "安慰"])
    is_waving = any(k in text for k in ["hello", "good morning", "hi", "bye", "早晨", "揮手", "你好"])

    # 1. Hygiene Domain (Bathroom Routine)
    if is_hygiene:
        bg = "bathroom"
        chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 36.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "teaching", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "teaching", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        
        # Anchored hand-level toothbrush & soap bubbles
        stickers.append({"id": "prop_toothbrush_blue", "type": "icon", "content": "toothbrush_blue", "x_percent": 42.0, "y_percent": 74.0, "scale": 0.85, "rotation_deg": -15.0, "layer": 3})
        stickers.append({"id": "prop_soap_bubbles", "type": "icon", "content": "soap_bubbles", "x_percent": 72.0, "y_percent": 30.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
        stickers.append({"id": "badge_hygiene", "type": "word", "content": "一齊刷牙", "english": "Brush Teeth Together", "color_theme": "sky", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 2. Mealtime & Dim Sum Domain
    elif is_dim_sum or (is_mealtime and has_grandparents):
        bg = "dining"
        gp_name = "grandparents_paternal" if any(k in text for k in ["爺爺", "嫲嫲"]) else "grandparents_maternal"
        chars.append({"name": gp_name, "pose": "drinking_tea", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        chars.append({"name": "levi", "pose": "eating", "scale": 1.0, "x_percent": 58.0, "y_percent": 88.0, "flip": False, "layer": 2})
        chars.append({"name": "luca", "pose": "eating", "scale": 1.0, "x_percent": 78.0, "y_percent": 88.0, "flip": True, "layer": 2})
        stickers.append({"id": "prop_dim_sum_basket", "type": "icon", "content": "dim_sum_basket", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_dim_sum", "type": "word", "content": "飲茶食點心", "english": "Yummy Dim Sum", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif is_mealtime:
        bg = "kitchen"
        if has_mom:
            chars.append({"name": "mom", "pose": "holding_fruit", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "sitting", "scale": 1.0, "x_percent": 24.0, "y_percent": 86.0, "flip": False, "layer": 1})
        chars.append({"name": "levi", "pose": "eating", "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
        chars.append({"name": "luca", "pose": "eating", "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        if has_dog or "banana" in text:
            chars.append({"name": "dog", "pose": "eating_banana", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})
        # Tangible fruit plate or bowl
        stickers.append({"id": "prop_fruit_plate", "type": "icon", "content": "fruit_plate", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_mealtime", "type": "word", "content": "好美味！", "english": "So Yummy!", "color_theme": "gold", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 3. Play, Cognitive & Blocks Domain
    elif is_blocks or is_toy_play:
        bg = "playroom"
        chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "holding_toy", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "playing_ball", "scale": 1.0, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        
        # Physical Block Tower or Toy Car between the twins
        prop_id = "prop_block_tower" if is_blocks else "prop_toy_car"
        stickers.append({"id": prop_id, "type": "icon", "content": prop_id.replace("prop_", ""), "x_percent": 50.0, "y_percent": 80.0, "scale": 1.15, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_play_together", "type": "word", "content": "輪流玩", "english": "Take Turns & Share", "color_theme": "purple", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    elif is_drawing_reading:
        bg = "reading_nook"
        if has_dad:
            chars.append({"name": "dad", "pose": "teaching", "scale": 1.0, "x_percent": 30.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "default", "scale": 1.0, "x_percent": 56.0, "y_percent": 88.0, "flip": True, "layer": 2})
            chars.append({"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 74.0, "y_percent": 88.0, "flip": True, "layer": 2})
        else:
            chars.append({"name": "levi", "pose": "pointing", "scale": 1.0, "x_percent": 36.0, "y_percent": 88.0, "flip": False, "layer": 1})
            chars.append({"name": "luca", "pose": "holding_toy", "scale": 1.0, "x_percent": 64.0, "y_percent": 88.0, "flip": True, "layer": 1})
        stickers.append({"id": "prop_picture_book", "type": "icon", "content": "picture_book", "x_percent": 50.0, "y_percent": 78.0, "scale": 1.1, "rotation_deg": 0.0, "layer": 3})
        stickers.append({"id": "badge_reading", "type": "word", "content": "睇故事書", "english": "Storybook Time", "color_theme": "rose", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 4. Bedtime & Sleep Domain
    elif is_bedtime:
        bg = "nursery"
        chars.append({"name": "levi", "pose": "sleeping", "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
        chars.append({"name": "luca", "pose": "sleeping", "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        if has_mom:
            chars.append({"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        elif has_dad:
            chars.append({"name": "dad", "pose": "kneeling", "scale": 1.0, "x_percent": 18.0, "y_percent": 86.0, "flip": False, "layer": 1})
        if has_dog:
            chars.append({"name": "dog", "pose": "default", "scale": 0.9, "x_percent": 84.0, "y_percent": 88.0, "flip": True, "layer": 2})
        stickers.append({"id": "prop_star", "type": "icon", "content": "star", "x_percent": 80.0, "y_percent": 26.0, "scale": 1.1, "rotation_deg": 10.0, "layer": 2})
        stickers.append({"id": "badge_goodnight", "type": "word", "content": "晚安早抖", "english": "Sweet Dreams", "color_theme": "indigo", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})

    # 5. Hugging, Love & Manners (Default Warm Preschool Staging)
    else:
        bg = "living_room" if not any(k in text for k in ["park", "outdoor", "公園"]) else "park"
        if has_dad:
            chars.append({"name": "dad", "pose": "kneeling", "scale": 1.0, "x_percent": 26.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
            chars.append({"name": "luca", "pose": "clapping" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        elif has_mom:
            chars.append({"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 26.0, "y_percent": 86.0, "flip": False, "layer": 1})
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else "default", "scale": 1.0, "x_percent": 54.0, "y_percent": 88.0, "flip": False, "layer": 2})
            chars.append({"name": "luca", "pose": "waving", "scale": 1.0, "x_percent": 76.0, "y_percent": 88.0, "flip": True, "layer": 2})
        else:
            chars.append({"name": "levi", "pose": "arms_out_hug" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 34.0, "y_percent": 88.0, "flip": False, "layer": 1})
            chars.append({"name": "luca", "pose": "clapping" if is_hugging else ("waving" if is_waving else "default"), "scale": 1.0, "x_percent": 66.0, "y_percent": 88.0, "flip": True, "layer": 1})
        
        if has_dog:
            chars.append({"name": "dog", "pose": "default", "scale": 1.0, "x_percent": 50.0, "y_percent": 90.0, "flip": False, "layer": 3})

        if is_hugging:
            stickers.append({"id": "prop_comfort_hearts", "type": "icon", "content": "comfort_hearts", "x_percent": 50.0, "y_percent": 42.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})
            stickers.append({"id": "badge_big_hug", "type": "word", "content": "抱抱", "english": "Big Warm Hug", "color_theme": "pink", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
        elif is_waving or any(k in text for k in ["good morning", "早晨"]):
            stickers.append({"id": "badge_good_morning", "type": "word", "content": "早晨", "english": "Good morning", "color_theme": "gold", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
        elif vocab:
            stickers.append({"id": f"badge_vocab_{vocab[:6]}", "type": "word", "content": vocab, "english": "Learn", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.0, "rotation_deg": 0.0, "layer": 2})

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
    if any(k in inst_lower for k in ["mountain", "hill", "wildflower", "山", "花"]):
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
        dog_pose = "eating_banana" if any(k in inst_lower for k in ["banana", "香蕉", "eat"]) else "default"
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
            elif any(k in inst_lower for k in ["wave", "hello", "揮手"]):
                luca_char["pose"] = "waving"
            elif any(k in inst_lower for k in ["sleep", "瞓"]):
                luca_char["pose"] = "sleeping"

    # 3. Sticker tweaks
    if any(k in inst_lower for k in ["thank you", "多謝"]):
        if not any(s.get("id") == "badge_thank_you" for s in stickers):
            stickers.append({"id": "badge_thank_you", "type": "word", "content": "多謝", "english": "Thank you", "color_theme": "amber", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
    elif any(k in inst_lower for k in ["please", "唔該"]):
        if not any(s.get("id") == "badge_please" for s in stickers):
            stickers.append({"id": "badge_please", "type": "word", "content": "唔該", "english": "Please", "color_theme": "emerald", "x_percent": 50.0, "y_percent": 22.0, "scale": 1.05, "rotation_deg": 0.0, "layer": 2})
    elif any(k in inst_lower for k in ["banana", "香蕉"]):
        if not any(s.get("id") == "prop_banana" for s in stickers):
            stickers.append({"id": "prop_banana", "type": "icon", "content": "banana", "x_percent": 78.0, "y_percent": 25.0, "scale": 1.1, "rotation_deg": 8.0, "layer": 2})
    elif any(k in inst_lower for k in ["car", "toy car", "車"]):
        if not any(s.get("id") == "prop_toy_car" for s in stickers):
            stickers.append({"id": "prop_toy_car", "type": "icon", "content": "toy_car", "x_percent": 22.0, "y_percent": 26.0, "scale": 1.1, "rotation_deg": -5.0, "layer": 2})
    elif any(k in inst_lower for k in ["abc", "blocks", "block", "積木"]):
        if not any(s.get("id") == "block_a" for s in stickers):
            stickers.append({"id": "block_a", "type": "letter", "content": "A", "color_theme": "rose", "x_percent": 20.0, "y_percent": 24.0, "scale": 1.0, "rotation_deg": -6.0, "layer": 2})

    updated["characters"] = chars
    updated["stickers"] = stickers
    return updated
