"""Regression tests for authoritative sticker UI categories."""

import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

from app.services.sticker_categories import UI_CATEGORY_LABELS, UI_CATEGORY_ORDER
from app.services.sticker_service import get_all_stickers_catalog


ROOT = Path(__file__).resolve().parent
CATALOG_URL = "/api/scene-director/stickers/catalog"


def _catalog_by_id():
    return {item["id"]: item for item in get_all_stickers_catalog()}


class TestStickerCategoryMetadata(unittest.TestCase):
    def test_catalog_assigns_one_authoritative_non_all_bucket(self):
        for item in get_all_stickers_catalog():
            with self.subTest(sticker=item["id"]):
                self.assertIn(item.get("ui_category"), UI_CATEGORY_ORDER)
                self.assertEqual(item.get("display_category"), UI_CATEGORY_LABELS[item["ui_category"]])

    def test_explicit_complaint_fixes(self):
        catalog = _catalog_by_id()
        expected = {
            "sticker_man_man_lai": ("word", "WordBadges"),
            "badge_dog": ("word", "WordBadges"),
            "badge_duckling": ("word", "WordBadges"),
            "badge_mealtime": ("word", "WordBadges"),
            "badge_spoon": ("word", "WordBadges"),
            "vocab_banana": ("word", "WordBadges"),
            "prop_duckling": ("icon", "Animals"),
            "prop_toddler_bowl": ("icon", "OtherProps"),
            "prop_sippy_cup": ("icon", "OtherProps"),
            "prop_milk_bottle": ("icon", "OtherProps"),
            "prop_balloon_red": ("icon", "OtherProps"),
            "prop_balloon_yellow": ("icon", "OtherProps"),
            "prop_balloon_blue": ("icon", "OtherProps"),
            "prop_balloon_green": ("icon", "OtherProps"),
            "prop_hot_air_balloon": ("icon", "Vehicles"),
            "prop_starfruit": ("icon", "FoodFruit"),
        }
        for sticker_id, (expected_type, expected_category) in expected.items():
            with self.subTest(sticker=sticker_id):
                self.assertEqual(catalog[sticker_id]["type"], expected_type)
                self.assertEqual(catalog[sticker_id]["display_category"], expected_category)

        for food_bowl in ("prop_rice_bowl", "prop_congee_bowl", "prop_noodle_bowl", "prop_yogurt_bowl", "prop_oatmeal_bowl"):
            with self.subTest(sticker=food_bowl):
                self.assertEqual(catalog[food_bowl]["display_category"], "FoodFruit")

    def test_portable_gallery_preserves_release_count_and_uses_effective_categories(self):
        data_marker = '<script id="asset-data" type="application/json">'
        html = (ROOT / "generated-asset-portal.html").read_text(encoding="utf-8")
        start = html.index(data_marker) + len(data_marker)
        end = html.index("</script>", start)
        data = json.loads(html[start:end])
        assets = {asset["id"]: asset for asset in data["assets"]}
        self.assertEqual(len(assets), 403)
        self.assertEqual(assets["prop_starfruit"]["category"], "Food & fruit")
        self.assertEqual(assets["prop_hot_air_balloon"]["category"], "Vehicles")
        self.assertEqual(assets["prop_block_tower"]["category"], "Toys")
        self.assertEqual(assets["bg_supermarket"]["category"], "Backgrounds")
        for optional_static_prop in ("prop_balloon_red", "prop_balloon_yellow", "prop_balloon_blue", "prop_balloon_green"):
            if optional_static_prop in assets:
                self.assertEqual(assets[optional_static_prop]["category"], "Other props")


class TestStickerCategoryBrowserParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise unittest.SkipTest("Playwright is not installed; skipping browser parity test") from exc
        cls.sync_playwright = staticmethod(sync_playwright)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(cls.base_url + CATALOG_URL, timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        else:
            cls.server.terminate()
            raise RuntimeError("Timed out waiting for test server")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=10)

    def test_studio_and_review_filters_match_api_metadata_for_full_catalog(self):
        complaint_ids = [
            "sticker_man_man_lai",
            "badge_dog",
            "badge_duckling",
            "badge_mealtime",
            "badge_spoon",
            "vocab_banana",
            "prop_toddler_bowl",
            "prop_sippy_cup",
            "prop_milk_bottle",
            "prop_balloon_red",
            "prop_balloon_yellow",
            "prop_balloon_blue",
            "prop_balloon_green",
            "prop_hot_air_balloon",
            "prop_rice_bowl",
            "prop_congee_bowl",
            "prop_noodle_bowl",
            "prop_yogurt_bowl",
            "prop_oatmeal_bowl",
            "prop_starfruit",
            "prop_duckling",
        ]
        studio_categories = ["word", "phonics", "vehicles", "toys", "shapes", "food", "animals", "other"]
        review_categories = ["word", "block", "vehicle", "toy", "shape", "food", "animal", "other"]
        review_to_studio = {
            "word": "word", "block": "phonics", "vehicle": "vehicles", "toy": "toys",
            "shape": "shapes", "food": "food", "animal": "animals", "other": "other",
        }

        with self.sync_playwright() as playwright:
            browser = None
            try:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
            except Exception as edge_error:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Exception as chromium_error:
                    self.skipTest(f"No Playwright browser available: Edge={edge_error}; Chromium={chromium_error}")
            context = browser.new_context()
            try:
                page = context.new_page()
                page.goto(self.base_url + "/review", wait_until="domcontentloaded")
                review = page.evaluate(
                    """async ({categories, catalogUrl}) => {
                        const data = await (await fetch(catalogUrl)).json();
                        return Object.fromEntries(data.stickers.map(sticker => [
                          sticker.id,
                          categories.filter(category => isStickerMatch(sticker, category))
                        ]));
                    }""",
                    {"categories": review_categories, "catalogUrl": CATALOG_URL},
                )
                page.goto(self.base_url + "/", wait_until="domcontentloaded")
                studio = page.evaluate(
                    """async ({categories, catalogUrl}) => {
                        const data = await (await fetch(catalogUrl)).json();
                        return Object.fromEntries(data.stickers.map(sticker => [
                          sticker.id,
                          categories.filter(category => isStorybookStickerCategory(sticker, category))
                        ]));
                    }""",
                    {"categories": studio_categories, "catalogUrl": CATALOG_URL},
                )
            finally:
                context.close()
                browser.close()

        self.assertEqual(set(studio), set(review))
        for sticker_id in studio:
            with self.subTest(sticker=sticker_id):
                self.assertEqual(len(studio[sticker_id]), 1)
                self.assertEqual(len(review[sticker_id]), 1)
                self.assertEqual(studio[sticker_id][0], review_to_studio[review[sticker_id][0]])
        for sticker_id in complaint_ids:
            self.assertIn(sticker_id, studio)


if __name__ == "__main__":
    unittest.main()
