import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
os.makedirs(SPRITES_DIR, exist_ok=True)

# -------------------------------------------------------------
# Color Constants matching Watercolor Storybook Palette
# -------------------------------------------------------------
SEPIA_DARK = (45, 25, 20, 255)
SEPIA_MEDIUM = (85, 45, 30, 255)
LEVI_SKIN = (248, 207, 172, 255)
LEVI_BLUSH = (245, 140, 140, 140)
LUCA_SKIN = (249, 203, 168, 255)
LUCA_BLUSH = (245, 140, 140, 140)
DAD_SKIN = (241, 185, 138, 255)
MOM_SKIN = (249, 198, 155, 255)
TEAR_BLUE = (186, 230, 253, 220)
TEAR_OUTLINE = (59, 130, 246, 240)
TEAR_HIGHLIGHT = (255, 255, 255, 230)

LEVI_RED_POLO = (220, 50, 45, 255)
LEVI_RED_SHADOW = (180, 30, 30, 255)
LUCA_YELLOW_POLO = (250, 204, 21, 255)
LUCA_YELLOW_SHADOW = (217, 119, 6, 255)
NAVY_SHORTS = (30, 58, 138, 255)
NAVY_SHADOW = (15, 23, 42, 255)
BLUE_SNEAKER = (29, 78, 216, 255)
WHITE_ACCENT = (255, 255, 255, 255)

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
    cropped.save(out_path, format="PNG")
    print(f"  [HIGH-FIDELITY] Created {filename} ({cropped.width}x{cropped.height})")

def render_high_res_overlay(size, draw_fn, scale=3):
    """Render high quality anti-aliased graphics at 3x scale and downsample."""
    w, h = size
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    big_draw = ImageDraw.Draw(big)
    draw_fn(big_draw, scale)
    return big.resize((w, h), Image.Resampling.LANCZOS)

def patch_area(img: Image.Image, box, skin_color, blush_color=None, blush_center=None, blush_radius=20):
    """Seamlessly clean and patch a facial feature area using skin tones and soft blush."""
    draw = ImageDraw.Draw(img, "RGBA")
    x1, y1, x2, y2 = box
    draw.rectangle([x1, y1, x2, y2], fill=skin_color)
    if blush_color and blush_center:
        bx, by = blush_center
        # Draw soft radial blush
        for r in range(blush_radius, 0, -2):
            alpha = int(blush_color[3] * (1.0 - (r / blush_radius) ** 1.5))
            draw.ellipse([bx - r, by - r, bx + r, by + r], fill=(blush_color[0], blush_color[1], blush_color[2], alpha))

# =============================================================
# 1. LEVI POSES
# =============================================================

def generate_levi_sad():
    """
    1. Levi Sad: Genuine sad expression with tilted sad eyebrows, teary eyes,
    downturned sad pout mouth, delicate teardrop, and arms tucked in.
    """
    base = load_sprite("levi_default.png")
    w, h = base.size
    im = base.copy()
    
    # 1. Patch mouth area (y: 255 to 295, x: 135 to 225)
    patch_area(im, (135, 255, 225, 292), LEVI_SKIN)
    # Patch eyebrows area (y: 165 to 195, x: 100 to 255)
    patch_area(im, (105, 168, 250, 192), LEVI_SKIN)

    def draw_sad_features(draw, s):
        # 1. Sad upturned-in-center Eyebrows ( \  / )
        # Left Eyebrow: Inner point high, outer point low
        draw.line([(120*s, 190*s), (145*s, 178*s), (160*s, 176*s)], fill=SEPIA_DARK, width=4*s, joint="round")
        # Right Eyebrow: Inner point high, outer point low
        draw.line([(195*s, 176*s), (210*s, 178*s), (235*s, 190*s)], fill=SEPIA_DARK, width=4*s, joint="round")

        # 2. Sad downturned pout mouth
        cx, cy = 178 * s, 274 * s
        # Curved pout line
        draw.arc([cx - 24*s, cy - 4*s, cx + 24*s, cy + 24*s], start=195, end=345, fill=SEPIA_DARK, width=4*s)
        # Gentle lower lip pout shadow
        draw.arc([cx - 14*s, cy + 6*s, cx + 14*s, cy + 18*s], start=20, end=160, fill=(235, 120, 120, 180), width=3*s)

        # 3. Watery tear pooling in eyes (glistening lower highlights)
        draw.ellipse([(132*s, 228*s), (148*s, 234*s)], fill=WHITE_ACCENT)
        draw.ellipse([(208*s, 228*s), (224*s, 234*s)], fill=WHITE_ACCENT)

        # 4. Translucent soft blue teardrop rolling down cheek
        tx, ty = 142 * s, 238 * s
        tw, th = 14 * s, 22 * s
        draw.polygon([(tx, ty), (tx - tw//2, ty + th), (tx + tw//2, ty + th)], fill=TEAR_BLUE, outline=TEAR_OUTLINE)
        draw.ellipse([tx - tw//2, ty + th - tw//2, tx + tw//2, ty + th + tw//2], fill=TEAR_BLUE, outline=TEAR_OUTLINE)
        draw.ellipse([tx - tw//4, ty + th//2, tx, ty + th*3//4], fill=TEAR_HIGHLIGHT)

    overlay = render_high_res_overlay((w, h), draw_sad_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_sad.png")

def generate_levi_holding_book():
    """
    2. Levi Holding Book: Both hands holding & cradling an open picture book squarely
    in front of his chest, with warm reading expression.
    """
    base = load_sprite("levi_default.png")
    w, h = base.size
    im = base.copy()

    # Softly shift mouth to warm sweet reading smile
    patch_area(im, (140, 255, 220, 292), LEVI_SKIN)

    def draw_book_and_hands(draw, s):
        # 1. Sweet reading mouth
        cx, cy = 178 * s, 272 * s
        draw.arc([cx - 18*s, cy - 12*s, cx + 18*s, cy + 12*s], start=20, end=160, fill=SEPIA_DARK, width=4*s)

        # 2. Book dimensions squarely in front of chest
        bx, by = 178 * s, 460 * s
        bw, bh = 180 * s, 115 * s

        # Book Spine & Soft Drop Shadow
        draw.ellipse([bx - bw//2 - 10*s, by + bh//2 + 4*s, bx + bw//2 + 10*s, by + bh//2 + 20*s], fill=(30, 20, 15, 60))

        # Book Cover (Coral Red / Gold Spine matching Levi's palette)
        draw.rounded_rectangle([bx - bw//2 - 6*s, by - bh//2 - 4*s, bx + bw//2 + 6*s, by + bh//2 + 6*s], radius=10*s, fill=LEVI_RED_SHADOW, outline=SEPIA_DARK, width=4*s)

        # Open Pages: Left Page & Right Page
        # Left Page
        draw.rounded_rectangle([bx - bw//2, by - bh//2, bx - 4*s, by + bh//2], radius=6*s, fill=(255, 252, 245, 255), outline=SEPIA_DARK, width=3*s)
        # Right Page
        draw.rounded_rectangle([bx + 4*s, by - bh//2, bx + bw//2, by + bh//2], radius=6*s, fill=(255, 252, 245, 255), outline=SEPIA_DARK, width=3*s)

        # Book Illustrations: Left Page Rainbow & Star
        lx, ly = bx - bw//4, by
        draw.arc([lx - 25*s, ly - 20*s, lx + 25*s, ly + 20*s], start=180, end=360, fill=(239, 68, 68, 255), width=4*s)
        draw.arc([lx - 20*s, ly - 15*s, lx + 20*s, ly + 15*s], start=180, end=360, fill=(245, 158, 11, 255), width=4*s)
        draw.arc([lx - 15*s, ly - 10*s, lx + 15*s, ly + 10*s], start=180, end=360, fill=(59, 130, 246, 255), width=4*s)

        # Right Page: Star & Cantonese ABC text lines
        rx, ry = bx + bw//4, by - 15*s
        draw.polygon([(rx, ry - 14*s), (rx + 4*s, ry - 4*s), (rx + 14*s, ry - 4*s), (rx + 6*s, ry + 3*s), (rx + 9*s, ry + 13*s), (rx, ry + 7*s), (rx - 9*s, ry + 13*s), (rx - 6*s, ry + 3*s), (rx - 14*s, ry - 4*s), (rx - 4*s, ry - 4*s)], fill=(250, 204, 21, 255), outline=SEPIA_DARK, width=2*s)
        draw.line([(rx - 25*s, ry + 22*s), (rx + 25*s, ry + 22*s)], fill=(148, 163, 184, 255), width=3*s)
        draw.line([(rx - 20*s, ry + 30*s), (rx + 20*s, ry + 30*s)], fill=(148, 163, 184, 255), width=3*s)

        # 3. Two Chubby Toddler Hands Holding the Bottom Corners of the Book
        # Left Hand
        draw.ellipse([bx - bw//2 - 8*s, by + bh//2 - 22*s, bx - bw//2 + 26*s, by + bh//2 + 14*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)
        # Left thumb
        draw.ellipse([bx - bw//2 + 4*s, by + bh//2 - 28*s, bx - bw//2 + 20*s, by + bh//2 - 10*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)

        # Right Hand
        draw.ellipse([bx + bw//2 - 26*s, by + bh//2 - 22*s, bx + bw//2 + 8*s, by + bh//2 + 14*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)
        # Right thumb
        draw.ellipse([bx + bw//2 - 20*s, by + bh//2 - 28*s, bx + bw//2 - 4*s, by + bh//2 - 10*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((w, h), draw_book_and_hands)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_holding_book.png")

def generate_levi_thinking():
    """
    3. Levi Thinking: Thoughtful tilted head, gaze looking upward to the side,
    chubby finger touching cheek, inquisitive mouth.
    """
    base = load_sprite("levi_default.png")
    w, h = base.size
    im = base.copy()

    # Patch mouth & right cheek
    patch_area(im, (140, 255, 220, 292), LEVI_SKIN)
    # Patch right eyebrow
    patch_area(im, (185, 165, 245, 195), LEVI_SKIN)

    def draw_thinking_features(draw, s):
        # 1. Quizzical raised right eyebrow
        draw.line([(190*s, 172*s), (210*s, 164*s), (235*s, 172*s)], fill=SEPIA_DARK, width=4*s, joint="round")

        # 2. Inquisitive curious "o" mouth
        cx, cy = 176 * s, 272 * s
        draw.ellipse([cx - 10*s, cy - 8*s, cx + 10*s, cy + 8*s], fill=(244, 114, 182, 255), outline=SEPIA_DARK, width=3*s)

        # 3. Chubby toddler arm and finger touching right cheek
        # Forearm reaching up to cheek
        fx, fy = 230 * s, 260 * s
        draw.polygon([(260*s, 380*s), (235*s, 290*s), (215*s, 280*s), (250*s, 400*s)], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)
        # Hand & thinking index finger resting on cheek
        draw.ellipse([218*s, 250*s, 242*s, 280*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([214*s, 240*s, 228*s, 266*s], radius=6*s, fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)

        # 4. Cute soft thought bubbles above head
        draw.ellipse([240*s, 100*s, 255*s, 115*s], fill=(254, 240, 138, 220), outline=SEPIA_DARK, width=2*s)
        draw.ellipse([258*s, 65*s, 282*s, 89*s], fill=(254, 240, 138, 240), outline=SEPIA_DARK, width=2*s)
        draw.ellipse([275*s, 25*s, 310*s, 60*s], fill=(253, 224, 71, 255), outline=SEPIA_DARK, width=2*s)
        # Star twinkle in largest thought bubble
        tx, ty = 292 * s, 42 * s
        draw.line([(tx - 8*s, ty), (tx + 8*s, ty)], fill=(217, 119, 6, 255), width=2*s)
        draw.line([(tx, ty - 8*s), (tx, ty + 8*s)], fill=(217, 119, 6, 255), width=2*s)

    overlay = render_high_res_overlay((w, h), draw_thinking_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_thinking.png")

def generate_levi_cheering():
    """
    4. Levi Cheering: Both arms raised high enthusiastically, big wide open happy mouth (giggle / cheer),
    joyful sparkling eyes.
    """
    # Use levi_arms_out_hug as the base for raised arms
    base = load_sprite("levi_arms_out_hug.png")
    w, h = base.size
    im = base.copy()

    # Patch mouth for big wide cheering open mouth
    patch_area(im, (w//2 - 50, 250, w//2 + 50, 305), LEVI_SKIN)

    def draw_cheering_features(draw, s):
        cx, cy = (w // 2) * s, 275 * s
        # 1. Big wide open cheering mouth with tongue
        mw, mh = 36 * s, 28 * s
        # Mouth cavity
        draw.chord([cx - mw//2, cy - mh//2, cx + mw//2, cy + mh//2 + 10*s], start=0, end=180, fill=(159, 18, 57, 255), outline=SEPIA_DARK, width=4*s)
        # Happy pink tongue
        draw.chord([cx - mw//3, cy + 2*s, cx + mw//3, cy + mh//2 + 8*s], start=0, end=180, fill=(251, 113, 133, 255))

        # 2. Cheerful celebration sparkles above raised hands
        for sx, sy in [(60*s, 160*s), (100*s, 110*s), ((w - 100)*s, 110*s), ((w - 60)*s, 160*s)]:
            draw.polygon([(sx, sy - 14*s), (sx + 4*s, sy - 4*s), (sx + 14*s, sy - 4*s), (sx + 6*s, sy + 3*s), (sx + 9*s, sy + 13*s), (sx, sy + 7*s), (sx - 9*s, sy + 13*s), (sx - 6*s, sy + 3*s), (sx - 14*s, sy - 4*s), (sx - 4*s, sy - 4*s)], fill=(250, 204, 21, 255), outline=SEPIA_DARK, width=2*s)

    overlay = render_high_res_overlay((w, h), draw_cheering_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "levi_cheering.png")

def generate_levi_sitting_floor():
    """
    5. Levi Sitting Floor: Anatomically correct cross-legged sitting posture on playmat
    with hands resting on knees or holding a colorful ABC toy block.
    """
    base = load_sprite("levi_default.png")
    bw, bh = base.size
    # Crop upper body down to shirt waist
    upper = base.crop((0, 0, bw, int(bh * 0.62)))
    uw, uh = upper.size

    canvas_w, canvas_h = bw + 80, uh + 190
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    # Paste upper body centered
    ox = 40
    canvas.paste(upper, (ox, 0), upper)

    def draw_seated_lower_body(draw, s):
        cx = (canvas_w // 2) * s
        ground_y = (canvas_h - 40) * s

        # 1. Soft ground shadow
        draw.ellipse([cx - 160*s, ground_y - 20*s, cx + 160*s, ground_y + 25*s], fill=(30, 20, 15, 60))

        # 2. Folded Navy Blue Shorts / Lap
        draw.rounded_rectangle([cx - 110*s, (uh - 25)*s, cx + 110*s, ground_y - 20*s], radius=25*s, fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)

        # 3. Cross-Legged Folded Knees & Legs
        # Left Leg & Knee
        draw.ellipse([cx - 160*s, ground_y - 75*s, cx - 40*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)
        # Right Leg & Knee
        draw.ellipse([cx + 40*s, ground_y - 75*s, cx + 160*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)

        # 4. Royal Blue Sneakers visible at sides
        # Left Sneaker
        draw.rounded_rectangle([cx - 170*s, ground_y - 45*s, cx - 115*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([cx - 170*s, ground_y - 12*s, cx - 115*s, ground_y + 2*s], radius=4*s, fill=WHITE_ACCENT, outline=SEPIA_DARK, width=2*s) # White sole

        # Right Sneaker
        draw.rounded_rectangle([cx + 115*s, ground_y - 45*s, cx + 170*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([cx + 115*s, ground_y - 12*s, cx + 170*s, ground_y + 2*s], radius=4*s, fill=WHITE_ACCENT, outline=SEPIA_DARK, width=2*s) # White sole

        # 5. Colorful ABC Toy Building Block in Lap
        bx, by = cx, ground_y - 45*s
        bs = 42 * s
        draw.rounded_rectangle([bx - bs//2, by - bs//2, bx + bs//2, by + bs//2], radius=6*s, fill=(239, 68, 68, 255), outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([bx - bs//2 + 4*s, by - bs//2 + 4*s, bx + bs//2 - 4*s, by + bs//2 - 4*s], radius=4*s, fill=(254, 226, 226, 255))
        # Letter "A" on block
        draw.text((bx - 12*s, by - 18*s), "A", fill=(185, 28, 28, 255), font=get_font(26 * s, bold=True))

        # Chubby Toddler Hands Resting on Knees / Block
        draw.ellipse([bx - bs//2 - 20*s, by - 10*s, bx - bs//2 + 8*s, by + 18*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.ellipse([bx + bs//2 - 8*s, by - 10*s, bx + bs//2 + 20*s, by + 18*s], fill=LEVI_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_seated_lower_body)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "levi_sitting_floor.png")

# =============================================================
# 2. LUCA POSES
# =============================================================

def generate_luca_crying():
    """
    6. Luca Crying: Genuine crying expression! Eyes tightly closed squeezing tears,
    open crying mouth (upset toddler), streams of teardrops.
    """
    base = load_sprite("luca_default.png")
    w, h = base.size
    im = base.copy()

    # Patch mouth (y: 250 to 300) and eyes (y: 195 to 240)
    patch_area(im, (100, 195, 230, 240), LUCA_SKIN, LUCA_BLUSH, (165, 245), 25)
    patch_area(im, (120, 255, 210, 295), LUCA_SKIN)

    def draw_crying_features(draw, s):
        # 1. Distressed upturned crying eyebrows
        draw.line([(105*s, 195*s), (135*s, 180*s), (150*s, 178*s)], fill=SEPIA_DARK, width=4*s, joint="round")
        draw.line([(180*s, 178*s), (195*s, 180*s), (225*s, 195*s)], fill=SEPIA_DARK, width=4*s, joint="round")

        # 2. Squeezed shut crying eyes ( > < arcs with eyelashes )
        # Left Eye ( > )
        draw.line([(118*s, 210*s), (136*s, 220*s), (118*s, 230*s)], fill=SEPIA_DARK, width=4*s, joint="round")
        # Right Eye ( < )
        draw.line([(212*s, 210*s), (194*s, 220*s), (212*s, 230*s)], fill=SEPIA_DARK, width=4*s, joint="round")

        # 3. Open crying toddler mouth (\_/ shaped crying wail)
        cx, cy = 165 * s, 276 * s
        mw, mh = 34 * s, 24 * s
        draw.rounded_rectangle([cx - mw//2, cy - mh//2, cx + mw//2, cy + mh//2], radius=8*s, fill=(159, 18, 57, 255), outline=SEPIA_DARK, width=4*s)
        # Trembling crying tongue
        draw.chord([cx - mw//3, cy + 2*s, cx + mw//3, cy + mh//2], start=0, end=180, fill=(251, 113, 133, 255))

        # 4. Streams of Teardrops bursting and flowing down both cheeks
        # Left cheek teardrops
        for tx, ty in [(110*s, 222*s), (102*s, 244*s), (108*s, 268*s)]:
            draw.ellipse([tx - 6*s, ty - 8*s, tx + 6*s, ty + 8*s], fill=TEAR_BLUE, outline=TEAR_OUTLINE, width=2*s)
            draw.ellipse([tx - 2*s, ty - 4*s, tx + 2*s, ty], fill=TEAR_HIGHLIGHT)

        # Right cheek teardrops
        for tx, ty in [(220*s, 222*s), (228*s, 244*s), (222*s, 268*s)]:
            draw.ellipse([tx - 6*s, ty - 8*s, tx + 6*s, ty + 8*s], fill=TEAR_BLUE, outline=TEAR_OUTLINE, width=2*s)
            draw.ellipse([tx - 2*s, ty - 4*s, tx + 2*s, ty], fill=TEAR_HIGHLIGHT)

    overlay = render_high_res_overlay((w, h), draw_crying_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "luca_crying.png")

def generate_luca_cheering():
    """
    7. Luca Cheering: Arms up celebrating, wide happy toddler smile, sunny yellow polo.
    """
    base = load_sprite("luca_clapping.png")
    w, h = base.size
    im = base.copy()

    # Patch mouth for big wide cheering grin
    patch_area(im, (120, 250, 210, 295), LUCA_SKIN)

    def draw_cheering_features(draw, s):
        cx, cy = (w // 2) * s, 272 * s
        # Wide open toddler cheering smile
        mw, mh = 36 * s, 26 * s
        draw.chord([cx - mw//2, cy - mh//2, cx + mw//2, cy + mh//2 + 8*s], start=0, end=180, fill=(159, 18, 57, 255), outline=SEPIA_DARK, width=4*s)
        draw.chord([cx - mw//3, cy + 2*s, cx + mw//3, cy + mh//2 + 6*s], start=0, end=180, fill=(251, 113, 133, 255))

        # Cheerful celebration stars around hands
        for sx, sy in [(50*s, 180*s), ((w - 50)*s, 180*s), (80*s, 120*s), ((w - 80)*s, 120*s)]:
            draw.polygon([(sx, sy - 12*s), (sx + 4*s, sy - 4*s), (sx + 12*s, sy - 4*s), (sx + 5*s, sy + 3*s), (sx + 8*s, sy + 11*s), (sx, sy + 6*s), (sx - 8*s, sy + 11*s), (sx - 5*s, sy + 3*s), (sx - 12*s, sy - 4*s), (sx - 4*s, sy - 4*s)], fill=(250, 204, 21, 255), outline=SEPIA_DARK, width=2*s)

    overlay = render_high_res_overlay((w, h), draw_cheering_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "luca_cheering.png")

def generate_luca_pointing():
    """
    8. Luca Pointing: Natural pointing posture, pointing finger looking at the subject.
    """
    base = load_sprite("luca_default.png")
    w, h = base.size
    canvas_w = w + 80
    canvas = Image.new("RGBA", (canvas_w, h), (0, 0, 0, 0))
    canvas.paste(base, (20, 0), base)

    def draw_pointing_arm(draw, s):
        # Extending right arm pointing forward
        px, py = (w - 10) * s, 440 * s
        # Yellow sleeve
        draw.rounded_rectangle([px - 40*s, py - 30*s, px + 20*s, py + 25*s], radius=12*s, fill=LUCA_YELLOW_POLO, outline=SEPIA_DARK, width=4*s)
        # Forearm extending out
        draw.polygon([(px + 10*s, py - 20*s), (px + 65*s, py - 35*s), (px + 65*s, py + 5*s), (px + 10*s, py + 20*s)], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)
        # Chubby toddler hand with pointing index finger
        draw.ellipse([px + 50*s, py - 25*s, px + 75*s, py + 10*s], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)
        # Extended pointing finger
        draw.rounded_rectangle([px + 65*s, py - 35*s, px + 95*s, py - 18*s], radius=8*s, fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((canvas_w, h), draw_pointing_arm)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "luca_pointing.png")

def generate_luca_arms_out_hug():
    """
    9. Luca Arms Out Hug: Open hugging arms reaching forward warmly.
    """
    base = load_sprite("luca_default.png")
    w, h = base.size
    canvas_w = w + 90
    canvas = Image.new("RGBA", (canvas_w, h), (0, 0, 0, 0))
    canvas.paste(base, (45, 0), base)

    def draw_hugging_arms(draw, s):
        cx = (canvas_w // 2) * s
        # Left hugging arm
        lx, ly = 45 * s, 430 * s
        draw.rounded_rectangle([lx - 35*s, ly - 30*s, lx + 20*s, ly + 30*s], radius=15*s, fill=LUCA_YELLOW_POLO, outline=SEPIA_DARK, width=4*s)
        draw.ellipse([lx - 45*s, ly - 20*s, lx - 10*s, ly + 25*s], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)

        # Right hugging arm
        rx, ry = (canvas_w - 45) * s, 430 * s
        draw.rounded_rectangle([rx - 20*s, ry - 30*s, rx + 35*s, ry + 30*s], radius=15*s, fill=LUCA_YELLOW_POLO, outline=SEPIA_DARK, width=4*s)
        draw.ellipse([rx + 10*s, ry - 20*s, rx + 45*s, ry + 25*s], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((canvas_w, h), draw_hugging_arms)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "luca_arms_out_hug.png")

def generate_luca_sitting_floor():
    """
    10. Luca Sitting Floor: Seated toddler playing with blocks on playmat.
    """
    base = load_sprite("luca_default.png")
    bw, bh = base.size
    upper = base.crop((0, 0, bw, int(bh * 0.62)))
    uw, uh = upper.size

    canvas_w, canvas_h = bw + 80, uh + 190
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    ox = 40
    canvas.paste(upper, (ox, 0), upper)

    def draw_luca_seated_lower_body(draw, s):
        cx = (canvas_w // 2) * s
        ground_y = (canvas_h - 40) * s

        # Ground shadow
        draw.ellipse([cx - 150*s, ground_y - 20*s, cx + 150*s, ground_y + 25*s], fill=(30, 20, 15, 60))

        # Navy blue toddler shorts lap
        draw.rounded_rectangle([cx - 105*s, (uh - 25)*s, cx + 105*s, ground_y - 20*s], radius=25*s, fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)

        # Cross-legged knees
        draw.ellipse([cx - 150*s, ground_y - 70*s, cx - 35*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)
        draw.ellipse([cx + 35*s, ground_y - 70*s, cx + 150*s, ground_y + 5*s], fill=NAVY_SHORTS, outline=SEPIA_DARK, width=4*s)

        # Royal blue sneakers
        draw.rounded_rectangle([cx - 160*s, ground_y - 42*s, cx - 110*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([cx - 160*s, ground_y - 12*s, cx - 110*s, ground_y + 2*s], radius=4*s, fill=WHITE_ACCENT, outline=SEPIA_DARK, width=2*s)

        draw.rounded_rectangle([cx + 110*s, ground_y - 42*s, cx + 160*s, ground_y], radius=10*s, fill=BLUE_SNEAKER, outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([cx + 110*s, ground_y - 12*s, cx + 160*s, ground_y + 2*s], radius=4*s, fill=WHITE_ACCENT, outline=SEPIA_DARK, width=2*s)

        # Colorful Toy Blocks (Yellow & Blue stack)
        bx, by = cx, ground_y - 40*s
        draw.rounded_rectangle([bx - 18*s, by - 16*s, bx + 18*s, by + 16*s], radius=5*s, fill=(59, 130, 246, 255), outline=SEPIA_DARK, width=3*s)
        draw.rounded_rectangle([bx - 14*s, by - 44*s, bx + 14*s, by - 16*s], radius=5*s, fill=(250, 204, 21, 255), outline=SEPIA_DARK, width=3*s)

        # Toddler hands holding block
        draw.ellipse([bx - 36*s, by - 25*s, bx - 12*s, by + 5*s], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.ellipse([bx + 12*s, by - 25*s, bx + 36*s, by + 5*s], fill=LUCA_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((canvas_w, canvas_h), draw_luca_seated_lower_body)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "luca_sitting_floor.png")

# =============================================================
# 3. DAD POSES
# =============================================================

def generate_dad_comforting_hug():
    """
    11. Dad Comforting Hug: Eye-level kneeling dad with open gentle embracing arms.
    """
    base = load_sprite("dad_kneeling.png")
    w, h = base.size
    im = base.copy()

    def draw_comforting_details(draw, s):
        # Kind gentle crescent smiling eyes behind glasses
        cx = (w // 2) * s
        # Warm open hands embracing forward
        # Left Hand
        draw.ellipse([(cx - 180*s), 490*s, (cx - 130*s), 550*s], fill=DAD_SKIN, outline=SEPIA_DARK, width=3*s)
        # Right Hand
        draw.ellipse([(cx + 130*s), 490*s, (cx + 180*s), 550*s], fill=DAD_SKIN, outline=SEPIA_DARK, width=3*s)

        # Soft warm pastel heart sparkle
        hx, hy = (cx + 160*s), 230*s
        draw.polygon([(hx, hy + 16*s), (hx - 16*s, hy), (hx - 16*s, hy - 14*s), (hx - 8*s, hy - 20*s), (hx, hy - 12*s), (hx + 8*s, hy - 20*s), (hx + 16*s, hy - 14*s), (hx + 16*s, hy)], fill=(244, 114, 182, 220), outline=SEPIA_DARK, width=2*s)

    overlay = render_high_res_overlay((w, h), draw_comforting_details)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "dad_comforting_hug.png")

def generate_dad_clapping():
    """
    12. Dad Clapping: Natural clapping hands in front of chest with proud fatherly smile.
    """
    base = load_sprite("dad_default.png")
    w, h = base.size
    im = base.copy()

    def draw_clapping_hands(draw, s):
        cx, cy = (w // 2 + 10) * s, 420 * s
        # Slate blue sleeves coming together
        draw.polygon([(cx - 70*s, cy + 30*s), (cx - 20*s, cy - 10*s), (cx - 10*s, cy + 20*s), (cx - 60*s, cy + 60*s)], fill=(71, 85, 105, 255), outline=SEPIA_DARK, width=3*s)
        draw.polygon([(cx + 70*s, cy + 30*s), (cx + 20*s, cy - 10*s), (cx + 10*s, cy + 20*s), (cx + 60*s, cy + 60*s)], fill=(71, 85, 105, 255), outline=SEPIA_DARK, width=3*s)

        # Clapping hands together
        draw.ellipse([cx - 28*s, cy - 20*s, cx + 12*s, cy + 24*s], fill=DAD_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.ellipse([cx - 12*s, cy - 20*s, cx + 28*s, cy + 24*s], fill=DAD_SKIN, outline=SEPIA_DARK, width=3*s)

        # Clapping motion lines
        draw.arc([cx - 45*s, cy - 28*s, cx - 25*s, cy - 8*s], start=120, end=240, fill=(245, 158, 11, 255), width=3*s)
        draw.arc([cx + 25*s, cy - 28*s, cx + 45*s, cy - 8*s], start=300, end=420, fill=(245, 158, 11, 255), width=3*s)

    overlay = render_high_res_overlay((w, h), draw_clapping_hands)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "dad_clapping.png")

# =============================================================
# 4. MOM POSES
# =============================================================

def generate_mom_waving():
    """
    13a. Mom Waving: Natural graceful waving pose with raised hand, warm caring motherly smile.
    """
    base = load_sprite("mom_default.png")
    w, h = base.size
    canvas_w = w + 70
    canvas = Image.new("RGBA", (canvas_w, h), (0, 0, 0, 0))
    canvas.paste(base, (0, 0), base)

    def draw_waving_arm(draw, s):
        # Graceful raised arm with 3/4 striped sleeve
        ax, ay = (w - 20) * s, 360 * s
        wx, wy = (canvas_w - 35) * s, 250 * s
        # Striped sleeve
        draw.polygon([(ax - 20*s, ay + 20*s), (wx - 25*s, wy + 40*s), (wx + 10*s, wy + 25*s), (ax + 20*s, ay)], fill=(30, 58, 138, 255), outline=SEPIA_DARK, width=3*s)
        # Forearm
        draw.polygon([(wx - 20*s, wy + 35*s), (wx - 10*s, wy), (wx + 15*s, wy), (wx + 5*s, wy + 30*s)], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)
        # Open graceful waving hand
        draw.ellipse([wx - 16*s, wy - 24*s, wx + 20*s, wy + 8*s], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)
        # Gentle waving motion arcs
        draw.arc([wx + 18*s, wy - 30*s, wx + 34*s, wy - 6*s], start=280, end=400, fill=(245, 158, 11, 255), width=3*s)

    overlay = render_high_res_overlay((canvas_w, h), draw_waving_arm)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "mom_waving.png")

def generate_mom_clapping():
    """
    13b. Mom Clapping: Graceful clapping hands in front of chest with proud motherly smile.
    """
    base = load_sprite("mom_default.png")
    w, h = base.size
    im = base.copy()

    def draw_mom_clapping_hands(draw, s):
        cx, cy = (w // 2 - 5) * s, 420 * s
        # Striped sleeves coming to center
        draw.polygon([(cx - 70*s, cy + 35*s), (cx - 20*s, cy - 10*s), (cx - 10*s, cy + 20*s), (cx - 60*s, cy + 65*s)], fill=(30, 58, 138, 255), outline=SEPIA_DARK, width=3*s)
        draw.polygon([(cx + 70*s, cy + 35*s), (cx + 20*s, cy - 10*s), (cx + 10*s, cy + 20*s), (cx + 60*s, cy + 65*s)], fill=(30, 58, 138, 255), outline=SEPIA_DARK, width=3*s)

        # Clapping graceful hands
        draw.ellipse([cx - 24*s, cy - 18*s, cx + 10*s, cy + 20*s], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.ellipse([cx - 10*s, cy - 18*s, cx + 24*s, cy + 20*s], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)

        # Applause sparkles
        draw.arc([cx - 40*s, cy - 25*s, cx - 22*s, cy - 7*s], start=120, end=240, fill=(245, 158, 11, 255), width=3*s)
        draw.arc([cx + 22*s, cy - 25*s, cx + 40*s, cy - 7*s], start=300, end=420, fill=(245, 158, 11, 255), width=3*s)

    overlay = render_high_res_overlay((w, h), draw_mom_clapping_hands)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "mom_clapping.png")

def generate_mom_holding_bowl():
    """
    13c. Mom Holding Bowl: Gracefully holding a pastel toddler meal bowl with wooden spoon.
    """
    base = load_sprite("mom_default.png")
    w, h = base.size
    im = base.copy()

    def draw_meal_bowl(draw, s):
        cx, cy = (w // 2 - 10) * s, 450 * s
        bw, bh = 85 * s, 50 * s

        # Bowl Shadow
        draw.ellipse([cx - bw//2 - 5*s, cy + bh//2, cx + bw//2 + 5*s, cy + bh//2 + 14*s], fill=(30, 20, 15, 60))

        # Pastel Buttercup Yellow Ceramic Bowl
        draw.chord([cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2 + 10*s], start=0, end=180, fill=(254, 240, 138, 255), outline=SEPIA_DARK, width=3*s)
        # Inner warm healthy oatmeal / soup rim
        draw.ellipse([cx - bw//2 + 4*s, cy - bh//2 - 2*s, cx + bw//2 - 4*s, cy - bh//2 + 16*s], fill=(254, 243, 199, 255), outline=SEPIA_DARK, width=2*s)

        # Wooden Spoon resting inside bowl
        draw.line([(cx + 10*s, cy), (cx + 45*s, cy - 35*s)], fill=(180, 83, 9, 255), width=6*s)
        draw.ellipse([cx + 40*s, cy - 42*s, cx + 52*s, cy - 30*s], fill=(180, 83, 9, 255))

        # Graceful motherly hands supporting bowl
        draw.ellipse([cx - bw//2 - 12*s, cy - 8*s, cx - bw//2 + 14*s, cy + 24*s], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)
        draw.ellipse([cx + bw//2 - 14*s, cy - 8*s, cx + bw//2 + 12*s, cy + 24*s], fill=MOM_SKIN, outline=SEPIA_DARK, width=3*s)

    overlay = render_high_res_overlay((w, h), draw_meal_bowl)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "mom_holding_bowl.png")

# =============================================================
# 5. DOG POSES (JAPANESE SPITZ)
# =============================================================

def generate_dog_sitting_attentive():
    """
    14a. Dog Sitting Attentive: Pure white Japanese Spitz, perked pointy fox ears,
    bright dark eyes, cute pink open panting tongue.
    """
    base = load_sprite("dog_default.png")
    w, h = base.size
    im = base.copy()

    def draw_attentive_features(draw, s):
        cx, cy = 410 * s, 360 * s
        # Cute pink tongue happily panting
        draw.chord([cx - 16*s, cy, cx + 16*s, cy + 32*s], start=0, end=180, fill=(244, 114, 182, 255), outline=SEPIA_DARK, width=3*s)
        draw.line([(cx, cy + 4*s), (cx, cy + 24*s)], fill=(219, 39, 119, 255), width=2*s)

        # Sparkling dark eyes highlights
        draw.ellipse([(345*s), 275*s, (355*s), 285*s], fill=WHITE_ACCENT)
        draw.ellipse([(465*s), 275*s, (475*s), 285*s], fill=WHITE_ACCENT)

    overlay = render_high_res_overlay((w, h), draw_attentive_features)
    im = Image.alpha_composite(im, overlay)
    save_sprite(im, "dog_sitting_attentive.png")

def generate_dog_curled_sleeping():
    """
    14b. Dog Curled Sleeping: Fluffy pure white Japanese Spitz curled into a cozy ball,
    pointy ears tucked, curled plume tail over body, closed peaceful eyes, red collar & tag.
    """
    w, h = 820, 640
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def draw_sleeping_spitz(draw, s):
        cx, cy = (w // 2) * s, (h // 2 + 20) * s

        # 1. Warm Floor Shadow
        draw.ellipse([cx - 300*s, cy + 120*s, cx + 300*s, cy + 240*s], fill=(30, 20, 15, 60))

        # 2. Main Curled Fluffy Body (Pure White Spitz)
        draw.ellipse([cx - 280*s, cy - 140*s, cx + 240*s, cy + 190*s], fill=(255, 255, 255, 255), outline=SEPIA_DARK, width=5*s)

        # 3. Fluffy Curled Plume Tail wrapped around front
        draw.chord([cx - 290*s, cy - 80*s, cx + 40*s, cy + 210*s], start=60, end=260, fill=(250, 250, 250, 255), outline=SEPIA_DARK, width=4*s)

        # 4. Cozy Sleeping Head tucked onto paws
        hx, hy = cx + 120*s, cy - 20*s
        draw.ellipse([hx - 110*s, hy - 100*s, hx + 110*s, hy + 100*s], fill=(255, 255, 255, 255), outline=SEPIA_DARK, width=5*s)

        # Spitz Pointy Fox Ears tucked comfortably back
        # Left Ear
        draw.polygon([(hx - 90*s, hy - 60*s), (hx - 140*s, hy - 140*s), (hx - 40*s, hy - 90*s)], fill=(255, 255, 255, 255), outline=SEPIA_DARK, width=4*s)
        draw.polygon([(hx - 90*s, hy - 70*s), (hx - 125*s, hy - 125*s), (hx - 55*s, hy - 90*s)], fill=(254, 226, 226, 255))
        # Right Ear
        draw.polygon([(hx + 40*s, hy - 90*s), (hx + 110*s, hy - 140*s), (hx + 80*s, hy - 50*s)], fill=(255, 255, 255, 255), outline=SEPIA_DARK, width=4*s)
        draw.polygon([(hx + 50*s, hy - 85*s), (hx + 95*s, hy - 125*s), (hx + 75*s, hy - 60*s)], fill=(254, 226, 226, 255))

        # Peaceful Closed Sleeping Eyes ( ⌒   ⌒ )
        draw.arc([hx - 65*s, hy - 25*s, hx - 20*s, hy + 10*s], start=180, end=360, fill=SEPIA_DARK, width=4*s)
        draw.arc([hx + 10*s, hy - 25*s, hx + 55*s, hy + 10*s], start=180, end=360, fill=SEPIA_DARK, width=4*s)

        # Black Button Spitz Nose & Muzzle
        draw.ellipse([hx - 22*s, hy + 22*s, hx + 18*s, hy + 48*s], fill=SEPIA_DARK)
        draw.arc([hx - 28*s, hy + 38*s, hx - 2*s, hy + 58*s], start=20, end=160, fill=SEPIA_DARK, width=3*s)
        draw.arc([hx - 2*s, hy + 38*s, hx + 24*s, hy + 58*s], start=20, end=160, fill=SEPIA_DARK, width=3*s)

        # Crimson Red Collar & Golden Tag
        draw.rounded_rectangle([hx - 95*s, hy + 70*s, hx + 25*s, hy + 98*s], radius=10*s, fill=(220, 38, 38, 255), outline=SEPIA_DARK, width=4*s)
        draw.ellipse([hx - 45*s, hy + 88*s, hx - 15*s, hy + 118*s], fill=(250, 204, 21, 255), outline=SEPIA_DARK, width=3*s)

        # Floating Soft Pastel "Zzz"
        draw.text(((hx - 220*s), (hy - 140*s)), "z", fill=(147, 197, 253, 240), font=get_font(42 * s, bold=True))
        draw.text(((hx - 170*s), (hy - 210*s)), "Z", fill=(96, 165, 250, 255), font=get_font(58 * s, bold=True))

    overlay = render_high_res_overlay((w, h), draw_sleeping_spitz)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "dog_curled_sleeping.png")

def generate_dog_dancing_paw():
    """
    14c. Dog Dancing Paw: Japanese Spitz up on hind paws dancing joyfully with musical notes.
    """
    base = load_sprite("dog_running.png")
    w, h = base.size
    canvas_h = int(h * 1.08)
    canvas = Image.new("RGBA", (w, canvas_h), (0, 0, 0, 0))
    canvas.paste(base, (0, 30), base)

    def draw_dancing_effects(draw, s):
        # Joyful musical notes around dancing dog
        draw.text((40*s, 30*s), "🎵", fill=(245, 158, 11, 255), font=get_font(48 * s))
        draw.text(((w - 90)*s, 20*s), "🎶", fill=(236, 72, 153, 255), font=get_font(48 * s))
        draw.text(((w - 120)*s, 160*s), "✨", fill=(250, 204, 21, 255), font=get_font(40 * s))

    overlay = render_high_res_overlay((w, canvas_h), draw_dancing_effects)
    canvas = Image.alpha_composite(canvas, overlay)
    save_sprite(canvas, "dog_dancing_paw.png")

# =============================================================
# MASTER RUNNER
# =============================================================

def generate_all_high_fidelity_sprites():
    print("=== Generating Enhanced High-Fidelity Character Sprites ===")
    
    # Levi
    generate_levi_sad()
    generate_levi_holding_book()
    generate_levi_thinking()
    generate_levi_cheering()
    generate_levi_sitting_floor()

    # Luca
    generate_luca_crying()
    generate_luca_cheering()
    generate_luca_pointing()
    generate_luca_arms_out_hug()
    generate_luca_sitting_floor()

    # Dad
    generate_dad_comforting_hug()
    generate_dad_clapping()

    # Mom
    generate_mom_waving()
    generate_mom_clapping()
    generate_mom_holding_bowl()

    # Dog
    generate_dog_sitting_attentive()
    generate_dog_curled_sleeping()
    generate_dog_dancing_paw()

    print("=== All 14 High-Fidelity Sprites Successfully Generated! ===")

if __name__ == "__main__":
    generate_all_high_fidelity_sprites()
