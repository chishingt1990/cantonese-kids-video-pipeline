"""Focused tests for local glyph-shaped phonics sticker release."""

import hashlib
import json
import re
import time
import unittest
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.sticker_service import get_all_stickers_catalog, get_or_render_sticker, generate_toy_block
from scripts.build_asset_portal import build as build_asset_portal

ROOT = Path(__file__).resolve().parent
PHONICS_PATH = ROOT / "config" / "phonics_release_v2.json"


def has_enclosed_alpha_hole(alpha: np.ndarray) -> bool:
    transparent = alpha <= 5
    exterior = np.zeros_like(transparent, dtype=bool)
    stack = []
    h, w = transparent.shape
    for x in range(w):
        if transparent[0, x]:
            stack.append((0, x))
        if transparent[h - 1, x]:
            stack.append((h - 1, x))
    for y in range(h):
        if transparent[y, 0]:
            stack.append((y, 0))
        if transparent[y, w - 1]:
            stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        if exterior[y, x] or not transparent[y, x]:
            continue
        exterior[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and transparent[ny, nx] and not exterior[ny, nx]:
                stack.append((ny, nx))
    return bool(np.any(transparent & ~exterior))


class TestPhonicsRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(PHONICS_PATH.read_text(encoding="utf-8"))
        cls.assets = cls.manifest["assets"]
        cls.by_id = {asset["id"]: asset for asset in cls.assets}
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    def test_73_unique_ids_and_compatible_ids(self):
        ids = [asset["id"] for asset in self.assets]
        self.assertEqual(len(ids), 73)
        self.assertEqual(len(ids), len(set(ids)))
        for required in ("block_a", "block_b", "block_c", "block_1", "block_2", "block_3"):
            self.assertIn(required, self.by_id)
        self.assertEqual(len([a for a in self.assets if a["kind"] == "letter"]), 52)
        self.assertEqual(len([a for a in self.assets if a["kind"] == "number"]), 21)

    def test_png_dimensions_holes_alpha_and_no_enclosing_rectangle(self):
        for asset in self.assets:
            path = ROOT / asset["runtime_path"]
            self.assertTrue(path.exists(), asset["id"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset["sha256"])
            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(list(image.size), asset["dimensions"])
                alpha = np.array(image.getchannel("A"))
            self.assertEqual(tuple(asset["dimensions"]), (220, 220))
            self.assertGreater(int(np.count_nonzero(alpha > 128)), 1500)
            ys, xs = np.where(alpha > 128)
            bbox = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
            self.assertGreaterEqual(bbox[0], 4, asset["id"])
            self.assertGreaterEqual(bbox[1], 4, asset["id"])
            self.assertLessEqual(bbox[2], 216, asset["id"])
            self.assertLessEqual(bbox[3], 216, asset["id"])
            self.assertGreaterEqual(max(bbox[2] - bbox[0], bbox[3] - bbox[1]), int(0.65 * 220), asset["id"])
            crop = alpha[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            self.assertEqual(
                int(max(alpha[0, :].max(), alpha[-1, :].max(), alpha[:, 0].max(), alpha[:, -1].max())),
                0,
                f"{asset['id']} touches the canvas edge",
            )
            if asset["content"] in {"A", "B", "0", "8"}:
                self.assertTrue(has_enclosed_alpha_hole(crop), f"{asset['id']} lost its interior hole")

    def test_catalog_labels_render_endpoint_and_cache(self):
        catalog = {item["id"]: item for item in get_all_stickers_catalog()}
        self.assertEqual(len([item for item in catalog.values() if item["id"] in self.by_id]), 73)
        for sticker_id in ("block_a", "block_lower_a", "block_0", "block_20"):
            self.assertIn(sticker_id, catalog)
            self.assertIn("(", catalog[sticker_id]["label"])
            path = Path(get_or_render_sticker(catalog[sticker_id]))
            before = (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
            time.sleep(0.001)
            self.assertEqual(Path(get_or_render_sticker(catalog[sticker_id])), path)
            after = (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(before, after)
            response = self.client.get(f"/api/scene-director/stickers/render/{sticker_id}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(hashlib.sha256(response.content).hexdigest(), before[1])

    def test_asset_portal_counts_189_and_categories(self):
        output = build_asset_portal()
        html = output.read_text(encoding="utf-8")
        match = re.search(r'<script id="asset-data" type="application/json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        # 189 pre-existing (60 artwork + 73 phonics + 56 props)
        #   + 53 family-expansion v3 (41 solo + 12 contact)
        #   + 32 family-interactions v4 (26 twin interactions + 6 four-person group composites)
        # = 274 unique assets.
        self.assertEqual(len(data["assets"]), 274)
        self.assertEqual(len(data["excluded"]), 8)
        self.assertIn("Letters", data["categories"])
        self.assertIn("Numbers", data["categories"])
        self.assertIn("Family sprites", data["categories"])
        self.assertIn("Family contacts", data["categories"])
        self.assertEqual(len([a for a in data["assets"] if a["category"] == "Letters"]), 52)
        self.assertEqual(len([a for a in data["assets"] if a["category"] == "Numbers"]), 21)
        self.assertEqual(len([a for a in data["assets"] if a["category"] == "Family sprites"]), 41)
        # v3 shipped 12 contact composites; v4 adds 32 (26 twin + 6 group) → 44.
        self.assertEqual(len([a for a in data["assets"] if a["category"] == "Family contacts"]), 44)
        self.assertNotIn("file:///", html)
        self.assertNotIn("copilot.cloud.microsoft/chat/conversation/", html)

    def test_legacy_renderer_respects_requested_size(self):
        for size in (120, 180, 220):
            with self.subTest(size=size):
                with generate_toy_block("A", size=size) as image:
                    self.assertEqual(image.size, (size, size))
                    self.assertEqual(image.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
