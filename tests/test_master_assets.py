import unittest
from pathlib import Path

from PIL import Image


ASSETS = Path(__file__).resolve().parents[1] / "assets"


class MasterArtworkTests(unittest.TestCase):
    def test_master_backgrounds_remain_hd(self):
        names = (
            "living_room", "nursery", "kitchen", "playroom", "beach",
            "park", "mountains", "dining", "bathroom", "reading_nook",
            "art_room", "supermarket",
        )
        for name in names:
            with self.subTest(background=name):
                with Image.open(ASSETS / "backgrounds" / f"bg_{name}.png") as image:
                    self.assertEqual(image.size, (1920, 1080))

    def test_family_anchors_have_visible_transparent_sprites(self):
        names = (
            "levi", "luca", "dad", "mom", "dog",
            "grandparents_paternal", "grandparents_maternal", "auntie_cousins",
        )
        for name in names:
            with self.subTest(character=name):
                with Image.open(ASSETS / "sprites" / f"{name}_default.png") as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertIsNotNone(image.getchannel("A").getbbox())


if __name__ == "__main__":
    unittest.main()
