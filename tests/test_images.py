"""Offline image contracts. All writes use disposable storage beneath the repository."""

import hashlib
import importlib
import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.routers import characters, scene_director
from app.services import asset_manifest as assets
from app.services import background_generator as backgrounds
from app.services import character_generator as sprites
from app.services import scene_director_service as director
from app.services import sticker_service as stickers
from app.utils.sprite_isolator import isolate_sprite_from_white_bg


class ImageFoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(__file__).resolve().parent / ("image-test-" + uuid.uuid4().hex)
        self.directory.mkdir()
        self.env = patch.dict(os.environ, {"KIDS_STUDIO_DATA_DIR": str(self.directory)})
        self.env.start()
        app = FastAPI()
        app.include_router(characters.router)
        app.include_router(scene_director.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        shutil.rmtree(self.directory)

    @staticmethod
    def _fake_outfit(character, prompt, output):
        Image.new("RGBA", (8, 8), (255, 0, 0, 255) if character == "levi" else (0, 255, 0, 255)).save(output)
        return output

    @staticmethod
    def _fake_background(prompt, history, output):
        Image.new("RGB", (8, 8), (20, 40, 60)).save(output)
        return output

    def preview_outfit(self, cid="levi", prompt="blue shirt"):
        with patch.object(characters, "generate_custom_character_sprite", self._fake_outfit):
            response = self.client.post("/api/characters/preview_outfit",
                                        json={"character_id": cid, "prompt": prompt})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def preview_background(self, iteration=1):
        with patch.object(characters, "generate_iterative_background", self._fake_background):
            response = self.client.post("/api/characters/iterate_background", json={
                "name": "Kitchen", "prompt": "park at night", "history": [], "iteration": iteration})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_outfit_preview_is_immutable_and_cross_character_safe(self):
        first = self.preview_outfit()
        original = self.client.get(first["preview_url"]).content
        second = self.preview_outfit("luca")
        self.assertNotEqual(first["preview_id"], second["preview_id"])
        self.assertEqual(self.client.get(first["preview_url"]).content, original)
        bad = self.client.post("/api/characters/save_outfit", json={
            "preview_id": first["preview_id"], "character_id": "luca", "prompt": "blue shirt"})
        self.assertEqual(bad.status_code, 409)
        good = self.client.post("/api/characters/save_outfit", json={
            "preview_id": first["preview_id"], "character_id": "levi", "prompt": "blue shirt"})
        self.assertEqual(good.status_code, 200, good.text)
        saved = good.json()
        self.assertEqual(self.client.get(saved["sprite_url"]).content, original)
        self.assertEqual(assets.resolve_sprite("levi", saved["pose_id"]).read_bytes(), original)
        character = next(c for c in assets.list_characters() if c["id"] == "levi")
        self.assertEqual(next(p for p in character["poses"] if p["id"] == saved["pose_id"])["label"], "blue shirt")

    def test_save_requires_preview_and_matches_prompt(self):
        self.assertEqual(self.client.post("/api/characters/save_outfit",
                         json={"character_id": "levi", "prompt": "blue"}).status_code, 422)
        preview = self.preview_outfit()
        response = self.client.post("/api/characters/save_outfit", json={
            "preview_id": preview["preview_id"], "character_id": "levi", "prompt": "green shirt"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post("/api/characters/save_outfit", json={
            "preview_id": "missing", "character_id": "levi", "prompt": "blue shirt"}).status_code, 404)

    def test_save_is_idempotent_and_has_no_prompt_name_collision(self):
        preview = self.preview_outfit()
        body = {"preview_id": preview["preview_id"], "character_id": "levi", "prompt": "blue shirt"}
        first = self.client.post("/api/characters/save_outfit", json=body).json()
        again = self.client.post("/api/characters/save_outfit", json=body).json()
        self.assertEqual(first["pose_id"], again["pose_id"])
        other = self.preview_outfit()
        body["preview_id"] = other["preview_id"]
        self.assertNotEqual(first["pose_id"], self.client.post("/api/characters/save_outfit", json=body).json()["pose_id"])

    def test_custom_background_cannot_shadow_master(self):
        master = assets.resolve_background("kitchen")
        before = hashlib.sha256(master.read_bytes()).hexdigest()
        preview = self.preview_background()
        response = self.client.post("/api/characters/save_background", json={
            "preview_id": preview["preview_id"], "name": "Kitchen", "prompt": "park at night", "iteration": 1})
        self.assertEqual(response.status_code, 200, response.text)
        custom = response.json()
        self.assertTrue(custom["background_id"].startswith("custom_"))
        listed = {item["id"]: item for item in assets.list_backgrounds()}
        self.assertEqual(listed[custom["background_id"]]["name"], "Kitchen")
        self.assertEqual(hashlib.sha256(master.read_bytes()).hexdigest(), before)
        self.assertEqual(self.client.get(custom["url"]).content, self.client.get(preview["preview_url"]).content)
        self.assertTrue(assets.resolve_background(custom["background_id"]).is_relative_to(self.directory))
        self.assertEqual(self.client.delete("/api/characters/background/kitchen").status_code, 400)
        self.assertEqual(self.client.delete("/api/characters/background/" + custom["background_id"]).status_code, 200)
        self.assertEqual(self.client.get(custom["url"]).status_code, 404)

    def test_background_save_binds_exact_preview_version(self):
        first = self.preview_background(1)
        second = self.preview_background(1)
        self.assertNotEqual(first["preview_id"], second["preview_id"])
        body = {"preview_id": first["preview_id"], "name": "Renamed", "prompt": "park at night", "iteration": 2}
        self.assertEqual(self.client.post("/api/characters/save_background", json=body).status_code, 409)
        body["iteration"] = 1
        body["prompt"] = "different"
        self.assertEqual(self.client.post("/api/characters/save_background", json=body).status_code, 409)
        body["prompt"] = "park at night"
        body["history"] = ["unreviewed changes"]
        self.assertEqual(self.client.post("/api/characters/save_background", json=body).status_code, 409)
        body["history"] = []
        self.assertEqual(self.client.post("/api/characters/save_background", json=body).status_code, 200)

    def test_preview_traversal_and_missing_assets_fail_closed(self):
        self.assertEqual(self.client.get("/api/characters/preview/..%5Csecret").status_code, 422)
        self.assertEqual(self.client.get("/api/characters/sprite/not_a_character.png").status_code, 404)
        self.assertEqual(self.client.get("/api/characters/background/bg_missing.png").status_code, 404)
        with self.assertRaises(ValueError):
            assets.image_path("sprites", "..\\escape.png")

    def test_runtime_manifest_matches_director_and_custom_library(self):
        self.assertIn("crying", assets.get_character_poses()["luca"])
        plan = director._validate_and_sanitize_plan({
            "background_id": "park", "characters": [{"name": "luca", "pose": "crying"}], "stickers": []}, {})
        self.assertEqual(plan["characters"][0]["pose"], "crying")
        with self.assertRaises(ValueError):
            director._validate_and_sanitize_plan({
                "characters": [{"name": "unknown", "pose": "default"}], "stickers": []}, {})
        with self.assertRaises(FileNotFoundError):
            assets.resolve_sprite("luca", "missing")

    def test_fallback_reports_unavailable_pose_and_resolves_replacement(self):
        plan = director._heuristic_fallback_director({"english": "Let us stack blocks.", "background": "park"})
        self.assertTrue(plan["warnings"])
        for char in plan["characters"]:
            self.assertTrue(assets.resolve_sprite(char["name"], char["pose"]).is_file())

    def test_provider_failure_is_disclosed_and_stickers_are_resolvable(self):
        with patch.object(director, "generate_ai_text", side_effect=RuntimeError("offline test")):
            plan = director.direct_single_scene({"english": "Goodbye!", "background": "park"})
        self.assertEqual(plan["direction_method"], "deterministic_fallback")
        self.assertTrue(plan["warnings"])
        for sticker in plan["stickers"]:
            self.assertTrue(Path(stickers.resolve_sticker_image(sticker["id"])).is_file())

    def test_director_preserves_custom_background(self):
        preview = self.preview_background()
        custom = self.client.post("/api/characters/save_background", json={
            "preview_id": preview["preview_id"], "name": "Park", "prompt": "park at night", "iteration": 1}).json()
        plan = director._validate_and_sanitize_plan({
            "background_id": "living_room", "characters": [{"name": "luca", "pose": "crying"}]},
            {"background": custom["background_id"]})
        self.assertEqual(plan["background"], custom["background_id"])

    def test_latest_background_refinement_wins(self):
        self.assertEqual(backgrounds.background_state("mountains at night", ["make it a beach", "sunny daytime"]),
                         ("beach", "sunny"))
        self.assertEqual(backgrounds.background_state("park at night", ["no night"]), ("park", "sunny"))
        self.assertEqual(backgrounds.background_state("kitchen", ["teaching kindness"]), ("kitchen", ""))

    def test_shirt_recolor_uses_original_signed_channels(self):
        source = self.directory / "source.png"
        raw = np.zeros((100, 20, 4), dtype=np.uint8)
        raw[:] = [250, 204, 21, 255]
        Image.fromarray(raw).save(source)
        out = self.directory / "blue.png"
        with patch.object(sprites, "get_character_poses", return_value={"luca": ["default"]}), \
             patch.object(sprites, "resolve_sprite", return_value=source):
            sprites.generate_custom_character_sprite("luca", "blue shirt", str(out))
        with Image.open(out) as image:
            colors = np.array(image)
        self.assertTrue(np.any(np.all(colors[:, :, :3] == [30, 122, 237], axis=-1)))
        raw[:] = [250, 240, 240, 255]
        Image.fromarray(raw).save(source)
        with patch.object(sprites, "get_character_poses", return_value={"levi": ["default"]}), \
             patch.object(sprites, "resolve_sprite", return_value=source):
            sprites.generate_custom_character_sprite("levi", "blue shirt", str(out))
        with Image.open(out) as image:
            colors = np.array(image)
        opaque = colors[:, :, 3] == 255
        self.assertTrue(np.all(colors[:, :, :3][opaque] == [250, 240, 240]))

    def test_services_refuse_master_output(self):
        with self.assertRaises(ValueError):
            sprites.generate_custom_character_sprite("levi", "blue", str(assets.MASTER_ASSETS / "sprites" / "levi.png"))
        with patch.object(backgrounds, "resolve_background", side_effect=AssertionError("must reject before reading")):
            with self.assertRaises(ValueError):
                backgrounds.generate_iterative_background("park", [], str(assets.MASTER_ASSETS / "backgrounds" / "bg_park.png"))

    def test_badge_cache_is_definition_addressed_and_blank_translation_stays_blank(self):
        a = {"id": "shared", "type": "word", "content": "晚安", "english": ""}
        b = {**a, "content": "早晨", "english": "Good morning"}
        first = Path(stickers.get_or_render_sticker(a))
        second = Path(stickers.get_or_render_sticker(b))
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_relative_to(self.directory))
        self.assertEqual(stickers.resolve_sticker_image(first.stem), str(first))
        metadata = json.loads(first.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["english"], "")
        self.assertEqual(stickers.get_or_render_sticker({"id": first.stem}), str(first))

    def test_unknown_sticker_does_not_generate_filename_text_or_star(self):
        before = set(self.directory.rglob("*"))
        self.assertEqual(self.client.get("/api/scene-director/stickers/render/badge_unknown.png").status_code, 404)
        with self.assertRaises(ValueError):
            stickers.get_or_render_sticker({"id": "prop_unicorn", "type": "icon", "content": "unicorn"})
        self.assertEqual(set(self.directory.rglob("*")), before)

    def test_legacy_approved_sticker_reuses_art_not_filename_vocabulary(self):
        legacy = assets.MASTER_ASSETS / "stickers" / "word_hiking.png"
        result = stickers.get_or_render_sticker({
            "id": "word_hiking", "type": "word", "content": "word_hiking", "english": ""})
        self.assertEqual(Path(result), legacy)

    def test_accessories_require_approved_art(self):
        with self.assertRaises(ValueError):
            sprites.generate_custom_character_sprite("levi", "superhero cape", str(self.directory / "cape.png"))
        self.assertFalse((self.directory / "cape.png").exists())

    def test_maintenance_defaults_to_candidates_and_requires_explicit_promotion(self):
        from scripts import maintenance_guard as guard
        target = self.directory / "approved" / "sprites" / "levi_default.png"
        with patch.object(guard, "ASSETS_ROOT", self.directory / "approved"), \
             patch.object(guard, "PROJECT_ROOT", self.directory):
            guard.configure_cli([])
            staged = guard.output_path(target)
            self.assertEqual(staged, self.directory / "artwork" / "candidates" / "assets" / "sprites" / "levi_default.png")
            self.assertFalse(target.exists())
            self.assertFalse(staged.exists())
            guard.configure_cli(["--promote"])
            self.assertEqual(guard.output_path(target), target)
            with self.assertRaises(ValueError):
                guard.output_path(self.directory / "approved" / "characters" / "levi.png")
            guard.configure_cli([])

    def test_fallback_materializes_typed_badges_before_preview(self):
        plan = director._heuristic_fallback_director({"english": "Goodbye!", "background": "park"})
        badge = plan["stickers"][0]
        self.assertEqual(badge["content"], "拜拜")
        self.assertTrue(badge["id"].startswith("generated_"))
        self.assertEqual(self.client.get("/api/scene-director/stickers/render/" + badge["id"]).status_code, 200)
        plan = director._heuristic_fallback_director({"english": "Dad teaches Levi to share.", "background": "park"})
        self.assertNotIn("grandparents_maternal", [c["name"] for c in plan["characters"]])
        self.assertFalse(any(s.get("content") == "dim_sum_basket" for s in plan["stickers"]))

    def test_tweaks_handle_negation_and_remove_without_adding(self):
        base = {"background": "park", "characters": [{"name": "levi", "pose": "default"}], "stickers": []}
        self.assertEqual(director.apply_copilot_tweak(base, "Levi 唔開心")["characters"][0]["pose"], "sad")
        self.assertNotIn("dog", [c["name"] for c in director.apply_copilot_tweak(base, "remove the dog")["characters"]])
        added = director.apply_copilot_tweak(base, "add the dog")
        self.assertIn("dog", [c["name"] for c in added["characters"]])
        removed = director.apply_copilot_tweak(added, "remove the dog")
        self.assertNotIn("dog", [c["name"] for c in removed["characters"]])
        unchanged = director.apply_copilot_tweak(base, "do not add the dog")
        self.assertNotIn("dog", [c["name"] for c in unchanged["characters"]])

    def test_module_import_does_not_write_or_generate(self):
        with patch.object(stickers, "get_or_render_sticker", side_effect=AssertionError("import generated")):
            with patch("PIL.Image.Image.save", side_effect=AssertionError("import wrote")):
                importlib.reload(stickers)

    def test_isolation_preserves_enclosed_white_and_existing_alpha(self):
        source = self.directory / "white.png"
        target = self.directory / "isolated.png"
        image = Image.new("RGB", (24, 24), "white")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 18, 18), fill="white", outline="black", width=2)
        image.save(source)
        isolate_sprite_from_white_bg(str(source), str(target))
        with Image.open(target) as result:
            self.assertEqual(result.getpixel((12, 12))[3], 255)
            self.assertEqual(result.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
