import os
import json
import shutil
import datetime
import uuid
import copy
import logging
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw
from app.storage import PROJECTS_DIR, project_path, project_lock, project_is_busy, atomic_write_json, validate_id, contained_path
from app.models import ProjectData

logger = logging.getLogger(__name__)


class RevisionConflict(ValueError):
    pass


class ProjectCorruptError(ValueError):
    pass

DEFAULT_EP01_DATA = {
    "id": "ep01_meeting_family",
    "episode_id": "ep01_meeting_family",
    "title_cantonese": "見到屋企人",
    "title_english": "Meeting the Family",
    "target_age": "1-2 years",
    "theme": "Family & Greetings",
    "moral_lesson": "Family members give us love, warm hugs, and comfort every day.",
    "created_at": "2026-09-01T10:00:00Z",
    "updated_at": "2026-09-20T12:00:00Z",
    "version": 1,
    "_autoDirected": True,
    "vocab_words": [
        {"chinese": "屋企人", "english": "Family"},
        {"chinese": "爸爸 / 媽媽", "english": "Dad / Mom"},
        {"chinese": "哥哥 / 細佬", "english": "Big Brother / Little Brother"},
        {"chinese": "狗狗", "english": "Doggy"}
    ],
    "subtitle_options": {
        "pill_style": "warm_cream",
        "font_size_cn": 52,
        "font_size_en": 26
    },
    "scenes": [
        {
            "scene_number": 1,
            "title": "Hello Sweet Babies!",
            "background": "living_room",
            "speaker": "Dad",
            "characters": [
                {"name": "dad", "pose": "default", "scale": 1.0, "x_percent": 50, "y_percent": 88, "flip": False, "layer": 1}
            ],
            "stickers": [
                {"id": "badge_good_morning", "type": "word", "content": "早晨", "english": "Good morning", "color_theme": "gold", "x_percent": 50, "y_percent": 22, "scale": 1.05, "rotation_deg": 0, "layer": 2}
            ],
            "cantonese": "Hello 兩個BB！今日爸爸同你哋一齊見下屋企人啦！",
            "english": "Hello sweet babies! Today Dad will introduce our whole family to you!",
            "vocab_highlight": "屋企人",
            "duration_sec": 7,
            "audio_url": "/api/audio/clip/scene_01_voice.wav"
        },
        {
            "scene_number": 2,
            "title": "Gentle Morning Hugs",
            "background": "living_room",
            "speaker": "Mom",
            "characters": [
                {"name": "levi", "pose": "arms_out_hug", "scale": 1.0, "x_percent": 34, "y_percent": 88, "flip": False, "layer": 1},
                {"name": "luca", "pose": "waving", "scale": 1.0, "x_percent": 66, "y_percent": 88, "flip": True, "layer": 1}
            ],
            "stickers": [
                {"id": "badge_big_hug", "type": "word", "content": "抱抱", "english": "Big hug", "color_theme": "pink", "x_percent": 50, "y_percent": 22, "scale": 1.05, "rotation_deg": 0, "layer": 2}
            ],
            "cantonese": "早晨呀 Levi 同 Luca！哥哥同細佬抱抱啦！",
            "english": "Good morning Levi and Luca! Big brother and little brother give warm hugs!",
            "vocab_highlight": "哥哥 / 細佬",
            "duration_sec": 7,
            "audio_url": "/api/audio/clip/scene_02_voice.wav"
        },
        {
            "scene_number": 3,
            "title": "Friendly Puppy Waves",
            "background": "living_room",
            "speaker": "Child",
            "characters": [
                {"name": "dog", "pose": "default", "scale": 1.0, "x_percent": 50, "y_percent": 88, "flip": False, "layer": 1}
            ],
            "stickers": [
                {"id": "badge_dog", "type": "word", "content": "狗狗", "english": "Doggy", "color_theme": "amber", "x_percent": 50, "y_percent": 22, "scale": 1.05, "rotation_deg": 0, "layer": 2}
            ],
            "cantonese": "汪汪！狗狗搖尾巴，好開心咁行埋嚟同大家打招呼！",
            "english": "Woof woof! Doggy wags tail happily coming over to say hello to everyone!",
            "vocab_highlight": "狗狗",
            "duration_sec": 6,
            "audio_url": "/api/audio/clip/scene_03_voice.wav"
        },
        {
            "scene_number": 4,
            "title": "Paternal Grandparents Smile",
            "background": "living_room",
            "speaker": "Dad",
            "characters": [
                {"name": "grandparents_paternal", "pose": "drinking_tea", "scale": 1.0, "x_percent": 50, "y_percent": 88, "flip": False, "layer": 1}
            ],
            "stickers": [
                {"id": "badge_grandparents", "type": "word", "content": "爺爺 嫲嫲", "english": "Grandparents", "color_theme": "rose", "x_percent": 50, "y_percent": 22, "scale": 1.05, "rotation_deg": 0, "layer": 2}
            ],
            "cantonese": "爺爺同嫲嫲飲緊熱茶，笑瞇瞇咁望住兩個乖孫！",
            "english": "Grandpa and Grandma are sipping warm tea, smiling warmly at their sweet grandsons!",
            "vocab_highlight": "屋企人",
            "duration_sec": 8,
            "audio_url": "/api/audio/clip/scene_04_voice.wav"
        },
        {
            "scene_number": 5,
            "title": "Big Warm Family Hug",
            "background": "living_room",
            "speaker": "Mom",
            "characters": [
                {"name": "levi", "pose": "waving", "scale": 1.0, "x_percent": 22, "y_percent": 88, "flip": False, "layer": 1},
                {"name": "dad", "pose": "kneeling", "scale": 1.0, "x_percent": 40, "y_percent": 88, "flip": False, "layer": 1},
                {"name": "mom", "pose": "kneeling_hug", "scale": 1.0, "x_percent": 60, "y_percent": 88, "flip": True, "layer": 1},
                {"name": "luca", "pose": "clapping", "scale": 1.0, "x_percent": 78, "y_percent": 88, "flip": True, "layer": 1}
            ],
            "stickers": [
                {"id": "badge_family_love", "type": "word", "content": "幸福一家", "english": "Happy Family", "color_theme": "gold", "x_percent": 50, "y_percent": 22, "scale": 1.1, "rotation_deg": 0, "layer": 2}
            ],
            "cantonese": "一家人齊齊整整、相親相愛，一齊講聲：我愛你！",
            "english": "The whole family united in warmth and love, saying together: We love you!",
            "vocab_highlight": "屋企人",
            "duration_sec": 8,
            "audio_url": "/api/audio/clip/scene_05_voice.wav"
        }
    ]
}

def ensure_seed_project():
    """Compatibility hook: reads never seed or restore deleted user projects."""
    return None

def _render_simple_thumbnail(proj_dir: str, title_cn: str, title_en: str):
    """Renders a warm 640x360 cover card for the project."""
    thumb_path = contained_path(proj_dir, "thumbnail.png")
    if os.path.exists(thumb_path):
        return
    img = Image.new("RGB", (640, 360), (255, 251, 235))
    draw = ImageDraw.Draw(img)
    # Warm pastel border
    draw.rounded_rectangle([12, 12, 628, 348], radius=24, fill=(254, 243, 199), outline=(245, 158, 11), width=3)
    img.save(thumb_path, "PNG")

def list_projects() -> List[Dict[str, Any]]:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if not item.is_dir():
            continue
        try:
            data = get_project(item.name)
            if data is None:
                continue
            has_thumb = get_thumbnail_path(item.name) is not None
            projects.append({
                **{key: data.get(key, "") for key in ("id", "title_cantonese", "title_english", "target_age", "theme", "created_at", "updated_at", "revision")},
                "scene_count": len(data["scenes"]),
                "has_thumbnail": has_thumb,
                "thumbnail_url": f"/api/projects/{item.name}/thumbnail" if has_thumb else None,
                "has_rendered_video": bool(data.get("rendered_video")),
                "rendered_video": data.get("rendered_video"),
                "migration_warnings": data.get("migration_warnings", []),
            })
        except (ValueError, OSError):
            projects.append({"id": item.name, "title_english": "Unreadable project — original preserved", "error": "project_unreadable", "scene_count": 0, "updated_at": ""})
    return sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)


def _sanitize_media(data: dict, project_id: str) -> dict:
    data = copy.deepcopy(data)
    warnings = list(data.get("migration_warnings", [])) if isinstance(data.get("migration_warnings"), list) else []

    def clean(value):
        if isinstance(value, dict):
            for key in list(value):
                item = value[key]
                if key in {"audio_url", "master_audio_url", "video_url"} and item:
                    prefix = f"/api/render/video/{project_id}/" if key == "video_url" else f"/api/audio/clip/{project_id}/"
                    valid = isinstance(item, str) and item.startswith(prefix)
                    if valid:
                        try:
                            filename = item[len(prefix):]
                            if any(c in filename for c in "\\%?#") or "/" in filename:
                                raise ValueError()
                            folder = "audio" if item.startswith("/api/audio/") else "renders"
                            valid = project_path(project_id, folder, filename).is_file()
                        except ValueError:
                            valid = False
                    if not valid:
                        value.pop(key, None)
                        warnings.append("Unowned or missing legacy media reference removed; regenerate this project's audio/render.")
                else:
                    clean(item)
        elif isinstance(value, list):
            for item in value:
                clean(item)

    clean(data)
    rendered = data.get("rendered_video")
    if rendered:
        try:
            filename = rendered["filename"]
            if not isinstance(filename, str) or any(c in filename for c in "/\\"):
                raise ValueError()
            if not rendered.get("input_fingerprint") or not project_path(project_id, "renders", filename).is_file():
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            data.pop("rendered_video", None)
            warnings.append("Legacy or missing render removed; render this project before publishing.")
    if warnings:
        data["migration_warnings"] = list(dict.fromkeys(str(w) for w in warnings))
    return data

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    with project_lock(project_id):
        path = project_path(project_id, "project.json")
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw = _sanitize_media(raw, project_id)
            data = ProjectData.model_validate(raw).model_dump(mode="json", exclude_none=True)
            data["id"] = data["episode_id"] = project_id
            return data
        except (ValueError, TypeError, AttributeError) as exc:
            raise ProjectCorruptError("Project data is unreadable; the original file has been preserved") from exc

def save_project(project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    with project_lock(project_id):
        data = ProjectData.model_validate(_sanitize_media(data, project_id)).model_dump(mode="json", exclude_none=True)
        current = get_project(project_id)
        revision = current.get("revision", 0) if current else 0
        if data["revision"] != revision:
            raise RevisionConflict("Project changed since it was loaded. Reload before saving.")
        data["id"] = data["episode_id"] = project_id
        data["revision"] = revision + 1
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data["created_at"] = (current or {}).get("created_at") or data.get("created_at") or now_iso
        data["updated_at"] = now_iso
        atomic_write_json(project_path(project_id, "project.json"), data)
        try:
            _render_simple_thumbnail(str(project_path(project_id)), data["title_cantonese"], data["title_english"])
        except (OSError, ValueError):
            logger.warning("Project saved, but thumbnail creation failed")
        return data

def duplicate_project(project_id: str) -> Optional[Dict[str, Any]]:
    original = get_project(project_id)
    if not original:
        return None
    new_id = f"proj_{uuid.uuid4().hex}"
    clone_data = copy.deepcopy(original)
    clone_data["title_english"] = f"{original.get('title_english', 'Untitled')} (Copy)"
    clone_data["revision"] = 0
    clone_data["created_at"] = ""
    clone_data.pop("rendered_video", None)
    return save_project(new_id, clone_data)

def delete_project(project_id: str) -> bool:
    with project_lock(project_id):
        if project_is_busy(project_id):
            raise RevisionConflict("This project has active media work. Wait for completion or cancel it before deleting.")
        p_dir = project_path(project_id)
        if p_dir.is_dir():
            # A local recoverable trash folder avoids irrevocable accidental deletion.
            trash = contained_path(PROJECTS_DIR.parent, "trash", f"{project_id}_{uuid.uuid4().hex}")
            trash.parent.mkdir(parents=True, exist_ok=True)
            p_dir.rename(trash)
            return True
        return False

def get_thumbnail_path(project_id: str) -> Optional[str]:
    path = project_path(project_id, "thumbnail.png")
    return str(path) if path.is_file() else None
