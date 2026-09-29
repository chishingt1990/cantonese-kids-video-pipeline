import os

try:
    from scripts.maintenance_guard import PROJECT_ROOT, configure_cli, output_path
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from maintenance_guard import PROJECT_ROOT, configure_cli, output_path

from app.utils.sprite_isolator import isolate_sprite_from_white_bg

SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")

BRAIN_ROOT = r"C:\Users\chish\.gemini\antigravity\brain"

def isolate_clean_sprite(src_path: str, dst_path: str, threshold: int = 35):
    isolate_sprite_from_white_bg(
        src_path, str(output_path(dst_path)), threshold=threshold
    )

# Map authentic brain illustrations to canonical sprite filenames
AUTHENTIC_SPRITE_MAP = {
    # Dog poses
    os.path.join(BRAIN_ROOT, "8309e611-398f-427a-89b3-458f1dbe37dc", "dog_spitz_eating_banana_1789247985470.jpg"): "dog_eating_banana.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dog_ball_1789319450855.jpg"): "dog_playing_ball.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dog_running_1789319402485.jpg"): "dog_running.png",
    
    # Dad poses
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_sitting_1789359772399.jpg"): "dad_sitting.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_kneeling_1789319624316.jpg"): "dad_kneeling.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_teaching_1789453167912.jpg"): "dad_teaching.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_waving_1789319664154.jpg"): "dad_waving.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "dad_drinking_1789453253933.jpg"): "dad_drinking.png",
    
    # Mom poses
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "mom_kneeling_1789319707641.jpg"): "mom_kneeling_hug.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "mom_fruit_1789337297402.jpg"): "mom_holding_fruit.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "mom_teaching_1789453228406.jpg"): "mom_teaching.png",
    
    # Levi poses
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "levi_pointing_1789319522682.jpg"): "levi_pointing.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "levi_running_1789319495627.jpg"): "levi_running.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "levi_eating_1789224982042.jpg"): "levi_eating.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "levi_sleeping_1789224971803.jpg"): "levi_sleeping.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "levi_stretching_1789225297544.jpg"): "levi_stretching.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "levi_waving_1789224959323.jpg"): "levi_waving.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "levi_arms_out_hug_1789225391043.jpg"): "levi_arms_out_hug.png",
    
    # Luca poses
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "luca_clapping_1789319549055.jpg"): "luca_clapping.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "luca_toy_1789319574967.jpg"): "luca_holding_toy.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "luca_eating_1789225072067.jpg"): "luca_eating.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "luca_sleeping_1789225061916.jpg"): "luca_sleeping.png",
    os.path.join(BRAIN_ROOT, "706d91eb-30af-4825-a9a0-115b05e85ba1", "luca_waving_1789225051798.jpg"): "luca_waving.png",
    
    # Extended family
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "grandparents_paternal_tea_1789337325526.jpg"): "grandparents_paternal_tea.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "grandparents_maternal_waving_1789337384719.jpg"): "grandparents_maternal_waving.png",
    os.path.join(BRAIN_ROOT, "84457e01-0f2f-45ce-9821-2b2c70c480eb", "auntie_cousins_waving_1789337454764.jpg"): "auntie_cousins_waving.png",
}

def main(argv=None):
    configure_cli(argv)
    print("=== Extracting & Restoring Authentic Character Pose Sprites ===")
    for src_path, sprite_name in AUTHENTIC_SPRITE_MAP.items():
        if os.path.exists(src_path):
            dst_path = os.path.join(SPRITES_DIR, sprite_name)
            isolate_clean_sprite(src_path, dst_path)
        else:
            print(f"Warning: Source not found: {src_path}")
    print("=== Complete! ===")

if __name__ == "__main__":
    main()
