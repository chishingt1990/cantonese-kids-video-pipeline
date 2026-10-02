"""Regression tests for reviewed legacy sticker cleanup and alias safety."""

import hashlib
import json
from pathlib import Path
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.routers.scene_director import router
from app.services.scene_director_service import _validate_and_sanitize_plan
from app.services.sticker_service import (
    LEGACY_STICKER_ALIASES,
    get_all_stickers_catalog,
    get_or_render_sticker,
    resolve_sticker_id,
)


ROOT = Path(__file__).resolve().parent


class TestLegacyStickerCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_catalog_hides_only_reviewed_aliases_and_keeps_word_prop_pairs(self):
        catalog = {item["id"]: item for item in get_all_stickers_catalog()}
        self.assertEqual(len(catalog), len(get_all_stickers_catalog()))
        for hidden in LEGACY_STICKER_ALIASES:
            self.assertNotIn(hidden, catalog)

        self.assertIn("badge_duckling", catalog)
        self.assertIn("prop_duckling", catalog)
        self.assertEqual(catalog["badge_duckling"]["type"], "word")
        self.assertEqual(catalog["prop_duckling"]["type"], "icon")
        self.assertEqual(catalog["badge_duckling"]["chinese"], "鴨仔")

        self.assertIn("vocab_banana", catalog)
        self.assertIn("prop_banana", catalog)
        self.assertEqual(catalog["vocab_banana"]["type"], "word")
        self.assertEqual(catalog["prop_banana"]["type"], "icon")
        self.assertEqual(catalog["vocab_banana"]["english"], "BANANA")

        # Unreviewed/custom discovered files should remain selectable instead of
        # being removed by a release-only allowlist.
        self.assertIn("sticker_man_man_lai", catalog)

    def test_legacy_alias_render_matches_canonical_without_cycles(self):
        for old_id, canonical_id in LEGACY_STICKER_ALIASES.items():
            with self.subTest(old_id=old_id):
                self.assertEqual(resolve_sticker_id(old_id), canonical_id)
                self.assertEqual(resolve_sticker_id(canonical_id), canonical_id)
                old_path = Path(get_or_render_sticker({"id": old_id}))
                canonical_path = Path(get_or_render_sticker({"id": canonical_id}))
                self.assertEqual(old_path, canonical_path)
                response = self.client.get(f"/api/scene-director/stickers/render/{old_id}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), hashlib.sha256(canonical_path.read_bytes()).hexdigest())

    def test_preview_endpoint_uses_full_legacy_sticker_info_like_export(self):
        old_scene_sticker = {
            "id": "badge_play_together",
            "type": "word",
            "content": "輪流玩",
            "english": "Take Turns & Share",
            "color_theme": "purple",
        }
        export_path = Path(get_or_render_sticker(old_scene_sticker))
        response = self.client.get(
            "/api/scene-director/stickers/render/badge_play_together.png",
            params={k: v for k, v in old_scene_sticker.items() if k != "id"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(hashlib.sha256(response.content).hexdigest(), hashlib.sha256(export_path.read_bytes()).hexdigest())
        self.assertEqual(export_path.name, "badge_take_turns_v1.png")

        default_response = self.client.get("/api/scene-director/stickers/render/badge_play_together.png")
        default_path = ROOT / "assets" / "stickers" / "badge_play_together_v1.png"
        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(hashlib.sha256(default_response.content).hexdigest(), hashlib.sha256(default_path.read_bytes()).hexdigest())

    def test_director_and_export_use_same_alias_resolution(self):
        plan = _validate_and_sanitize_plan({
            "characters": [{"name": "levi", "pose": "default"}],
            "stickers": [
                {"id": "word_take_turns", "type": "word", "content": "輪流", "english": "OLD"},
                {"id": "badge_play_together", "type": "word", "content": "輪流玩", "english": "Take Turns & Share"},
                {"id": "prop_toy_car_red", "type": "icon", "content": "toy_car_red"},
            ],
        }, {})
        by_id = {s["legacy_id"]: s for s in plan["stickers"] if "legacy_id" in s}
        self.assertEqual(by_id["word_take_turns"]["id"], "badge_take_turns_v1")
        self.assertEqual(by_id["word_take_turns"]["content"], "輪住玩")
        self.assertEqual(by_id["badge_play_together"]["id"], "badge_take_turns_v1")
        self.assertEqual(by_id["prop_toy_car_red"]["id"], "prop_toy_car")

    def test_local_replacements_have_real_alpha_and_are_distinct(self):
        paths = {
            name: ROOT / "assets" / "stickers" / f"{name}.png"
            for name in ("prop_comfort_hearts", "prop_sparkle_cluster", "badge_vocab_A 係 Ap", "badge_vocab_C 係 Ca")
        }
        self.assertNotEqual(hashlib.sha256(paths["prop_comfort_hearts"].read_bytes()).hexdigest(),
                            hashlib.sha256(paths["prop_sparkle_cluster"].read_bytes()).hexdigest())
        for name, path in paths.items():
            with self.subTest(name=name):
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    alpha = image.getchannel("A")
                    self.assertIsNotNone(alpha.getbbox())
                    self.assertGreater(sum(1 for px in alpha.getdata() if px > 128), 1500)
                    if name.startswith("prop_"):
                        # Guard against the prior blank white-circle placeholder.
                        self.assertGreater(len(image.convert("RGB").getcolors(maxcolors=1000000)), 10)

    def test_approved_release_hashes_unchanged(self):
        for manifest_name in (
            "artwork_release_v1.json",
            "phonics_release_v2.json",
            "props_release_v2.json",
            "family_release_v3.json",
            "family_interactions_v4.json",
        ):
            manifest = json.loads((ROOT / "config" / manifest_name).read_text(encoding="utf-8"))
            for asset in manifest["assets"]:
                with self.subTest(manifest=manifest_name, asset=asset["id"]):
                    path = ROOT / asset["runtime_path"]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])


if __name__ == "__main__":
    unittest.main()
