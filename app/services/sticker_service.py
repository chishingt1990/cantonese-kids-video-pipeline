import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional, Dict, Any, List

STICKER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "stickers")
os.makedirs(STICKER_DIR, exist_ok=True)

def get_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/msjhbd.ttc" if bold else "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/seguiemj.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

STICKER_CATALOG = [
    # 1. Manners & Life Skills
    {
        "id": "badge_thank_you",
        "type": "word",
        "label": "多謝 (Thank You)",
        "chinese": "多謝",
        "english": "Thank you",
        "icon": "🙏",
        "color_theme": "amber"
    },
    {
        "id": "badge_please",
        "type": "word",
        "label": "唔該 (Please / Thanks)",
        "chinese": "唔該",
        "english": "Please",
        "icon": "✨",
        "color_theme": "emerald"
    },
    {
        "id": "badge_good_morning",
        "type": "word",
        "label": "早晨 (Good Morning)",
        "chinese": "早晨",
        "english": "Good morning",
        "icon": "☀️",
        "color_theme": "gold"
    },
    {
        "id": "badge_good_job",
        "type": "word",
        "label": "好乖！ (Good Job!)",
        "chinese": "好乖！",
        "english": "Good job!",
        "icon": "⭐",
        "color_theme": "rose"
    },
    {
        "id": "badge_big_hug",
        "type": "word",
        "label": "抱抱 (Big Hug)",
        "chinese": "抱抱",
        "english": "Big hug",
        "icon": "💖",
        "color_theme": "pink"
    },
    {
        "id": "badge_sharing",
        "type": "word",
        "label": "分享 (Sharing)",
        "chinese": "分享",
        "english": "Share toys",
        "icon": "🤝",
        "color_theme": "sky"
    },
    {
        "id": "badge_take_turns",
        "type": "word",
        "label": "輪流玩 (Take Turns)",
        "chinese": "輪流玩",
        "english": "Take turns",
        "icon": "🔄",
        "color_theme": "purple"
    },
    {
        "id": "badge_family",
        "type": "word",
        "label": "屋企人 (Family)",
        "chinese": "屋企人",
        "english": "Family",
        "icon": "🏡",
        "color_theme": "amber"
    },
    {
        "id": "badge_polite",
        "type": "word",
        "label": "有禮貌 (Polite)",
        "chinese": "有禮貌",
        "english": "Polite",
        "icon": "🌸",
        "color_theme": "emerald"
    },
    {
        "id": "badge_dog",
        "type": "word",
        "label": "狗狗 (Doggy)",
        "chinese": "狗狗",
        "english": "Doggy",
        "icon": "🐕",
        "color_theme": "gold"
    },
    {
        "id": "badge_big_brother",
        "type": "word",
        "label": "哥哥 (Levi)",
        "chinese": "哥哥",
        "english": "Big brother",
        "icon": "🧒",
        "color_theme": "rose"
    },
    {
        "id": "badge_little_brother",
        "type": "word",
        "label": "細佬 (Luca)",
        "chinese": "細佬",
        "english": "Little brother",
        "icon": "👦",
        "color_theme": "gold"
    },
    # 2. Phonics Blocks
    {
        "id": "block_a",
        "type": "letter",
        "label": "Block A",
        "letter": "A",
        "color_theme": "rose"
    },
    {
        "id": "block_b",
        "type": "letter",
        "label": "Block B",
        "letter": "B",
        "color_theme": "sky"
    },
    {
        "id": "block_c",
        "type": "letter",
        "label": "Block C",
        "letter": "C",
        "color_theme": "emerald"
    },
    # 3. Numbers
    {
        "id": "block_1",
        "type": "number",
        "label": "Number 1",
        "number": "1",
        "color_theme": "amber"
    },
    {
        "id": "block_2",
        "type": "number",
        "label": "Number 2",
        "number": "2",
        "color_theme": "teal"
    },
    {
        "id": "block_3",
        "type": "number",
        "label": "Number 3",
        "number": "3",
        "color_theme": "indigo"
    },
    # 4. Tangible Preschool Milestone Props & Objects
    {
        "id": "prop_banana",
        "type": "icon",
        "label": "香蕉 (Banana)",
        "icon": "banana"
    },
    {
        "id": "prop_apple",
        "type": "icon",
        "label": "蘋果 (Apple)",
        "icon": "apple"
    },
    {
        "id": "prop_toy_car",
        "type": "icon",
        "label": "玩具車 (Toy Car)",
        "icon": "toy_car"
    },
    {
        "id": "prop_star",
        "type": "icon",
        "label": "星星 (Star)",
        "icon": "star"
    },
    {
        "id": "prop_toothbrush_blue",
        "type": "icon",
        "label": "藍色牙刷 (Blue Toothbrush)",
        "icon": "toothbrush_blue"
    },
    {
        "id": "prop_toothbrush_yellow",
        "type": "icon",
        "label": "黃色牙刷 (Yellow Toothbrush)",
        "icon": "toothbrush_yellow"
    },
    {
        "id": "prop_soap_bubbles",
        "type": "icon",
        "label": "肥皂泡泡 (Soap Bubbles)",
        "icon": "soap_bubbles"
    },
    {
        "id": "prop_washcloth",
        "type": "icon",
        "label": "小毛巾 (Soft Washcloth)",
        "icon": "washcloth"
    },
    {
        "id": "prop_dim_sum_basket",
        "type": "icon",
        "label": "點心蒸籠 (Steaming Dim Sum)",
        "icon": "dim_sum_basket"
    },
    {
        "id": "prop_fruit_plate",
        "type": "icon",
        "label": "水果拼盤 (Fruit Slices Plate)",
        "icon": "fruit_plate"
    },
    {
        "id": "prop_sippy_cup",
        "type": "icon",
        "label": "飲水杯 (Toddler Sippy Cup)",
        "icon": "sippy_cup"
    },
    {
        "id": "prop_toddler_bowl",
        "type": "icon",
        "label": "幼兒餐碗 (Toddler Bowl & Spoon)",
        "icon": "toddler_bowl"
    },
    {
        "id": "prop_block_tower",
        "type": "icon",
        "label": "積木塔 (ABC Block Tower)",
        "icon": "block_tower"
    },
    {
        "id": "prop_picture_book",
        "type": "icon",
        "label": "故事書 (Open Picture Book)",
        "icon": "picture_book"
    },
    {
        "id": "prop_crayons",
        "type": "icon",
        "label": "彩色蠟筆 (Wax Crayons)",
        "icon": "crayons"
    },
    {
        "id": "prop_balloon_red",
        "type": "icon",
        "label": "紅氣球 (Red Balloon)",
        "icon": "balloon_red"
    },
    {
        "id": "prop_sparkle_cluster",
        "type": "icon",
        "label": "閃爍星星 (Twinkle Sparkles)",
        "icon": "sparkle_cluster"
    },
    {
        "id": "prop_comfort_hearts",
        "type": "icon",
        "label": "溫暖愛心 (Warm Hug Hearts)",
        "icon": "comfort_hearts"
    }
]

THEME_COLORS = {
    "amber": {"bg": (255, 251, 235), "border": (245, 158, 11), "text": (180, 83, 9), "dark": (40, 30, 20)},
    "emerald": {"bg": (236, 253, 245), "border": (16, 185, 129), "text": (4, 120, 87), "dark": (20, 40, 30)},
    "gold": {"bg": (254, 252, 232), "border": (234, 179, 8), "text": (161, 98, 7), "dark": (45, 35, 15)},
    "rose": {"bg": (255, 241, 242), "border": (244, 63, 94), "text": (190, 18, 60), "dark": (50, 20, 25)},
    "pink": {"bg": (253, 242, 248), "border": (236, 72, 153), "text": (190, 24, 93), "dark": (45, 20, 35)},
    "sky": {"bg": (240, 249, 255), "border": (14, 165, 233), "text": (3, 105, 161), "dark": (20, 35, 50)},
    "teal": {"bg": (240, 253, 250), "border": (20, 184, 166), "text": (15, 118, 110), "dark": (15, 40, 35)},
    "purple": {"bg": (250, 245, 255), "border": (168, 85, 247), "text": (126, 34, 206), "dark": (35, 20, 45)},
    "indigo": {"bg": (238, 242, 255), "border": (99, 102, 241), "text": (67, 56, 202), "dark": (25, 25, 50)},
}

THEME_PALETTES = {
    "amber": {
        "fill": (255, 252, 244),
        "tint": (254, 243, 199),
        "line": (120, 80, 45),
        "text_cn": (70, 45, 25),
        "text_en": (165, 95, 20),
        "dot": (245, 158, 11)
    },
    "gold": {
        "fill": (255, 253, 242),
        "tint": (254, 249, 195),
        "line": (130, 95, 35),
        "text_cn": (75, 50, 15),
        "text_en": (175, 115, 20),
        "dot": (234, 179, 8)
    },
    "rose": {
        "fill": (255, 248, 250),
        "tint": (254, 226, 226),
        "line": (140, 60, 70),
        "text_cn": (90, 30, 40),
        "text_en": (190, 45, 75),
        "dot": (244, 63, 94)
    },
    "emerald": {
        "fill": (246, 253, 249),
        "tint": (209, 250, 229),
        "line": (45, 100, 75),
        "text_cn": (25, 65, 45),
        "text_en": (15, 125, 85),
        "dot": (16, 185, 129)
    },
    "sky": {
        "fill": (245, 251, 255),
        "tint": (224, 242, 254),
        "line": (50, 90, 130),
        "text_cn": (25, 55, 85),
        "text_en": (20, 115, 175),
        "dot": (14, 165, 233)
    },
    "purple": {
        "fill": (253, 248, 255),
        "tint": (243, 232, 255),
        "line": (105, 65, 135),
        "text_cn": (65, 35, 90),
        "text_en": (140, 65, 185),
        "dot": (168, 85, 247)
    },
    "pink": {
        "fill": (255, 248, 252),
        "tint": (252, 231, 243),
        "line": (140, 65, 110),
        "text_cn": (90, 35, 70),
        "text_en": (195, 50, 130),
        "dot": (236, 72, 153)
    },
    "teal": {
        "fill": (242, 253, 250),
        "tint": (204, 251, 241),
        "line": (35, 95, 85),
        "text_cn": (20, 65, 60),
        "text_en": (15, 125, 115),
        "dot": (20, 184, 166)
    },
    "indigo": {
        "fill": (245, 247, 255),
        "tint": (224, 231, 255),
        "line": (65, 70, 140),
        "text_cn": (45, 45, 95),
        "text_en": (79, 70, 229),
        "dot": (99, 102, 241)
    }
}

def draw_mini_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r_out: float, r_in: float, fill_color, outline_color=None):
    """Draws a sweet hand-drawn pastel star motif."""
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill_color, outline=outline_color)

def generate_vocab_badge(chinese: str, english: str = "", theme: str = "amber", width: int = 340, height: int = 140) -> Image.Image:
    """
    Renders a warm, storybook picture-book word sticker:
    - Content-proportional dimensions (NO large empty void at bottom!)
    - Centered vertical typography lockup (Chinese + English perfectly balanced)
    - Hand-drawn warm sepia contour lines matching character & background art style
    - Soft pastel watercolor fill with delicate inner tint
    - White die-cut outline and soft warm drop shadow
    """
    palette = THEME_PALETTES.get(theme, THEME_PALETTES["amber"])
    scale = 2  # 2x supersampling for high fidelity

    font_cn = get_font(42 * scale, bold=True)
    font_en = get_font(18 * scale, bold=True)

    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bbox_cn = dummy_draw.textbbox((0, 0), chinese, font=font_cn)
    w_cn = bbox_cn[2] - bbox_cn[0]
    h_cn = bbox_cn[3] - bbox_cn[1]

    w_en, h_en = 0, 0
    if english:
        bbox_en = dummy_draw.textbbox((0, 0), english.upper(), font=font_en)
        w_en = bbox_en[2] - bbox_en[0]
        h_en = bbox_en[3] - bbox_en[1]

    text_max_w = max(w_cn, w_en)
    line_gap = 8 * scale if english else 0
    text_total_h = h_cn + (h_en + line_gap if english else 0)

    # Snug, balanced margins
    pad_x = 32 * scale
    pad_y = 14 * scale

    sw = text_max_w + pad_x * 2
    sh = text_total_h + pad_y * 2
    
    # Proportions: minimum width & height
    sw = max(sw, 150 * scale)
    sh = max(sh, 62 * scale)

    margin = 12 * scale
    total_w = sw + margin * 2
    total_h = sh + margin * 2

    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # 1. Soft Warm Gaussian Shadow
    shadow = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    rad = int(sh * 0.46)
    s_draw.rounded_rectangle(
        [margin, margin + 4 * scale, margin + sw, margin + sh + 4 * scale],
        radius=rad,
        fill=(70, 45, 30, 45)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(5 * scale))
    canvas.alpha_composite(shadow)

    # 2. Outer White Die-Cut Border (Sticker cutline)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [margin, margin, margin + sw, margin + sh],
        radius=rad,
        fill=(255, 255, 255, 255)
    )

    # 3. Inner Pastel Fill with delicate watercolor edge
    inner_pad = 4 * scale
    inner_rad = max(4, rad - inner_pad)
    draw.rounded_rectangle(
        [margin + inner_pad, margin + inner_pad, margin + sw - inner_pad, margin + sh - inner_pad],
        radius=inner_rad,
        fill=palette["fill"] + (255,),
        outline=palette["tint"] + (255,),
        width=3 * scale
    )

    # 4. Soft Sepia Line Contour (matches character & background picture-book style)
    outline_pad = inner_pad + 2 * scale
    outline_rad = max(4, inner_rad - 2 * scale)
    draw.rounded_rectangle(
        [margin + outline_pad, margin + outline_pad, margin + sw - outline_pad, margin + sh - outline_pad],
        radius=outline_rad,
        outline=palette["line"] + (220,),
        width=int(2 * scale)
    )

    # 5. Hand-drawn miniature decorative stars
    star_r_out = 5 * scale
    star_r_in = 2.2 * scale
    draw_mini_star(draw, margin + outline_pad + 12 * scale, total_h // 2, star_r_out, star_r_in, palette["tint"] + (255,), palette["line"] + (180,))
    draw_mini_star(draw, total_w - margin - outline_pad - 12 * scale, total_h // 2, star_r_out, star_r_in, palette["tint"] + (255,), palette["line"] + (180,))

    # 6. Perfectly Centered Vertical Lockup
    cx = total_w // 2
    cy = total_h // 2

    if english:
        top_y = cy - text_total_h // 2
        cn_center_y = top_y + h_cn // 2
        en_center_y = top_y + h_cn + line_gap + h_en // 2

        draw.text((cx, cn_center_y), chinese, font=font_cn, fill=palette["text_cn"], anchor="mm")
        draw.text((cx, en_center_y), english.upper(), font=font_en, fill=palette["text_en"], anchor="mm")
    else:
        draw.text((cx, cy), chinese, font=font_cn, fill=palette["text_cn"], anchor="mm")

    target_w = total_w // scale
    target_h = total_h // scale
    return canvas.resize((target_w, target_h), Image.Resampling.LANCZOS)

def generate_toy_block(content: str, theme: str = "rose", size: int = 180) -> Image.Image:
    """Renders a preschool wooden toy block with bright bevel and drop shadow."""
    s = size * 2
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    
    # Shadow
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle([24, 38, s - 24, s - 10], radius=36, fill=(0, 0, 0, 65))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow)

    # White Border
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([24, 24, s - 24, s - 24], radius=36, fill=(255, 255, 255, 255))

    # Block Face
    c_theme = THEME_COLORS.get(theme, THEME_COLORS["rose"])
    draw.rounded_rectangle([32, 32, s - 32, s - 32], radius=30, fill=c_theme["border"] + (255,))
    
    # Glossy Highlight Curve
    draw.chord([40, 40, s - 40, s - 40], 180, 270, fill=(255, 255, 255, 90))

    font = get_font(104, bold=True)
    draw.text((s // 2, s // 2), content, font=font, fill=(255, 255, 255), anchor="mm")

    return canvas.resize((size, size), Image.Resampling.LANCZOS)

def generate_prop_icon(icon_name: str, size: int = 180) -> Image.Image:
    """Renders a transparent cartoon prop sticker with white die-cut border."""
    s = size * 2
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = s // 2, s // 2

    # Drop shadow
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse([cx - 100, cy - 80 + 16, cx + 100, cy + 80 + 16], fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(shadow)
    draw = ImageDraw.Draw(canvas)

    if icon_name == "banana":
        # Die cut white backing
        draw.arc([cx - 110, cy - 110, cx + 110, cy + 110], 30, 180, fill=(255, 255, 255), width=36)
        # Yellow banana curve
        draw.arc([cx - 100, cy - 100, cx + 100, cy + 100], 35, 175, fill=(250, 204, 21), width=24)
        # Brown stem & tip
        draw.ellipse([cx + 65, cy + 50, cx + 85, cy + 70], fill=(120, 53, 15))
        draw.ellipse([cx - 85, cy - 5, cx - 65, cy + 15], fill=(180, 83, 9))
    elif icon_name == "apple":
        draw.ellipse([cx - 88, cy - 78, cx + 88, cy + 78], fill=(255, 255, 255))
        draw.ellipse([cx - 80, cy - 70, cx + 80, cy + 70], fill=(239, 68, 68))
        draw.ellipse([cx - 20, cy - 85, cx + 20, cy - 55], fill=(34, 197, 94))
    elif icon_name == "toy_car":
        # White backing
        draw.rounded_rectangle([cx - 105, cy - 35, cx + 105, cy + 65], radius=24, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 65, cy - 75, cx + 55, cy - 15], radius=20, fill=(255, 255, 255))
        # Red car body
        draw.rounded_rectangle([cx - 95, cy - 25, cx + 95, cy + 55], radius=18, fill=(239, 68, 68))
        draw.rounded_rectangle([cx - 55, cy - 65, cx + 45, cy - 15], radius=14, fill=(59, 130, 246))
        # Wheels
        draw.ellipse([cx - 75, cy + 30, cx - 35, cy + 70], fill=(30, 41, 59))
        draw.ellipse([cx + 35, cy + 30, cx + 75, cy + 70], fill=(30, 41, 59))
    elif "toothbrush" in icon_name:
        # Chunky toddler toothbrush with soft foam
        is_yellow = "yellow" in icon_name
        body_color = (250, 204, 21) if is_yellow else (56, 189, 248)
        # White die-cut outline
        draw.rounded_rectangle([cx - 26, cy - 92, cx + 26, cy + 86], radius=22, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 42, cy - 92, cx + 42, cy - 40], radius=18, fill=(255, 255, 255))
        # Handle
        draw.rounded_rectangle([cx - 16, cy - 82, cx + 16, cy + 76], radius=16, fill=body_color)
        # White bristles
        draw.rounded_rectangle([cx - 32, cy - 82, cx + 32, cy - 50], radius=10, fill=(240, 249, 255), outline=(186, 230, 253), width=3)
        # Bubbly foam
        draw.ellipse([cx - 20, cy - 92, cx + 4, cy - 68], fill=(255, 255, 255))
        draw.ellipse([cx - 2, cy - 96, cx + 22, cy - 72], fill=(255, 255, 255))
    elif "bubble" in icon_name:
        # Iridescent soap bubbles
        for (bx, by, br, b_col) in [(cx - 35, cy - 25, 48, (224, 242, 254)), (cx + 35, cy - 35, 36, (243, 232, 255)), (cx + 10, cy + 35, 42, (254, 242, 242))]:
            draw.ellipse([bx - br - 6, by - br - 6, bx + br + 6, by + br + 6], fill=(255, 255, 255))
            draw.ellipse([bx - br, by - br, bx + br, by + br], fill=b_col, outline=(147, 197, 253), width=4)
            draw.chord([bx - br + 8, by - br + 8, bx + br - 8, by + br - 8], 200, 270, fill=(255, 255, 255, 200))
    elif "washcloth" in icon_name:
        # Soft folded yellow washcloth
        draw.rounded_rectangle([cx - 76, cy - 64, cx + 76, cy + 64], radius=24, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 66, cy - 54, cx + 66, cy + 54], radius=18, fill=(254, 240, 138), outline=(234, 179, 8), width=3)
        draw.text((cx, cy), "🐻", font=get_font(52), fill=(180, 83, 9), anchor="mm")
    elif "dim_sum" in icon_name:
        # Steaming bamboo basket with dumplings
        draw.ellipse([cx - 86, cy - 46, cx + 86, cy + 66], fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 82, cy - 20, cx + 82, cy + 60], radius=16, fill=(217, 119, 6), outline=(255, 255, 255), width=4)
        draw.ellipse([cx - 80, cy - 40, cx + 80, cy + 10], fill=(254, 243, 199), outline=(180, 83, 9), width=3)
        # 3 little steamed dumplings
        draw.ellipse([cx - 50, cy - 30, cx - 10, cy + 2], fill=(255, 255, 255), outline=(245, 158, 11), width=2)
        draw.ellipse([cx + 10, cy - 30, cx + 50, cy + 2], fill=(255, 255, 255), outline=(245, 158, 11), width=2)
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 8], fill=(255, 255, 255), outline=(245, 158, 11), width=2)
    elif "fruit_plate" in icon_name:
        # White plate with watermelon and orange slices
        draw.ellipse([cx - 86, cy - 66, cx + 86, cy + 66], fill=(255, 255, 255))
        draw.ellipse([cx - 78, cy - 58, cx + 78, cy + 58], fill=(248, 250, 252), outline=(203, 213, 225), width=3)
        # Watermelon slice
        draw.chord([cx - 55, cy - 40, cx + 5, cy + 20], 0, 180, fill=(239, 68, 68), outline=(34, 197, 94), width=4)
        # Orange slice
        draw.chord([cx + 5, cy - 30, cx + 65, cy + 30], 180, 360, fill=(249, 115, 22), outline=(254, 215, 170), width=3)
    elif "sippy_cup" in icon_name:
        # Mint green 2-handled toddler cup
        draw.rounded_rectangle([cx - 76, cy - 56, cx + 76, cy + 66], radius=24, fill=(255, 255, 255))
        # Handles
        draw.rounded_rectangle([cx - 68, cy - 30, cx + 68, cy + 40], radius=16, fill=(167, 243, 208), outline=(5, 150, 105), width=3)
        # Cup body
        draw.rounded_rectangle([cx - 45, cy - 46, cx + 45, cy + 56], radius=18, fill=(52, 211, 153), outline=(4, 120, 87), width=3)
        # Lid
        draw.ellipse([cx - 48, cy - 58, cx + 48, cy - 34], fill=(254, 240, 138), outline=(202, 138, 4), width=3)
    elif "toddler_bowl" in icon_name:
        # Suction bowl with spoon
        draw.ellipse([cx - 86, cy - 46, cx + 86, cy + 66], fill=(255, 255, 255))
        draw.chord([cx - 75, cy - 45, cx + 75, cy + 55], 0, 180, fill=(244, 63, 94), outline=(190, 18, 60), width=4)
        draw.rounded_rectangle([cx + 20, cy - 65, cx + 40, cy + 10], radius=8, fill=(250, 204, 21), outline=(180, 83, 9), width=2)
    elif "block_tower" in icon_name:
        # 3 Stacked wooden blocks A, B, C
        draw.rounded_rectangle([cx - 65, cy - 75, cx + 65, cy + 75], radius=20, fill=(255, 255, 255))
        font_b = get_font(38, bold=True)
        # Top block A
        draw.rounded_rectangle([cx - 28, cy - 68, cx + 28, cy - 18], radius=8, fill=(254, 226, 226), outline=(239, 68, 68), width=3)
        draw.text((cx, cy - 43), "A", font=font_b, fill=(185, 28, 28), anchor="mm")
        # Middle block B
        draw.rounded_rectangle([cx - 48, cy - 16, cx + 8, cy + 34], radius=8, fill=(254, 249, 195), outline=(234, 179, 8), width=3)
        draw.text((cx - 20, cy + 9), "B", font=font_b, fill=(161, 98, 7), anchor="mm")
        # Bottom block C
        draw.rounded_rectangle([cx - 8, cy - 16, cx + 48, cy + 34], radius=8, fill=(209, 250, 229), outline=(16, 185, 129), width=3)
        draw.text((cx + 20, cy + 9), "C", font=font_b, fill=(4, 120, 87), anchor="mm")
    elif "picture_book" in icon_name:
        # Open storybook
        draw.rounded_rectangle([cx - 86, cy - 56, cx + 86, cy + 56], radius=20, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 78, cy - 48, cx - 4, cy + 46], radius=8, fill=(255, 251, 235), outline=(180, 83, 9), width=3)
        draw.rounded_rectangle([cx + 4, cy - 48, cx + 78, cy + 46], radius=8, fill=(255, 251, 235), outline=(180, 83, 9), width=3)
        draw.text((cx - 40, cy), "☀️", font=get_font(42), anchor="mm")
        draw.text((cx + 40, cy), "🐶", font=get_font(42), anchor="mm")
    elif "crayon" in icon_name:
        # 3 chunky crayons
        draw.rounded_rectangle([cx - 76, cy - 66, cx + 76, cy + 66], radius=20, fill=(255, 255, 255))
        for (ox, c_col) in [(-36, (239, 68, 68)), (0, (59, 130, 246)), (36, (34, 197, 94))]:
            draw.rounded_rectangle([cx + ox - 12, cy - 45, cx + ox + 12, cy + 55], radius=6, fill=c_col, outline=(30, 41, 59), width=2)
    elif "balloon" in icon_name:
        # Red floating balloon
        draw.ellipse([cx - 56, cy - 80, cx + 56, cy + 40], fill=(255, 255, 255))
        draw.ellipse([cx - 48, cy - 72, cx + 48, cy + 32], fill=(239, 68, 68), outline=(185, 28, 28), width=3)
        draw.chord([cx - 36, cy - 60, cx + 10, cy - 14], 180, 270, fill=(255, 255, 255, 160))
        # String
        draw.line([cx, cy + 34, cx - 8, cy + 55, cx + 8, cy + 75], fill=(120, 80, 50), width=3)
    elif "heart" in icon_name:
        # Trio of soft pink watercolor hearts
        draw.ellipse([cx - 65, cy - 65, cx + 65, cy + 65], fill=(255, 255, 255))
        font_h = get_font(72)
        draw.text((cx, cy), "💖", font=font_h, anchor="mm")
    elif "sparkle" in icon_name:
        # Twinkle star sparkles
        draw.ellipse([cx - 65, cy - 65, cx + 65, cy + 65], fill=(255, 255, 255))
        font_s = get_font(76)
        draw.text((cx, cy), "✨", font=font_s, anchor="mm")
    else:  # Star
        draw.ellipse([cx - 88, cy - 88, cx + 88, cy + 88], fill=(255, 255, 255))
        font = get_font(130)
        draw.text((cx, cy), "⭐", font=font, fill=(250, 204, 21), anchor="mm")

    return canvas.resize((size, size), Image.Resampling.LANCZOS)

def get_or_render_sticker(sticker_info: Dict[str, Any], force: bool = False) -> str:
    """Returns absolute file path to the transparent sticker PNG, generating if not present."""
    s_id = sticker_info.get("id") or "sticker_custom"
    file_path = os.path.join(STICKER_DIR, f"{s_id}.png")
    
    if os.path.exists(file_path) and not force:
        return file_path

    s_type = sticker_info.get("type", "word")
    if s_type == "letter":
        letter = sticker_info.get("content") or sticker_info.get("letter") or "A"
        theme = sticker_info.get("color_theme") or "rose"
        img = generate_toy_block(letter, theme)
    elif s_type == "number":
        num = sticker_info.get("content") or sticker_info.get("number") or "1"
        theme = sticker_info.get("color_theme") or "amber"
        img = generate_toy_block(num, theme)
    elif s_type == "icon":
        icon = sticker_info.get("content") or sticker_info.get("icon") or "banana"
        img = generate_prop_icon(icon)
    else:  # word badge
        chinese = sticker_info.get("content") or sticker_info.get("chinese") or "多謝"
        english = sticker_info.get("english") or "Thank you"
        theme = sticker_info.get("color_theme") or "amber"
        img = generate_vocab_badge(chinese, english, theme)

    img.save(file_path, format="PNG")
    return file_path

def ensure_base_stickers():
    """Pre-generates all default catalog stickers on startup."""
    for s in STICKER_CATALOG:
        get_or_render_sticker(s)

ensure_base_stickers()
