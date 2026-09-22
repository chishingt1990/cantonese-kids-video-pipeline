import os
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import numpy as np

W, H = 1920, 1080

def get_base_archetype(all_text: str, bg_dir: str) -> tuple[str, Image.Image]:
    """Selects the best watercolor picture-book archetype image matching the prompt."""
    text = all_text.lower()
    
    # 1. Mountain / Hills / Outdoor Nature
    if any(k in text for k in ["mountain", "hill", "wildflower", "valley", "hiking", "meadow", "grassland"]):
        fn = "bg_mountains.png"
    # 2. Beach / Ocean / Seaside / Sandcastle
    elif any(k in text for k in ["beach", "sandcastle", "ocean", "sea", "coast", "shore", "island", "waves"]):
        fn = "bg_beach.png"
    # 3. Park / Picnic / Garden / Backyard
    elif any(k in text for k in ["park", "picnic", "garden", "lawn", "outside", "yard", "playground"]):
        fn = "bg_park.png"
    # 4. Kitchen / High Chairs / Cooking
    elif any(k in text for k in ["kitchen", "high chair", "cook", "chef", "breakfast"]):
        fn = "bg_kitchen.png"
    # 5. Playroom / Toys / Blocks / Castle
    elif any(k in text for k in ["playroom", "toy", "block", "play area", "play mat"]):
        fn = "bg_playroom.png"
    # 6. Bedtime Nursery / Night Crib
    elif any(k in text for k in ["nursery", "crib", "bedtime", "sleep", "bedroom"]):
        fn = "bg_nursery.png"
    # 7. Bathroom / Bubble Bath / Tub
    elif any(k in text for k in ["bathroom", "bath", "tub", "bubble", "duck", "wash", "shower"]):
        fn = "bg_bathroom.png"
    # 8. Dining Room / Dim Sum / Family Meal
    elif any(k in text for k in ["dining", "dim sum", "table", "tea", "banquet", "eat", "meal"]):
        fn = "bg_dining.png"
    # 9. Reading Nook / Story Corner
    elif any(k in text for k in ["reading", "nook", "book", "story", "library", "bookshelf"]):
        fn = "bg_reading_nook.png"
    # 10. Default / Living Room
    else:
        fn = "bg_living_room.png"

    path = os.path.join(bg_dir, fn)
    if os.path.exists(path):
        base_img = Image.open(path).convert("RGB")
        if base_img.size != (W, H):
            base_img = base_img.resize((W, H), Image.Resampling.LANCZOS)
        return fn, base_img
    
    # Global fallback if file missing
    fallback = Image.new("RGB", (W, H), (255, 248, 235))
    return "fallback", fallback

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
        np.random.seed(42)
        for _ in range(25):
            sx = int(np.random.uniform(100, W - 100))
            sy = int(np.random.uniform(40, 420))
            r = int(np.random.uniform(2, 5))
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
    if history is None:
        history = []
    
    # Accumulated prompt context across all iteration turns
    all_text = " ".join([prompt] + history).strip()
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    
    # 1. Select Base Watercolor Archetype
    _, base_img = get_base_archetype(all_text, bg_dir)
    
    # 2. Apply Atmospheric Lighting & Palette Refinements
    final_img = apply_storybook_atmosphere(base_img, all_text)
    
    # 3. Save Output
    if not output_path:
        output_path = os.path.join(bg_dir, "temp_preview_bg.png")
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_img.save(output_path, format="PNG")
    return output_path

def generate_pastel_room(theme: str, output_path: str):
    """Backwards compatibility wrapper."""
    return generate_iterative_background(theme, [], output_path)
