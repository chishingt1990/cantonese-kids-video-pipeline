#!/usr/bin/env python3
"""
YouTube Cantonese Children's Content & Watch History Inspector.
Connects to YouTube Data API to analyze watched or popular Cantonese educational videos,
extracting animation styles, visual framing, vocabulary pacing, and musical elements.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from googleapiclient.discovery import build
    from src.auth.google_oauth import get_credentials
except ImportError:
    pass

OUTPUT_STYLES_FILE = PROJECT_ROOT / "config" / "youtube_style_insights.json"


# Curated benchmark knowledge base of top Cantonese preschool animation channels on YouTube
BENCHMARK_CHANNELS = {
    "dimdim_cantonese": {
        "channel_name": "Uncle Germ / 點點話 (DimDim)",
        "style_category": "2D Chibi / Cute Sticker Flashcard",
        "visual_features": [
            "1:2 toddler-proportioned characters with oversized expressive heads",
            "Crisp bold outlines with soft pastel fills",
            "Floating flashcard words with Traditional Chinese + clear Jyutping",
            "Clean uncluttered backgrounds so babies focus on the subject",
            "Gentle bounce and wobble animations on vocal syllables"
        ],
        "audio_features": [
            "Slow, exaggerated parentese (infant-directed speech)",
            "Playful xylophone and gentle acoustic guitar background music",
            "Sound effects (ding, pop, sparkle) paired with each key word"
        ],
        "recommended_for": "Daily objects, family names, basic actions for under-2-year-olds"
    },
    "baobao_cantonese": {
        "channel_name": "BaoBao Learn Cantonese",
        "style_category": "Modern Minimalist Vector & Storybook",
        "visual_features": [
            "Flat vector aesthetics similar to modern Scandinavian children's books",
            "High color contrast (deep navy, sunflower yellow, mint green)",
            "Side-by-side Cantonese characters, Jyutping, and English subtitles"
        ],
        "audio_features": [
            "Authentic Hong Kong colloquial Cantonese",
            "Call-and-response repetition ('Where is Dad? 爸爸喺邊度呀？')"
        ],
        "recommended_for": "Sentence patterns, interactive search-and-find scenes"
    },
    "babybus_cantonese": {
        "channel_name": "BabyBus Cantonese (寶寶巴士 粵語)",
        "style_category": "2.5D Soft Felt / Rounded Chibi",
        "visual_features": [
            "Tactile rounded characters resembling soft plush toys",
            "Vibrant saturated colors that capture infant visual attention",
            "High kinetic energy and dynamic camera movements"
        ],
        "audio_features": [
            "Catchy repetitive nursery rhymes and musical hooks",
            "Character voice acting with distinct vocal timbres"
        ],
        "recommended_for": "Songs, routines (brushing teeth, bath time, mealtime)"
    },
    "peppa_pig_cantonese": {
        "channel_name": "Peppa Pig Cantonese Dub (粉紅豬小妹 粵語)",
        "style_category": "Minimalist 2D Profile Cutout",
        "visual_features": [
            "2D flat cutout characters with constant side-view eye alignment",
            "Simple primary color blocks without shading or gradients",
            "Charming, childlike geometric line art"
        ],
        "audio_features": [
            "Everyday family dialogue, funny snorts, laughter, wholesome everyday humor"
        ],
        "recommended_for": "Family dynamics, sibling interactions, garden play"
    }
}


def inspect_youtube_user_data(creds):
    """
    Checks user's playlists, subscriptions, and liked videos for Cantonese children's channels.
    """
    if not creds:
        print("No active OAuth credentials found. Running in benchmark knowledge-base mode.", flush=True)
        return {"benchmarks": BENCHMARK_CHANNELS}

    try:
        youtube = build("youtube", "v3", credentials=creds)
        print("Querying YouTube account for subscriptions, playlists, and liked videos...", flush=True)

        found_items = []
        keywords = ["粵語", "廣東話", "Cantonese", "兒歌", "寶寶", "BB", "Kids", "Baby", "童謠", "Little", "Story", "故事", "DimDim", "點點", "CoCo", "Super", "JoJo"]

        # 1. Inspect Subscriptions
        try:
            subs_resp = youtube.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=50
            ).execute()
            print(f"Inspecting {len(subs_resp.get('items', []))} channel subscriptions...", flush=True)
            for item in subs_resp.get("items", []):
                title = item["snippet"]["title"]
                desc = item["snippet"].get("description", "")
                full_text = title + " " + desc
                if any(k.lower() in full_text.lower() for k in keywords):
                    found_items.append({
                        "type": "subscribed_channel",
                        "title": title,
                        "description": desc[:150],
                        "channel_id": item["snippet"]["resourceId"]["channelId"]
                    })
        except Exception as e:
            print(f"Notice (Subscriptions): {e}", flush=True)

        # 2. Inspect Playlists
        try:
            playlists_resp = youtube.playlists().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=25
            ).execute()
            print(f"Inspecting {len(playlists_resp.get('items', []))} playlists...", flush=True)
            for item in playlists_resp.get("items", []):
                title = item["snippet"]["title"]
                desc = item["snippet"].get("description", "")
                full_text = title + " " + desc
                found_items.append({
                    "type": "playlist",
                    "title": title,
                    "item_count": item["contentDetails"]["itemCount"]
                })
        except Exception as e:
            print(f"Notice (Playlists): {e}", flush=True)

        # 3. Inspect Liked Videos ("LL")
        try:
            liked_resp = youtube.playlistItems().list(
                part="snippet",
                playlistId="LL",
                maxResults=50
            ).execute()
            print(f"Inspecting {len(liked_resp.get('items', []))} recent liked videos...", flush=True)
            for item in liked_resp.get("items", []):
                title = item["snippet"]["title"]
                channel = item["snippet"].get("videoOwnerChannelTitle", "")
                full_text = title + " " + channel
                if any(k.lower() in full_text.lower() for k in keywords):
                    found_items.append({
                        "type": "liked_video",
                        "title": title,
                        "channel": channel
                    })
        except Exception as e:
            print(f"Notice (Liked Videos): {e}", flush=True)

        return {"user_discoveries": found_items, "benchmarks": BENCHMARK_CHANNELS}

    except Exception as e:
        print(f"Error querying YouTube API: {e}", flush=True)
        return {"benchmarks": BENCHMARK_CHANNELS}


def save_insights(data):
    """Saves style insights to JSON."""
    OUTPUT_STYLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_STYLES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Style insights written to: {OUTPUT_STYLES_FILE}")


if __name__ == "__main__":
    creds = None
    try:
        from src.auth.google_oauth import get_credentials
        creds = get_credentials()
    except Exception:
        pass

    insights = inspect_youtube_user_data(creds)
    save_insights(insights)
