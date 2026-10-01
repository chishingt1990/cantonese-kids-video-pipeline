"""Offline release integration tests; sticker writes are isolated in a temporary tree."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parent


class TestArtworkRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.scratch = Path(cls.temp.name)
        cls.manifest = json.loads((ROOT / "config" / "artwork_release_v1.json").read_text(encoding="utf-8"))
        (cls.scratch / "config").mkdir()
        shutil.copyfile(ROOT / "config" / "artwork_release_v1.json", cls.scratch / "config" / "artwork_release_v1.json")
        for asset in cls.manifest["assets"]:
            target = cls.scratch / asset["runtime_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / asset["runtime_path"], target)
        for filename in ("phonics_release_v2.json", "props_release_v2.json"):
            manifest_path = ROOT / "config" / filename
            if manifest_path.exists():
                shutil.copyfile(manifest_path, cls.scratch / "config" / filename)
                for asset in json.loads(manifest_path.read_text(encoding="utf-8"))["assets"]:
                    target = cls.scratch / asset["runtime_path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / asset["runtime_path"], target)

        def load(name, relative):
            target = cls.scratch / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
            spec = importlib.util.spec_from_file_location(name, target)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        cls.glyph = load("app.services.glyph_sticker_service", "app/services/glyph_sticker_service.py")
        cls.glyph_modules = patch.dict(sys.modules, {"app.services.glyph_sticker_service": cls.glyph})
        cls.glyph_modules.start()
        cls.addClassCleanup(cls.glyph_modules.stop)
        cls.stickers = load("release_stickers", "app/services/sticker_service.py")
        cls.ai = types.ModuleType("app.services.ai_service")
        cls.ai.generate_ai_text = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline test"))
        cls.modules = patch.dict(sys.modules, {
            "app.services.sticker_service": cls.stickers,
            "app.services.ai_service": cls.ai,
        })
        cls.modules.start()
        cls.addClassCleanup(cls.modules.stop)
        cls.director = load("release_director", "app/services/scene_director_service.py")
        cls.director_modules = patch.dict(sys.modules, {"app.services.scene_director_service": cls.director})
        cls.director_modules.start()
        cls.addClassCleanup(cls.director_modules.stop)
        cls.characters = load("release_characters", "app/routers/characters.py")
        cls.routes = load("release_director_routes", "app/routers/scene_director.py")
        app = FastAPI()
        app.include_router(cls.characters.router)
        app.include_router(cls.routes.router)
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_pose_discovery_and_image_endpoints(self):
        response = self.client.get("/api/characters/all")
        self.assertEqual(response.status_code, 200)
        chars = {c["id"]: c for c in response.json()["characters"]}
        for name in ("levi", "luca"):
            poses = {p["id"]: p for p in chars[name]["poses"]}
            for pose in ("jumping", "dancing", "brushing_teeth"):
                with self.subTest(name=name, pose=pose):
                    self.assertIn(pose, poses)
                    self.assertEqual(poses[pose]["label"], self.characters.POSE_LABELS[pose])
                    response = self.client.get(f"/api/characters/sprite/{name}_{pose}.png")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, (self.scratch / "assets" / "sprites" / f"{name}_{pose}.png").read_bytes())

    def test_badges_are_labeled_and_cached_without_overwrite(self):
        catalog = self.client.get("/api/scene-director/stickers/catalog").json()["stickers"]
        by_id = {s["id"]: s for s in catalog}
        expected = {
            "badge_routine_brush_teeth": ("刷牙", "BRUSH TEETH"),
            "badge_routine_wash_hands": ("洗手", "WASH HANDS"),
            "badge_routine_eat": ("食飯", "MEALTIME"),
            "badge_play_together_v1": ("一齊玩", "PLAY TOGETHER"),
            "badge_take_turns_v1": ("輪住玩", "TAKE TURNS"),
            "badge_bedtime_sleep": ("瞓覺", "SLEEP"),
        }
        self.stickers.ensure_base_stickers()
        for asset in self.manifest["assets"]:
            if asset["kind"] != "badge":
                continue
            with self.subTest(badge=asset["id"]):
                item = by_id[asset["id"]]
                self.assertEqual((item["chinese"], item["english"]), expected[asset["id"]])
                path = Path(self.stickers.get_or_render_sticker(item))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                response = self.client.get(f"/api/scene-director/stickers/render/{asset['id']}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), asset["sha256"])

    def test_ai_plan_preserves_new_poses_and_explicit_coordinates(self):
        for name in ("levi", "luca"):
            for pose in ("jumping", "dancing", "brushing_teeth"):
                with self.subTest(name=name, pose=pose):
                    char = {"name": name, "pose": pose, "x_percent": 31, "y_percent": 77, "scale": 1.2, "flip": False}
                    plan = self.director._validate_and_sanitize_plan({"characters": [char]}, {})
                    self.assertEqual(plan["characters"][0], char)
                    self.assertEqual(char["y_percent"], 77)
                    self.assertEqual(char["pose"], pose)
                    default = self.director._validate_and_sanitize_plan({"characters": [{"name": name, "pose": pose}]}, {})
                    self.assertAlmostEqual(default["characters"][0]["y_percent"], self.director.STARTER_POSE_Y[pose])
        unknown = self.director._validate_and_sanitize_plan({"characters": [{"name": "levi", "pose": "unknown"}]}, {})
        self.assertEqual(unknown["characters"][0]["pose"], "default")
        self.assertEqual(unknown["characters"][0]["y_percent"], 88)

    def test_approved_badge_content_cannot_disagree_with_cached_image(self):
        plan = self.director._validate_and_sanitize_plan({
            "characters": [{"name": "levi", "pose": "default"}],
            "stickers": [{"id": "badge_routine_brush_teeth", "content": "wrong", "english": "WRONG", "x_percent": 35}],
        }, {})
        badge = plan["stickers"][0]
        self.assertEqual(badge["content"], "刷牙")
        self.assertEqual(badge["english"], "BRUSH TEETH")
        self.assertEqual(badge["x_percent"], 35)

    def test_offline_action_cues(self):
        cases = [
            ("一齊跳起", "jumping", "playroom"),
            ("Levi and Luca are jumping", "jumping", "playroom"),
            ("大家跳舞", "dancing", "playroom"),
            ("The twins are dancing", "dancing", "playroom"),
            ("一齊刷牙", "brushing_teeth", "bathroom"),
            ("Brush your teeth", "brushing_teeth", "bathroom"),
            ("Brush teeth before bedtime", "brushing_teeth", "bathroom"),
        ]
        for text, pose, background in cases:
            with self.subTest(text=text):
                response = self.client.post("/api/scene-director/direct-scene", json={"scene": {"cantonese": text}})
                self.assertEqual(response.status_code, 200)
                plan = response.json()["plan"]
                self.assertEqual({c["pose"] for c in plan["characters"]}, {pose})
                self.assertEqual(plan["background"], background)
                self.assertTrue(all(c["flip"] is False for c in plan["characters"]))
                self.assertTrue(all(abs(c["y_percent"] - self.director.STARTER_POSE_Y[pose]) < 0.001 for c in plan["characters"]))

    def test_priority_and_word_boundaries(self):
        for text in ("jumpers in a shop", "dancefloor", "brush painting", "toothbrush"):
            self.assertIsNone(self.director._starter_action(text), text)
        sad = self.director._heuristic_fallback_director({"english": "Luca is sad about dancing"})
        self.assertNotIn("dancing", [c["pose"] for c in sad["characters"]])
        self.assertIn("badge_calm_down", [s["id"] for s in sad["stickers"]])
        hygiene = self.director._heuristic_fallback_director({"english": "wash hands before jumping"})
        self.assertNotIn("jumping", [c["pose"] for c in hygiene["characters"]])
        self.assertIn("badge_routine_wash_hands", [s["id"] for s in hygiene["stickers"]])
        outdoors = self.director._heuristic_fallback_director({"english": "jumping", "background": "park"})
        self.assertEqual(outdoors["background"], "park")

    def test_badge_lesson_cues(self):
        for text, badge in [
            ("洗手", "badge_routine_wash_hands"), ("食飯", "badge_routine_eat"),
            ("一齊玩", "badge_play_together_v1"), ("輪住玩", "badge_take_turns_v1"),
            ("瞓覺", "badge_bedtime_sleep"),
        ]:
            with self.subTest(text=text):
                plan = self.director._heuristic_fallback_director({"cantonese": text})
                self.assertIn(badge, [s["id"] for s in plan["stickers"]])

    def test_tweaks_preserve_original_scene_and_target_only_named_child(self):
        scene = {"characters": [{"name": "levi", "pose": "default", "y_percent": 76}, {"name": "luca", "pose": "default"}]}
        saved = copy.deepcopy(scene)
        for name in ("levi", "luca"):
            for text, pose in (("jump", "jumping"), ("dance", "dancing"), ("brush teeth", "brushing_teeth")):
                result = self.director.apply_copilot_tweak(scene, f"{name} {text}")
                target = next(c for c in result["characters"] if c["name"] == name)
                self.assertEqual(target["pose"], pose)
                self.assertEqual(next(c for c in result["characters"] if c["name"] != name)["pose"], "default")
                if name == "levi":
                    self.assertEqual(target["y_percent"], 76)
        self.assertEqual(scene, saved)

    def test_all_release_hashes_and_sprite_padding(self):
        for asset in self.manifest["assets"]:
            path = ROOT / asset["runtime_path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGBA")
                if asset["kind"] == "sprite":
                    self.assertEqual(image.getchannel("A").getbbox(), (8, 8, image.width - 8, image.height - 8))
                    self.assertEqual(image.getchannel("A").getextrema(), (0, 255))

    def test_complete_prop_catalog_and_cache_integrity(self):
        props = [a for a in self.manifest["assets"] if a["kind"] == "prop"]
        self.assertEqual(len(props), 48)
        catalog = self.client.get("/api/scene-director/stickers/catalog").json()["stickers"]
        ids = [s["id"] for s in catalog]
        for prop in props:
            with self.subTest(prop=prop["id"]):
                self.assertEqual(ids.count(prop["id"]), 1)
                response = self.client.get(f"/api/scene-director/stickers/render/{prop['id']}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), prop["sha256"])
                with self.assertRaises(ValueError):
                    self.stickers.get_or_render_sticker({"id": prop["id"]}, force=True)
        self.stickers.ensure_base_stickers()
        for prop in props:
            self.assertEqual(hashlib.sha256((self.scratch / prop["runtime_path"]).read_bytes()).hexdigest(), prop["sha256"])

    def test_new_props_are_available_to_offline_and_ai_direction(self):
        for name, prop_id in [("giraffe", "prop_giraffe"), ("救護車", "prop_ambulance"),
                              ("broccoli", "prop_broccoli"), ("sandwich", "prop_sandwich"),
                              ("backpack", "prop_backpack")]:
            with self.subTest(name=name):
                self.assertIn(prop_id, self.director.DIRECTOR_SYSTEM_PROMPT)
                plan = self.director._heuristic_fallback_director({"title": name})
                self.assertIn(prop_id, [s["id"] for s in plan["stickers"]])
        self.assertIsNone(self.director._expanded_prop("background bicyclepath"))
        sad = self.director._heuristic_fallback_director({"english": "Luca is sad about the giraffe"})
        self.assertIn("badge_calm_down", [s["id"] for s in sad["stickers"]])


if __name__ == "__main__":
    unittest.main()
