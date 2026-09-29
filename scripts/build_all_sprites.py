import os
from PIL import Image

try:
    from scripts.maintenance_guard import PROJECT_ROOT, configure_cli, output_path as guarded_output_path
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from maintenance_guard import PROJECT_ROOT, configure_cli, output_path as guarded_output_path

from app.utils.sprite_isolator import isolate_sprite_from_white_bg

SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
CHAR_DIR = os.path.join(PROJECT_ROOT, "assets", "characters")
BRAIN_DIR = r"C:\Users\chish\.gemini\antigravity\brain\f340737b-7662-449f-a19e-c09b4ce0f071"

def isolate_sprite(image_path: str, output_path: str, threshold: int = 35) -> str:
    return isolate_sprite_from_white_bg(
        image_path, str(guarded_output_path(output_path)), threshold=threshold
    )

def main(argv=None):
    configure_cli(argv)
    print("=== Processing High-Fidelity Concepts into Sprites ===")
    
    # 1. Map generated concepts to sprite targets
    concept_map = {
        "levi_sad_concept_1790105472217.jpg": "levi_sad.png",
        "levi_holding_book_concept_1790105497347.jpg": "levi_holding_book.png",
        "levi_thinking_concept_1790105530318.jpg": "levi_thinking.png",
        "levi_sitting_floor_concept_1790105686447.jpg": "levi_sitting_floor.png",
        "luca_crying_concept_1790105798935.jpg": "luca_crying.png",
        "luca_pointing_concept_1790105903717.jpg": "luca_pointing.png",
        "luca_sitting_floor_concept_1790105918167.jpg": "luca_sitting_floor.png",
        "dad_comforting_hug_concept_1790105931858.jpg": "dad_comforting_hug.png",
        "dad_clapping_concept_1790105984612.jpg": "dad_clapping.png",
        "mom_waving_concept_1790106039089.jpg": "mom_waving.png",
        "mom_holding_bowl_concept_1790106059254.jpg": "mom_holding_bowl.png",
        "dog_curled_sleeping_concept_1790106288256.jpg": "dog_curled_sleeping.png",
    }

    for concept_file, sprite_target in concept_map.items():
        src_path = os.path.join(BRAIN_DIR, concept_file)
        dst_path = os.path.join(SPRITES_DIR, sprite_target)
        if os.path.exists(src_path):
            isolate_sprite(src_path, dst_path)
        else:
            print(f"Warning: Concept {concept_file} not found")

    # 2. Dog Sitting Attentive
    dog_src = os.path.join(CHAR_DIR, "dog_cartoon.jpg")
    dog_dst = os.path.join(SPRITES_DIR, "dog_sitting_attentive.png")
    if os.path.exists(dog_src):
        isolate_sprite(dog_src, dog_dst, threshold=25)

    # 3. Dog Dancing Paw - Clean borders
    dog_dance_path = os.path.join(SPRITES_DIR, "dog_dancing_paw.png")
    if os.path.exists(dog_dance_path):
        im = Image.open(dog_dance_path).convert("RGBA")
        # Ensure alpha mask is clean
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        im.save(guarded_output_path(dog_dance_path), "PNG")
        print("[CLEANED] dog_dancing_paw.png")

    print("\nAll high-fidelity sprites built successfully!")

if __name__ == "__main__":
    main()
