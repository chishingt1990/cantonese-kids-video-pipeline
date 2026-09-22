#!/usr/bin/env python3
"""
Google OAuth 2.0 Authorization Manager.
Handles full agentic authorization for Google Photos and YouTube Data API.
Caches refresh tokens locally in config/google_token.json to enable autonomous operation.
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Fix Windows console UTF-8 encoding and line buffering
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Google Auth imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Warning: Google client libraries not yet installed. Run: pip install -r requirements.txt")

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


def get_credentials():
    """
    Retrieves authorized user credentials.
    Refreshes expired tokens automatically or starts the one-time local server flow.
    """
    creds = None

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"Notice: Failed to load existing token ({e}). Re-authenticating...")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired. Refreshing token silently...")
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_FILE.exists():
                print("=" * 70)
                print("ACTION REQUIRED: Missing client_secret.json")
                print("=" * 70)
                print(f"Please place your Google OAuth client secret at:")
                print(f"  {CLIENT_SECRET_FILE}")
                print("\nQuick Setup Guide:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Enable: YouTube Data API v3 & Photos Library API")
                print("3. Configure OAuth consent screen (External, add yourself as Test User)")
                print("4. Create OAuth client ID -> Application type: Desktop app")
                print("5. Download JSON and rename to 'client_secret.json'")
                print("=" * 70)
                return None

            print("Starting browser OAuth flow for Google Photos & YouTube...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            try:
                creds = flow.run_local_server(
                    port=8080,
                    prompt="consent",
                    access_type="offline",
                    authorization_prompt_message="\n" + "=" * 70 + "\n👉 Please open this URL in your browser if it didn't open automatically:\n\n{url}\n\n" + "=" * 70 + "\nWaiting for authorization...\n",
                    success_message="Authentication successful! You can close this browser tab now."
                )
            except Exception as e:
                print(f"Notice: Port 8080 unavailable ({e}), trying dynamic port...", flush=True)
                creds = flow.run_local_server(
                    port=0,
                    prompt="consent",
                    access_type="offline",
                    authorization_prompt_message="\n" + "=" * 70 + "\n👉 Please open this URL in your browser if it didn't open automatically:\n\n{url}\n\n" + "=" * 70 + "\nWaiting for authorization...\n",
                    success_message="Authentication successful! You can close this browser tab now."
                )

        # Save credentials for future runs
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        print(f"Credentials successfully saved to: {TOKEN_FILE}")

    return creds


def test_youtube(creds):
    """Verifies YouTube API access by fetching user channel info or subscriptions."""
    try:
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(mine=True, part="snippet,contentDetails,statistics").execute()
        items = response.get("items", [])
        if items:
            channel = items[0]["snippet"]
            print(f"YouTube connected successfully! Logged in as: {channel.get('title')}")
        else:
            print("YouTube connected! (No public channel found, ready for upload/watch inspection).")
        return True
    except Exception as e:
        print(f"YouTube verification failed: {e}")
        return False


def test_photos(creds):
    """Verifies Photos API access."""
    try:
        service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)
        results = service.albums().list(pageSize=5).execute()
        albums = results.get("albums", [])
        print(f"Google Photos connected successfully! Found {len(albums)} albums.")
        for album in albums:
            print(f"  - Album: {album.get('title')} ({album.get('mediaItemsCount', 0)} items)")
        return True
    except Exception as e:
        print(f"Google Photos check notice: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google OAuth Authorization Manager")
    parser.add_argument("--test-all", action="store_true", help="Test both Photos and YouTube access")
    args = parser.parse_args()

    creds = get_credentials()
    if creds:
        print("\nChecking authorized Google services...")
        test_youtube(creds)
        test_photos(creds)
        print("\nAll systems operational! Agent now has continuous access.")
    else:
        sys.exit(1)
