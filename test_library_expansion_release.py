"""Release checks for the 100-sticker library expansion v5."""

import hashlib
import importlib.util
import json
import re
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.scene_director_service import _heuristic_fallback_director, DIRECTOR_SYSTEM_PROMPT
from app.services.sticker_service import (
    get_all_stickers_catalog,
    get_or_render_sticker,
)


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "config" / "library_expansion_v5.json"


class TestLibraryExpansionRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.assets = cls.manifest["assets"]
        cls.by_id = {asset["id"]: asset for asset in cls.assets}
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_manifest_counts_unique_hashes_and_no_private_data(self):
        self.assertEqual(self.manifest["release_id"], "library_expansion_v5")
        self.assertEqual(self.manifest["asset_count"], 100)
        self.assertEqual(self.manifest["prior_portal_asset_count"], 274)
        self.assertEqual(self.manifest["expected_portal_asset_count"], 374)
        self.assertEqual(
            self.manifest["partitions"],
            {"vehicles": 20, "toys": 20, "shapes": 12, "foodfruit": 28, "animals": 20},
        )
        self.assertEqual(len(self.assets), 100)
        self.assertEqual(len(self.by_id), 100)
        self.assertEqual(len({asset["sha256"] for asset in self.assets}), 100)
        text = MANIFEST.read_text(encoding="utf-8")
        for forbidden in (
            "C:\\Users",
            "C:/Users",
            "/Users/",
            "conversation_url",
            "communication_log_id",
            "approval_evidence",
            "runner-stdout",
            "runner-stderr",
            "microsoft.com",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_png_integrity_padding_and_manifest_dimensions(self):
        for asset in self.assets:
            with self.subTest(asset=asset["id"]):
                path = ROOT / asset["runtime_path"]
                self.assertTrue(path.exists())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(list(image.size), asset["size"])
                    alpha = image.getchannel("A")
                    self.assertEqual(alpha.getbbox(), (8, 8, image.width - 8, image.height - 8))
                    self.assertEqual(alpha.getextrema(), (0, 255))
                    self.assertGreater(sum(1 for value in alpha.getdata() if value > 128), 1500)
                self.assertFalse(asset["processing"]["rgb_changes"])
                self.assertEqual(asset["processing"]["resampling"], "none")
                self.assertEqual(asset["processing"]["transparent_padding_each_side"], 8)

    def test_shape_geometry_stays_distinct(self):
        expected = {
            "shape_circle": (0.95, 1.05),
            "shape_rectangle": (1.45, 1.55),
            "shape_oval": (1.38, 1.50),
            "shape_semicircle": (1.85, 2.05),
        }
        for asset_id, (low, high) in expected.items():
            with self.subTest(shape=asset_id):
                path = ROOT / self.by_id[asset_id]["runtime_path"]
                with Image.open(path) as image:
                    bbox = image.getchannel("A").getbbox()
                ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
                self.assertGreaterEqual(ratio, low)
                self.assertLessEqual(ratio, high)
                self.assertEqual(self.by_id[asset_id]["kind"], "shape")
                self.assertEqual(self.by_id[asset_id]["catalog_type"], "shape")

    def test_catalog_api_render_and_get_or_render_use_exact_bytes(self):
        catalog = {item["id"]: item for item in get_all_stickers_catalog()}
        for asset in self.assets:
            with self.subTest(asset=asset["id"]):
                item = catalog[asset["id"]]
                self.assertEqual(item["label"], f"{asset['chinese']} ({asset['name']})")
                self.assertEqual(item["category"], asset["category"])
                expected_type = "shape" if asset["kind"] == "shape" else "icon"
                self.assertEqual(item["type"], expected_type)
                response = self.client.get(f"/api/scene-director/stickers/render/{asset['id']}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), asset["sha256"])
                self.assertEqual(hashlib.sha256(Path(get_or_render_sticker(item)).read_bytes()).hexdigest(), asset["sha256"])

    def test_word_prop_distinction_and_custom_discovery_survive(self):
        catalog = {item["id"]: item for item in get_all_stickers_catalog()}
        self.assertEqual(catalog["vocab_banana"]["type"], "word")
        self.assertEqual(catalog["vocab_banana"]["english"], "BANANA")
        self.assertEqual(catalog["prop_banana"]["type"], "icon")
        self.assertIn("sticker_man_man_lai", catalog)

    def test_director_prompt_and_explicit_queries_cover_new_assets(self):
        for asset_id in ("prop_zebra", "prop_canoe", "prop_toy_drum", "shape_circle"):
            with self.subTest(asset=asset_id):
                self.assertIn(asset_id, DIRECTOR_SYSTEM_PROMPT)
        for cue, expected in (
            ("Look at the zebra together", "prop_zebra"),
            ("Point to the canoe", "prop_canoe"),
            ("Find the circle shape", "shape_circle"),
        ):
            with self.subTest(cue=cue):
                plan = _heuristic_fallback_director({"title": cue})
                self.assertIn(expected, [s["id"] for s in plan["stickers"]])

    def test_asset_portal_totals_and_categories(self):
        spec = importlib.util.spec_from_file_location(
            "build_asset_portal", ROOT / "scripts" / "build_asset_portal.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = module.build()
        text = Path(output).read_text(encoding="utf-8")
        match = re.search(r'<script id="asset-data" type="application/json">(.*?)</script>', text)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(len(data["assets"]), 374)
        self.assertEqual(len([a for a in data["assets"] if a["batch"] == "Library expansion v5"]), 100)
        v5 = [a for a in data["assets"] if a["batch"] == "Library expansion v5"]
        self.assertEqual(len([a for a in v5 if a["category"] == "Shapes"]), 12)
        self.assertEqual(len([a for a in v5 if a["category"] == "Animals"]), 20)
        self.assertEqual(len([a for a in data["assets"] if a.get("family_buckets")]), 91)
        self.assertNotIn("file:///", text)
        self.assertNotIn("conversation_url", text)


if __name__ == "__main__":
    unittest.main()
