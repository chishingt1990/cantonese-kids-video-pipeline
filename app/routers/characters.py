import json
import os
import shutil
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.storage import atomic_write_json, validate_id
from app.services import asset_manifest as assets
from app.services.background_generator import generate_iterative_background
from app.services.character_generator import generate_custom_character_sprite

router = APIRouter(prefix="/api/characters", tags=["characters"])


def _asset_response(loader, *args):
    try:
        path = loader(*args)
        return FileResponse(path, media_type="image/png")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/")
@router.get("/all")
def list_characters():
    return {"characters": assets.list_characters()}


@router.get("/sprite/{filename}")
def get_sprite(filename: str):
    return _asset_response(assets.resolve_sprite_filename, filename)


@router.get("/sprite/{char_id}/{pose_id}")
def get_sprite_by_char_pose(char_id: str, pose_id: str):
    return _asset_response(assets.resolve_sprite, char_id, pose_id)


@router.get("/backgrounds")
def list_backgrounds():
    backgrounds = assets.list_backgrounds()
    for bg in backgrounds:
        if not bg["is_core"]:
            metadata = assets.image_path("backgrounds", bg["filename"][:-4] + ".json")
            if metadata.is_file():
                bg["name"] = json.loads(metadata.read_text(encoding="utf-8"))["name"]
    return {"backgrounds": backgrounds}


@router.get("/background/{filename}")
def get_background(filename: str):
    bid = filename.removesuffix(".png").removeprefix("bg_")
    return _asset_response(assets.resolve_background, bid)


@router.delete("/background/{bg_id}")
def delete_background(bg_id: str):
    try:
        validate_id(bg_id)
        path = assets.resolve_background(bg_id)
        if not bg_id.startswith("custom_") or path.parent != assets.image_dir("backgrounds"):
            raise HTTPException(400, "Approved master artwork cannot be deleted.")
        path.unlink()
        assets.image_path("backgrounds", path.stem + ".json").unlink(missing_ok=True)
        return {"status": "deleted", "bg_id": bg_id}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


class OutfitPromptRequest(BaseModel):
    character_id: str
    prompt: str = Field(min_length=1, max_length=2000)

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value):
        if not value.strip():
            raise ValueError("Describe an available pose or recolor")
        return value.strip()


class SaveOutfitRequest(OutfitPromptRequest):
    preview_id: str


class BgPromptRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "prompt")
    @classmethod
    def nonblank_text(cls, value):
        if not value.strip():
            raise ValueError("Name and prompt cannot be blank")
        return value.strip()


class IterativeBgRequest(BgPromptRequest):
    history: list[str] = Field(default_factory=list, max_length=100)
    iteration: int = Field(default=1, ge=1, le=10000)


class SaveBgRequest(BgPromptRequest):
    preview_id: str
    iteration: int = Field(default=0, ge=0, le=10000)
    history: list[str] | None = Field(default=None, max_length=100)


def _preview_paths(preview_id):
    validate_id(preview_id)
    return (assets.image_path("previews", preview_id + ".png"),
            assets.image_path("previews", preview_id + ".json"))


def _read_preview(preview_id, kind):
    try:
        image, metadata = _preview_paths(preview_id)
        if not image.is_file() or not metadata.is_file():
            raise HTTPException(404, "Preview no longer exists; generate another preview.")
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if data["kind"] != kind or data["preview_id"] != preview_id:
            raise HTTPException(409, "Preview belongs to a different image request.")
        return image, data
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/preview/{preview_id}")
def get_preview(preview_id: str):
    try:
        image, metadata = _preview_paths(preview_id)
        if not image.is_file() or not metadata.is_file():
            raise HTTPException(404, "Preview not found")
        return FileResponse(image, media_type="image/png",
                            headers={"Cache-Control": "private, max-age=31536000, immutable"})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _generate_preview(kind, metadata, generate):
    preview_id = uuid.uuid4().hex
    image, sidecar = _preview_paths(preview_id)
    image.parent.mkdir(parents=True, exist_ok=True)
    pending = assets.image_path("previews", preview_id + ".pending.png")
    try:
        generate(str(pending))
        os.replace(pending, image)
        metadata.update(kind=kind, preview_id=preview_id, asset_id="custom_" + uuid.uuid4().hex)
        atomic_write_json(sidecar, metadata)
    except (ValueError, FileNotFoundError) as exc:
        image.unlink(missing_ok=True)
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        image.unlink(missing_ok=True)
        raise
    finally:
        pending.unlink(missing_ok=True)
    return {"status": "preview_ready", "preview_id": preview_id,
            "preview_url": f"/api/characters/preview/{preview_id}",
            "generation_method": "preset_transformation", **{
                k: v for k, v in metadata.items() if k in {"name", "character_id", "iteration"}
            }}


@router.post("/preview_outfit")
def preview_outfit(req: OutfitPromptRequest):
    return _generate_preview(
        "outfit", {"character_id": req.character_id, "prompt": req.prompt.strip()},
        lambda output: generate_custom_character_sprite(req.character_id, req.prompt, output),
    )


def _copy_immutable(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        return
    pending = destination.with_name(uuid.uuid4().hex + ".pending.png")
    try:
        shutil.copyfile(source, pending)
        os.replace(pending, destination)
    finally:
        pending.unlink(missing_ok=True)


@router.post("/save_outfit")
def save_outfit(req: SaveOutfitRequest):
    image, metadata = _read_preview(req.preview_id, "outfit")
    if (req.character_id != metadata["character_id"] or req.prompt.strip() != metadata["prompt"]):
        raise HTTPException(409, "Character or prompt changed after preview; preview again before saving.")
    pose_id = metadata["asset_id"]
    filename = f"{req.character_id}_{pose_id}.png"
    _copy_immutable(image, assets.image_path("sprites", filename))
    atomic_write_json(assets.image_path("sprites", filename[:-4] + ".json"),
                      {"label": req.prompt[:80], "preview_id": req.preview_id})
    return {"status": "saved", "preview_id": req.preview_id, "character_id": req.character_id,
            "pose_id": pose_id, "label": req.prompt[:80], "sprite_filename": filename,
            "sprite_url": f"/api/characters/sprite/{filename}"}


@router.post("/preview_background")
def preview_background(req: BgPromptRequest):
    return _generate_preview(
        "background", {"name": req.name, "prompt": req.prompt.strip(), "history": [], "iteration": 0},
        lambda output: generate_iterative_background(req.prompt, [], output),
    )


@router.post("/iterate_background")
def iterate_background(req: IterativeBgRequest):
    return _generate_preview(
        "background", {"name": req.name, "prompt": req.prompt.strip(),
                       "history": req.history, "iteration": req.iteration},
        lambda output: generate_iterative_background(req.prompt, req.history, output),
    )


@router.post("/save_background")
def save_background(req: SaveBgRequest):
    image, metadata = _read_preview(req.preview_id, "background")
    if (req.prompt.strip() != metadata["prompt"] or req.iteration != metadata["iteration"]
            or (req.history is not None and req.history != metadata["history"])):
        raise HTTPException(409, "Background prompt or version changed after preview.")
    bid = metadata["asset_id"]
    filename = f"bg_{bid}.png"
    _copy_immutable(image, assets.image_path("backgrounds", filename))
    atomic_write_json(assets.image_path("backgrounds", f"bg_{bid}.json"),
                      {"name": req.name, "preview_id": req.preview_id})
    return {"status": "saved", "preview_id": req.preview_id, "background_id": bid,
            "name": req.name, "filename": filename, "url": f"/api/characters/background/{filename}"}


@router.post("/custom_outfit")
def custom_outfit_alias(req: SaveOutfitRequest):
    return save_outfit(req)


@router.post("/custom_background")
def custom_background_alias(req: SaveBgRequest):
    return save_background(req)
