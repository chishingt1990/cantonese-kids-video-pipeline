import os
import json
import logging
import threading
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.services.ai_service import generate_ai_text
from app.services import project_service

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]

UPLOAD_JOBS: Dict[str, Dict[str, Any]] = {}

def get_credentials() -> Optional[Credentials]:
    """Loads and validates cached Google OAuth credentials."""
    if not TOKEN_FILE.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        return creds if creds and creds.valid else None
    except Exception as e:
        logger.warning(f"Failed to load or refresh Google OAuth token: {e}")
        return None

def get_channel_info() -> Dict[str, Any]:
    """Returns connected YouTube channel metadata or connected=False."""
    creds = get_credentials()
    if not creds:
        return {"connected": False}
    try:
        youtube = build("youtube", "v3", credentials=creds)
        res = youtube.channels().list(mine=True, part="snippet,statistics").execute()
        items = res.get("items", [])
        if not items:
            return {"connected": True, "channel": {"title": "Connected Account", "avatar": ""}}
        ch = items[0]
        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        thumb = snippet.get("thumbnails", {}).get("default", {}).get("url", "")
        return {
            "connected": True,
            "channel": {
                "id": ch.get("id"),
                "title": snippet.get("title", "YouTube Channel"),
                "description": snippet.get("description", ""),
                "avatar": thumb,
                "subscribers": stats.get("subscriberCount", "0"),
                "video_count": stats.get("videoCount", "0")
            }
        }
    except Exception as e:
        logger.error(f"Error checking YouTube channel info: {e}")
        return {"connected": False, "error": str(e)}

def get_auth_url(redirect_uri: str) -> str:
    """Creates Google OAuth authorization URL for the web studio."""
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(f"Missing client secrets file: {CLIENT_SECRET_FILE}")
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return auth_url

def exchange_code_for_token(code: str, redirect_uri: str) -> bool:
    """Exchanges one-time authorization code for token and saves to config/google_token.json."""
    try:
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        return True
    except Exception as e:
        logger.error(f"Failed to exchange OAuth code: {e}")
        return False

def disconnect_channel() -> bool:
    """Revokes / removes cached google_token.json."""
    if TOKEN_FILE.exists():
        try:
            os.remove(TOKEN_FILE)
            return True
        except Exception:
            pass
    return False

def generate_ai_metadata(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates YouTube preschool metadata: Title, Description with timestamps, and SEO tags."""
    title_cn = project_data.get("title_cantonese", "廣東話幼兒教學")
    title_en = project_data.get("title_english", "Cantonese Kids Learning")
    age = project_data.get("target_age", "1-3 years")
    theme = project_data.get("theme", "Preschool Fun")
    moral = project_data.get("moral_lesson", "")
    vocab_list = project_data.get("vocab_words", [])
    scenes = project_data.get("scenes", [])

    # Calculate mathematical timestamps
    timestamps = []
    accum_sec = 0
    for idx, s in enumerate(scenes):
        m = int(accum_sec // 60)
        sec = int(accum_sec % 60)
        s_title = s.get("title") or f"Scene {idx + 1}"
        s_cn = s.get("cantonese") or ""
        timestamps.append(f"{m:02d}:{sec:02d} - {s_title} ({s_cn[:8]}...)")
        accum_sec += float(s.get("duration_sec", 6))

    timestamp_str = "\n".join(timestamps)
    vocab_str = ", ".join([f"{v.get('chinese', '')} ({v.get('english', '')})" for v in vocab_list])

    prompt = f"""You are a YouTube SEO and preschool education expert for overseas Cantonese-speaking families.
Generate the optimal YouTube metadata for this children's educational video:

Episode Title: {title_cn} ({title_en})
Target Age: {age}
Lesson Theme: {theme}
Moral Lesson: {moral}
Target Vocabulary: {vocab_str}

Calculated Scene Chapters:
{timestamp_str}

Return ONLY a valid JSON object matching this schema:
{{
  "title": "{title_cn} {title_en} | 幼兒廣東話兒歌教學 (Cantonese for Kids)",
  "description": "Engaging 2-paragraph preschool description with cultural warmth, followed by timestamps and vocab list",
  "tags": ["粵語兒歌", "幼兒廣東話", "學廣東話", "Cantonese for kids", "Hong Kong Cantonese", "Preschool Cantonese"]
}}
"""
    try:
        raw = generate_ai_text(prompt, "You are a specialized YouTube preschool video metadata generator.")
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        data = json.loads(cleaned.strip())
        
        # Ensure calculated timestamps are included in description
        if "00:00" not in data.get("description", ""):
            data["description"] = f"{data.get('description', '')}\n\n⏱️ Timestamps:\n{timestamp_str}\n\n🔤 Vocabulary:\n{vocab_str}\n\n#CantoneseForKids #幼兒廣東話 #LearnCantonese"
        return data
    except Exception as e:
        logger.warning(f"AI metadata generation fallback: {e}")
        desc = (
            f"🌟 {title_cn} ({title_en})\n"
            f"Fun and gentle preschool Cantonese learning for toddlers aged {age}!\n\n"
            f"⏱️ Timestamps:\n{timestamp_str}\n\n"
            f"🔤 Vocabulary Highlights:\n{vocab_str}\n\n"
            f"❤️ Moral Lesson: {moral}\n\n"
            f"#CantoneseForKids #幼兒廣東話 #粵語兒歌 #BilingualPreschool"
        )
        return {
            "title": f"{title_cn} {title_en} | 幼兒廣東話兒歌教學 (Cantonese for Kids)",
            "description": desc,
            "tags": [
                "粵語兒歌", "幼兒廣東話", "學廣東話", "Cantonese for kids",
                "Hong Kong Cantonese", "Preschool Cantonese", "Bilingual Kids", "Twin Toddlers"
            ]
        }

def extract_scene_frames(project_id: str, video_path: str) -> List[str]:
    """Extracts high-quality 16:9 thumbnail frame candidates from rendered video using FFmpeg."""
    frames_dir = PROJECT_ROOT / "projects" / project_id / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(video_path):
        return []

    # Extract 4 representative frames at 1s, 7s, 15s, 22s
    frame_files = []
    for idx, sec in enumerate([1.5, 8.0, 16.0, 24.0]):
        out_f = frames_dir / f"frame_{idx + 1}.jpg"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            str(out_f)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if out_f.exists():
                frame_files.append(f"/api/youtube/frame/{project_id}/frame_{idx + 1}.jpg")
        except Exception:
            continue
            
    return frame_files

def start_youtube_upload(
    job_id: str,
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: str = "unlisted",
    made_for_kids: bool = True,
    thumbnail_path: Optional[str] = None
):
    """Starts background resumable upload to YouTube."""
    UPLOAD_JOBS[job_id] = {
        "status": "uploading",
        "progress": 5,
        "video_id": None,
        "url": None,
        "error": None
    }

    def _worker():
        try:
            creds = get_credentials()
            if not creds:
                raise RuntimeError("Not authorized. Please connect your YouTube account in Step 5.")
                
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags[:30],
                    "categoryId": "27"  # Education
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": made_for_kids,
                    "embeddable": True
                }
            }

            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024 * 2,  # 2MB chunks
                resumable=True
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 85) + 5
                    UPLOAD_JOBS[job_id]["progress"] = pct

            video_id = response.get("id")
            video_url = f"https://youtu.be/{video_id}"
            UPLOAD_JOBS[job_id]["video_id"] = video_id
            UPLOAD_JOBS[job_id]["url"] = video_url
            UPLOAD_JOBS[job_id]["progress"] = 92

            # Upload custom thumbnail if specified
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                except Exception as e:
                    logger.warning(f"Could not upload custom thumbnail: {e}")

            UPLOAD_JOBS[job_id]["progress"] = 100
            UPLOAD_JOBS[job_id]["status"] = "complete"

        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            UPLOAD_JOBS[job_id]["status"] = "error"
            UPLOAD_JOBS[job_id]["error"] = str(e)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
