import os
import numpy as np
from PIL import Image, ImageDraw

try:
    from scripts.maintenance_guard import PROJECT_ROOT, configure_cli, output_path as guarded_output_path
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from maintenance_guard import PROJECT_ROOT, configure_cli, output_path as guarded_output_path

from app.utils.sprite_isolator import isolate_sprite_from_white_bg

SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
BRAIN_ROOT = r"C:\Users\chish\.gemini\antigravity\brain"

def isolate_sprite(image_path: str, output_path: str, threshold: int = 35):
    filename = isolate_sprite_from_white_bg(
        image_path, str(guarded_output_path(output_path)), threshold=threshold
    )
    with Image.open(filename) as image:
        return image.convert("RGBA")

def fix_dad_teaching():
    """1. Replace Dad teaching with the authentic youthful Dad."""
    src = os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_teaching_young_1789512117701.jpg")
    dst = os.path.join(SPRITES_DIR, "dad_teaching.png")
    if os.path.exists(src):
        isolate_sprite(src, dst)
        print("  -> Fixed dad_teaching.png to youthful Dad!")

def fix_levi_sad_matte():
    """2. Remove glossy specular white highlights from Levi Sad hair/shirt for matte cartoon consistency."""
    p = os.path.join(SPRITES_DIR, "levi_sad.png")
    im = Image.open(p).convert("RGBA")
    arr = np.array(im)

    # Replace pure glossy white highlights on hair (top 20% of image, x: 120-220, y: 30-140)
    # where color is near white > 220 in the dark hair region
    hair_mask = (arr[:200, :, 0] > 180) & (arr[:200, :, 1] > 180) & (arr[:200, :, 2] > 180) & (arr[:200, :, 3] > 200)
    # In hair region, hair dark color is (45, 45, 50)
    # Let's softly fill hair highlights with dark hair tone
    hair_color = [42, 45, 52, 255]
    for y in range(30, 160):
        for x in range(80, 260):
            if arr[y, x, 3] > 150:
                # If pixel is bright white highlight in hair
                if arr[y, x, 0] > 200 and arr[y, x, 1] > 200 and arr[y, x, 2] > 200:
                    arr[y, x] = hair_color

    out = Image.fromarray(arr, "RGBA")
    out.save(guarded_output_path(p), "PNG")
    print("  -> Reverted glossy hair highlights on levi_sad.png to matte cartoon finish!")

def fix_dog_eating_banana():
    """3. Build Dog Eating Sweet Banana using the canonical cartoon dog model with matching bold outlines & red collar."""
    # Base dog: dog_running or dog_playing_ball
    base_p = os.path.join(SPRITES_DIR, "dog_playing_ball.png")
    im = Image.open(base_p).convert("RGBA")
    w, h = im.size

    # The mouth region where the ball sits is roughly x: 480 to 680, y: 280 to 450
    # Inpaint the ball area and replace with a delicious cartoon peeled yellow banana
    draw = ImageDraw.Draw(im, "RGBA")

    # Draw authentic cartoon peeled banana in mouth
    # Banana body color: bright golden yellow (250, 204, 21, 255), outline: dark chocolate (45, 25, 20, 255)
    # Banana peel peels extending out
    bx, by = 600, 370
    scale = 3
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(big)

    CHARCOAL = (45, 25, 20, 255)
    BANANA_YELLOW = (250, 204, 21, 255)
    BANANA_PALE = (254, 240, 138, 255)
    BANANA_TIP = (180, 83, 9, 255)

    # Draw peeled banana curve extending from mouth
    # Banana flesh
    bdraw.polygon([((bx-60)*scale, (by-30)*scale), ((bx+60)*scale, (by-60)*scale), ((bx+80)*scale, (by-20)*scale), ((bx-40)*scale, (by+20)*scale)], fill=BANANA_PALE, outline=CHARCOAL, width=4*scale)
    # Banana peel flaps
    bdraw.polygon([((bx+20)*scale, (by-30)*scale), ((bx+90)*scale, (by-10)*scale), ((bx+70)*scale, (by+40)*scale), ((bx+10)*scale, (by+10)*scale)], fill=BANANA_YELLOW, outline=CHARCOAL, width=4*scale)
    bdraw.polygon([((bx-10)*scale, (by-10)*scale), ((bx-20)*scale, (by+60)*scale), ((bx+30)*scale, (by+70)*scale), ((bx+20)*scale, (by+10)*scale)], fill=BANANA_YELLOW, outline=CHARCOAL, width=4*scale)
    # Banana stem tip
    bdraw.ellipse([((bx-70)*scale, (by-35)*scale), ((bx-50)*scale, (by-15)*scale)], fill=BANANA_TIP, outline=CHARCOAL, width=3*scale)

    big_down = big.resize((w, h), Image.Resampling.LANCZOS)
    im = Image.alpha_composite(im, big_down)

    dst_p = os.path.join(SPRITES_DIR, "dog_eating_banana.png")
    im.save(guarded_output_path(dst_p), "PNG")
    print("  -> Fixed dog_eating_banana.png to match canonical cartoon dog style!")

def main(argv=None):
    configure_cli(argv)
    print("=== Standardizing Sprites to Canonical Art Style ===")
    fix_dad_teaching()
    fix_levi_sad_matte()
    fix_dog_eating_banana()
    print("=== Standardization Complete! ===")

if __name__ == "__main__":
    main()
