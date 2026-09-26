import os
import shutil
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from collections import deque

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
CHAR_DIR = os.path.join(PROJECT_ROOT, "assets", "characters")
BRAIN_DIR = r"C:\Users\chish\.gemini\antigravity\brain\f340737b-7662-449f-a19e-c09b4ce0f071"

os.makedirs(SPRITES_DIR, exist_ok=True)

def isolate_sprite(image_path: str, output_path: str, threshold: int = 35) -> str:
    """
    Isolate sprite with boundary-seeded floodfill to protect interior white highlights/fur/socks.
    """
    im = Image.open(image_path).convert('RGB')
    arr = np.array(im)
    h, w, _ = arr.shape

    # Distance from pure white
    diff = np.max(np.abs(arr.astype(int) - 255), axis=2)

    visited = np.zeros((h, w), dtype=bool)
    is_bg = np.zeros((h, w), dtype=bool)

    queue = deque()
    # Seed from all borders
    for x in range(w):
        queue.append((0, x))
        queue.append((h - 1, x))
    for y in range(h):
        queue.append((y, 0))
        queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        if visited[y, x]:
            continue
        visited[y, x] = True

        # Check if border pixel is background
        if diff[y, x] < threshold or (arr[y, x, 0] > 240 and arr[y, x, 1] > 240 and arr[y, x, 2] > 240):
            is_bg[y, x] = True
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    if diff[ny, nx] < threshold or (arr[ny, nx, 0] > 242 and arr[ny, nx, 1] > 242 and arr[ny, nx, 2] > 242):
                        queue.append((ny, nx))

    # Alpha mask
    alpha = np.where(is_bg, 0, 255).astype(np.uint8)
    alpha_im = Image.fromarray(alpha, mode='L')
    alpha_smooth = alpha_im.filter(ImageFilter.GaussianBlur(0.8))
    smooth_arr = np.array(alpha_smooth)

    rgba = np.dstack([arr, smooth_arr])
    rgba[is_bg, 3] = 0

    out_im = Image.fromarray(rgba, 'RGBA')

    # Tight crop
    bbox = out_im.getbbox()
    if bbox:
        pad = 8
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        out_im = out_im.crop((left, top, right, bottom))

    out_im.save(output_path, 'PNG', optimize=True)
    print(f"[SPRITE ISOLATED] {os.path.basename(output_path)} -> ({out_im.width}x{out_im.height})")
    return output_path

def main():
    print("=== Processing High-Fidelity Concepts into Sprites ===")
    
    # 1. Map generated concepts to sprite targets
    concept_map = {
        "levi_sad_concept_1790105472217.jpg": "levi_sad.png",
        "levi_holding_book_concept_1790105497347.jpg": "levi_holding_book.png",
        "levi_thinking_concept_1790105530318.jpg": "levi_thinking.png",
        "levi_sitting_floor_concept_1790105686447.jpg": "levi_sitting_floor.png",
        "luca_crying_concept_1790105798935.jpg": "luca_crying.png",
        "luca_pointing_concept_1790105903717.jpg": "luca_pointing.png",
        "luca_sitting_floor_concept_1790105918167.jpg": "luca_sitting_floor.png",
        "dad_comforting_hug_concept_1790105931858.jpg": "dad_comforting_hug.png",
        "dad_clapping_concept_1790105984612.jpg": "dad_clapping.png",
        "mom_waving_concept_1790106039089.jpg": "mom_waving.png",
        "mom_holding_bowl_concept_1790106059254.jpg": "mom_holding_bowl.png",
        "dog_curled_sleeping_concept_1790106288256.jpg": "dog_curled_sleeping.png",
    }

    for concept_file, sprite_target in concept_map.items():
        src_path = os.path.join(BRAIN_DIR, concept_file)
        dst_path = os.path.join(SPRITES_DIR, sprite_target)
        if os.path.exists(src_path):
            isolate_sprite(src_path, dst_path)
        else:
            print(f"Warning: Concept {concept_file} not found")

    # 2. Dog Sitting Attentive
    dog_src = os.path.join(CHAR_DIR, "dog_cartoon.jpg")
    dog_dst = os.path.join(SPRITES_DIR, "dog_sitting_attentive.png")
    if os.path.exists(dog_src):
        isolate_sprite(dog_src, dog_dst, threshold=25)

    # 3. Dog Dancing Paw - Clean borders
    dog_dance_path = os.path.join(SPRITES_DIR, "dog_dancing_paw.png")
    if os.path.exists(dog_dance_path):
        im = Image.open(dog_dance_path).convert("RGBA")
        # Ensure alpha mask is clean
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        im.save(dog_dance_path, "PNG")
        print("[CLEANED] dog_dancing_paw.png")

    print("\nAll high-fidelity sprites built successfully!")

if __name__ == "__main__":
    main()
