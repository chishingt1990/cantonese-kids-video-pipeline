import os
import shutil
import re
from pathlib import Path
from PIL import Image
import numpy as np
from app.services.asset_manifest import MASTER_ASSETS, get_character_poses, resolve_sprite

def generate_custom_character_sprite(character_id: str, prompt: str, output_path: str) -> str:
    """
    Select approved poses and apply supported clothing recolors.

    This is a deterministic image transformation, not an image-model generation.
    New accessories require approved artwork rather than geometric overlays.
    """
    if Path(output_path).resolve().is_relative_to(MASTER_ASSETS.resolve()):
        raise ValueError("Master artwork is read-only; use a preview or candidate output.")
    poses = get_character_poses().get(character_id)
    if not poses:
        raise ValueError(f"Unknown character: {character_id}")
    prompt_lower = prompt.lower()
    def matches(*words):
        return any(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", prompt_lower) for word in words)
    if matches("cape", "superhero", "party hat", "birthday", "crown"):
        raise ValueError("No approved accessory variant is available. Choose an existing pose or shirt recolor.")

    # 1. Exact High-Fidelity Match: Dog eating banana
    if character_id == "dog" and (matches("banana") or (matches("eat") and matches("fruit"))):
        if "eating_banana" in poses:
            dog_banana = resolve_sprite(character_id, "eating_banana")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copyfile(dog_banana, output_path)
            return output_path

    # 2. Base Pose Selection
    pose_suffix = "default"
    if matches("teach", "teaching", "book", "read", "reading", "story", "storybook"):
        pose_suffix = "holding_book" if "holding_book" in poses else "teaching"
    elif matches("drink", "drinking", "tea", "coffee", "mug"):
        pose_suffix = "drinking_tea" if "drinking_tea" in poses else "drinking"
    elif matches("sit", "sitting", "chair"):
        pose_suffix = "sitting_attentive" if character_id == "dog" else "sitting"
    elif matches("kneel", "kneeling"):
        pose_suffix = "kneeling_hug" if character_id == "mom" else "kneeling"
    elif matches("point", "pointing"):
        pose_suffix = "pointing"
    elif matches("run", "running", "play", "playing"):
        pose_suffix = "running"
    elif matches("eat", "eating", "banana", "apple", "fruit", "cookie", "food", "hungry", "snack"):
        pose_suffix = "eating"
    elif matches("wave", "waving", "hello", "hi", "greet"):
        pose_suffix = "waving"
    elif matches("sleep", "sleeping", "nap", "bed", "pajama", "pj"):
        pose_suffix = "curled_sleeping" if character_id == "dog" else "sleeping"
    elif matches("stretch", "stretching", "yawn", "yawning", "wake up"):
        pose_suffix = "stretching"
    elif matches("hug", "hugging", "arms out", "cuddle", "cuddling"):
        pose_suffix = {"dad": "comforting_hug", "mom": "kneeling_hug"}.get(character_id, "arms_out_hug")

    if pose_suffix not in poses:
        raise ValueError(f"No approved {character_id} pose for '{pose_suffix}'. Choose an available pose.")
    base_candidate = resolve_sprite(character_id, pose_suffix)

    base_im = Image.open(base_candidate).convert("RGBA")
    w, h = base_im.size

    # 3. Shirt Recoloring (torso-bounded to avoid touching facial blush or lips)
    arr = np.array(base_im)
    source = arr.astype(np.int16)
    r, g, b, a = source[:,:,0], source[:,:,1], source[:,:,2], source[:,:,3]
    y_coords = np.arange(h)[:, None]

    # Torso region: 32% to 67% of height
    is_torso = (y_coords >= int(h * 0.32)) & (y_coords <= int(h * 0.67)) & (a > 100)

    # Detect Levi's red/coral polo shirt
    is_red_shirt = is_torso & (r > 155) & (r > g + 40) & (r > b + 40)
    # Detect Luca's yellow polo shirt
    is_yellow_shirt = is_torso & (r > 190) & (g > 160) & (b < 110)

    if character_id == "levi":
        if any(k in prompt_lower for k in ["yellow", "gold", "amber"]):
            # Recolor red shirt to bright yellow
            arr[is_red_shirt, :3] = np.stack([np.clip(r[is_red_shirt] + 20, 0, 255),
                np.clip(r[is_red_shirt] * 0.85, 0, 255), np.clip(b[is_red_shirt] * 0.25, 0, 60)], axis=-1)
        elif "green" in prompt_lower:
            arr[is_red_shirt, :3] = np.stack([np.clip(b[is_red_shirt] * .4, 0, 50),
                np.clip(r[is_red_shirt] * .9, 0, 255), np.clip(b[is_red_shirt] * .5, 0, 70)], axis=-1)
        elif "blue" in prompt_lower:
            arr[is_red_shirt, :3] = np.stack([np.clip(b[is_red_shirt] * .3, 0, 50),
                np.clip(g[is_red_shirt] * .7, 0, 150), np.clip(r[is_red_shirt] * .95, 0, 255)], axis=-1)
    elif character_id == "luca":
        if any(k in prompt_lower for k in ["red", "coral"]):
            arr[is_yellow_shirt, :3] = np.stack([np.clip(r[is_yellow_shirt] + 10, 0, 255),
                np.clip(g[is_yellow_shirt] * .4, 0, 90), np.clip(b[is_yellow_shirt] * .6, 0, 80)], axis=-1)
        elif "blue" in prompt_lower:
            arr[is_yellow_shirt, 0] = 30
            arr[is_yellow_shirt, 1] = np.clip(g[is_yellow_shirt] * 0.6, 0, 140).astype(np.uint8)
            arr[is_yellow_shirt, 2] = np.clip(r[is_yellow_shirt] * 0.95, 0, 255).astype(np.uint8)

    base_im = Image.fromarray(arr)

    # 5. Canvas Expansion for Props/Accessories
    canvas_w = w + 160
    canvas_h = h + 60
    out = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    char_x = 30
    char_y = 40
    out.alpha_composite(base_im, (char_x, char_y))

    # Crop to tight bounding box with padding
    bbox = out.getbbox()
    if bbox:
        out = out.crop((max(0, bbox[0]-8), max(0, bbox[1]-8), min(canvas_w, bbox[2]+8), min(canvas_h, bbox[3]+8)))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out.save(output_path, format="PNG")
    return output_path
