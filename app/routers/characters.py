import os
import glob
import time
import shutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.background_generator import generate_pastel_room, generate_iterative_background
from app.services.character_generator import generate_custom_character_sprite

router = APIRouter(prefix="/api/characters", tags=["characters"])

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
                {"id": "waving", "label": "Waving Hello", "sprite": "levi_waving.png"},
                {"id": "running", "label": "Skipping & Running", "sprite": "levi_running.png"},
                {"id": "pointing", "label": "Pointing Excitedly", "sprite": "levi_pointing.png"},
                {"id": "sleeping", "label": "Sleeping (Star PJs)", "sprite": "levi_sleeping.png"},
                {"id": "eating", "label": "Eating Oatmeal", "sprite": "levi_eating.png"},
                {"id": "stretching", "label": "Stretching / Yawning", "sprite": "levi_stretching.png"},
                {"id": "arms_out_hug", "label": "Arms Out for Hug", "sprite": "levi_arms_out_hug.png"},
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
                {"id": "waving", "label": "Waving Hello", "sprite": "luca_waving.png"},
                {"id": "clapping", "label": "Clapping with Joy", "sprite": "luca_clapping.png"},
                {"id": "holding_toy", "label": "Hugging Teddy Bear", "sprite": "luca_holding_toy.png"},
                {"id": "sleeping", "label": "Sleeping (Star PJs)", "sprite": "luca_sleeping.png"},
                {"id": "eating", "label": "Eating Fruit", "sprite": "luca_eating.png"},
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
                {"id": "waving", "label": "👋 Waving Warmly", "sprite": "dad_waving.png"},
                {"id": "drinking", "label": "☕ Drinking Coffee", "sprite": "dad_drinking.png"},
                {"id": "teaching", "label": "📖 Teaching Storybook", "sprite": "dad_teaching.png"},
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
                {"id": "holding_fruit", "label": "🍎 Holding Fruit Snacks", "sprite": "mom_holding_fruit.png"},
                {"id": "teaching", "label": "📖 Teaching Storybook", "sprite": "mom_teaching.png"},
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
                {"id": "default", "label": "Default Sitting", "sprite": "dog_default.png"},
                {"id": "running", "label": "🐾 Bouncing & Running", "sprite": "dog_running.png"},
                {"id": "playing_ball", "label": "🎾 Playing with Red Ball", "sprite": "dog_playing_ball.png"},
                {"id": "eating_banana", "label": "🍌 Eating Sweet Banana", "sprite": "dog_eating_banana.png"}
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
    
    # Dynamically scan sprites for saved custom poses
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sprites_dir = os.path.join(project_root, "assets", "sprites")
    for char in chars:
        cid = char["id"]
        custom_files = glob.glob(os.path.join(sprites_dir, f"{cid}_custom_*.png"))
        for cf in sorted(custom_files):
            fname = os.path.basename(cf)
            pid = fname[len(cid)+1:-4]
            # Avoid duplicate if id or sprite filename already registered
            if not any(p["id"] == pid or p.get("sprite") == fname for p in char["poses"]):
                char["poses"].append({
                    "id": pid,
                    "label": f"✨ {pid.replace('_', ' ').title()}",
                    "sprite": fname
                })

    return {"characters": chars}

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

    path = os.path.join(sprites_dir, clean_name)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    
    # Match against multi-word character prefixes
    known_prefixes = [
        "grandparents_paternal",
        "grandparents_maternal",
        "auntie_cousins",
        "dad",
        "mom",
        "dog",
        "levi",
        "luca"
    ]
    char_prefix = None
    for pfx in known_prefixes:
        if clean_name.startswith(pfx):
            char_prefix = pfx
            break
    if not char_prefix:
        char_prefix = clean_name.split("_")[0]

    fallback_char = os.path.join(sprites_dir, f"{char_prefix}_default.png")
    if os.path.exists(fallback_char):
        return FileResponse(fallback_char, media_type="image/png")
        
    fallback_char_simple = os.path.join(sprites_dir, f"{char_prefix}.png")
    if os.path.exists(fallback_char_simple):
        return FileResponse(fallback_char_simple, media_type="image/png")
        
    # Global fallback only as absolute last resort
    return FileResponse(os.path.join(sprites_dir, "levi_default.png"), media_type="image/png")

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
        "backyard_garden": "🌻 Family Backyard Garden"
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
        "farm_field", "duck_pond", "backyard_garden"
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


