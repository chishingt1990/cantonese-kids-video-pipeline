#!/usr/bin/env python3
"""
Photo Reference Extractor & Feature Cataloger.
Manages reference portraits for all family members and the family Shiba Inu.
Supports local directory organization and Google Photos picker imports.
"""

import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_PHOTOS_DIR = PROJECT_ROOT / "assets" / "raw_photos"

MEMBER_DIRS = [
    ("dad", "Dad (爸爸)"),
    ("mom", "Mom (媽媽)"),
    ("levi_older_brother", "Levi (Older Twin Brother / 哥哥)"),
    ("luca_younger_brother", "Luca (Younger Twin Brother / 細佬)"),
    ("grandparents_paternal", "Paternal Grandparents (爺爺 & 嫲嫲)"),
    ("grandparents_maternal", "Maternal Grandparents (公公 & 婆婆)"),
    ("aunt_and_cousins", "Auntie & Cousins (姑媽、表哥、表弟)"),
    ("dog", "Family Dog (狗狗 - 柴犬 Shiba Inu)"),
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}


def init_photo_folders():
    """Ensures dedicated folders exist for each family member."""
    RAW_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    for folder_key, label in MEMBER_DIRS:
        folder = RAW_PHOTOS_DIR / folder_key
        folder.mkdir(parents=True, exist_ok=True)
        readme = folder / "README.txt"
        if not readme.exists():
            readme.write_text(f"Drop 1-3 clear reference photos for {label} here.\nSupported formats: JPG, PNG, WEBP, HEIC.\n", encoding="utf-8")


def scan_photos():
    """Scans and reports the photo inventory for character generation."""
    init_photo_folders()
    print("=" * 70)
    print("📸 Family Portrait Reference Inventory")
    print("=" * 70)

    total_photos = 0
    status_summary = {}

    for folder_key, label in MEMBER_DIRS:
        folder = RAW_PHOTOS_DIR / folder_key
        photos = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
        count = len(photos)
        total_photos += count
        status_summary[folder_key] = count

        if count > 0:
            print(f"✅ {label:35s}: {count} photo(s) found")
            for p in photos[:3]:
                print(f"     - {p.name}")
        else:
            print(f"⏳ {label:35s}: 0 photos (drop into assets/raw_photos/{folder_key}/)")

    print("-" * 70)
    print(f"Total reference photos available: {total_photos}")
    print("=" * 70)
    return status_summary


if __name__ == "__main__":
    scan_photos()
