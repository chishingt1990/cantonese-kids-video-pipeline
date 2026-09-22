import os
import json
import shutil
import datetime
import uuid
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

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
    """Initializes ep01_meeting_family if projects directory is empty."""
    ep01_dir = os.path.join(PROJECTS_DIR, "ep01_meeting_family")
    p_file = os.path.join(ep01_dir, "project.json")
    if not os.path.exists(p_file):
        os.makedirs(ep01_dir, exist_ok=True)
        with open(p_file, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_EP01_DATA, f, indent=2, ensure_ascii=False)
        _render_simple_thumbnail(ep01_dir, "見到屋企人", "Meeting the Family")

def _render_simple_thumbnail(proj_dir: str, title_cn: str, title_en: str):
    """Renders a warm 640x360 cover card for the project."""
    thumb_path = os.path.join(proj_dir, "thumbnail.png")
    if os.path.exists(thumb_path):
        return
    img = Image.new("RGB", (640, 360), (255, 251, 235))
    draw = ImageDraw.Draw(img)
    # Warm pastel border
    draw.rounded_rectangle([12, 12, 628, 348], radius=24, fill=(254, 243, 199), outline=(245, 158, 11), width=3)
    img.save(thumb_path, "PNG")

def list_projects() -> List[Dict[str, Any]]:
    """Returns metadata summary for all projects on disk, sorted by updated_at descending."""
    ensure_seed_project()
    projects = []
    
    for item in os.listdir(PROJECTS_DIR):
        item_path = os.path.join(PROJECTS_DIR, item)
        if os.path.isdir(item_path):
            p_file = os.path.join(item_path, "project.json")
            if os.path.exists(p_file):
                try:
                    with open(p_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    p_id = data.get("id") or data.get("episode_id") or item
                    scenes = data.get("scenes", [])
                    has_video = False
                    
                    # Check if rendered video exists
                    rendered_video = data.get("rendered_video", {})
                    if rendered_video and rendered_video.get("filename"):
                        has_video = True
                    
                    thumb_path = os.path.join(item_path, "thumbnail.png")
                    has_thumb = os.path.exists(thumb_path)
                    
                    projects.append({
                        "id": p_id,
                        "title_cantonese": data.get("title_cantonese", "未命名項目"),
                        "title_english": data.get("title_english", "Untitled Project"),
                        "target_age": data.get("target_age", "1-2 years"),
                        "theme": data.get("theme", ""),
                        "scene_count": len(scenes),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "has_thumbnail": has_thumb,
                        "thumbnail_url": f"/api/projects/{p_id}/thumbnail" if has_thumb else None,
                        "has_rendered_video": has_video,
                        "rendered_video": rendered_video
                    })
                except Exception:
                    continue
                    
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return projects

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full project data by ID."""
    ensure_seed_project()
    p_dir = os.path.join(PROJECTS_DIR, project_id)
    p_file = os.path.join(p_dir, "project.json")
    if os.path.exists(p_file):
        with open(p_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_project(project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Saves or updates project state on disk."""
    ensure_seed_project()
    p_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(p_dir, exist_ok=True)
    
    # Ensure ID consistency and timestamp update
    data["id"] = project_id
    data["episode_id"] = project_id
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not data.get("created_at"):
        data["created_at"] = now_iso
    data["updated_at"] = now_iso
    
    p_file = os.path.join(p_dir, "project.json")
    with open(p_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    _render_simple_thumbnail(p_dir, data.get("title_cantonese", ""), data.get("title_english", ""))
    return data

def duplicate_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Clones an existing project into a new folder."""
    original = get_project(project_id)
    if not original:
        return None
        
    now = datetime.datetime.now(datetime.timezone.utc)
    new_id = f"proj_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    new_dir = os.path.join(PROJECTS_DIR, new_id)
    os.makedirs(new_dir, exist_ok=True)
    
    clone_data = dict(original)
    clone_data["id"] = new_id
    clone_data["episode_id"] = new_id
    clone_data["title_english"] = f"{original.get('title_english', 'Untitled')} (Copy)"
    clone_data["created_at"] = now.isoformat()
    clone_data["updated_at"] = now.isoformat()
    # Reset rendered video on clone
    clone_data.pop("rendered_video", None)
    
    p_file = os.path.join(new_dir, "project.json")
    with open(p_file, "w", encoding="utf-8") as f:
        json.dump(clone_data, f, indent=2, ensure_ascii=False)
        
    orig_thumb = os.path.join(PROJECTS_DIR, project_id, "thumbnail.png")
    copied = False
    if os.path.exists(orig_thumb):
        try:
            with open(orig_thumb, "rb") as rf:
                thumb_bytes = rf.read()
            with open(os.path.join(new_dir, "thumbnail.png"), "wb") as wf:
                wf.write(thumb_bytes)
            copied = True
        except Exception as e:
            logger.warning(f"Could not copy thumbnail directly: {e}")
            
    if not copied:
        _render_simple_thumbnail(new_dir, clone_data.get("title_cantonese", ""), clone_data.get("title_english", ""))
        
    return clone_data

def delete_project(project_id: str) -> bool:
    """Deletes a project folder from disk."""
    p_dir = os.path.join(PROJECTS_DIR, project_id)
    if os.path.exists(p_dir) and os.path.isdir(p_dir):
        shutil.rmtree(p_dir)
        return True
    return False

def get_thumbnail_path(project_id: str) -> Optional[str]:
    """Returns absolute path to project thumbnail if it exists."""
    thumb_path = os.path.join(PROJECTS_DIR, project_id, "thumbnail.png")
    if os.path.exists(thumb_path):
        return thumb_path
    return None
