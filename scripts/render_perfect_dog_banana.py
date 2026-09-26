import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")

def create_cartoon_banana_spitz():
    # Use dog_running.png as base (exact same Japanese Spitz with red collar and gold medallion)
    dog = Image.open(os.path.join(SPRITES_DIR, "dog_running.png")).convert("RGBA")
    w, h = dog.size

    # Target mouth center: x: 630, y: 380
    scale = 4
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)

    STROKE = (45, 25, 20, 255)
    BANANA_YELLOW = (250, 204, 21, 255)
    BANANA_SHADOW = (234, 179, 8, 255)
    BANANA_FLESH = (255, 252, 230, 255)
    BANANA_TIP = (120, 53, 15, 255)

    bx, by = 640 * scale, 395 * scale
    bw, bh = 140 * scale, 45 * scale

    # 1. Back banana peel
    draw.polygon([
        (bx - 40*scale, by + 10*scale),
        (bx - 70*scale, by + 50*scale),
        (bx - 30*scale, by + 65*scale),
        (bx - 10*scale, by + 20*scale)
    ], fill=BANANA_SHADOW, outline=STROKE, width=3*scale)

    # 2. Main curved banana body (peeled sweet yellow banana)
    draw.chord([
        bx - 120*scale, by - 60*scale,
        bx + 60*scale, by + 50*scale
    ], start=15, end=190, fill=BANANA_YELLOW, outline=STROKE, width=4*scale)

    # 3. Inner sweet edible banana flesh extending into mouth
    draw.chord([
        bx - 80*scale, by - 45*scale,
        bx + 30*scale, by + 35*scale
    ], start=15, end=185, fill=BANANA_FLESH, outline=STROKE, width=3*scale)

    # 4. Front peeled skin flaps hanging down
    draw.polygon([
        (bx - 10*scale, by + 5*scale),
        (bx + 35*scale, by + 55*scale),
        (bx + 10*scale, by + 65*scale),
        (bx - 25*scale, by + 15*scale)
    ], fill=BANANA_YELLOW, outline=STROKE, width=3*scale)

    # 5. Banana stem end
    draw.rounded_rectangle([
        bx - 125*scale, by - 15*scale,
        bx - 105*scale, by + 5*scale
    ], radius=5*scale, fill=BANANA_TIP, outline=STROKE, width=3*scale)

    # 6. Dog Upper Teeth and Lip overlapping banana naturally
    draw.arc([bx - 30*scale, by - 25*scale, bx + 20*scale, by + 10*scale], start=160, end=340, fill=(255, 255, 255, 255), width=4*scale)

    big_down = big.resize((w, h), Image.Resampling.LANCZOS)
    combined = Image.alpha_composite(dog, big_down)

    out_path = os.path.join(SPRITES_DIR, "dog_eating_banana.png")
    combined.save(out_path, "PNG", optimize=True)
    print(f"Saved {out_path} ({combined.width}x{combined.height})")

if __name__ == "__main__":
    create_cartoon_banana_spitz()
