import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from scripts.maintenance_guard import PROJECT_ROOT, configure_cli, output_path
except ModuleNotFoundError as exc:
    if exc.name not in {"scripts", "scripts.maintenance_guard"}:
        raise
    from maintenance_guard import PROJECT_ROOT, configure_cli, output_path

SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
CHAR_DIR = os.path.join(PROJECT_ROOT, "assets", "characters")

# -------------------------------------------------------------
# Canonical Color Constants matching Style Guide & Glossy Finish
# -------------------------------------------------------------
CHARCOAL_STROKE = (30, 41, 59, 255)       # Solid dark slate #1e293b
SEPIA_STROKE = (45, 25, 20, 255)          # Deep storybook outline

# Skin Tones & Rosy Blushes
LEVI_SKIN = (248, 207, 172, 255)
LEVI_SKIN_SHADOW = (235, 180, 145, 255)
LEVI_BLUSH = (244, 114, 182, 140)

LUCA_SKIN = (249, 203, 168, 255)
LUCA_SKIN_SHADOW = (235, 175, 140, 255)
LUCA_BLUSH = (244, 114, 182, 140)

DAD_SKIN = (241, 185, 138, 255)
MOM_SKIN = (249, 198, 155, 255)

# Solid Saturated Clothing Palette
LEVI_RED_POLO = (220, 38, 38, 255)        # Solid vibrant red #dc2626
LEVI_RED_DARK = (185, 28, 28, 255)
LEVI_RED_LIGHT = (239, 68, 68, 255)

LUCA_YELLOW_POLO = (250, 204, 21, 255)    # Solid golden yellow #facc15
LUCA_YELLOW_DARK = (217, 119, 6, 255)
LUCA_YELLOW_LIGHT = (254, 240, 138, 255)

NAVY_SHORTS = (30, 58, 138, 255)          # Deep solid navy #1e3a8a
NAVY_SHADOW = (15, 23, 42, 255)
BLUE_SNEAKER = (29, 78, 216, 255)
WHITE_GLOSS = (255, 255, 255, 255)
WHITE_SPECULAR = (255, 255, 255, 230)

DAD_GREEN_SHIRT = (47, 133, 90, 255)      # Solid rich forest slate
DAD_KHAKI_PANTS = (194, 165, 126, 255)

MOM_LAVENDER_SWEATER = (192, 132, 210, 255)
MOM_BEIGE_PANTS = (212, 190, 160, 255)

# Glossy Teardrop Palette
TEAR_BLUE_FILL = (147, 197, 253, 220)
TEAR_BLUE_STROKE = (37, 99, 235, 255)

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

def load_sprite(name: str) -> Image.Image:
    p = os.path.join(SPRITES_DIR, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"Sprite not found: {p}")
    return Image.open(p).convert("RGBA")

def save_sprite(im: Image.Image, filename: str):
    bbox = im.getbbox()
    if bbox:
        pad = 8
        w, h = im.size
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad)
        )
        cropped = im.crop(crop_box)
    else:
        cropped = im
    out_path = os.path.join(SPRITES_DIR, filename)
    cropped.save(output_path(out_path), format="PNG", optimize=True)
    print(f"  [GLOSSY SOLID SPRITE] Saved {filename} ({cropped.width}x{cropped.height})")

def render_high_res_overlay(size, draw_fn, scale=3):
    """Render high quality anti-aliased graphics at 3x scale and downsample."""
    w, h = size
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    big_draw = ImageDraw.Draw(big)
    draw_fn(big_draw, scale)
    return big.resize((w, h), Image.Resampling.LANCZOS)

def patch_face_area(img: Image.Image, box, skin_color, blush_color=None, blush_center=None, blush_radius=20):
    """Seamlessly clean and patch a facial feature area using skin tones and soft blush."""
    draw = ImageDraw.Draw(img, "RGBA")
    x1, y1, x2, y2 = box
    draw.rectangle([x1, y1, x2, y2], fill=skin_color)
    if blush_color and blush_center:
        bx, by = blush_center
        for r in range(blush_radius, 0, -2):
            alpha = int(blush_color[3] * (1.0 - (r / blush_radius) ** 1.5))
            draw.ellipse([bx - r, by - r, bx + r, by + r], fill=(blush_color[0], blush_color[1], blush_color[2], alpha))

# =============================================================
# 1. LEVI POSES (Solid Red Polo, Glossy Highlights)
# =============================================================

def generate_levi_sad():
    """
    1. Levi Sad: Genuine sad expression with tilted sad eyebrows, teary eyes,
    downturned sad pout mouth, glossy teardrop, solid red polo.
    """
    base = load_sprite("levi.png")
    w, h = base.size
    im = base.copy()
    
    # 1. Seamlessly patch mouth and eyebrow areas
    patch_face_area(im, (135, 255, 225, 298), LEVI_SKIN)
    patch_face_area(im, (105, 168, 250, 196), LEVI_SKIN)

    def draw_sad_features(draw, s):
        # 1. Sad upturned-in-center Eyebrows ( \  / )
        draw.line([(120*s, 192*s), (145*s, 178*s), (160*s, 176*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")
        draw.line([(195*s, 176*s), (210*s, 178*s), (235*s, 192*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")

        # 2. Sad downturned pout mouth with solid lip color
        cx, cy = 178 * s, 276 * s
        # Curved pout line
        draw.arc([cx - 24*s, cy - 6*s, cx + 24*s, cy + 24*s], start=195, end=345, fill=CHARCOAL_STROKE, width=4*s)
        # Gentle lower lip pout shadow with rosy tint
        draw.arc([cx - 14*s, cy + 6*s, cx + 14*s, cy + 20*s], start=20, end=160, fill=(235, 120, 120, 200), width=3*s)

        # 3. Glossy tear pooling in eyes (glistening lower eye crescent)
        draw.ellipse([(130*s, 226*s), (148*s, 234*s)], fill=WHITE_GLOSS)
        draw.ellipse([(208*s, 226*s), (226*s, 234*s)], fill=WHITE_GLOSS)

        # 4. Glossy 3D teardrop rolling down cheek
        tx, ty = 142 * s, 240 * s
        tw, th = 14 * s, 22 * s
        # Solid teardrop body with stroke
        draw.polygon([(tx, ty), (tx - tw//2, ty + th), (tx + tw//2, ty + th)], fill=TEAR_BLUE_FILL, outline=TEAR_BLUE_STROKE)
        draw.ellipse([tx - tw//2, ty + th - tw//2, tx + tw//2, ty + th + tw//2], fill=TEAR_BLUE_FILL, outline=TEAR_BLUE_STROKE)
        # Glossy white curved highlight
        draw.ellipse([tx - tw//4, ty + th//2, tx, ty + th*3//4], fill=WHITE_SPECULAR)
        draw.ellipse([tx - 2*s, ty + th - 4*s, tx + 2*s, ty + th], fill=WHITE_GLOSS)

    overlay = render_high_res_overlay((w, h), draw_sad_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_sad.png")

def generate_levi_holding_book():
    """
    2. Levi Holding Book: Both hands cradling an open picture book squarely
    in front of chest, solid colors, glossy finish, zero hanging side arms.
    """
    base = load_sprite("levi.png")
    w, h = base.size
    im = base.copy()

    # Softly shift mouth to warm sweet reading smile
    patch_face_area(im, (140, 255, 220, 295), LEVI_SKIN)

    # Inpaint side arms to eliminate hanging arm ghosting behind the book
    # Left arm zone (x: 55 to 110, y: 380 to 560), Right arm zone (x: 245 to 305, y: 380 to 560)
    draw_base = ImageDraw.Draw(im, "RGBA")
    draw_base.rectangle([55, 410, 110, 560], fill=(0, 0, 0, 0))
    draw_base.rectangle([245, 410, 305, 560], fill=(0, 0, 0, 0))

    def draw_book_and_hands(draw, s):
        # 1. Sweet reading mouth
        cx, cy = 178 * s, 272 * s
        draw.arc([cx - 18*s, cy - 12*s, cx + 18*s, cy + 12*s], start=20, end=160, fill=CHARCOAL_STROKE, width=4*s)

        # 2. Solid Color Storybook dimensions squarely in front of chest
        bx, by = 178 * s, 460 * s
        bw, bh = 186 * s, 120 * s

        # Book Soft Drop Shadow
        draw.ellipse([bx - bw//2 - 10*s, by + bh//2 + 4*s, bx + bw//2 + 10*s, by + bh//2 + 22*s], fill=(15, 23, 42, 60))

        # Vibrant Glossy Book Cover (Crimson Red / Golden Trim)
        draw.rounded_rectangle([bx - bw//2 - 6*s, by - bh//2 - 4*s, bx + bw//2 + 6*s, by + bh//2 + 6*s], radius=10*s, fill=LEVI_RED_DARK, outline=CHARCOAL_STROKE, width=4*s)

        # Crisp Open Pages: Left & Right
        draw.rounded_rectangle([bx - bw//2, by - bh//2, bx - 4*s, by + bh//2], radius=6*s, fill=(255, 255, 255, 255), outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([bx + 4*s, by - bh//2, bx + bw//2, by + bh//2], radius=6*s, fill=(255, 255, 255, 255), outline=CHARCOAL_STROKE, width=3*s)

        # Book Illustrations: Left Page Rainbow & Sun
        lx, ly = bx - bw//4, by
        draw.arc([lx - 25*s, ly - 20*s, lx + 25*s, ly + 20*s], start=180, end=360, fill=(239, 68, 68, 255), width=4*s)
        draw.arc([lx - 20*s, ly - 15*s, lx + 20*s, ly + 15*s], start=180, end=360, fill=(245, 158, 11, 255), width=4*s)
        draw.arc([lx - 15*s, ly - 10*s, lx + 15*s, ly + 10*s], start=180, end=360, fill=(59, 130, 246, 255), width=4*s)

        # Right Page: Golden Star & Text Lines
        rx, ry = bx + bw//4, by - 15*s
        draw.polygon([(rx, ry - 14*s), (rx + 4*s, ry - 4*s), (rx + 14*s, ry - 4*s), (rx + 6*s, ry + 3*s), (rx + 9*s, ry + 13*s), (rx, ry + 7*s), (rx - 9*s, ry + 13*s), (rx - 6*s, ry + 3*s), (rx - 14*s, ry - 4*s), (rx - 4*s, ry - 4*s)], fill=(250, 204, 21, 255), outline=CHARCOAL_STROKE, width=2*s)
        draw.line([(rx - 25*s, ry + 22*s), (rx + 25*s, ry + 22*s)], fill=(148, 163, 184, 255), width=3*s)
        draw.line([(rx - 20*s, ry + 30*s), (rx + 20*s, ry + 30*s)], fill=(148, 163, 184, 255), width=3*s)

        # 3. Natural Arms extending from shoulders to hold book
        # Left Arm Sleeves & Forearm
        draw.polygon([(90*s, 380*s), (65*s, 440*s), (bx - bw//2 + 10*s, by + bh//2 - 10*s), (120*s, 410*s)], fill=LEVI_RED_POLO, outline=CHARCOAL_STROKE, width=3*s)
        # Right Arm Sleeves & Forearm
        draw.polygon([(270*s, 380*s), (295*s, 440*s), (bx + bw//2 - 10*s, by + bh//2 - 10*s), (240*s, 410*s)], fill=LEVI_RED_POLO, outline=CHARCOAL_STROKE, width=3*s)

        # Chubby Toddler Hands Holding the Bottom Corners of the Book
        # Left Hand
        draw.ellipse([bx - bw//2 - 8*s, by + bh//2 - 22*s, bx - bw//2 + 26*s, by + bh//2 + 14*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([bx - bw//2 + 4*s, by + bh//2 - 28*s, bx - bw//2 + 20*s, by + bh//2 - 10*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        # Right Hand
        draw.ellipse([bx + bw//2 - 26*s, by + bh//2 - 22*s, bx + bw//2 + 8*s, by + bh//2 + 14*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([bx + bw//2 - 20*s, by + bh//2 - 28*s, bx + bw//2 - 4*s, by + bh//2 - 10*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((w, h), draw_book_and_hands)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_holding_book.png")

def generate_levi_thinking():
    """
    3. Levi Thinking: Inquisitive head tilt, one chubby finger to chin,
    glossy curious gaze, clean two-arm anatomy (no extra arm).
    """
    base = load_sprite("levi.png")
    w, h = base.size
    im = base.copy()

    # Erase mouth and right eyebrow
    patch_face_area(im, (140, 255, 220, 295), LEVI_SKIN)
    patch_face_area(im, (185, 165, 245, 198), LEVI_SKIN)
    # Erase right side arm to avoid 3-arm glitch
    draw_base = ImageDraw.Draw(im, "RGBA")
    draw_base.rectangle([240, 420, 310, 560], fill=(0, 0, 0, 0))

    def draw_thinking_features(draw, s):
        # 1. Quizzical raised right eyebrow
        draw.line([(190*s, 172*s), (210*s, 164*s), (235*s, 172*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")

        # 2. Inquisitive curious "o" mouth
        cx, cy = 176 * s, 272 * s
        draw.ellipse([cx - 10*s, cy - 8*s, cx + 10*s, cy + 8*s], fill=(244, 114, 182, 255), outline=CHARCOAL_STROKE, width=3*s)

        # 3. Natural right arm reaching up to touch chin
        # Red sleeve
        draw.rounded_rectangle([230*s, 380*s, 280*s, 440*s], radius=15*s, fill=LEVI_RED_POLO, outline=CHARCOAL_STROKE, width=4*s)
        # Forearm reaching up to cheek
        draw.polygon([(250*s, 410*s), (225*s, 290*s), (205*s, 280*s), (240*s, 430*s)], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        # Hand & thinking index finger resting on cheek
        draw.ellipse([210*s, 250*s, 238*s, 280*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([206*s, 240*s, 220*s, 266*s], radius=6*s, fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)

        # 4. Cute glossy thought bubble
        draw.ellipse([240*s, 100*s, 255*s, 115*s], fill=(254, 240, 138, 240), outline=CHARCOAL_STROKE, width=2*s)
        draw.ellipse([258*s, 65*s, 282*s, 89*s], fill=(254, 240, 138, 240), outline=CHARCOAL_STROKE, width=2*s)
        draw.ellipse([275*s, 25*s, 310*s, 60*s], fill=(253, 224, 71, 255), outline=CHARCOAL_STROKE, width=2*s)
        # Glossy star in thought bubble
        tx, ty = 292 * s, 42 * s
        draw.line([(tx - 8*s, ty), (tx + 8*s, ty)], fill=(217, 119, 6, 255), width=2*s)
        draw.line([(tx, ty - 8*s), (tx, ty + 8*s)], fill=(217, 119, 6, 255), width=2*s)

    overlay = render_high_res_overlay((w, h), draw_thinking_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_thinking.png")

def generate_levi_sitting_floor():
    """
    4. Levi Sitting Floor: Cross-legged sitting posture on playmat with solid
    navy shorts, red polo, royal blue sneakers, holding a toy block.
    """
    base = load_sprite("levi.png")
    bw, bh = base.size
    upper = base.crop((0, 0, bw, int(bh * 0.62)))
    uw, uh = upper.size

    canvas_w, canvas_h = bw + 80, uh + 180
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = 40
    canvas.paste(upper, (ox, 0), upper)

    def draw_seated_lower_body(draw, s):
        cx = (canvas_w // 2) * s
        ground_y = (canvas_h - 40) * s

        # 1. Soft ground shadow
        draw.ellipse([cx - 160*s, ground_y - 20*s, cx + 160*s, ground_y + 25*s], fill=(15, 23, 42, 60))

        # 2. Folded Solid Navy Blue Shorts / Lap
        draw.rounded_rectangle([cx - 110*s, (uh - 25)*s, cx + 110*s, ground_y - 20*s], radius=25*s, fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)

        # 3. Cross-Legged Folded Knees
        draw.ellipse([cx - 160*s, ground_y - 75*s, cx - 40*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)
        draw.ellipse([cx + 40*s, ground_y - 75*s, cx + 160*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)

        # 4. Royal Blue Sneakers with glossy white soles
        # Left Sneaker
        draw.rounded_rectangle([cx - 170*s, ground_y - 45*s, cx - 115*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([cx - 170*s, ground_y - 12*s, cx - 115*s, ground_y + 2*s], radius=4*s, fill=WHITE_GLOSS, outline=CHARCOAL_STROKE, width=2*s)

        # Right Sneaker
        draw.rounded_rectangle([cx + 115*s, ground_y - 45*s, cx + 170*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([cx + 115*s, ground_y - 12*s, cx + 170*s, ground_y + 2*s], radius=4*s, fill=WHITE_GLOSS, outline=CHARCOAL_STROKE, width=2*s)

        # 5. Colorful ABC Toy Block in Lap
        bx, by = cx, ground_y - 45*s
        bs = 44 * s
        draw.rounded_rectangle([bx - bs//2, by - bs//2, bx + bs//2, by + bs//2], radius=6*s, fill=LEVI_RED_POLO, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([bx - bs//2 + 4*s, by - bs//2 + 4*s, bx + bs//2 - 4*s, by + bs//2 - 4*s], radius=4*s, fill=(254, 226, 226, 255))
        draw.text((bx - 12*s, by - 18*s), "A", fill=(185, 28, 28, 255), font=get_font(26 * s, bold=True))

        # Hands Resting on Knees / Block
        draw.ellipse([bx - bs//2 - 20*s, by - 10*s, bx - bs//2 + 8*s, by + 18*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([bx + bs//2 - 8*s, by - 10*s, bx + bs//2 + 20*s, by + 18*s], fill=LEVI_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_seated_lower_body)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "levi_sitting_floor.png")

# =============================================================
# 2. LUCA POSES (Solid Sunny-Yellow Polo, Glossy Highlights)
# =============================================================

def generate_luca_crying():
    """
    5. Luca Crying: Genuine crying expression! Eyes tightly closed squeezing tears,
    open crying wail mouth, glossy teardrop streams, sunny yellow polo.
    """
    base = load_sprite("luca.png")
    w, h = base.size
    im = base.copy()

    # Patch mouth & eyes cleanly
    patch_face_area(im, (100, 195, 230, 242), LUCA_SKIN, LUCA_BLUSH, (165, 245), 25)
    patch_face_area(im, (120, 255, 210, 298), LUCA_SKIN)

    def draw_crying_features(draw, s):
        # 1. Distressed upturned crying eyebrows
        draw.line([(105*s, 195*s), (135*s, 180*s), (150*s, 178*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")
        draw.line([(180*s, 178*s), (195*s, 180*s), (225*s, 195*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")

        # 2. Squeezed shut crying eyes ( > < arcs with eyelashes )
        draw.line([(118*s, 210*s), (136*s, 220*s), (118*s, 230*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")
        draw.line([(212*s, 210*s), (194*s, 220*s), (212*s, 230*s)], fill=CHARCOAL_STROKE, width=4*s, joint="round")

        # 3. Open crying toddler mouth (\_/ shaped crying wail)
        cx, cy = 165 * s, 276 * s
        mw, mh = 34 * s, 24 * s
        draw.rounded_rectangle([cx - mw//2, cy - mh//2, cx + mw//2, cy + mh//2], radius=8*s, fill=(159, 18, 57, 255), outline=CHARCOAL_STROKE, width=4*s)
        # Trembling crying tongue
        draw.chord([cx - mw//3, cy + 2*s, cx + mw//3, cy + mh//2], start=0, end=180, fill=(251, 113, 133, 255))

        # 4. Glossy Teardrops bursting and flowing down both cheeks
        for tx, ty in [(110*s, 222*s), (102*s, 244*s), (108*s, 268*s)]:
            draw.ellipse([tx - 6*s, ty - 8*s, tx + 6*s, ty + 8*s], fill=TEAR_BLUE_FILL, outline=TEAR_BLUE_STROKE, width=2*s)
            draw.ellipse([tx - 2*s, ty - 4*s, tx + 2*s, ty], fill=WHITE_GLOSS)

        for tx, ty in [(220*s, 222*s), (228*s, 244*s), (222*s, 268*s)]:
            draw.ellipse([tx - 6*s, ty - 8*s, tx + 6*s, ty + 8*s], fill=TEAR_BLUE_FILL, outline=TEAR_BLUE_STROKE, width=2*s)
            draw.ellipse([tx - 2*s, ty - 4*s, tx + 2*s, ty], fill=WHITE_GLOSS)

    overlay = render_high_res_overlay((w, h), draw_crying_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "luca_crying.png")

def generate_luca_pointing():
    """
    6. Luca Pointing: Exact Luca model, natural pointing right arm, clean 2-arm anatomy.
    """
    base = load_sprite("luca.png")
    w, h = base.size
    canvas_w = w + 70
    canvas = Image.new("RGBA", (canvas_w, h), (0, 0, 0, 0))
    canvas.paste(base, (20, 0), base)

    # Inpaint right hanging arm
    draw_base = ImageDraw.Draw(canvas, "RGBA")
    draw_base.rectangle([215, 410, 275, 560], fill=(0, 0, 0, 0))

    def draw_pointing_arm(draw, s):
        px, py = (w - 10) * s, 440 * s
        # Sunny yellow sleeve
        draw.rounded_rectangle([px - 40*s, py - 30*s, px + 20*s, py + 25*s], radius=12*s, fill=LUCA_YELLOW_POLO, outline=CHARCOAL_STROKE, width=4*s)
        # Forearm extending out
        draw.polygon([(px + 10*s, py - 20*s), (px + 65*s, py - 35*s), (px + 65*s, py + 5*s), (px + 10*s, py + 20*s)], fill=LUCA_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        # Chubby hand with pointing index finger
        draw.ellipse([px + 50*s, py - 25*s, px + 75*s, py + 10*s], fill=LUCA_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([px + 65*s, py - 35*s, px + 95*s, py - 18*s], radius=8*s, fill=LUCA_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((canvas_w, h), draw_pointing_arm)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "luca_pointing.png")

def generate_luca_sitting_floor():
    """
    7. Luca Sitting Floor: Seated toddler in sunny yellow polo on playmat.
    """
    base = load_sprite("luca.png")
    bw, bh = base.size
    upper = base.crop((0, 0, bw, int(bh * 0.62)))
    uw, uh = upper.size

    canvas_w, canvas_h = bw + 80, uh + 180
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = 40
    canvas.paste(upper, (ox, 0), upper)

    def draw_seated_luca(draw, s):
        cx = (canvas_w // 2) * s
        ground_y = (canvas_h - 40) * s

        # Drop shadow
        draw.ellipse([cx - 160*s, ground_y - 20*s, cx + 160*s, ground_y + 25*s], fill=(15, 23, 42, 60))

        # Folded Navy Shorts
        draw.rounded_rectangle([cx - 110*s, (uh - 25)*s, cx + 110*s, ground_y - 20*s], radius=25*s, fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)
        draw.ellipse([cx - 160*s, ground_y - 75*s, cx - 40*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)
        draw.ellipse([cx + 40*s, ground_y - 75*s, cx + 160*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=CHARCOAL_STROKE, width=4*s)

        # Sneakers
        draw.rounded_rectangle([cx - 170*s, ground_y - 45*s, cx - 115*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([cx - 170*s, ground_y - 12*s, cx - 115*s, ground_y + 2*s], radius=4*s, fill=WHITE_GLOSS, outline=CHARCOAL_STROKE, width=2*s)
        draw.rounded_rectangle([cx + 115*s, ground_y - 45*s, cx + 170*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=CHARCOAL_STROKE, width=3*s)
        draw.rounded_rectangle([cx + 115*s, ground_y - 12*s, cx + 170*s, ground_y + 2*s], radius=4*s, fill=WHITE_GLOSS, outline=CHARCOAL_STROKE, width=2*s)

        # Hands in Lap
        draw.ellipse([cx - 35*s, ground_y - 50*s, cx - 5*s, ground_y - 20*s], fill=LUCA_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([cx + 5*s, ground_y - 50*s, cx + 35*s, ground_y - 20*s], fill=LUCA_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_seated_luca)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "luca_sitting_floor.png")

# =============================================================
# 3. DAD POSES (Solid Green Shirt, Khaki Pants)
# =============================================================

def generate_dad_comforting_hug():
    """
    8. Dad Comforting Hug: Kneeling dad with open welcoming arms, solid colors, clean 2-arm anatomy.
    """
    base = load_sprite("dad.png")
    bw, bh = base.size
    upper = base.crop((0, 0, bw, int(bh * 0.65)))
    uw, uh = upper.size

    canvas_w, canvas_h = bw + 140, uh + 190
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = 70
    canvas.paste(upper, (ox, 0), upper)

    # Inpaint hanging side arms
    draw_base = ImageDraw.Draw(canvas, "RGBA")
    draw_base.rectangle([ox + 40, 360, ox + 110, 560], fill=(0, 0, 0, 0))
    draw_base.rectangle([ox + 270, 360, ox + 340, 560], fill=(0, 0, 0, 0))

    def draw_kneeling_hug(draw, s):
        cx = (canvas_w // 2) * s
        ground_y = (canvas_h - 40) * s

        # Drop shadow
        draw.ellipse([cx - 180*s, ground_y - 20*s, cx + 180*s, ground_y + 25*s], fill=(15, 23, 42, 60))

        # Kneeling Khaki Chinos
        draw.rounded_rectangle([cx - 130*s, (uh - 20)*s, cx + 130*s, ground_y - 15*s], radius=25*s, fill=DAD_KHAKI_PANTS, outline=CHARCOAL_STROKE, width=4*s)

        # Open Hugging Arms Reaching Forward
        # Left Arm
        draw.polygon([(ox + 70)*s, 340*s, 30*s, 440*s, 40*s, 470*s, (ox + 100)*s, 400*s], fill=DAD_GREEN_SHIRT, outline=CHARCOAL_STROKE, width=4*s)
        draw.ellipse([15*s, 430*s, 55*s, 475*s], fill=DAD_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        # Right Arm
        draw.polygon([(ox + 310)*s, 340*s, (canvas_w - 30)*s, 440*s, (canvas_w - 40)*s, 470*s, (ox + 280)*s, 400*s], fill=DAD_GREEN_SHIRT, outline=CHARCOAL_STROKE, width=4*s)
        draw.ellipse([(canvas_w - 55)*s, 430*s, (canvas_w - 15)*s, 475*s], fill=DAD_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_kneeling_hug)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "dad_comforting_hug.png")

def generate_dad_clapping():
    """
    9. Dad Clapping: Proud fatherly clapping hands in front of chest.
    """
    base = load_sprite("dad.png")
    w, h = base.size
    im = base.copy()

    # Inpaint hanging side arms to eliminate extra limbs
    draw_base = ImageDraw.Draw(im, "RGBA")
    draw_base.rectangle([50, 380, 110, 560], fill=(0, 0, 0, 0))
    draw_base.rectangle([270, 380, 330, 560], fill=(0, 0, 0, 0))

    def draw_clapping_arms(draw, s):
        cx = (w // 2) * s
        # Clapping Arms meeting in center of chest
        draw.polygon([(90*s, 360*s), (cx - 30*s, 450*s), (cx - 10*s, 480*s), (120*s, 400*s)], fill=DAD_GREEN_SHIRT, outline=CHARCOAL_STROKE, width=4*s)
        draw.polygon([(290*s, 360*s), (cx + 30*s, 450*s), (cx + 10*s, 480*s), (260*s, 400*s)], fill=DAD_GREEN_SHIRT, outline=CHARCOAL_STROKE, width=4*s)

        # Clapping Hands with proud pose
        draw.ellipse([cx - 35*s, 440*s, cx + 5*s, 485*s], fill=DAD_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([cx - 5*s, 440*s, cx + 35*s, 485*s], fill=DAD_SKIN, outline=CHARCOAL_STROKE, width=3*s)

        # Celebration sparkle
        draw.line([(cx, 420*s), (cx, 432*s)], fill=(250, 204, 21, 255), width=3*s)
        draw.line([(cx - 8*s, 426*s), (cx + 8*s, 426*s)], fill=(250, 204, 21, 255), width=3*s)

    overlay = render_high_res_overlay((w, h), draw_clapping_arms)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "dad_clapping.png")

# =============================================================
# 4. MOM POSES (Solid Striped / Lavender, Glossy Dark Hair)
# =============================================================

def generate_mom_waving():
    """
    10. Mom Waving: Graceful waving pose with clean 2-arm anatomy.
    """
    base = load_sprite("mom.png")
    w, h = base.size
    canvas_w = w + 60
    canvas = Image.new("RGBA", (canvas_w, h), (0, 0, 0, 0))
    canvas.paste(base, (10, 0), base)

    # Inpaint right hanging arm
    draw_base = ImageDraw.Draw(canvas, "RGBA")
    draw_base.rectangle([290, 380, 360, 560], fill=(0, 0, 0, 0))

    def draw_waving_arm(draw, s):
        rx, ry = (w - 20) * s, 420 * s
        # Lavender sleeve reaching up
        draw.polygon([(280*s, 360*s), (canvas_w - 30)*s, 310*s, (canvas_w - 45)*s, 335*s, 295*s, 395*s], fill=MOM_LAVENDER_SWEATER, outline=CHARCOAL_STROKE, width=4*s)
        # Graceful waving hand
        hx, hy = (canvas_w - 25) * s, 295 * s
        draw.ellipse([hx - 20*s, hy - 25*s, hx + 20*s, hy + 20*s], fill=MOM_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((canvas_w, h), draw_waving_arm)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "mom_waving.png")

def generate_mom_holding_bowl():
    """
    11. Mom Holding Bowl: Holding a steaming bamboo dim sum basket with both hands.
    """
    base = load_sprite("mom.png")
    w, h = base.size
    im = base.copy()

    # Inpaint hanging side arms
    draw_base = ImageDraw.Draw(im, "RGBA")
    draw_base.rectangle([70, 380, 130, 560], fill=(0, 0, 0, 0))
    draw_base.rectangle([310, 380, 370, 560], fill=(0, 0, 0, 0))

    def draw_dim_sum_basket(draw, s):
        cx, cy = (w // 2) * s, 470 * s
        bw, bh = 140 * s, 70 * s

        # Arms holding basket
        draw.polygon([(100*s, 360*s), (cx - bw//2 + 10*s, cy + 10*s), (cx - bw//2 + 25*s, cy + 30*s), (130*s, 390*s)], fill=MOM_LAVENDER_SWEATER, outline=CHARCOAL_STROKE, width=4*s)
        draw.polygon([(340*s, 360*s), (cx + bw//2 - 10*s, cy + 10*s), (cx + bw//2 - 25*s, cy + 30*s), (310*s, 390*s)], fill=MOM_LAVENDER_SWEATER, outline=CHARCOAL_STROKE, width=4*s)

        # Bamboo Steamer Basket
        draw.rounded_rectangle([cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2], radius=15*s, fill=(217, 160, 102, 255), outline=CHARCOAL_STROKE, width=4*s)
        draw.line([(cx - bw//2, cy), (cx + bw//2, cy)], fill=(180, 120, 70, 255), width=3*s)

        # Steaming Dim Sum Dumplings inside
        for dx in [-35*s, 0, 35*s]:
            draw.ellipse([cx + dx - 18*s, cy - 25*s, cx + dx + 18*s, cy], fill=(255, 250, 240, 255), outline=CHARCOAL_STROKE, width=2*s)
            draw.ellipse([cx + dx - 4*s, cy - 18*s, cx + dx + 4*s, cy - 10*s], fill=(239, 68, 68, 255)) # Orange roe garnish

        # Hands holding rim
        draw.ellipse([cx - bw//2 - 10*s, cy - 10*s, cx - bw//2 + 15*s, cy + 20*s], fill=MOM_SKIN, outline=CHARCOAL_STROKE, width=3*s)
        draw.ellipse([cx + bw//2 - 15*s, cy - 10*s, cx + bw//2 + 10*s, cy + 20*s], fill=MOM_SKIN, outline=CHARCOAL_STROKE, width=3*s)

    overlay = render_high_res_overlay((w, h), draw_dim_sum_basket)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "mom_holding_bowl.png")

# =============================================================
# 5. DOG POSES (Fluffy Pure White Spitz, Red Collar, Golden Bell)
# =============================================================

def generate_dog_curled_sleeping():
    """
    12. Dog Curled Sleeping: Pure white fluffy Spitz sleeping curled up in a donut ball.
    """
    canvas_w, canvas_h = 500, 450
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    def draw_spitz_sleeping(draw, s):
        cx, cy = (canvas_w // 2) * s, (canvas_h // 2) * s

        # Drop shadow
        draw.ellipse([cx - 180*s, cy + 120*s, cx + 180*s, cy + 170*s], fill=(15, 23, 42, 50))

        # Fluffy white body donut circle
        draw.ellipse([cx - 170*s, cy - 140*s, cx + 170*s, cy + 140*s], fill=(255, 255, 255, 255), outline=CHARCOAL_STROKE, width=4*s)

        # Bushy plume tail wrapped around
        draw.arc([cx - 150*s, cy - 120*s, cx + 150*s, cy + 120*s], start=30, end=240, fill=(241, 245, 249, 255), width=35*s)

        # Cute head resting inside curve
        hx, hy = cx - 20*s, cy - 20*s
        draw.ellipse([hx - 70*s, hy - 60*s, hx + 70*s, hy + 60*s], fill=(255, 255, 255, 255), outline=CHARCOAL_STROKE, width=4*s)

        # Fluffy Spitz Ears
        draw.polygon([(hx - 55*s, hy - 45*s), (hx - 30*s, hy - 105*s), (hx - 10*s, hy - 50*s)], fill=(255, 255, 255, 255), outline=CHARCOAL_STROKE, width=3*s)
        draw.polygon([(hx - 45*s, hy - 45*s), (hx - 30*s, hy - 90*s), (hx - 18*s, hy - 50*s)], fill=(254, 205, 211, 255))

        # Red Collar & Golden Bell
        draw.arc([hx - 50*s, hy + 20*s, hx + 50*s, hy + 75*s], start=10, end=170, fill=(220, 38, 38, 255), width=10*s)
        draw.ellipse([hx - 12*s, hy + 65*s, hx + 12*s, hy + 89*s], fill=(250, 204, 21, 255), outline=CHARCOAL_STROKE, width=2*s)

        # Sleeping peaceful curved eyes ( ^ ^ )
        draw.arc([hx - 35*s, hy - 15*s, hx - 15*s, hy], start=180, end=360, fill=CHARCOAL_STROKE, width=3*s)
        draw.arc([hx + 15*s, hy - 15*s, hx + 35*s, hy], start=180, end=360, fill=CHARCOAL_STROKE, width=3*s)

        # Black Button Nose
        draw.ellipse([hx - 10*s, hy + 12*s, hx + 10*s, hy + 26*s], fill=(15, 23, 42, 255))

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_spitz_sleeping)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "dog_curled_sleeping.png")

def main(argv=None):
    configure_cli(argv)
    print("=== Generating 100% Consistent Glossy Solid Sprites ===")
    generate_levi_sad()
    generate_levi_holding_book()
    generate_levi_thinking()
    generate_levi_sitting_floor()
    generate_luca_crying()
    generate_luca_pointing()
    generate_luca_sitting_floor()
    generate_dad_comforting_hug()
    generate_dad_clapping()
    generate_mom_waving()
    generate_mom_holding_bowl()
    generate_dog_curled_sleeping()
    print("=== All Glossy Solid Sprites Generated Successfully! ===")

if __name__ == "__main__":
    main()
