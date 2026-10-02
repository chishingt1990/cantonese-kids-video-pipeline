"""Offline integration tests for the family-expansion v3 release.

Covers:
* Manifest cardinality, hash integrity, mode/RGBA and 8-pixel padding check.
* Alias runtime paths (``*_standing.png``) are byte-identical to their primary.
* ``family_catalog`` exposes the new individual poses and contact composites.
* ``characters`` router lists each new individual relative and each contact as
  a selectable character with the correct poses and sprite URLs.
* The sprite resolver returns the right bytes for direct names, batch-nickname
  aliases (``auntie_*`` -> ``aunt_sister_*``; ``cousin_ben_*`` -> ``cousin_younger_*``)
  and does NOT misclassify similar prefixes (``paternal_grandpa`` vs the legacy
  ``grandparents_paternal`` group file).
* The scene director keeps the new poses (does not collapse to ``default``),
  rejects truly unknown poses, drops duplicate inner members when a contact
  sprite is already selected, and surfaces the new vocabulary in the system
  prompt.
* The render-service scale lookup still classifies legacy IDs as adult/toddler/
  pet and classifies new relatives/contacts correctly.
* Previous releases (artwork v1, phonics v2, props v2) are unchanged by this
  release: their asset counts and 189-asset baseline total are preserved.
"""

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


class TestFamilyRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.scratch = Path(cls.temp.name)
        cls.manifest = json.loads((ROOT / "config" / "family_release_v3.json").read_text(encoding="utf-8"))
        (cls.scratch / "config").mkdir()
        for name in ("artwork_release_v1.json", "phonics_release_v2.json",
                     "props_release_v2.json", "family_release_v3.json"):
            source = ROOT / "config" / name
            if source.exists():
                shutil.copyfile(source, cls.scratch / "config" / name)
                for asset in json.loads(source.read_text(encoding="utf-8"))["assets"]:
                    target = cls.scratch / asset["runtime_path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / asset["runtime_path"], target)
                    for alias in asset.get("alias_runtime_paths", []):
                        alias_target = cls.scratch / alias
                        alias_target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(ROOT / alias, alias_target)
        # Copy the legacy anchor files that the resolver prefix tests depend on
        # (they live beside the new release files under assets/sprites/).
        for legacy in ("grandparents_paternal.png", "grandparents_paternal_default.png",
                       "grandparents_maternal.png", "grandparents_maternal_default.png",
                       "auntie_cousins.png", "auntie_cousins_default.png",
                       "auntie_cousins_waving.png",
                       "mom.png", "mom_default.png", "dad.png", "dad_default.png",
                       "levi.png", "levi_default.png", "luca.png", "luca_default.png",
                       "dog.png", "dog_default.png"):
            source = ROOT / "assets" / "sprites" / legacy
            if source.exists():
                target = cls.scratch / "assets" / "sprites" / legacy
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)

        def load(module_name, relative):
            target = cls.scratch / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
            spec = importlib.util.spec_from_file_location(module_name, target)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        cls.family = load("app.services.family_catalog", "app/services/family_catalog.py")
        cls.family_modules = patch.dict(sys.modules, {"app.services.family_catalog": cls.family})
        cls.family_modules.start()
        cls.addClassCleanup(cls.family_modules.stop)
        cls.glyph = load("app.services.glyph_sticker_service", "app/services/glyph_sticker_service.py")
        cls.glyph_modules = patch.dict(sys.modules, {"app.services.glyph_sticker_service": cls.glyph})
        cls.glyph_modules.start()
        cls.addClassCleanup(cls.glyph_modules.stop)
        cls.stickers = load("app.services.sticker_service", "app/services/sticker_service.py")
        cls.ai = types.ModuleType("app.services.ai_service")
        cls.ai.generate_ai_text = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline test"))
        cls.modules = patch.dict(sys.modules, {
            "app.services.sticker_service": cls.stickers,
            "app.services.ai_service": cls.ai,
        })
        cls.modules.start()
        cls.addClassCleanup(cls.modules.stop)
        cls.director = load("app.services.scene_director_service", "app/services/scene_director_service.py")
        cls.director_modules = patch.dict(sys.modules, {"app.services.scene_director_service": cls.director})
        cls.director_modules.start()
        cls.addClassCleanup(cls.director_modules.stop)
        cls.characters = load("app.routers.characters", "app/routers/characters.py")
        app = FastAPI()
        app.include_router(cls.characters.router)
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)

    # --- Manifest + file bytes -----------------------------------------
    def test_manifest_shape_and_counts(self):
        self.assertEqual(self.manifest["release_id"], "family_release_v3")
        self.assertEqual(self.manifest["status"], "approved_complete_release")
        self.assertEqual(len(self.manifest["assets"]), 53,
                         "53 approved assets expected (54 jobs minus the submission_uncertain one)")
        excluded = self.manifest["excluded_jobs"]
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["job_id"], "paternal_grandpa_seated_storytelling_r01")
        solo = [a for a in self.manifest["assets"] if a["category"] == "solo"]
        contact = [a for a in self.manifest["assets"] if a["category"] == "contact"]
        self.assertEqual(len(solo), 41)
        self.assertEqual(len(contact), 12)
        standalone_refs = [a for a in solo if a.get("is_standalone_reference")]
        self.assertEqual(len(standalone_refs), 7,
                         "One standalone standing reference per new identity")

    def test_all_release_hashes_padding_and_alias_integrity(self):
        for asset in self.manifest["assets"]:
            primary = ROOT / asset["runtime_path"]
            self.assertEqual(hashlib.sha256(primary.read_bytes()).hexdigest(), asset["sha256"],
                             f"Primary hash mismatch: {asset['runtime_path']}")
            with Image.open(primary) as image:
                self.assertEqual(image.mode, "RGBA")
                alpha = image.getchannel("A")
                self.assertEqual(alpha.getbbox(), (8, 8, image.width - 8, image.height - 8),
                                 f"Expected 8px transparent padding on every side: {asset['runtime_path']}")
                self.assertEqual(alpha.getextrema(), (0, 255),
                                 f"Alpha should include fully transparent and fully opaque pixels: {asset['runtime_path']}")
            # Processing provenance must match the sprite release convention.
            self.assertFalse(asset["processing"]["rgb_changes"])
            self.assertEqual(asset["processing"]["resampling"], "none")
            self.assertEqual(asset["processing"]["transparent_padding_each_side"], 8)
            for alias in asset.get("alias_runtime_paths", []):
                alias_path = ROOT / alias
                self.assertTrue(alias_path.exists(), f"Alias file missing: {alias}")
                self.assertEqual(primary.read_bytes(), alias_path.read_bytes(),
                                 f"Alias not byte-identical: {alias}")

    def test_prior_release_counts_are_untouched(self):
        prior = {
            "artwork_release_v1.json": 60,
            "phonics_release_v2.json": 73,
            "props_release_v2.json": 56,
        }
        total = 0
        for name, expected in prior.items():
            data = json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))
            self.assertEqual(len(data["assets"]), expected, name)
            total += expected
        self.assertEqual(total, 189, "189-asset legacy baseline must stay intact")
        self.assertEqual(total + len(self.manifest["assets"]), 242,
                         "Expected 189 + 53 = 242 unique assets after this release")

    # --- Catalog API ---------------------------------------------------
    def test_catalog_individual_poses_cover_each_character(self):
        poses = self.family.individual_poses()
        self.assertEqual(poses["paternal_grandpa"], ["default", "waving", "offering_food_or_gift"],
                         "Missing paternal_grandpa_seated_storytelling must drop that pose entirely")
        self.assertEqual(poses["paternal_grandma"],
                         ["default", "waving", "seated_storytelling", "offering_food_or_gift"])
        self.assertEqual(poses["aunt_sister"],
                         ["default", "waving", "crouching_to_talk", "playing_helping"])
        self.assertEqual(poses["cousin_ryan"],
                         ["default", "waving", "showing_toy", "passing_toy", "sitting_playing"])
        self.assertEqual(poses["cousin_younger"],
                         ["default", "waving", "showing_toy", "passing_toy", "sitting_playing"])
        self.assertEqual(poses["mom"],
                         ["listening_crouched", "reading_book", "offering_object",
                          "open_handed_explaining", "comforting_open_arms", "walking"])
        self.assertEqual(poses["dad"],
                         ["listening_crouched", "reading_book", "offering_object",
                          "open_handed_explaining", "comforting_open_arms", "walking"])

    def test_catalog_contact_sprites_metadata(self):
        contacts = {c["id"]: c for c in self.family.contact_sprites()}
        self.assertEqual(len(contacts), 12)
        for cid, members, action, scale in [
            ("contact_mom_levi_hug", ["mom", "levi"], "hug", "adult"),
            ("contact_maternal_grandpa_cousin_younger_hug",
             ["maternal_grandpa", "cousin_younger"], "hug", "adult"),
            ("contact_aunt_sister_cousin_ryan_handholding",
             ["aunt_sister", "cousin_ryan"], "handholding", "adult"),
            ("contact_mom_cousin_ryan_carrying_child",
             ["mom", "cousin_ryan"], "carrying_child", "adult"),
        ]:
            with self.subTest(contact=cid):
                self.assertIn(cid, contacts)
                self.assertEqual(contacts[cid]["members"], members)
                self.assertEqual(contacts[cid]["action"], action)
                self.assertEqual(contacts[cid]["scale_class"], scale)
        self.assertEqual(self.family.contact_members("contact_mom_levi_hug"), ["mom", "levi"])
        self.assertTrue(self.family.is_contact_id("contact_mom_levi_hug"))
        self.assertFalse(self.family.is_contact_id("mom"))

    def test_catalog_scale_class_covers_legacy_and_new(self):
        base = self.family.base_height_for
        # Legacy categories must keep their historical base heights so the
        # renderer behaviour matches the pre-release code path.
        self.assertEqual(base("mom"), 760)
        self.assertEqual(base("grandparents_paternal"), 760)
        self.assertEqual(base("levi"), 520)
        self.assertEqual(base("dog"), 320)
        # New family categories pick up their declared scale class.
        self.assertEqual(base("aunt_sister"), 760)
        self.assertEqual(base("maternal_grandma"), 760)
        self.assertEqual(base("cousin_ryan"), 640, "older_child base height is 640px")
        self.assertEqual(base("cousin_younger"), 520, "Ben is a toddler-size cousin")
        # Contact composites must size to the tallest participant, never the toddler.
        self.assertEqual(base("contact_mom_levi_hug"), 760)
        self.assertEqual(base("contact_maternal_grandma_levi_carrying_child"), 760)
        # Unknown IDs fall back to toddler base so pre-existing behaviour is kept.
        self.assertEqual(base("mystery_future_character"), 520)

    # --- Characters router endpoints ----------------------------------
    def test_characters_endpoint_lists_new_individuals_and_contacts(self):
        response = self.client.get("/api/characters/all")
        self.assertEqual(response.status_code, 200)
        chars = {c["id"]: c for c in response.json()["characters"]}
        # Legacy group IDs must still be present.
        for legacy in ("grandparents_paternal", "grandparents_maternal", "auntie_cousins",
                       "levi", "luca", "mom", "dad", "dog"):
            self.assertIn(legacy, chars, f"Legacy character disappeared: {legacy}")
        # New individuals.
        for new_id, expected_poses in [
            ("paternal_grandpa", ["default", "waving", "offering_food_or_gift"]),
            ("paternal_grandma", ["default", "waving", "seated_storytelling", "offering_food_or_gift"]),
            ("maternal_grandpa", ["default", "waving", "seated_storytelling", "offering_food_or_gift"]),
            ("maternal_grandma", ["default", "waving", "seated_storytelling", "offering_food_or_gift"]),
            ("aunt_sister", ["default", "waving", "crouching_to_talk", "playing_helping"]),
            ("cousin_ryan", ["default", "waving", "showing_toy", "passing_toy", "sitting_playing"]),
            ("cousin_younger", ["default", "waving", "showing_toy", "passing_toy", "sitting_playing"]),
        ]:
            with self.subTest(character=new_id):
                self.assertIn(new_id, chars)
                pose_ids = [p["id"] for p in chars[new_id]["poses"]]
                for pose in expected_poses:
                    self.assertIn(pose, pose_ids, f"{new_id} missing pose {pose}")
                self.assertEqual(chars[new_id]["family_release"], "v3")
        # All 12 contacts.
        contact_ids = [c["id"] for c in response.json()["characters"] if c["id"].startswith("contact_")]
        self.assertEqual(len(contact_ids), 12)
        for cid in contact_ids:
            self.assertEqual(chars[cid]["poses"][0]["id"], "default")
            self.assertTrue(chars[cid]["sprite_url"].startswith("/api/characters/sprite/contact_"))
            self.assertTrue(chars[cid]["members"], f"{cid} must expose members metadata")
        # Specific display sanity checks.
        self.assertIn("Ben", chars["cousin_younger"]["name"],
                      "cousin_younger must advertise Ben as the display name")
        self.assertIn("姑媽", chars["aunt_sister"]["name"])

    def test_sprite_endpoint_resolves_direct_and_alias_filenames(self):
        checks = [
            # Direct new filenames.
            ("paternal_grandpa_default.png", "paternal_grandpa_default.png"),
            ("paternal_grandpa_standing.png", "paternal_grandpa_standing.png"),
            ("paternal_grandma_seated_storytelling.png", "paternal_grandma_seated_storytelling.png"),
            ("cousin_younger_showing_toy.png", "cousin_younger_showing_toy.png"),
            ("aunt_sister_playing_helping.png", "aunt_sister_playing_helping.png"),
            ("contact_mom_levi_hug.png", "contact_mom_levi_hug.png"),
            ("contact_dad_cousin_younger_handholding.png", "contact_dad_cousin_younger_handholding.png"),
            # Batch-nickname aliases.
            ("auntie_waving.png", "aunt_sister_waving.png"),
            ("auntie_default.png", "aunt_sister_default.png"),
            ("cousin_ben_default.png", "cousin_younger_default.png"),
            ("cousin_ben_sitting_playing.png", "cousin_younger_sitting_playing.png"),
        ]
        sprites_dir = ROOT / "assets" / "sprites"
        for requested, expected_filename in checks:
            with self.subTest(filename=requested):
                response = self.client.get(f"/api/characters/sprite/{requested}")
                self.assertEqual(response.status_code, 200)
                expected_bytes = (sprites_dir / expected_filename).read_bytes()
                self.assertEqual(response.content, expected_bytes,
                                 f"{requested} should resolve to {expected_filename}")

    def test_sprite_endpoint_does_not_confuse_similar_prefixes(self):
        """paternal_grandpa_* must NOT fall back to grandparents_paternal.png."""
        sprites_dir = ROOT / "assets" / "sprites"
        # A new paternal_grandpa pose that exists in the family release.
        resp = self.client.get("/api/characters/sprite/paternal_grandpa_waving.png")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, (sprites_dir / "paternal_grandpa_waving.png").read_bytes())
        # An intentionally non-existent paternal_grandpa pose should fall back
        # to paternal_grandpa_default.png — NOT to grandparents_paternal_default.png
        # (the legacy group).
        resp = self.client.get("/api/characters/sprite/paternal_grandpa_jogging.png")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, (sprites_dir / "paternal_grandpa_default.png").read_bytes())
        self.assertNotEqual(resp.content, (sprites_dir / "grandparents_paternal_default.png").read_bytes())
        # Legacy group filename must still work unchanged.
        resp = self.client.get("/api/characters/sprite/grandparents_paternal_default.png")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, (sprites_dir / "grandparents_paternal_default.png").read_bytes())

    def test_auntie_cousins_legacy_group_is_not_rewritten_by_alias(self):
        """Regression: ``auntie_cousins_default.png`` / ``auntie_cousins_waving.png``
        must serve the exact legacy group bytes, not be rewritten by the
        ``auntie`` -> ``aunt_sister`` alias into a nonexistent file (which
        would then fall back to ``aunt_sister_default.png`` and silently
        break the legacy group default/waving on the stage).
        """
        sprites_dir = ROOT / "assets" / "sprites"
        checked = 0
        for legacy in ("auntie_cousins_default.png", "auntie_cousins_waving.png",
                       "auntie_cousins.png"):
            src = sprites_dir / legacy
            if not src.exists():
                continue  # Not all repos ship every variant historically.
            with self.subTest(filename=legacy):
                resp = self.client.get(f"/api/characters/sprite/{legacy}")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.content, src.read_bytes(),
                                 f"{legacy} must serve the legacy group bytes verbatim")
                aunt_default = (sprites_dir / "aunt_sister_default.png").read_bytes()
                self.assertNotEqual(
                    resp.content, aunt_default,
                    f"{legacy} must not have been rewritten to aunt_sister_default.png",
                )
                checked += 1
        self.assertGreaterEqual(
            checked, 2,
            "Expected at least auntie_cousins_default.png and auntie_cousins_waving.png to be present",
        )
        # The alias helper itself must refuse to rewrite protected canonical prefixes.
        self.assertIsNone(self.family.filename_alias_resolution("auntie_cousins_default.png"))
        self.assertIsNone(self.family.filename_alias_resolution("auntie_cousins_waving.png"))
        self.assertIsNone(self.family.filename_alias_resolution("auntie_cousins.png"))
        # Non-protected alias filenames still resolve.
        self.assertEqual(
            self.family.filename_alias_resolution("auntie_waving.png"),
            "aunt_sister_waving.png",
        )
        self.assertEqual(
            self.family.filename_alias_resolution("cousin_ben_default.png"),
            "cousin_younger_default.png",
        )

    def test_characters_endpoint_exposes_stage_height_metadata(self):
        """Regression: every character entry must advertise ``stage_height_percent``,
        ``base_height_px`` and ``scale_class`` so ``app/static/app.js`` can size
        them correctly without hardcoding an adult/toddler/dog list that would
        miss the new relatives and contact composites."""
        response = self.client.get("/api/characters/all")
        self.assertEqual(response.status_code, 200)
        chars = {c["id"]: c for c in response.json()["characters"]}
        expectations = [
            # Legacy IDs must retain their historical values exactly.
            ("levi", "toddler", 50, 520),
            ("luca", "toddler", 50, 520),
            ("mom", "adult", 72, 760),
            ("dad", "adult", 72, 760),
            ("dog", "pet", 30, 320),
            ("grandparents_paternal", "adult", 72, 760),
            ("grandparents_maternal", "adult", 72, 760),
            ("auntie_cousins", "adult", 72, 760),
            # New individual relatives.
            ("paternal_grandpa", "adult", 72, 760),
            ("paternal_grandma", "adult", 72, 760),
            ("maternal_grandpa", "adult", 72, 760),
            ("maternal_grandma", "adult", 72, 760),
            ("aunt_sister", "adult", 72, 760),
            # Older-child class (new): Ryan at 6-7y.
            ("cousin_ryan", "older_child", 60, 640),
            # Toddler-class cousin (Ben) stays at the twin size.
            ("cousin_younger", "toddler", 50, 520),
        ]
        for cid, cls, pct, base in expectations:
            with self.subTest(character=cid):
                self.assertIn(cid, chars, f"missing {cid}")
                self.assertEqual(chars[cid]["scale_class"], cls)
                self.assertEqual(chars[cid]["stage_height_percent"], pct)
                self.assertEqual(chars[cid]["base_height_px"], base)
        # Every contact composite must size to the adult class so the frontend
        # never shrinks a mom+toddler hug to toddler proportions.
        contact_ids = [cid for cid in chars if cid.startswith("contact_")]
        self.assertEqual(len(contact_ids), 12)
        for cid in contact_ids:
            with self.subTest(contact=cid):
                self.assertEqual(chars[cid]["scale_class"], "adult")
                self.assertEqual(chars[cid]["stage_height_percent"], 72)
                self.assertEqual(chars[cid]["base_height_px"], 760)

    def test_frontend_consumes_stage_height_metadata(self):
        """Regression: ``app/static/app.js`` must read ``stage_height_percent``
        from the backend instead of using the old hardcoded adult/toddler list
        exclusively, otherwise new relatives and contact composites would be
        drawn at the 50% toddler height. The legacy hardcoded list stays as a
        safe fallback for older server responses that lack the metadata.
        """
        js_text = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("charMeta.stage_height_percent", js_text,
                      "Frontend must read stage_height_percent from the API")
        self.assertIn("`h-[${charMeta.stage_height_percent}%]`", js_text)
        # Legacy fallback must still exist so an older server response renders
        # the pre-release characters at the same height as before.
        self.assertIn("'dad', 'mom', 'grandparents_paternal'", js_text)

    # --- Director validation ------------------------------------------
    def test_director_preserves_new_individual_poses(self):
        for name, pose in [
            ("paternal_grandpa", "offering_food_or_gift"),
            ("paternal_grandma", "seated_storytelling"),
            ("maternal_grandpa", "waving"),
            ("aunt_sister", "crouching_to_talk"),
            ("cousin_ryan", "showing_toy"),
            ("cousin_younger", "passing_toy"),
            ("mom", "walking"),
            ("dad", "listening_crouched"),
        ]:
            with self.subTest(name=name, pose=pose):
                plan = self.director._validate_and_sanitize_plan(
                    {"characters": [{"name": name, "pose": pose, "x_percent": 50, "y_percent": 86, "scale": 1.0, "flip": False}]},
                    {},
                )
                self.assertEqual(plan["characters"][0]["pose"], pose,
                                 f"{name}/{pose} must not collapse to default")

    def test_director_resets_unknown_pose_but_keeps_existing_default(self):
        plan = self.director._validate_and_sanitize_plan(
            {"characters": [{"name": "paternal_grandpa", "pose": "break_dance", "x_percent": 50}]},
            {},
        )
        self.assertEqual(plan["characters"][0]["pose"], "default")

    def test_director_preserves_contact_sprite_and_drops_duplicate_members(self):
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                {"name": "contact_mom_levi_hug", "pose": "default", "x_percent": 50, "y_percent": 86},
                # These two inner members must be dropped because the composite
                # already shows them hugging. Rendering them separately would
                # duplicate the kid and the mom on top of the composite.
                {"name": "mom", "pose": "default", "x_percent": 20},
                {"name": "levi", "pose": "default", "x_percent": 80},
                # An unrelated character must NOT be dropped.
                {"name": "dad", "pose": "default", "x_percent": 90},
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertIn("contact_mom_levi_hug", names)
        self.assertIn("dad", names)
        self.assertNotIn("mom", names)
        self.assertNotIn("levi", names)
        # The contact's own pose stays "default".
        contact = next(c for c in plan["characters"] if c["name"] == "contact_mom_levi_hug")
        self.assertEqual(contact["pose"], "default")

    def test_director_resolves_overlapping_contact_members_deterministically(self):
        """Regression: when two contact composites share a member (e.g. dad in
        both ``contact_dad_luca_hug`` and ``contact_dad_cousin_younger_handholding``),
        the second composite must be dropped so dad is not drawn twice.
        Rule: first valid contact wins in document order; later contacts whose
        member set intersects any kept contact are dropped. Standalone members
        of the kept contact are also dropped. Non-member characters pass
        through untouched.
        """
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                # First-wins: dad+luca hug stays.
                {"name": "contact_dad_luca_hug", "pose": "default", "x_percent": 30, "y_percent": 86},
                # Shares dad with the first contact -> must be dropped.
                {"name": "contact_dad_cousin_younger_handholding", "pose": "default",
                 "x_percent": 70, "y_percent": 86},
                # Standalone dad: inside first contact -> drop.
                {"name": "dad", "pose": "default", "x_percent": 10},
                # Standalone luca: inside first contact -> drop.
                {"name": "luca", "pose": "default", "x_percent": 90},
                # Unrelated character stays.
                {"name": "mom", "pose": "default", "x_percent": 50},
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertIn("contact_dad_luca_hug", names)
        self.assertNotIn("contact_dad_cousin_younger_handholding", names,
                         "Overlapping composite must be dropped (dad already in first)")
        self.assertNotIn("dad", names, "Standalone dad is inside the kept composite")
        self.assertNotIn("luca", names, "Standalone luca is inside the kept composite")
        self.assertIn("mom", names, "Unrelated characters survive")
        # Nothing should be drawn twice.
        self.assertEqual(len(names), len(set(names)))

    def test_director_resolves_three_way_overlap_and_keeps_unrelated_contact(self):
        """A non-overlapping second contact must survive even when a third
        contact shares a member with the first (the third is dropped, not
        the independent second)."""
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                # mom+levi hug — kept.
                {"name": "contact_mom_levi_hug", "pose": "default", "x_percent": 25},
                # Independent (dad+luca) — kept.
                {"name": "contact_dad_luca_hug", "pose": "default", "x_percent": 75},
                # Shares mom -> dropped.
                {"name": "contact_mom_cousin_ryan_carrying_child", "pose": "default", "x_percent": 50},
                # Shares dad -> dropped.
                {"name": "contact_dad_cousin_younger_handholding", "pose": "default", "x_percent": 90},
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertEqual(sorted(names), sorted(["contact_mom_levi_hug", "contact_dad_luca_hug"]))

    def test_director_contact_filter_leaves_pure_solo_plans_untouched(self):
        """Plans with no contacts at all must flow through the sanitizer with
        no character dropped (regression guard that the new overlap pass does
        not inadvertently filter non-contact plans)."""
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                {"name": "mom", "pose": "default", "x_percent": 25},
                {"name": "dad", "pose": "default", "x_percent": 50},
                {"name": "levi", "pose": "default", "x_percent": 75},
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertEqual(sorted(names), ["dad", "levi", "mom"])

    def test_director_prompt_lists_new_vocabulary(self):
        prompt = self.director.DIRECTOR_SYSTEM_PROMPT
        for token in ("paternal_grandpa", "paternal_grandma", "maternal_grandpa",
                      "maternal_grandma", "aunt_sister", "cousin_ryan", "cousin_younger",
                      "seated_storytelling", "offering_food_or_gift",
                      "showing_toy", "listening_crouched", "comforting_open_arms",
                      "contact_mom_levi_hug", "contact_dad_cousin_younger_handholding"):
            with self.subTest(token=token):
                self.assertIn(token, prompt, f"Director prompt must mention {token}")


if __name__ == "__main__":
    unittest.main()
