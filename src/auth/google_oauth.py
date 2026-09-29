#!/usr/bin/env python3
"""Explicit local YouTube authorization. Source-media import is not implemented."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow
from app.storage import atomic_write_json, project_lock
from app.services.youtube_service import (
    CLIENT_SECRET_FILE, TOKEN_FILE, SCOPES,
    get_credentials as cached_credentials, _youtube,
)


def get_credentials(allow_interactive=False):
    creds = cached_credentials()
    if creds or not allow_interactive:
        return creds
    if not CLIENT_SECRET_FILE.is_file():
        raise RuntimeError("Configure a Google OAuth desktop client before connecting.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), scopes=SCOPES)
    creds = flow.run_local_server(host="127.0.0.1", port=0, prompt="consent", access_type="offline")
    if not creds.has_scopes(SCOPES):
        raise RuntimeError("YouTube permissions were not granted.")
    with project_lock("google-credentials"):
        atomic_write_json(TOKEN_FILE, json.loads(creds.to_json()))
        try:
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass
    return creds


def test_youtube(creds):
    try:
        _youtube(creds).channels().list(mine=True, part="id").execute()
        return True
    except Exception:
        return False


def test_photos(creds):
    raise NotImplementedError("Google Photos source import requires a separate explicit Picker workflow; it is not available.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explicit local YouTube connection")
    parser.add_argument("--connect", action="store_true", help="Open browser consent if credentials are unavailable")
    parser.add_argument("--test-youtube", action="store_true", help="Explicitly call YouTube to verify this connection")
    args = parser.parse_args()
    credentials = get_credentials(allow_interactive=args.connect)
    if not credentials:
        print("Not connected. Use the studio or explicitly pass --connect.")
        sys.exit(1)
    if args.test_youtube and not test_youtube(credentials):
        print("YouTube verification failed. Reconnect or retry later.")
        sys.exit(1)
    print("YouTube credentials available. No Photos or source-import capability is implied.")
