"""Historical asset/live-provider checks; run only in a disposable checkout.

The default offline regression suite is ``python -m unittest discover -s tests``.
This suite predates project-scoped media and modifies assets in its working
directory. Explicit opt-in preserves it for migration reference without making
ordinary test discovery contact providers or overwrite artwork.
"""
import os
import unittest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.services.background_generator import generate_iterative_background
from app.services.sticker_service import STICKER_CATALOG, get_or_render_sticker
from app.services.scene_director_service import apply_copilot_tweak
from app.services.ai_service import _generate_dynamic_fallback_script

client = TestClient(app)

@unittest.skipUnless(
    os.environ.get("KIDS_STUDIO_RUN_LEGACY_TESTS") == "1",
    "Legacy asset/live checks require an explicitly opted-in disposable checkout",
)
class TestCantoneseKidsPipeline(unittest.TestCase):

    def test_01_master_backgrounds_exist_and_1080p(self):
        """Verify all 10 master backgrounds exist as 1920x1080."""
        bg_dir = "assets/backgrounds"
        expected = [
            "living_room", "nursery", "kitchen", "playroom", "beach",
            "park", "mountains", "dining", "bathroom", "reading_nook"
        ]
        res = client.get("/api/characters/backgrounds")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        bgs = {b["id"]: b for b in data["backgrounds"]}
        
        for bg_id in expected:
            self.assertIn(bg_id, bgs, f"Missing background preset: {bg_id}")
            fn = f"bg_{bg_id}.png"
            p = os.path.join(bg_dir, fn)
            self.assertTrue(os.path.exists(p), f"File {p} does not exist")
            im = Image.open(p)
            self.assertEqual(im.size, (1920, 1080), f"{fn} is not 1920x1080: {im.size}")
            im.close()
        print("[OK] All 10 master backgrounds verified at 1920x1080 HD!")

    def test_02_background_generator_mountains_and_atmosphere(self):
        """Verify generator handles mountains and applies atmosphere cleanly."""
        temp_out = "assets/backgrounds/temp_test_mountain_run.png"
        try:
            res_path = generate_iterative_background(
                "Gentle rolling wildflower hills and mountain path",
                ["Make it golden sunset light"],
                temp_out
            )
            self.assertTrue(os.path.exists(res_path))
            im = Image.open(res_path)
            self.assertEqual(im.size, (1920, 1080))
            im.close()
            print("[OK] Custom background generator handled mountains with golden sunset refinement!")
        finally:
            if os.path.exists(temp_out):
                os.remove(temp_out)

    def test_03_character_congruency(self):
        """Verify character poses and outfit rules are strictly enforced."""
        res = client.get("/api/characters/all")
        self.assertEqual(res.status_code, 200)
        chars = {c["id"]: c for c in res.json()["characters"]}
        
        levi = chars["levi"]
        self.assertIn("Coral Red Polo", levi["outfit"])
        levi_pose_ids = [p["id"] for p in levi["poses"]]
        self.assertNotIn("eating_banana_yellow_shirt", levi_pose_ids)
        
        luca = chars["luca"]
        self.assertIn("Bright Yellow Polo", luca["outfit"])
        
        # Verify sprite files exist on disk, have alpha channel, and have solid filled bodies (not hollow outlines)
        all_char_ids = list(chars.keys())
        for char_id in all_char_ids:
            char_data = chars[char_id]
            for pose in char_data.get("poses", []):
                fn = pose["sprite"]
                p = os.path.join("assets", "sprites", fn)
                self.assertTrue(os.path.exists(p), f"Sprite file missing: {p}")
                im = Image.open(p)
                self.assertEqual(im.mode, "RGBA", f"Sprite {fn} is not RGBA: {im.mode}")
                
                # Visual Integrity & Solid Fill Density Checks
                import numpy as np
                arr = np.array(im)
                alpha = arr[:, :, 3]
                opaque_px = int(np.sum(alpha > 0))
                total_px = arr.shape[0] * arr.shape[1]
                density = opaque_px / total_px
                
                # 1. Detect hollow/empty sprite
                self.assertGreaterEqual(opaque_px, 70000, f"Sprite {fn} is hollow/empty with only {opaque_px} opaque pixels")
                self.assertGreaterEqual(density, 0.25, f"Sprite {fn} has sparse wireframe density: {density:.2f}")
                
                # 2. Detect uncolored line-art outlines (wireframe check)
                r = arr[:, :, 0][alpha > 0]
                g = arr[:, :, 1][alpha > 0]
                b = arr[:, :, 2][alpha > 0]
                near_black_lines = (r < 50) & (g < 50) & (b < 50)
                filled_body_ratio = float((~near_black_lines).mean())
                self.assertGreaterEqual(filled_body_ratio, 0.65, f"Sprite {fn} is a hollow outline with only {filled_body_ratio*100:.1f}% filled body")
                
                im.close()
        print("[OK] Character congruency & Solid Fill Integrity verified across all characters (no hollow outlines)!")

    def test_04_word_stickers_snug_centered_proportions(self):
        """Verify all word stickers use the snug pill badge design with no bottom void."""
        for s in STICKER_CATALOG:
            if s.get("type") == "word":
                p = get_or_render_sticker(s)
                im = Image.open(p)
                w, h = im.size
                # Height should be proportional and compact (h <= 110 for standard words)
                self.assertLessEqual(h, 120, f"Sticker {s['id']} has excessive height ({h}px)")
                self.assertEqual(im.mode, "RGBA")
                im.close()
        print("[OK] All word stickers verified: snug, balanced, centered typography!")

    def test_05_background_delete_protections(self):
        """Verify core backgrounds cannot be deleted, and custom backgrounds can."""
        # Core deletion attempt should fail with 400
        res = client.delete("/api/characters/background/mountains")
        self.assertEqual(res.status_code, 400)
        
        # Create dummy custom background
        custom_p = "assets/backgrounds/bg_custom_test_suite.png"
        dummy = Image.new("RGB", (100, 100), (255, 255, 255))
        dummy.save(custom_p)
        try:
            res_del = client.delete("/api/characters/background/custom_test_suite")
            self.assertEqual(res_del.status_code, 200)
            self.assertFalse(os.path.exists(custom_p))
            print("[OK] Background deletion API verified: core protected, custom removable!")
        finally:
            if os.path.exists(custom_p):
                os.remove(custom_p)

    def test_06_scene_copilot_tweaks(self):
        """Verify natural language scene co-pilot correctly updates backgrounds, poses, and stickers."""
        base_scene = {
            "background": "living_room",
            "characters": [
                {"name": "levi", "pose": "default", "scale": 1.0, "x_percent": 34, "y_percent": 88},
                {"name": "luca", "pose": "default", "scale": 1.0, "x_percent": 66, "y_percent": 88}
            ],
            "stickers": []
        }
        
        # Tweak 1: Mountains
        s1 = apply_copilot_tweak(base_scene, "Change background to gentle wildflower mountain hills")
        self.assertEqual(s1["background"], "mountains")
        
        # Tweak 2: Dog Eat Banana
        s2 = apply_copilot_tweak(base_scene, "Make Spitz dog hold and eat sweet banana in mouth")
        dog = next((c for c in s2["characters"] if c["name"] == "dog"), None)
        self.assertIsNotNone(dog)
        self.assertEqual(dog["pose"], "eating_banana")
        
        # Tweak 3: Hug
        s3 = apply_copilot_tweak(base_scene, "Levi give big warm hug")
        levi = next((c for c in s3["characters"] if c["name"] == "levi"), None)
        self.assertEqual(levi["pose"], "arms_out_hug")
        
        # Tweak 4: Sticker
        s4 = apply_copilot_tweak(base_scene, "Add a 多謝 thank you sticker")
        self.assertTrue(any(st.get("id") == "badge_thank_you" for st in s4["stickers"]))
        
        print("[OK] Inline Scene Co-pilot successfully tested for backgrounds, poses, and stickers!")

    def test_07_review_gallery_endpoints(self):
        """Verify the visual asset review gallery and staging stager endpoints respond with 200."""
        r1 = client.get("/review")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("Visual Asset Inspector", r1.text)

        r2 = client.get("/gallery")
        self.assertEqual(r2.status_code, 200)

        # Check that characters endpoint has full data
        r3 = client.get("/api/characters/all")
        self.assertEqual(r3.status_code, 200)
        chars = r3.json().get("characters", [])
        self.assertGreaterEqual(len(chars), 8)

        # Check stickers catalog
        r4 = client.get("/api/scene-director/stickers/catalog")
        self.assertEqual(r4.status_code, 200)
        stks = r4.json().get("stickers", [])
        self.assertGreaterEqual(len(stks), 20)
        print("[OK] Review gallery and staging sandbox endpoints verified successfully!")

    def test_08_dynamic_script_theme_linkage_and_7_scenes(self):
        """Verify dynamic script synthesis produces strictly 7 scenes matching user theme and moral lesson."""
        idea = {
            "title_cantonese": "氣球飛走咗",
            "title_english": "The Red Balloon Flew Away",
            "description": "Luca's balloon drifts into the sky. Dad comforts him and explains it is okay to feel sad.",
            "moral_lesson": "Managing disappointment and gentle deep breaths",
            "target_vocab": ["氣球", "唔開心", "深呼吸", "爸爸抱抱"],
            "scenes_preview": [
                "Playing with red balloon in park",
                "Sudden gust of wind lifts balloon",
                "Balloon floats above treetops",
                "Luca begins to tear up and frown",
                "Dad kneels and gives warm comforting hug",
                "Dad teaches slow gentle deep breaths",
                "Both smile and wave goodbye to the balloon"
            ]
        }
        res = _generate_dynamic_fallback_script(idea, ["dad", "luca", "levi", "dog", "mom"])
        self.assertEqual(len(res["scenes"]), 7, f"Expected 7 scenes, got {len(res['scenes'])}")
        self.assertEqual(res["title_cantonese"], "氣球飛走咗")
        self.assertEqual(res["title_english"], "The Red Balloon Flew Away")
        self.assertIn("park", res["scenes"][0]["background"])
        
        # Verify dialogue connects to idea theme and vocabulary
        dialogues = " ".join([s["cantonese"] for s in res["scenes"]])
        self.assertIn("氣球", dialogues)
        self.assertIn("唔開心", dialogues)
        self.assertIn("深呼吸", dialogues)

        # Verify all scenes have required fields
        for s in res["scenes"]:
            self.assertIn("title", s)
            self.assertIn("cantonese", s)
            self.assertIn("english", s)
            self.assertIn("background", s)
            self.assertIn("speaker", s)
            self.assertIn("duration_sec", s)
            self.assertGreaterEqual(s["duration_sec"], 6)
            self.assertIn("characters", s)
            self.assertGreaterEqual(len(s["characters"]), 1)
        print("[OK] Dynamic script generation verified: exactly 7 scenes, 100% theme-linked, parentese dialogue!")

    def test_09_grandparents_and_relatives_sprite_routing(self):
        """Verify sprite endpoint routes relatives, pose aliases, and young dad sprites without Levi fallback."""
        r_levi = client.get("/api/characters/sprite/levi_default.png")
        self.assertEqual(r_levi.status_code, 200)

        # 1. Paternal Grandparents with tea pose
        r_tea = client.get("/api/characters/sprite/grandparents_paternal/tea")
        self.assertEqual(r_tea.status_code, 200)
        self.assertNotEqual(r_tea.content, r_levi.content, "grandparents_paternal/tea wrongly fell back to Levi")

        # 2. Paternal Grandparents alias drinking_tea
        r_drink = client.get("/api/characters/sprite/grandparents_paternal/drinking_tea")
        self.assertEqual(r_drink.status_code, 200)
        self.assertEqual(r_drink.content, r_tea.content, "drinking_tea alias should match tea sprite")

        # 3. Maternal Grandparents standing
        r_mat = client.get("/api/characters/sprite/grandparents_maternal/standing")
        self.assertEqual(r_mat.status_code, 200)
        self.assertNotEqual(r_mat.content, r_levi.content, "grandparents_maternal wrongly fell back to Levi")

        # 4. Young Dad Teaching (cross-legged with book)
        r_dad_teach = client.get("/api/characters/sprite/dad/teaching")
        self.assertEqual(r_dad_teach.status_code, 200)
        self.assertNotEqual(r_dad_teach.content, r_levi.content)

        # 5. Young Dad Sitting (cheerful stool)
        r_dad_sit = client.get("/api/characters/sprite/dad/sitting")
        self.assertEqual(r_dad_sit.status_code, 200)
        self.assertNotEqual(r_dad_sit.content, r_levi.content)

        # 6. Direct filename lookup
        r_direct = client.get("/api/characters/sprite/dad_teaching.png")
        self.assertEqual(r_direct.status_code, 200)
        self.assertEqual(r_direct.content, r_dad_teach.content)

        print("[OK] Sprite routing verified: Paternal tea, maternal standing, youthful dad sprites with zero 404s or Levi fallbacks!")

    def test_10_scene_director_background_preservation(self):
        """Verify scene director preserves user-specified backgrounds (mountains, playground, duck_pond)."""
        payload = {
            "project": {
                "title_cantonese": "公園同大自然",
                "scenes": [
                    {"scene_number": 1, "background": "mountains", "cantonese": "行山好健康呀！", "english": "Hiking in the mountains is healthy!"},
                    {"scene_number": 2, "background": "playground", "cantonese": "公園玩滑梯！", "english": "Let's slide on the playground slide!"},
                    {"scene_number": 3, "background": "duck_pond", "cantonese": "睇下鴨仔游水！", "english": "Look at the cute duckies swimming!"}
                ]
            }
        }
        res = client.post("/api/scene-director/auto-direct", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        directed_scenes = data.get("scenes", [])
        self.assertEqual(len(directed_scenes), 3)

        self.assertEqual(directed_scenes[0]["background"], "mountains", "Mountains background was reset")
        self.assertEqual(directed_scenes[1]["background"], "playground", "Playground background was reset")
        self.assertEqual(directed_scenes[2]["background"], "duck_pond", "Duck pond background was reset")

        print("[OK] Scene director background preservation verified across all outdoor presets!")

    def test_11_audio_duration_sync_and_remix(self):
        """Verify audio synthesize endpoint returns duration and audio URL for scene synchronization."""
        payload = {
            "scene_idx": 1,
            "text": "早晨呀！今日大家一齊去公園玩！",
            "persona": "dad"
        }
        res = client.post("/api/audio/tts/scene", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("duration", data)
        self.assertGreater(data["duration"], 0.0)
        self.assertIn("audio_url", data)
        self.assertIn("master_audio_url", data)
        print("[OK] Single TTS synthesis and audio duration sync endpoint verified successfully!")

    def test_12_expanded_asset_library_and_staging_intelligence(self):
        """Verify expanded poses, props, backgrounds, and emotional empathy staging."""
        # 1. Verify New Backgrounds Exist as 1920x1080 HD
        res_bg = client.get("/api/characters/backgrounds")
        self.assertEqual(res_bg.status_code, 200)
        bg_ids = {b["id"] for b in res_bg.json()["backgrounds"]}
        self.assertIn("art_room", bg_ids)
        self.assertIn("supermarket", bg_ids)
        for bg in ["art_room", "supermarket"]:
            im = Image.open(f"assets/backgrounds/bg_{bg}.png")
            self.assertEqual(im.size, (1920, 1080))
            im.close()

        # 2. Verify Character Poses in API
        res_chars = client.get("/api/characters/all")
        self.assertEqual(res_chars.status_code, 200)
        char_dict = {c["id"]: {p["id"]: p for p in c["poses"]} for c in res_chars.json()["characters"]}
        
        # Levi authentic poses
        for p in ["sad", "holding_book", "playing_blocks", "playing_car", "waving", "pointing", "running", "stretching", "eating", "sleeping"]:
            self.assertIn(p, char_dict["levi"])
            im = Image.open(f"assets/sprites/levi_{p}.png")
            self.assertEqual(im.mode, "RGBA")
            im.close()
            
        # Luca authentic poses
        for p in ["crying", "playing_blocks", "playing_car", "waving", "clapping", "holding_toy", "eating", "sleeping"]:
            self.assertIn(p, char_dict["luca"])
            im = Image.open(f"assets/sprites/luca_{p}.png")
            self.assertEqual(im.mode, "RGBA")
            im.close()

        # Dad & Mom poses
        self.assertIn("kneeling", char_dict["dad"])
        self.assertIn("teaching", char_dict["dad"])
        self.assertIn("sitting", char_dict["dad"])
        self.assertIn("waving", char_dict["dad"])
        self.assertIn("drinking", char_dict["dad"])
        self.assertIn("kneeling_hug", char_dict["mom"])
        self.assertIn("holding_fruit", char_dict["mom"])
        self.assertIn("teaching", char_dict["mom"])

        # Dog poses
        self.assertIn("playing_ball", char_dict["dog"])
        self.assertIn("running", char_dict["dog"])
        self.assertIn("eating_banana", char_dict["dog"])

        # 3. Verify New Props and Badges in Catalog
        res_stk = client.get("/api/scene-director/stickers/catalog")
        self.assertEqual(res_stk.status_code, 200)
        stk_ids = {s["id"] for s in res_stk.json()["stickers"]}
        for prop in ["prop_bus", "prop_fire_truck", "prop_airplane", "prop_duckling", "prop_kitty_cat", "prop_har_gow", "prop_siu_mai", "prop_egg_tart", "prop_watermelon_slice", "prop_balloon_yellow", "badge_calm_down", "badge_well_done"]:
            self.assertIn(prop, stk_ids)

        # 4. Verify Emotional / Sadness Staging picks crying Luca and comforting Dad/Mom
        sad_scene = {
            "scene_number": 3,
            "title": "Balloon Flew Away",
            "cantonese": "氣球飛走咗，細佬好唔開心想喊！",
            "english": "The balloon flew away, little brother feels sad and tearful!",
            "speaker": "Dad",
            "vocab_highlight": "唔開心"
        }
        sad_directed = client.post("/api/scene-director/auto-direct", json={"project": {"scenes": [sad_scene]}}).json()["scenes"][0]
        char_poses = {c["name"]: c["pose"] for c in sad_directed["characters"]}
        self.assertEqual(char_poses.get("luca"), "crying")
        self.assertEqual(char_poses.get("dad"), "comforting_hug")
        stk_ids_staged = [s["id"] for s in sad_directed["stickers"]]
        self.assertIn("prop_comfort_hearts", stk_ids_staged)
        self.assertIn("badge_calm_down", stk_ids_staged)

        # 5. Verify Celebration Staging picks cheering Levi and Luca + well done badge
        cheer_scene = {
            "scene_number": 6,
            "title": "We Succeeded!",
            "cantonese": "成功啦！好叻仔，大家一齊拍手慶祝！",
            "english": "We did it! Clever boys, let's all clap and celebrate!",
            "speaker": "Dad",
            "vocab_highlight": "好叻仔"
        }
        cheer_directed = client.post("/api/scene-director/auto-direct", json={"project": {"scenes": [cheer_scene]}}).json()["scenes"][0]
        cheer_poses = {c["name"]: c["pose"] for c in cheer_directed["characters"]}
        self.assertEqual(cheer_poses.get("levi"), "cheering")
        self.assertEqual(cheer_poses.get("luca"), "cheering")
        cheer_stk_ids = [s["id"] for s in cheer_directed["stickers"]]
        self.assertIn("badge_well_done", cheer_stk_ids)

        print("[OK] Expanded Asset Library & Emotional Empathy Staging Intelligence verified 100%!")

if __name__ == "__main__":
    unittest.main()
