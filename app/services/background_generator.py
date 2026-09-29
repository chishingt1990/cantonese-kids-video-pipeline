import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import numpy as np
from app.services.asset_manifest import MASTER_ASSETS, image_path, resolve_background

W, H = 1920, 1080

SETTING_WORDS = {
    "mountains": ["mountain", "mountains", "hill", "hills", "wildflower", "valley", "hiking", "山"],
    "beach": ["beach", "sandcastle", "ocean", "sea", "coast", "shore", "island", "waves", "沙灘"],
    "park": ["park", "picnic", "lawn", "outside", "公園"],
    "backyard_garden": ["garden", "backyard", "花園"],
    "playground": ["playground", "swing", "slide", "滑梯"],
    "kitchen": ["kitchen", "high chair", "cook", "chef", "breakfast", "廚房"],
    "playroom": ["playroom", "toy", "blocks", "play area", "play mat", "玩具房"],
    "nursery": ["nursery", "crib", "bedtime", "sleep", "bedroom", "睡房"],
    "bathroom": ["bathroom", "bath", "tub", "wash", "shower", "浴室"],
    "dining": ["dining", "dim sum", "banquet", "tea", "meal", "飲茶"],
    "reading_nook": ["reading", "nook", "book", "story", "library", "bookshelf", "睇書"],
    "living_room": ["living room", "sofa", "客廳"],
    "farm_field": ["farm", "field", "農場"],
    "duck_pond": ["duck pond", "pond", "鴨池"],
    "art_room": ["art room", "art studio", "easel", "畫室"],
    "supermarket": ["supermarket", "grocery", "超市"],
}


def _latest_match(text, groups):
    found = []
    text = text.lower()
    for label, words in groups.items():
        for word in words:
            pattern = re.escape(word)
            if word.isascii():
                pattern = r"(?<!\w)" + pattern + r"(?!\w)"
            for match in re.finditer(pattern, text):
                prefix = text[max(0, match.start() - 20):match.start()]
                if re.search(r"(?:not|no|without|remove|instead of)\s+(?:the\s+)?$", prefix):
                    continue
                found.append((match.start(), len(word), label))
    return max(found)[2] if found else None


def background_state(prompt, history=None):
    setting, lighting = "living_room", ""
    lighting_words = {
        "night": ["night", "midnight", "moon", "dark", "twilight", "bedtime", "夜晚"],
        "sunset": ["sunset", "dusk", "evening", "golden hour", "warm glow", "黃昏"],
        "sunny": ["sunny", "morning", "bright", "daylight", "sunshine", "daytime", "白天"],
    }
    for instruction in [prompt, *(history or [])]:
        setting = _latest_match(instruction, SETTING_WORDS) or setting
        lighting = _latest_match(instruction, lighting_words) or lighting
        if re.search(r"\b(?:remove|no|not)\s+(?:the\s+)?(?:night|moon|stars)\b", instruction.lower()):
            lighting = "sunny"
    return setting, lighting

def get_base_archetype(all_text: str, bg_dir: str) -> tuple[str, Image.Image]:
    """Selects the best watercolor picture-book archetype image matching the prompt."""
    setting, _ = background_state(all_text)
    path = resolve_background(setting)
    with Image.open(path) as image:
        base_img = image.convert("RGB")
    if base_img.size != (W, H):
        base_img = base_img.resize((W, H), Image.Resampling.LANCZOS)
    return path.name, base_img

def apply_storybook_atmosphere(img: Image.Image, all_text: str) -> Image.Image:
    """
    Applies warm storybook atmospheric glazes (sunset, night, morning, cozy warmth)
    while preserving the underlying watercolor picture-book line art and textures.
    """
    text = all_text.lower()
    res = img.copy()

    is_night = any(k in text for k in ["night", "midnight", "star", "moon", "dark", "twilight", "bedtime"])
    is_sunset = any(k in text for k in ["sunset", "dusk", "evening", "golden hour", "orange", "warm glow"])
    is_sunny = any(k in text for k in ["sunny", "morning", "bright", "daylight", "sunshine"])

    if is_night:
        # Deep royal blue/indigo night wash
        night_overlay = Image.new("RGBA", (W, H), (15, 23, 60, 110))
        res = res.convert("RGBA")
        res = Image.alpha_composite(res, night_overlay).convert("RGB")
        
        # Dim slightly and increase contrast
        enhancer = ImageEnhance.Brightness(res)
        res = enhancer.enhance(0.85)
        
        # Add delicate soft glowing stars and crescent moon if prompted
        draw = ImageDraw.Draw(res, "RGBA")
        rng = np.random.default_rng(42)
        for _ in range(25):
            sx = int(rng.uniform(100, W - 100))
            sy = int(rng.uniform(40, 420))
            r = int(rng.uniform(2, 5))
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 240, 200))
        
        # Soft crescent moon
        draw.ellipse([1500, 80, 1610, 190], fill=(255, 245, 180, 230))
        draw.ellipse([1480, 70, 1590, 180], fill=(25, 30, 65, 240))
        
    elif is_sunset:
        # Warm golden apricot & rose sunset wash
        sunset_gradient = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sunset_gradient)
        for y in range(H):
            t = y / float(H)
            r = int(255 * (1 - t) + 245 * t)
            g = int(140 * (1 - t) + 190 * t)
            b = int(60 * (1 - t) + 160 * t)
            alpha = int(75 * (1 - t) + 35 * t)
            s_draw.line([(0, y), (W, y)], fill=(r, g, b, alpha))
            
        res = res.convert("RGBA")
        res = Image.alpha_composite(res, sunset_gradient).convert("RGB")
        enhancer = ImageEnhance.Color(res)
        res = enhancer.enhance(1.15)
        
    elif is_sunny:
        # Subtle cheerful warmth
        warm_tint = Image.new("RGBA", (W, H), (255, 245, 200, 30))
        res = res.convert("RGBA")
        res = Image.alpha_composite(res, warm_tint).convert("RGB")
        enhancer = ImageEnhance.Brightness(res)
        res = enhancer.enhance(1.04)

    return res

def generate_iterative_background(prompt: str, history: list[str] = None, output_path: str = None) -> str:
    """
    Generates a 1920x1080 storybook pastel background grounded in the watercolor style guide:
    - Analyzes setting keywords to select or seed from high-fidelity watercolor archetypes
    - Applies natural language refinements (lighting, time of day, atmosphere)
    - Preserves high-resolution watercolor line art, paper texture, and open stage ground line
    """
    if not output_path:
        raise ValueError("An explicit isolated preview output is required")
    if Path(output_path).resolve().is_relative_to(MASTER_ASSETS.resolve()):
        raise ValueError("Master artwork is read-only; use a preview or candidate output.")
    if history is None:
        history = []
    
    setting, lighting = background_state(prompt, history)
    with Image.open(resolve_background(setting)) as image:
        base_img = image.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    final_img = apply_storybook_atmosphere(base_img, lighting)
    
    # 3. Save Output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_img.save(output_path, format="PNG")
    return output_path

def generate_pastel_room(theme: str, output_path: str):
    """Backwards compatibility wrapper."""
    return generate_iterative_background(theme, [], output_path)
