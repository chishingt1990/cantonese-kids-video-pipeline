import os
import shutil
from pathlib import Path

try:
    from scripts.maintenance_guard import PROJECT_ROOT, configure_cli, output_path
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from maintenance_guard import PROJECT_ROOT, configure_cli, output_path

from app.utils.sprite_isolator import isolate_sprite_from_white_bg

CHAR_DIR = PROJECT_ROOT / "assets" / "characters"
SPRITE_DIR = PROJECT_ROOT / "assets" / "sprites"
brain_dir = Path(r"C:\Users\chish\.gemini\antigravity\brain\706d91eb-30af-4825-a9a0-115b05e85ba1")

# 2. Function to create clean RGBA cutouts with soft anti-aliased alpha borders
def create_clean_sprite(src_path, dst_path, is_dog=False):
    isolate_sprite_from_white_bg(
        str(src_path), str(output_path(dst_path)), threshold=10 if is_dog else 15
    )

characters = [
    ('dad_cartoon.jpg', 'dad.png', False),
    ('mom_cartoon.jpg', 'mom.png', False),
    ('levi_cartoon.jpg', 'levi.png', False),
    ('luca_cartoon.jpg', 'luca.png', False),
    ('dog_cartoon.jpg', 'dog.png', True),
    ('grandparents_paternal_cartoon.jpg', 'grandparents_paternal.png', False),
    ('grandparents_maternal_cartoon.jpg', 'grandparents_maternal.png', False),
    ('auntie_cousins_cartoon.jpg', 'auntie_cousins.png', False)
]

def main(argv=None):
    configure_cli(argv)
    candidate_sources = {}
    for concept, master in (
        ("levi_style_aligned_opt2.jpg", "levi_cartoon.jpg"),
        ("luca_style_aligned_final.jpg", "luca_cartoon.jpg"),
    ):
        # Master replacements remain candidates even when derived sprites are promoted.
        candidate = output_path(CHAR_DIR / master, promote=False)
        shutil.copy(brain_dir / concept, candidate)
        candidate_sources[master] = candidate
    print("Staged Levi and Luca master candidates; canonical masters unchanged")

    for src, dst, is_dog in characters:
        src_full = candidate_sources.get(src, CHAR_DIR / src)
        dst_full = SPRITE_DIR / dst
        if os.path.exists(src_full):
            create_clean_sprite(src_full, dst_full, is_dog)
        else:
            print(f"Warning: {src_full} not found")

    print("All character sprites created successfully!")

if __name__ == "__main__":
    main()
