"""Shared, read-only master catalogue and isolated generated-image storage."""

import os
import json
from pathlib import Path

from app.storage import ROOT, contained_path, validate_id

MASTER_ASSETS = ROOT / "assets"
CHARACTERS = {
    "levi": ("Levi (哥哥)", "Older Twin Brother", "Coral Red Polo & Navy Shorts", "Upward quiff"),
    "luca": ("Luca (細佬)", "Younger Twin Brother", "Bright Yellow Polo & Navy Shorts", "Downward bangs with cowlick"),
    "dad": ("Dad (爸爸)", "Father / Narrator", "Slate Blue Polo & Khaki Chinos", "Short neat dark hair"),
    "mom": ("Mom (媽媽)", "Mother", "Coral Apron & Warm Smile", "Low side ponytail"),
    "dog": ("Doggy (狗狗)", "Family Pet", "Red Collar with Golden Tag", "White Japanese Spitz"),
    "grandparents_paternal": ("爺爺 & 嫲嫲", "Paternal Grandparents", "Blue Polo & Lavender Blouse", "Grey hair"),
    "grandparents_maternal": ("公公 & 婆婆", "Maternal Grandparents", "White Tee & Floral Top", "Grey hair"),
    "auntie_cousins": ("姑媽 & 表哥", "Auntie & Cousins", "Summer Casual & Cool Glasses", "Dark hair"),
}
BACKGROUND_NAMES = {
    "living_room": "Living Room Play Mat", "nursery": "Bedtime Nursery & Crib",
    "kitchen": "Kitchen & High Chairs", "playroom": "Toy Playroom & Blocks",
    "beach": "Sandcastle Beach", "park": "Sunny Green Park",
    "mountains": "Gentle Wildflower Hills", "dining": "Dim Sum Dining Room",
    "bathroom": "Bubble Bath & Duckies", "reading_nook": "Storybook Reading Nook",
    "playground": "Playground Swings & Slide", "farm_field": "Sunny Farm Meadow",
    "duck_pond": "Storybook Duck Pond", "backyard_garden": "Family Backyard Garden",
    "art_room": "Art Studio", "supermarket": "Preschool Market",
}


def image_dir(kind: str) -> Path:
    if kind not in {"previews", "sprites", "backgrounds", "stickers"}:
        raise ValueError("Unknown image storage category")
    data = Path(os.environ.get("KIDS_STUDIO_DATA_DIR") or ROOT / "data")
    path = contained_path(data, "artwork", kind)
    if path.is_relative_to(MASTER_ASSETS.resolve()):
        raise ValueError("Generated images cannot be stored in the master artwork library")
    return path


def image_path(kind: str, filename: str) -> Path:
    path = contained_path(image_dir(kind), filename)
    if path.is_relative_to(MASTER_ASSETS.resolve()):
        raise ValueError("Master artwork is read-only")
    return path


def _approved_files(kind: str, pattern: str = "*.png"):
    directory = contained_path(MASTER_ASSETS, kind)
    if directory.is_dir():
        for path in sorted(directory.glob(pattern)):
            if not any(word in path.stem for word in ("temp_", "test_", ".pending")):
                yield contained_path(directory, path.name)


def _pose_files(character_id: str) -> dict:
    validate_id(character_id)
    if character_id not in CHARACTERS:
        raise ValueError(f"Unknown character: {character_id}")
    result = {}
    for path in _approved_files("sprites", character_id + "*.png"):
        if path.stem == character_id:
            result.setdefault("default", path)
        elif path.stem.startswith(character_id + "_"):
            pose = path.stem[len(character_id) + 1:]
            if "temp_" not in pose and "test_" not in pose:
                result[pose] = path
    if character_id == "grandparents_paternal" and "tea" in result:
        result["drinking_tea"] = result.pop("tea")
    custom = image_dir("sprites")
    if custom.is_dir():
        for path in sorted(custom.glob(f"{character_id}_custom_*.png")):
            pose = path.stem[len(character_id) + 1:]
            result[pose] = image_path("sprites", path.name)
    return result


def get_character_poses() -> dict:
    return {cid: list(_pose_files(cid)) for cid in CHARACTERS}


def resolve_sprite(character_id: str, pose: str = "default") -> Path:
    validate_id(pose)
    if character_id == "grandparents_paternal" and pose == "tea":
        pose = "drinking_tea"
    path = _pose_files(character_id).get(pose)
    if path is None or not path.is_file():
        raise FileNotFoundError(f"Approved sprite unavailable: {character_id}/{pose}")
    return path


def resolve_sprite_filename(filename: str) -> Path:
    stem = filename[:-4] if filename.endswith(".png") else filename
    validate_id(stem)
    for cid in sorted(CHARACTERS, key=len, reverse=True):
        if stem == cid:
            return resolve_sprite(cid)
        if stem.startswith(cid + "_"):
            return resolve_sprite(cid, stem[len(cid) + 1:])
    raise FileNotFoundError("Unknown sprite")


def list_characters() -> list:
    result = []
    for cid, (name, role, outfit, hair) in CHARACTERS.items():
        poses = _pose_files(cid)
        pose_records = []
        for pid, path in poses.items():
            label = pid.replace("_", " ").title()
            if path.parent == image_dir("sprites"):
                metadata = image_path("sprites", path.stem + ".json")
                if metadata.is_file():
                    label = json.loads(metadata.read_text(encoding="utf-8")).get("label", label)
            pose_records.append({"id": pid, "label": label, "sprite": path.name})
        result.append({
            "id": cid, "name": name, "role": role, "outfit": outfit, "hair": hair,
            "poses": pose_records,
            "sprite_url": f"/api/characters/sprite/{cid}/default",
        })
    return result


def list_backgrounds() -> list:
    result = {}
    for path in _approved_files("backgrounds"):
        if path.stem.startswith("bg_"):
            bid = path.stem[3:]
            result[bid] = {
                "id": bid, "name": BACKGROUND_NAMES.get(bid, bid.replace("_", " ").title()),
                "filename": path.name, "url": f"/api/characters/background/{path.name}",
                "is_core": True,
            }
    directory = image_dir("backgrounds")
    if directory.is_dir():
        for path in sorted(directory.glob("bg_custom_*.png")):
            bid = path.stem[3:]
            name = bid
            metadata = image_path("backgrounds", path.stem + ".json")
            if metadata.is_file():
                name = json.loads(metadata.read_text(encoding="utf-8")).get("name", bid)
            result[bid] = {
                "id": bid, "name": name, "filename": path.name,
                "url": f"/api/characters/background/{path.name}", "is_core": False,
            }
    return list(result.values())


def resolve_background(background_id: str) -> Path:
    validate_id(background_id)
    # Approved masters take precedence; writable data can never shadow them.
    master = contained_path(MASTER_ASSETS, "backgrounds", f"bg_{background_id}.png")
    if master.is_file() and not any(x in background_id for x in ("temp_", "test_")):
        return master
    if background_id.startswith("custom_"):
        custom = image_path("backgrounds", f"bg_{background_id}.png")
        if custom.is_file():
            return custom
    raise FileNotFoundError(f"Approved background unavailable: {background_id}")
