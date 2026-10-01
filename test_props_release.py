"""Regression checks for the recovered prop expansion; run in an isolated copy."""

import hashlib
import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.scene_director_service import _heuristic_fallback_director, DIRECTOR_SYSTEM_PROMPT
from app.services.sticker_service import STICKER_CATALOG, get_or_render_sticker

ROOT = Path(__file__).resolve().parent


class TestPropsRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "config" / "props_release_v2.json").read_text(encoding="utf-8"))
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_exact_saved_count_missing_excluded(self):
        self.assertEqual(len(self.manifest["assets"]), 56)
        ids = {a["id"] for a in self.manifest["assets"]}
        self.assertEqual(len(ids), 56)
        self.assertEqual(len(self.manifest["excluded_unrecovered_ids"]), 8)
        self.assertFalse(ids.intersection(self.manifest["excluded_unrecovered_ids"]))

    def test_export_integrity_and_catalog_routes(self):
        catalog = {s["id"]: s for s in STICKER_CATALOG}
        for asset in self.manifest["assets"]:
            with self.subTest(asset=asset["id"]):
                path = ROOT / asset["runtime_path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertLessEqual(max(image.size), 1024)
                    self.assertEqual(image.getchannel("A").getbbox(), (8, 8, image.width - 8, image.height - 8))
                self.assertEqual(catalog[asset["id"]]["chinese"], asset["chinese"])
                response = self.client.get("/api/scene-director/stickers/render/" + asset["id"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), asset["sha256"])
                with self.assertRaises(ValueError):
                    get_or_render_sticker({"id": asset["id"]}, force=True)

    def test_toy_and_food_direction(self):
        for cue, expected in [("rocking horse", "prop_rocking_horse"),
                              ("垃圾車", "prop_garbage_truck"),
                              ("楊桃", "prop_starfruit"), ("炸雞", "prop_fried_chicken_plate"),
                              ("西瓜同紅燈籠椒", "prop_red_bell_pepper")]:
            with self.subTest(cue=cue):
                self.assertIn(expected, DIRECTOR_SYSTEM_PROMPT)
                plan = _heuristic_fallback_director({"title": cue})
                self.assertIn(expected, [s["id"] for s in plan["stickers"]])


if __name__ == "__main__":
    unittest.main()
