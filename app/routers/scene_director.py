import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.scene_director_service import (
    auto_direct_entire_project,
    direct_single_scene,
    apply_copilot_tweak
)
from app.services.sticker_service import (
    STICKER_CATALOG,
    get_all_stickers_catalog,
    get_or_render_sticker,
    STICKER_DIR
)

router = APIRouter(prefix="/api/scene-director", tags=["scene-director"])

class ProjectDirectRequest(BaseModel):
    project: Dict[str, Any]

@router.post("/auto-direct")
def auto_direct_project(req: ProjectDirectRequest):
    """Auto-directs all scenes in a project using visual intelligence."""
    try:
        directed_scenes = auto_direct_entire_project(req.project)
        return {
            "status": "success",
            "scenes": directed_scenes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SingleSceneDirectRequest(BaseModel):
    scene: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

@router.post("/direct-scene")
def direct_scene(req: SingleSceneDirectRequest):
    """Directs a single scene."""
    try:
        plan = direct_single_scene(req.scene, req.context)
        return {
            "status": "success",
            "plan": plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CopilotTweakRequest(BaseModel):
    scene: Dict[str, Any]
    instruction: str

@router.post("/copilot-tweak")
def copilot_tweak(req: CopilotTweakRequest):
    """Applies an instant natural language tweak to the scene."""
    try:
        updated_scene = apply_copilot_tweak(req.scene, req.instruction)
        return {
            "status": "success",
            "scene": updated_scene
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Stickers Router endpoints
@router.get("/stickers/catalog")
def list_stickers():
    """Returns dynamic catalog of all educational puffy stickers and props."""
    return {"stickers": get_all_stickers_catalog()}

@router.get("/stickers/render/{sticker_id}")
def render_sticker_image(sticker_id: str):
    """Returns transparent PNG of the requested sticker, generating if needed."""
    clean_id = os.path.basename(sticker_id.split("?")[0].replace(".png", ""))
    
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    # Check if exact PNG file exists on disk
    direct_candidates = [
        os.path.join(STICKER_DIR, f"{clean_id}.png"),
        os.path.join(STICKER_DIR, f"prop_{clean_id.replace('prop_', '')}.png"),
        os.path.join(STICKER_DIR, f"badge_{clean_id.replace('badge_', '')}.png"),
        os.path.join(STICKER_DIR, f"block_{clean_id.replace('block_', '')}.png")
    ]
    for cand in direct_candidates:
        if os.path.exists(cand):
            return FileResponse(cand, media_type="image/png", headers=no_cache_headers)
            
    all_catalog = get_all_stickers_catalog()
    match = next((s for s in all_catalog if s["id"] == clean_id), None)
    
    if match:
        path = get_or_render_sticker(match)
    else:
        # Custom on-the-fly badge
        path = get_or_render_sticker({"id": clean_id, "type": "word", "chinese": clean_id, "english": ""})

    if os.path.exists(path):
        return FileResponse(path, media_type="image/png", headers=no_cache_headers)
    raise HTTPException(status_code=404, detail="Sticker not found")

