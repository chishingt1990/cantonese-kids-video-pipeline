import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
STICKERS_DIR = os.path.join(PROJECT_ROOT, "assets", "stickers")
BACKGROUNDS_DIR = os.path.join(PROJECT_ROOT, "assets", "backgrounds")

os.makedirs(SPRITES_DIR, exist_ok=True)
os.makedirs(STICKERS_DIR, exist_ok=True)
os.makedirs(BACKGROUNDS_DIR, exist_ok=True)

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

# ==========================================
# 1. CHARACTER SPRITE SYNTHESIS
# ==========================================

def load_base(filename):
    p = os.path.join(SPRITES_DIR, filename)
    if os.path.exists(p):
        return Image.open(p).convert("RGBA")
    return None

def save_sprite(im: Image.Image, filename: str):
    bbox = im.getbbox()
    if bbox:
        # Keep slight margin
        cropped = im.crop((max(0, bbox[0]-6), max(0, bbox[1]-6), min(im.width, bbox[2]+6), min(im.height, bbox[3]+6)))
    else:
        cropped = im
    out_path = os.path.join(SPRITES_DIR, filename)
    cropped.save(out_path, format="PNG")
    print(f"  [SPRITE] Created {filename} ({cropped.width}x{cropped.height})")

def synthesize_character_sprites():
    from scripts.generate_high_fidelity_sprites import generate_all_high_fidelity_sprites
    generate_all_high_fidelity_sprites()

# ==========================================
# 2. PROPS & STICKERS GENERATION
# ==========================================

def draw_die_cut_prop(canvas, cx, cy, draw_fn, size=240):
    scale = 2
    total = size * scale
    im = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(im)
    
    # 1. Soft Warm Shadow
    shadow = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.ellipse([total*0.15, total*0.75, total*0.85, total*0.92], fill=(60, 40, 30, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12 * scale))
    im.alpha_composite(shadow)

    # 2. Draw artwork on high res
    draw = ImageDraw.Draw(im)
    draw_fn(draw, total // 2, total // 2, total)

    res = im.resize((size, size), Image.Resampling.LANCZOS)
    return res

def save_prop(im: Image.Image, filename: str):
    p = os.path.join(STICKERS_DIR, filename)
    im.save(p, format="PNG")
    print(f"  [PROP] Created {filename}")

def generate_all_props():
    print("=== Generating Expanded Milestone Props & Stickers ===")

    # 1. School Bus
    def draw_bus(draw, cx, cy, s):
        # White border
        draw.rounded_rectangle([cx - 160, cy - 90, cx + 160, cy + 90], radius=40, fill=(255, 255, 255))
        # Yellow body
        draw.rounded_rectangle([cx - 150, cy - 80, cx + 150, cy + 80], radius=32, fill=(250, 204, 21), outline=(217, 119, 6), width=6)
        # Windows
        for wx in [-110, -40, 30, 100]:
            draw.rounded_rectangle([cx + wx - 25, cy - 60, cx + wx + 25, cy - 10], radius=12, fill=(224, 242, 254), outline=(14, 165, 233), width=4)
        # Headlights & Smile
        draw.ellipse([cx + 120, cy + 15, cx + 145, cy + 40], fill=(254, 240, 138), outline=(202, 138, 4), width=3)
        # Wheels
        draw.ellipse([cx - 110, cy + 50, cx - 50, cy + 110], fill=(30, 41, 59), outline=(255, 255, 255), width=6)
        draw.ellipse([cx + 50, cy + 50, cx + 110, cy + 110], fill=(30, 41, 59), outline=(255, 255, 255), width=6)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_bus), "prop_bus.png")

    # 2. Fire Truck
    def draw_fire_truck(draw, cx, cy, s):
        draw.rounded_rectangle([cx - 160, cy - 90, cx + 160, cy + 90], radius=40, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 150, cy - 80, cx + 150, cy + 80], radius=32, fill=(239, 68, 68), outline=(185, 28, 28), width=6)
        # Ladder on top
        draw.rounded_rectangle([cx - 110, cy - 105, cx + 110, cy - 80], radius=8, fill=(226, 232, 240), outline=(71, 85, 105), width=4)
        # Windows & Siren
        draw.rounded_rectangle([cx + 40, cy - 60, cx + 120, cy - 10], radius=12, fill=(224, 242, 254), outline=(14, 165, 233), width=4)
        draw.ellipse([cx + 70, cy - 95, cx + 95, cy - 70], fill=(59, 130, 246), outline=(255, 255, 255), width=3) # Blue flashing light
        # Wheels
        draw.ellipse([cx - 110, cy + 50, cx - 50, cy + 110], fill=(30, 41, 59), outline=(255, 255, 255), width=6)
        draw.ellipse([cx + 50, cy + 50, cx + 110, cy + 110], fill=(30, 41, 59), outline=(255, 255, 255), width=6)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_fire_truck), "prop_fire_truck.png")

    # 3. Airplane
    def draw_plane(draw, cx, cy, s):
        draw.ellipse([cx - 150, cy - 60, cx + 150, cy + 60], fill=(255, 255, 255))
        draw.ellipse([cx - 140, cy - 50, cx + 140, cy + 50], fill=(56, 189, 248), outline=(2, 132, 199), width=6)
        # Wings & Tail
        draw.polygon([(cx - 30, cy), (cx + 20, cy - 90), (cx + 60, cy - 90), (cx + 30, cy)], fill=(255, 255, 255), outline=(2, 132, 199), width=5)
        draw.polygon([(cx - 130, cy - 10), (cx - 160, cy - 80), (cx - 130, cy - 80), (cx - 100, cy - 10)], fill=(239, 68, 68), outline=(185, 28, 28), width=4)
        # Windows
        for px in [-60, -10, 40, 90]:
            draw.ellipse([cx + px - 10, cy - 18, cx + px + 10, cy + 2], fill=(255, 255, 255), outline=(14, 165, 233), width=2)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_plane), "prop_airplane.png")

    # 4. Train
    def draw_train(draw, cx, cy, s):
        draw.rounded_rectangle([cx - 150, cy - 80, cx + 150, cy + 80], radius=32, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 140, cy - 70, cx + 140, cy + 70], radius=24, fill=(16, 185, 129), outline=(4, 120, 87), width=6)
        draw.rounded_rectangle([cx - 130, cy - 110, cx - 80, cy - 60], radius=12, fill=(239, 68, 68), outline=(185, 28, 28), width=4) # Chimney
        # Wheels
        for wx in [-100, -30, 40, 100]:
            draw.ellipse([cx + wx - 25, cy + 45, cx + wx + 25, cy + 95], fill=(245, 158, 11), outline=(255, 255, 255), width=4)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_train), "prop_train.png")

    # 5. (Retired 2026-10-04: flat minimal animal icons removed; animals now follow STYLE_GUIDE.md §13 detailed cartoon style. See prop_cow.png etc.)

    # 6. Rainbow
    def draw_rainbow(draw, cx, cy, s):
        colors = [(239, 68, 68), (249, 115, 22), (250, 204, 21), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
        for idx, col in enumerate(colors):
            r = 130 - idx * 14
            draw.arc([cx - r, cy - r + 30, cx + r, cy + r + 30], 180, 360, fill=col, width=14)
        # Clouds on flanks
        draw.ellipse([cx - 140, cy + 10, cx - 60, cy + 70], fill=(255, 255, 255), outline=(203, 213, 225), width=4)
        draw.ellipse([cx + 60, cy + 10, cx + 140, cy + 70], fill=(255, 255, 255), outline=(203, 213, 225), width=4)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_rainbow), "prop_rainbow.png")

    # 7. Smiling Sun
    def draw_sun(draw, cx, cy, s):
        draw.ellipse([cx - 95, cy - 95, cx + 95, cy + 95], fill=(255, 255, 255))
        # Rays
        for i in range(8):
            ang = i * math.pi / 4
            rx = cx + math.cos(ang) * 110
            ry = cy + math.sin(ang) * 110
            draw.line([(cx, cy), (rx, ry)], fill=(245, 158, 11), width=10)
        draw.ellipse([cx - 75, cy - 75, cx + 75, cy + 75], fill=(250, 204, 21), outline=(217, 119, 6), width=6)
        draw.ellipse([cx - 35, cy - 20, cx - 15, cy], fill=(120, 53, 15))
        draw.ellipse([cx + 15, cy - 20, cx + 35, cy], fill=(120, 53, 15))
        draw.arc([cx - 30, cy - 5, cx + 30, cy + 40], 0, 180, fill=(180, 83, 9), width=5)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_sun), "prop_sun_smiling.png")

    # 8. Dim Sum Har Gow (Crystal Shrimp Dumpling)
    def draw_har_gow(draw, cx, cy, s):
        draw.ellipse([cx - 100, cy - 70, cx + 100, cy + 70], fill=(255, 255, 255))
        # Translucent dumpling with pink shrimp inside
        draw.ellipse([cx - 90, cy - 60, cx + 90, cy + 60], fill=(255, 241, 242), outline=(244, 114, 182), width=4)
        draw.ellipse([cx - 50, cy - 30, cx + 50, cy + 30], fill=(251, 146, 60), outline=(249, 115, 22), width=3) # Shrimp filling
        # Pleats on top
        for px in [-50, -25, 0, 25, 50]:
            draw.line([(cx + px, cy - 55), (cx + px, cy - 25)], fill=(244, 114, 182), width=3)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_har_gow), "prop_har_gow.png")

    # 9. Dim Sum Siu Mai
    def draw_siu_mai(draw, cx, cy, s):
        draw.rounded_rectangle([cx - 80, cy - 75, cx + 80, cy + 75], radius=24, fill=(255, 255, 255))
        # Yellow wonton wrapper
        draw.rounded_rectangle([cx - 70, cy - 65, cx + 70, cy + 65], radius=18, fill=(254, 240, 138), outline=(234, 179, 8), width=5)
        # Pork & shrimp filling with orange crab roe dots
        draw.ellipse([cx - 55, cy - 55, cx + 55, cy + 10], fill=(254, 215, 170), outline=(249, 115, 22), width=3)
        draw.ellipse([cx - 12, cy - 35, cx + 12, cy - 12], fill=(239, 68, 68)) # Crab roe
    save_prop(draw_die_cut_prop(None, 0, 0, draw_siu_mai), "prop_siu_mai.png")

    # 10. Egg Tart
    def draw_egg_tart(draw, cx, cy, s):
        draw.ellipse([cx - 95, cy - 65, cx + 95, cy + 65], fill=(255, 255, 255))
        # Golden flaky crust
        draw.ellipse([cx - 85, cy - 55, cx + 85, cy + 55], fill=(217, 119, 6), outline=(180, 83, 9), width=5)
        # Glossy yellow egg custard center
        draw.ellipse([cx - 65, cy - 40, cx + 65, cy + 40], fill=(250, 204, 21), outline=(234, 179, 8), width=3)
        draw.chord([cx - 40, cy - 30, cx + 20, cy + 10], 180, 270, fill=(255, 255, 255, 120)) # Gloss highlight
    save_prop(draw_die_cut_prop(None, 0, 0, draw_egg_tart), "prop_egg_tart.png")

    # 11. Watermelon Slice
    def draw_watermelon(draw, cx, cy, s):
        draw.chord([cx - 100, cy - 80, cx + 100, cy + 80], 0, 180, fill=(255, 255, 255))
        draw.chord([cx - 90, cy - 70, cx + 90, cy + 70], 0, 180, fill=(34, 197, 94), outline=(22, 101, 52), width=5) # Green rind
        draw.chord([cx - 75, cy - 60, cx + 75, cy + 60], 0, 180, fill=(239, 68, 68)) # Red pulp
        # Black seeds
        for sx, sy in [(-35, 10), (0, 30), (35, 10), (-15, -15), (20, -15)]:
            draw.ellipse([cx + sx - 4, cy + sy - 6, cx + sx + 4, cy + sy + 6], fill=(30, 41, 59))
    save_prop(draw_die_cut_prop(None, 0, 0, draw_watermelon), "prop_watermelon_slice.png")

    # 12. Strawberry
    def draw_strawberry(draw, cx, cy, s):
        draw.ellipse([cx - 80, cy - 70, cx + 80, cy + 90], fill=(255, 255, 255))
        draw.ellipse([cx - 70, cy - 60, cx + 70, cy + 80], fill=(239, 68, 68), outline=(185, 28, 28), width=6)
        # Green leaves on top
        draw.polygon([(cx - 60, cy - 60), (cx - 20, cy - 95), (cx, cy - 50), (cx + 20, cy - 95), (cx + 60, cy - 60), (cx, cy - 40)], fill=(34, 197, 94), outline=(22, 101, 52), width=4)
        # Yellow seed dots
        for sx, sy in [(-30, -10), (0, 0), (30, -10), (-20, 30), (20, 30), (0, 55)]:
            draw.ellipse([cx + sx - 3, cy + sy - 3, cx + sx + 3, cy + sy + 3], fill=(254, 240, 138))
    save_prop(draw_die_cut_prop(None, 0, 0, draw_strawberry), "prop_strawberry.png")

    # 13. Baby Milk Bottle
    def draw_bottle(draw, cx, cy, s):
        draw.rounded_rectangle([cx - 60, cy - 100, cx + 60, cy + 100], radius=24, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 50, cy - 50, cx + 50, cy + 90], radius=18, fill=(240, 249, 255), outline=(186, 230, 253), width=5) # Glass/plastic bottle
        draw.rounded_rectangle([cx - 45, cy - 20, cx + 45, cy + 85], radius=12, fill=(255, 255, 255)) # Milk inside
        draw.rounded_rectangle([cx - 45, cy - 70, cx + 45, cy - 50], radius=8, fill=(244, 114, 182)) # Pink cap collar
        draw.rounded_rectangle([cx - 20, cy - 100, cx + 20, cy - 70], radius=12, fill=(254, 240, 138), outline=(234, 179, 8), width=3) # Silicone teat
    save_prop(draw_die_cut_prop(None, 0, 0, draw_bottle), "prop_milk_bottle.png")

    # 14. Cookies
    def draw_cookie(draw, cx, cy, s):
        draw.ellipse([cx - 85, cy - 85, cx + 85, cy + 85], fill=(255, 255, 255))
        draw.ellipse([cx - 75, cy - 75, cx + 75, cy + 75], fill=(217, 119, 6), outline=(180, 83, 9), width=5)
        for sx, sy in [(-35, -25), (10, -40), (-15, 10), (35, 0), (-25, 40), (25, 35)]:
            draw.ellipse([cx + sx - 8, cy + sy - 8, cx + sx + 8, cy + sy + 8], fill=(69, 26, 3))
    save_prop(draw_die_cut_prop(None, 0, 0, draw_cookie), "prop_cookie.png")

    # 15. Balloons (Yellow, Blue, Green)
    def make_balloon(col, outline_col, fn):
        def draw_b(draw, cx, cy, s):
            draw.ellipse([cx - 75, cy - 105, cx + 75, cy + 55], fill=(255, 255, 255))
            draw.ellipse([cx - 65, cy - 95, cx + 65, cy + 45], fill=col, outline=outline_col, width=5)
            # Knot & string
            draw.polygon([(cx - 15, cy + 45), (cx + 15, cy + 45), (cx, cy + 60)], fill=outline_col)
            draw.line([(cx, cy + 60), (cx + 10, cy + 110)], fill=(148, 163, 184), width=4)
        save_prop(draw_die_cut_prop(None, 0, 0, draw_b), fn)
    make_balloon((250, 204, 21), (202, 138, 4), "prop_balloon_yellow.png")
    make_balloon((59, 130, 246), (29, 78, 216), "prop_balloon_blue.png")
    make_balloon((34, 197, 94), (22, 101, 52), "prop_balloon_green.png")

    # 16. Gift Box
    def draw_gift(draw, cx, cy, s):
        draw.rounded_rectangle([cx - 85, cy - 75, cx + 85, cy + 85], radius=24, fill=(255, 255, 255))
        draw.rounded_rectangle([cx - 75, cy - 65, cx + 75, cy + 75], radius=18, fill=(168, 85, 247), outline=(126, 34, 206), width=5)
        # Gold ribbon crosses
        draw.line([(cx, cy - 65), (cx, cy + 75)], fill=(250, 204, 21), width=24)
        draw.line([(cx - 75, cy), (cx + 75, cy)], fill=(250, 204, 21), width=24)
        # Bow on top
        draw.ellipse([cx - 45, cy - 95, cx - 5, cy - 65], fill=(250, 204, 21), outline=(202, 138, 4), width=3)
        draw.ellipse([cx + 5, cy - 95, cx + 45, cy - 65], fill=(250, 204, 21), outline=(202, 138, 4), width=3)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_gift), "prop_gift_box.png")

    # 17. Party Hat
    def draw_party_hat(draw, cx, cy, s):
        draw.polygon([(cx, cy - 110), (cx - 75, cy + 75), (cx + 75, cy + 75)], fill=(255, 255, 255))
        draw.polygon([(cx, cy - 100), (cx - 65, cy + 65), (cx + 65, cy + 65)], fill=(244, 63, 94), outline=(190, 18, 60), width=5)
        # Polka dots
        for px, py in [(-20, 20), (20, 20), (0, -30)]:
            draw.ellipse([cx + px - 10, cy + py - 10, cx + px + 10, cy + py + 10], fill=(250, 204, 21))
        # Pom pom on top
        draw.ellipse([cx - 20, cy - 125, cx + 20, cy - 85], fill=(250, 204, 21), outline=(202, 138, 4), width=3)
    save_prop(draw_die_cut_prop(None, 0, 0, draw_party_hat), "prop_party_hat.png")

# ==========================================
# 3. EXPANDED BACKGROUNDS GENERATION
# ==========================================

def generate_expanded_backgrounds():
    print("=== Generating Expanded Background Presets ===")
    W, H = 1920, 1080

    # 1. Art Room (bg_art_room.png)
    art_path = os.path.join(BACKGROUNDS_DIR, "bg_art_room.png")
    canvas = Image.new("RGB", (W, H), (255, 251, 235))
    draw = ImageDraw.Draw(canvas)
    # Warm pastel wall & wooden floor
    draw.rectangle([0, 0, W, 720], fill=(255, 248, 230))
    draw.rectangle([0, 720, W, H], fill=(234, 179, 8)) # Warm oak floor
    # Floor planks
    for y in range(720, H, 60):
        draw.line([(0, y), (W, y)], fill=(180, 83, 9), width=2)
    # Arched Window overlooking sunny garden
    draw.chord([760, 80, 1160, 480], 180, 360, fill=(224, 242, 254), outline=(180, 83, 9), width=8)
    draw.rectangle([760, 280, 1160, 520], fill=(224, 242, 254), outline=(180, 83, 9), width=8)
    draw.ellipse([860, 400, 1060, 600], fill=(134, 239, 172)) # Green garden tree outside
    # Triangular pennant bunting
    colors = [(244, 63, 94), (250, 204, 21), (59, 130, 246), (34, 197, 94), (168, 85, 247)]
    for i in range(12):
        bx = 80 + i * 150
        c = colors[i % len(colors)]
        draw.polygon([(bx, 40), (bx + 120, 40), (bx + 60, 140)], fill=c, outline=(120, 53, 15), width=2)
    # Wooden Easel with canvas painting on left
    draw.polygon([(180, 760), (320, 260), (460, 760)], outline=(146, 64, 14), width=12)
    draw.rectangle([220, 360, 420, 600], fill=(255, 255, 255), outline=(180, 83, 9), width=6) # Canvas
    draw.arc([260, 420, 380, 540], 180, 360, fill=(239, 68, 68), width=10) # Rainbow arch on canvas
    draw.arc([270, 430, 370, 530], 180, 360, fill=(250, 204, 21), width=10)
    # Colorful paint jars on right shelf
    draw.rounded_rectangle([1450, 460, 1820, 480], radius=8, fill=(146, 64, 14))
    for idx, col in enumerate([(239, 68, 68), (250, 204, 21), (59, 130, 246), (34, 197, 94)]):
        draw.rounded_rectangle([1480 + idx * 80, 390, 1530 + idx * 80, 460], radius=10, fill=col, outline=(30, 41, 59), width=3)
    canvas.save(art_path, format="PNG")
    print(f"  [BG] Created bg_art_room.png (1920x1080)")

    # 2. Supermarket (bg_supermarket.png)
    super_path = os.path.join(BACKGROUNDS_DIR, "bg_supermarket.png")
    canvas2 = Image.new("RGB", (W, H), (240, 253, 250))
    draw2 = ImageDraw.Draw(canvas2)
    # Pastel mint wall & warm tile floor
    draw2.rectangle([0, 0, W, 720], fill=(236, 253, 245))
    draw2.rectangle([0, 720, W, H], fill=(241, 245, 249)) # Clean supermarket floor
    for y in range(720, H, 50):
        draw2.line([(0, y), (W, y)], fill=(203, 213, 225), width=2)
    # Supermarket banner & fruit stands
    draw2.rounded_rectangle([400, 60, 1520, 180], radius=24, fill=(245, 158, 11), outline=(180, 83, 9), width=6)
    draw2.text((960, 120), "🍎 超市小市場 FRESH MARKET 🍌", font=get_font(48, bold=True), fill=(255, 255, 255), anchor="mm")
    # Wooden fruit crates on left and right
    draw2.rounded_rectangle([120, 520, 460, 720], radius=16, fill=(217, 119, 6), outline=(146, 64, 14), width=6)
    # Red apples in left crate
    for ax in [180, 250, 320, 390]:
        for ay in [560, 630]:
            draw2.ellipse([ax - 25, ay - 25, ax + 25, ay + 25], fill=(239, 68, 68), outline=(185, 28, 28), width=3)
    # Yellow bananas in right crate
    draw2.rounded_rectangle([1460, 520, 1800, 720], radius=16, fill=(217, 119, 6), outline=(146, 64, 14), width=6)
    for bx in [1520, 1600, 1680, 1740]:
        draw2.arc([bx - 30, 580, bx + 30, 680], 30, 180, fill=(250, 204, 21), width=18)
    canvas2.save(super_path, format="PNG")
    print(f"  [BG] Created bg_supermarket.png (1920x1080)")

if __name__ == "__main__":
    synthesize_character_sprites()
    generate_all_props()
    generate_expanded_backgrounds()
    print("All assets successfully generated!")
