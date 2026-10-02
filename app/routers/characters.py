import os
import glob
import time
import shutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.background_generator import generate_pastel_room, generate_iterative_background
from app.services.character_generator import generate_custom_character_sprite
from app.services import family_catalog

router = APIRouter(prefix="/api/characters", tags=["characters"])

POSE_LABELS = {
    "jumping": "Jumping / 跳起",
    "dancing": "Dancing / 跳舞",
    "brushing_teeth": "Brushing Teeth / 刷牙",
    "default": "Default Standing",
    "sad": "😢 Sad / Needing Hug",
    "holding_book": "📖 Holding Storybook",
    "playing_blocks": "🧱 Stacking Toy Blocks",
    "playing_car": "🚗 Pushing Toy Car",
    "sitting_floor": "🧘 Sitting on Play Mat",
    "cheering": "🙌 Cheering with Joy",
    "clapping": "👏 Clapping Happily",
    "crying": "😭 Crying with Tears",
    "thinking": "🤔 Curious & Thinking",
    "waving": "👋 Waving Hello",
    "pointing": "👉 Pointing Excitedly",
    "running": "🏃 Skipping & Running",
    "arms_out_hug": "🤗 Open Arms for Hug",
    "stretching": "🥱 Stretching & Yawning",
    "eating": "🥣 Eating Breakfast",
    "sleeping": "😴 Sleeping (Star PJs)",
    "holding_toy": "🧸 Hugging Toy",
    "sitting": "🪑 Sitting on Chair",
    "kneeling": "🧎 Kneeling at Eye Level",
    "comforting_hug": "🤗 Open Arms Comforting Hug",
    "kneeling_hug": "🤗 Open Arms Warm Hug",
    "holding_fruit": "🍎 Holding Fruit Platter",
    "holding_bowl": "🥣 Holding Meal Bowl",
    "teaching": "📖 Teaching & Praising",
    "drinking": "☕ Drinking Warm Tea/Coffee",
    "drinking_tea": "🍵 Drinking Warm Tea",
    "curled_sleeping": "😴 Curled Up Sleeping",
    "sitting_attentive": "🦮 Sitting Attentively",
    "dancing_paw": "🐾 Dancing on Paws",
    "eating_banana": "🍌 Eating Sweet Banana",
    "playing_ball": "🎾 Playing with Ball",
}
# Merge the family-expansion v3 pose vocabulary (standing, seated_storytelling,
# offering_food_or_gift, listening_crouched, reading_book, walking, hug, ...)
# so dynamic sprite discovery picks up human-readable labels for the new poses.
for _pose_id, _label in family_catalog.pose_labels().items():
    POSE_LABELS.setdefault(_pose_id, _label)

@router.get("/")
@router.get("/all")
def list_characters():
    chars = [
        {
            "id": "levi",
            "name": "Levi (哥哥)",
            "role": "Older Twin Brother",
            "outfit": "Coral Red Polo & Navy Shorts",
            "hair": "Naturally curves upward (quiff)",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "levi_default.png"},
                {"id": "sad", "label": "😢 Sad / Needing Hug", "sprite": "levi_sad.png"},
                {"id": "holding_book", "label": "📖 Holding Storybook", "sprite": "levi_holding_book.png"},
                {"id": "playing_blocks", "label": "🧱 Stacking Toy Blocks", "sprite": "levi_playing_blocks.png"},
                {"id": "playing_car", "label": "🚗 Pushing Toy Car", "sprite": "levi_playing_car.png"},
                {"id": "sitting_floor", "label": "🧘 Sitting on Play Mat", "sprite": "levi_sitting_floor.png"},
                {"id": "cheering", "label": "🙌 Cheering with Joy", "sprite": "levi_cheering.png"},
                {"id": "clapping", "label": "👏 Clapping Happily", "sprite": "levi_clapping.png"},
                {"id": "thinking", "label": "🤔 Curious & Thinking", "sprite": "levi_thinking.png"},
                {"id": "waving", "label": "👋 Waving Hello", "sprite": "levi_waving.png"},
                {"id": "pointing", "label": "👉 Pointing Excitedly", "sprite": "levi_pointing.png"},
                {"id": "running", "label": "🏃 Skipping & Running", "sprite": "levi_running.png"},
                {"id": "arms_out_hug", "label": "🤗 Open Arms for Hug", "sprite": "levi_arms_out_hug.png"},
                {"id": "stretching", "label": "🥱 Stretching & Yawning", "sprite": "levi_stretching.png"},
                {"id": "eating", "label": "🥣 Eating Breakfast", "sprite": "levi_eating.png"},
                {"id": "sleeping", "label": "😴 Sleeping (Star PJs)", "sprite": "levi_sleeping.png"},
            ],
            "sprite_url": "/api/characters/sprite/levi_default.png"
        },
        {
            "id": "luca",
            "name": "Luca (細佬)",
            "role": "Younger Twin Brother",
            "outfit": "Bright Yellow Polo & Navy Shorts",
            "hair": "Combed down bangs with cowlick",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "luca_default.png"},
                {"id": "crying", "label": "😭 Crying with Tears", "sprite": "luca_crying.png"},
                {"id": "playing_blocks", "label": "🧱 Stacking Toy Blocks", "sprite": "luca_playing_blocks.png"},
                {"id": "playing_car", "label": "🚗 Pushing Toy Car", "sprite": "luca_playing_car.png"},
                {"id": "sitting_floor", "label": "🧘 Sitting on Play Mat", "sprite": "luca_sitting_floor.png"},
                {"id": "cheering", "label": "🙌 Cheering with Joy", "sprite": "luca_cheering.png"},
                {"id": "clapping", "label": "👏 Clapping with Joy", "sprite": "luca_clapping.png"},
                {"id": "pointing", "label": "👉 Pointing Excitedly", "sprite": "luca_pointing.png"},
                {"id": "arms_out_hug", "label": "🤗 Open Arms for Hug", "sprite": "luca_arms_out_hug.png"},
                {"id": "waving", "label": "👋 Waving Hello", "sprite": "luca_waving.png"},
                {"id": "holding_toy", "label": "🧸 Hugging Teddy Bear", "sprite": "luca_holding_toy.png"},
                {"id": "holding_book", "label": "📖 Holding Storybook", "sprite": "luca_holding_book.png"},
                {"id": "eating", "label": "🍎 Eating Fruit Snack", "sprite": "luca_eating.png"},
                {"id": "sleeping", "label": "😴 Sleeping (Star PJs)", "sprite": "luca_sleeping.png"},
            ],
            "sprite_url": "/api/characters/sprite/luca_default.png"
        },
        {
            "id": "dad",
            "name": "Dad (爸爸)",
            "role": "Father / Narrator",
            "outfit": "Slate Blue Polo & Khaki Chinos",
            "hair": "Short neat dark hair",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "dad_default.png"},
                {"id": "sitting", "label": "🪑 Sitting on Chair", "sprite": "dad_sitting.png"},
                {"id": "kneeling", "label": "🧎 Kneeling at Eye Level", "sprite": "dad_kneeling.png"},
                {"id": "teaching", "label": "📖 Teaching Storybook", "sprite": "dad_teaching.png"},
                {"id": "comforting_hug", "label": "🤗 Open Arms Comforting Hug", "sprite": "dad_comforting_hug.png"},
                {"id": "clapping", "label": "👏 Clapping Proudly", "sprite": "dad_clapping.png"},
                {"id": "pointing", "label": "👉 Pointing", "sprite": "dad_pointing.png"},
                {"id": "waving", "label": "👋 Waving Warmly", "sprite": "dad_waving.png"},
                {"id": "drinking", "label": "☕ Drinking Warm Coffee/Tea", "sprite": "dad_drinking.png"},
            ],
            "sprite_url": "/api/characters/sprite/dad_default.png"
        },
        {
            "id": "mom",
            "name": "Mom (媽媽)",
            "role": "Mother / Narrator",
            "outfit": "Coral Apron & Warm Smile",
            "hair": "Soft dark hair in low bun",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "mom_default.png"},
                {"id": "kneeling_hug", "label": "🤗 Open Arms Warm Hug", "sprite": "mom_kneeling_hug.png"},
                {"id": "holding_fruit", "label": "🍎 Holding Fruit Platter", "sprite": "mom_holding_fruit.png"},
                {"id": "holding_bowl", "label": "🥣 Holding Meal Bowl", "sprite": "mom_holding_bowl.png"},
                {"id": "waving", "label": "👋 Waving Warmly", "sprite": "mom_waving.png"},
                {"id": "clapping", "label": "👏 Clapping Happily", "sprite": "mom_clapping.png"},
                {"id": "teaching", "label": "📖 Teaching & Praising", "sprite": "mom_teaching.png"},
            ],
            "sprite_url": "/api/characters/sprite/mom_default.png"
        },
        {
            "id": "dog",
            "name": "Doggy (狗狗)",
            "role": "Family Pet",
            "outfit": "Red Collar with Golden Tag",
            "hair": "Pure white fluffy fur (Japanese Spitz)",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "dog_default.png"},
                {"id": "playing_ball", "label": "🎾 Playing with Ball", "sprite": "dog_playing_ball.png"},
                {"id": "running", "label": "🐾 Bouncing & Running", "sprite": "dog_running.png"},
                {"id": "eating_banana", "label": "🍌 Eating Sweet Banana", "sprite": "dog_eating_banana.png"},
                {"id": "curled_sleeping", "label": "😴 Curled Up Sleeping", "sprite": "dog_curled_sleeping.png"},
                {"id": "sitting_attentive", "label": "🦮 Sitting Attentively", "sprite": "dog_sitting_attentive.png"},
                {"id": "dancing_paw", "label": "🐾 Dancing on Paws", "sprite": "dog_dancing_paw.png"},
            ],
            "sprite_url": "/api/characters/sprite/dog_default.png"
        },
        {
            "id": "grandparents_paternal",
            "name": "爺爺 & 嫲嫲",
            "role": "Paternal Grandparents",
            "outfit": "Blue Polo & Lavender Blouse",
            "hair": "Grey hair with warm smiles",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "grandparents_paternal_default.png"},
                {"id": "drinking_tea", "label": "🍵 Drinking Warm Tea", "sprite": "grandparents_paternal_tea.png"},
            ],
            "sprite_url": "/api/characters/sprite/grandparents_paternal_default.png"
        },
        {
            "id": "grandparents_maternal",
            "name": "公公 & 婆婆",
            "role": "Maternal Grandparents",
            "outfit": "White Tee & Floral Top",
            "hair": "Short grey & dark pixie cuts",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "grandparents_maternal_default.png"},
                {"id": "waving", "label": "👋 Waving Hello Warmly", "sprite": "grandparents_maternal_waving.png"},
            ],
            "sprite_url": "/api/characters/sprite/grandparents_maternal_default.png"
        },
        {
            "id": "auntie_cousins",
            "name": "姑媽 & 表哥",
            "role": "Auntie & Cousins",
            "outfit": "Summer Casual & Cool Glasses",
            "hair": "Modern family look",
            "poses": [
                {"id": "default", "label": "Default Standing", "sprite": "auntie_cousins_default.png"},
                {"id": "waving", "label": "👋 Waving Energetically", "sprite": "auntie_cousins_waving.png"},
            ],
            "sprite_url": "/api/characters/sprite/auntie_cousins_default.png"
        }
    ]

    # Append family-expansion v3 individual relatives and contact sprites.
    # Legacy group entries above remain untouched for compatibility with
    # existing episodes; new entries are additional selectable characters.
    individual_poses = family_catalog.individual_poses()
    for new_id in ("paternal_grandpa", "paternal_grandma", "maternal_grandpa",
                   "maternal_grandma", "aunt_sister", "cousin_ryan", "cousin_younger"):
        display = family_catalog.new_character_display(new_id) or {}
        poses = []
        for pose_id in individual_poses.get(new_id, ["default"]):
            poses.append({
                "id": pose_id,
                "label": POSE_LABELS.get(pose_id, pose_id.replace("_", " ").title()),
                "sprite": f"{new_id}_{pose_id}.png",
            })
        chars.append({
            "id": new_id,
            "name": display.get("name", new_id),
            "role": display.get("role", "Family"),
            "outfit": display.get("outfit", ""),
            "hair": display.get("hair", ""),
            "poses": poses,
            "sprite_url": f"/api/characters/sprite/{new_id}_default.png",
            "family_release": "v3",
        })
    for contact in family_catalog.contact_sprites():
        sprite = os.path.basename(contact["runtime_path"])
        chars.append({
            "id": contact["id"],
            "name": family_catalog.contact_display_name(contact["id"]),
            "role": "Family Contact Sprite",
            "outfit": "Composite contact (hug / handholding / adult carrying child)",
            "hair": "",
            "members": list(contact["members"]),
            "action": contact["action"],
            "scale_class": contact["scale_class"],
            "poses": [{
                "id": "default",
                "label": "Default Composite",
                "sprite": sprite,
            }],
            "sprite_url": f"/api/characters/sprite/{sprite}",
            "family_release": "v3",
        })
    
    # Dynamically scan sprites for all poses and custom additions
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sprites_dir = os.path.join(project_root, "assets", "sprites")
    for char in chars:
        cid = char["id"]
        # Filter existing list to only files that exist on disk
        char["poses"] = [p for p in char["poses"] if os.path.exists(os.path.join(sprites_dir, p.get("sprite", "")))]
        
        # Discover all on-disk sprite files for this character
        sprite_files = glob.glob(os.path.join(sprites_dir, f"{cid}_*.png"))
        for sf in sorted(sprite_files):
            fname = os.path.basename(sf)
            if fname.startswith("temp_") or fname.startswith("test_"):
                continue
            pid = fname[len(cid)+1:-4]
            # Avoid duplicate if id or sprite filename already registered
            if not any(p["id"] == pid or p.get("sprite") == fname for p in char["poses"]):
                label = POSE_LABELS.get(pid, f"✨ {pid.replace('_', ' ').title()}")
                char["poses"].append({
                    "id": pid,
                    "label": label,
                    "sprite": fname
                })

    # Expose a single source of truth for sizing: the stage-canvas height
    # percent used by app/static/app.js and the render-canvas base height
    # used by app/services/render_service.py. Legacy IDs resolve to their
    # historical values (adult 72% / 760px, toddler 50% / 520px, dog
    # 30% / 320px) via family_catalog's merged scale-class map; new family
    # IDs and contact composites pick up adult / older_child classifications.
    for char in chars:
        cid = char["id"]
        char["scale_class"] = family_catalog.scale_class_for(cid)
        char["stage_height_percent"] = family_catalog.stage_height_percent_for(cid)
        char["base_height_px"] = family_catalog.base_height_for(cid)
        # Browsing-only categorisation. ``family_buckets`` is a list because
        # multi-person composites (e.g. mom carrying Levi) belong to every
        # participant's bucket, while solo characters map to exactly one.
        # The runtime character ID, pose vocabulary and sprite_url are
        # unchanged — the renderer still receives the composite asset ID on
        # select so no duplicate participants are drawn.
        char["family_buckets"] = family_catalog.buckets_for(cid)

    return {
        "characters": chars,
        "family_buckets": [
            {"id": bid, **family_catalog.BUCKETS[bid]}
            for bid in family_catalog.BUCKET_ORDER
        ],
    }


@router.get("/sprite/{filename}")
def get_sprite(filename: str):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sprites_dir = os.path.join(project_root, "assets", "sprites")
    clean_name = os.path.basename(filename.split("?")[0].lower())
    if not clean_name.endswith(".png"):
        clean_name = f"{clean_name}.png"
    
    # Direct alias mappings
    aliases = {
        "grandparents_paternal_drinking_tea.png": "grandparents_paternal_tea.png",
        "grandparents_paternal_drinking.png": "grandparents_paternal_tea.png",
        "grandparents_maternal_drinking_tea.png": "grandparents_maternal_default.png",
        "mom_drinking.png": "mom_default.png",
    }
    if clean_name in aliases:
        clean_name = aliases[clean_name]

    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    # Serve the exact requested file first so legacy group filenames such as
    # ``auntie_cousins_default.png`` are returned verbatim rather than being
    # rewritten by the alias layer below.
    path = os.path.join(sprites_dir, clean_name)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png", headers=no_cache_headers)

    # Family-expansion v3 filename aliases: scripts that still use the batch
    # nicknames (``auntie_*.png``, ``cousin_ben_*.png``) resolve to the real
    # runtime filenames (``aunt_sister_*``, ``cousin_younger_*``) so legacy
    # references keep working without duplicating sprite bytes on disk.
    # ``filename_alias_resolution`` returns None for protected canonical
    # prefixes (``auntie_cousins_*``) to avoid clobbering legacy group IDs.
    family_resolved = family_catalog.filename_alias_resolution(clean_name)
    if family_resolved is not None:
        clean_name = family_resolved
        path = os.path.join(sprites_dir, clean_name)
        if os.path.exists(path):
            return FileResponse(path, media_type="image/png", headers=no_cache_headers)

    # Match against multi-word character prefixes. Order is longest-first so
    # ``paternal_grandpa_*`` is matched before any ``paternal_*`` substring and
    # ``cousin_younger_*`` is matched before any ``cousin_*`` substring.
    known_prefixes = family_catalog.known_character_prefixes()
    char_prefix = None
    for pfx in known_prefixes:
        token = f"{pfx}_"
        if clean_name.startswith(token) or clean_name == f"{pfx}.png":
            char_prefix = pfx
            break
    if not char_prefix:
        char_prefix = clean_name.split("_")[0]

    # Resolve aliases on the character prefix too, so e.g. ``cousin_ben_default.png``
    # falls back to ``cousin_younger_default.png`` on the retry step. Protected
    # canonical prefixes are preserved by returning them unchanged.
    if char_prefix in family_catalog._PROTECTED_CANONICAL_PREFIXES:
        aliased_prefix = char_prefix
    else:
        aliased_prefix = family_catalog.FILENAME_ALIAS_PREFIXES.get(char_prefix, char_prefix)

    fallback_char = os.path.join(sprites_dir, f"{aliased_prefix}_default.png")
    if os.path.exists(fallback_char):
        return FileResponse(fallback_char, media_type="image/png", headers=no_cache_headers)
        
    fallback_char_simple = os.path.join(sprites_dir, f"{aliased_prefix}.png")
    if os.path.exists(fallback_char_simple):
        return FileResponse(fallback_char_simple, media_type="image/png", headers=no_cache_headers)
        
    # Global fallback only as absolute last resort
    return FileResponse(os.path.join(sprites_dir, "levi_default.png"), media_type="image/png", headers=no_cache_headers)

@router.get("/sprite/{char_id}/{pose_id}")
def get_sprite_by_char_pose(char_id: str, pose_id: str):
    return get_sprite(f"{char_id}_{pose_id}.png")

@router.get("/backgrounds")
def list_backgrounds():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    
    known_names = {
        "living_room": "🛋️ Living Room Play Mat",
        "nursery": "🌙 Bedtime Nursery & Crib",
        "kitchen": "🥣 Kitchen & High Chairs",
        "playroom": "🧸 Toy Playroom & Blocks",
        "beach": "🏖️ Sandcastle Beach",
        "park": "🌳 Sunny Green Park",
        "mountains": "⛰️ Gentle Wildflower Hills",
        "dining": "🥟 Dim Sum Dining Room",
        "bathroom": "🛁 Bubble Bath & Duckies",
        "reading_nook": "📚 Storybook Reading Nook",
        "playground": "🛝 Playground Swings & Slide",
        "farm_field": "🌾 Sunny Farm Meadow & Hills",
        "duck_pond": "🦆 Storybook Duck Pond & Lake",
        "backyard_garden": "🌻 Family Backyard Garden",
        "art_room": "🎨 Watercolor Art Studio & Easel",
        "supermarket": "🛒 Preschool Market & Fruit Stand"
    }
    core_ids = set(known_names.keys())
    
    bgs = []
    for f in sorted(os.listdir(bg_dir)):
        if f.startswith("bg_") and f.endswith(".png") and "temp_preview" not in f:
            bg_id = f[3:-4]
            name = known_names.get(bg_id, f"🎨 {bg_id.replace('_', ' ').title()}")
            bgs.append({
                "id": bg_id,
                "name": name,
                "filename": f,
                "url": f"/api/characters/background/{f}",
                "is_core": bg_id in core_ids
            })
    return {"backgrounds": bgs}

@router.delete("/background/{bg_id}")
def delete_background(bg_id: str):
    clean_id = bg_id.replace("bg_", "").replace(".png", "").strip().lower()
    core_ids = {
        "living_room", "nursery", "kitchen", "playroom", "beach", "park", 
        "mountains", "dining", "bathroom", "reading_nook", "playground", 
        "farm_field", "duck_pond", "backyard_garden", "art_room", "supermarket"
    }
    if clean_id in core_ids:
        raise HTTPException(status_code=400, detail="Core master background presets cannot be deleted.")

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    
    candidates = [
        os.path.join(bg_dir, f"bg_{clean_id}.png"),
        os.path.join(bg_dir, f"{clean_id}.png"),
        os.path.join(bg_dir, f"{bg_id}")
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                os.remove(c)
                return {"status": "deleted", "bg_id": clean_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Background preset not found.")

@router.get("/background/{filename}")
def get_background(filename: str):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    clean_name = filename.split("?")[0].lower()
    path = os.path.join(bg_dir, clean_name)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    # Global fallback
    fallback = os.path.join(bg_dir, "bg_living_room.png")
    if os.path.exists(fallback):
        return FileResponse(fallback, media_type="image/png")
    return FileResponse(os.path.join(bg_dir, "bg_playroom.png"), media_type="image/png")

class OutfitPromptRequest(BaseModel):
    character_id: str
    prompt: str

@router.post("/preview_outfit")
def preview_outfit(req: OutfitPromptRequest):
    """Generates a live preview sprite based on prompt."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sprites_dir = os.path.join(project_root, "assets", "sprites")
    temp_file = os.path.join(sprites_dir, "temp_preview_sprite.png")
    
    generate_custom_character_sprite(req.character_id, req.prompt, temp_file)
    return {
        "status": "preview_ready",
        "character_id": req.character_id,
        "preview_url": f"/api/characters/sprite/temp_preview_sprite.png?t={int(time.time()*1000)}"
    }

class SaveOutfitRequest(BaseModel):
    character_id: str
    prompt: str

@router.post("/save_outfit")
def save_outfit(req: SaveOutfitRequest):
    """Permanently saves the generated preview sprite to the character's pose library."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sprites_dir = os.path.join(project_root, "assets", "sprites")
    
    temp_file = os.path.join(sprites_dir, "temp_preview_sprite.png")
    if not os.path.exists(temp_file):
        # Generate fresh if not previewed
        generate_custom_character_sprite(req.character_id, req.prompt, temp_file)
        
    safe_name = "".join(c for c in req.prompt.lower() if c.isalnum() or c == " ").strip().replace(" ", "_")[:24] or "custom"
    pose_id = f"custom_{safe_name}"
    final_file = os.path.join(sprites_dir, f"{req.character_id}_{pose_id}.png")
    
    shutil.copyfile(temp_file, final_file)
    
    return {
        "status": "saved",
        "character_id": req.character_id,
        "pose_id": pose_id,
        "label": f"✨ {req.prompt[:22]}",
        "sprite_filename": f"{req.character_id}_{pose_id}.png",
        "sprite_url": f"/api/characters/sprite/{req.character_id}_{pose_id}.png"
    }

class BgPromptRequest(BaseModel):
    name: str
    prompt: str

@router.post("/preview_background")
def preview_background(req: BgPromptRequest):
    """Generates a live preview pastel background based on prompt."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    temp_file = os.path.join(bg_dir, "temp_preview_bg.png")
    
    generate_iterative_background(f"{req.name} {req.prompt}", [], temp_file)
    return {
        "status": "preview_ready",
        "name": req.name,
        "preview_url": f"/api/characters/background/temp_preview_bg.png?t={int(time.time()*1000)}"
    }

class IterativeBgRequest(BaseModel):
    name: str
    prompt: str
    history: list[str] = []
    iteration: int = 1

@router.post("/iterate_background")
def iterate_background(req: IterativeBgRequest):
    """Generates an iterative background taking into account prompt & revision history."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    
    iter_filename = f"temp_preview_bg_v{req.iteration}.png"
    iter_file = os.path.join(bg_dir, iter_filename)
    default_preview = os.path.join(bg_dir, "temp_preview_bg.png")
    
    generate_iterative_background(req.prompt, req.history, iter_file)
    shutil.copyfile(iter_file, default_preview)
    
    return {
        "status": "preview_ready",
        "name": req.name,
        "iteration": req.iteration,
        "preview_url": f"/api/characters/background/{iter_filename}?t={int(time.time()*1000)}"
    }

class SaveBgRequest(BaseModel):
    name: str
    prompt: str = ""
    iteration: int = 0

@router.post("/save_background")
def save_background(req: SaveBgRequest):
    """Permanently saves the generated preview background to project presets."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    bg_dir = os.path.join(project_root, "assets", "backgrounds")
    
    src_file = os.path.join(bg_dir, f"temp_preview_bg_v{req.iteration}.png") if req.iteration > 0 else os.path.join(bg_dir, "temp_preview_bg.png")
    if not os.path.exists(src_file):
        src_file = os.path.join(bg_dir, "temp_preview_bg.png")
    if not os.path.exists(src_file):
        generate_iterative_background(f"{req.name} {req.prompt}", [], src_file)
        
    safe_name = "".join(c for c in req.name.lower() if c.isalnum() or c == " ").strip().replace(" ", "_")[:24] or "custom_room"
    bg_id = safe_name
    final_filename = f"bg_{bg_id}.png"
    final_file = os.path.join(bg_dir, final_filename)
    
    shutil.copyfile(src_file, final_file)
    
    return {
        "status": "saved",
        "background_id": bg_id,
        "name": f"🎨 {req.name}",
        "filename": final_filename,
        "url": f"/api/characters/background/{final_filename}"
    }

@router.post("/custom_outfit")
def custom_outfit_alias(req: SaveOutfitRequest):
    return save_outfit(req)

@router.post("/custom_background")
def custom_background_alias(req: SaveBgRequest):
    res = save_background(req)
    res["status"] = "success"
    return res


