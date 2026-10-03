"""Release checks for the targeted artwork repair v6 promotion."""

import hashlib
import json
import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.sticker_service import get_all_stickers_catalog, get_or_render_sticker
from scripts.build_asset_portal import build as build_asset_portal


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "config" / "artwork_repairs_v6.json"


class TestArtworkRepairsV6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.assets = cls.manifest["assets"]
        cls.by_id = {asset["id"]: asset for asset in cls.assets}
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_manifest_counts_privacy_and_explicit_exclusion(self):
        self.assertEqual(self.manifest["release_id"], "artwork_repairs_v6")
        self.assertEqual(self.manifest["asset_count"], 29)
        self.assertEqual(self.manifest["prop_count"], 27)
        self.assertEqual(self.manifest["background_count"], 2)
        self.assertEqual(self.manifest["excluded_count"], 1)
        self.assertEqual(self.manifest["expected_portal_asset_count"], 403)
        self.assertEqual(len(self.assets), 29)
        self.assertEqual(len(self.by_id), 29)
        self.assertNotIn("prop_washcloth", self.by_id)
        self.assertEqual(self.manifest["excluded"][0]["id"], "prop_washcloth")
        washcloth_path = ROOT / "assets" / "stickers" / "prop_washcloth.png"
        self.assertEqual(
            hashlib.sha256(washcloth_path.read_bytes()).hexdigest(),
            self.manifest["excluded"][0]["previous_runtime_sha256"],
        )
        text = MANIFEST.read_text(encoding="utf-8")
        for forbidden in (
            "C:\\Users",
            "C:/Users",
            "/Users/",
            "conversation_url",
            "approval_evidence",
            "copilot.cloud.microsoft/chat",
            "m365.cloud.microsoft/chat",
            "batch-prompts",
            "prompt\":",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_prop_integrity_exact_bytes_and_catalog_categories(self):
        catalog = {item["id"]: item for item in get_all_stickers_catalog()}
        expected_categories = {
            "prop_block_tower": "Toys",
            "prop_banana": "FoodFruit",
            "prop_kitty_cat": "Animals",
            "prop_balloon_red": "OtherProps",
            "prop_sippy_cup": "OtherProps",
        }
        for asset in [a for a in self.assets if a["kind"] == "prop"]:
            with self.subTest(asset=asset["id"]):
                path = ROOT / asset["runtime_path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                self.assertEqual(hashlib.sha256(Path(get_or_render_sticker(catalog[asset["id"]])).read_bytes()).hexdigest(), asset["sha256"])
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(list(image.size), asset["size"])
                    self.assertEqual(list(image.size), [1254, 1254])
                    self.assertIsNotNone(image.getchannel("A").getbbox())
                response = self.client.get(f"/api/scene-director/stickers/render/{asset['id']}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), asset["sha256"])
        self.assertEqual(self.by_id["prop_block_tower"]["sha256"], "2929407ccf9936ed24191e25a28e063411e85427bb345c7e670c22fc33a7a56c")
        for sticker_id, display_category in expected_categories.items():
            with self.subTest(sticker=sticker_id):
                self.assertEqual(catalog[sticker_id]["display_category"], display_category)

    def test_background_exports_are_16x9_rgb_crop_resize(self):
        for bg_id in ("bg_supermarket", "bg_art_room"):
            with self.subTest(background=bg_id):
                asset = self.by_id[bg_id]
                path = ROOT / asset["runtime_path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
                with Image.open(path) as image:
                    self.assertEqual(image.mode, "RGB")
                    self.assertEqual(image.size, (1920, 1080))
                crop = asset["processing"]["source_crop_ltrb"]
                self.assertEqual(crop, [0, 120, 1536, 984])
                self.assertEqual(crop[2] - crop[0], 1536)
                self.assertEqual(crop[3] - crop[1], 864)
                self.assertAlmostEqual((crop[2] - crop[0]) / (crop[3] - crop[1]), 16 / 9)
                self.assertIn("not a native generated-HD claim", asset["processing"]["resampling"])
                response = self.client.get(f"/api/characters/background/{Path(asset['runtime_path']).name}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(), asset["sha256"])

    def test_asset_portal_counts_unique_ids_and_repair_categories(self):
        output = build_asset_portal()
        text = output.read_text(encoding="utf-8")
        match = re.search(r'<script id="asset-data" type="application/json">(.*?)</script>', text)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        ids = [asset["id"] for asset in data["assets"]]
        self.assertEqual(len(ids), 403)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len([a for a in data["assets"] if a["batch"] == "Targeted repairs v6"]), 29)
        self.assertEqual(len([a for a in data["assets"] if a["category"] == "Backgrounds"]), 2)
        self.assertEqual(len(data["excluded"]), 9)
        self.assertIn("Backgrounds", data["categories"])
        self.assertNotIn("file:///", text)
        self.assertNotIn("conversation_url", text)


if __name__ == "__main__":
    unittest.main()
