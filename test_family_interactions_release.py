"""Offline integration tests for the family-interactions v4 release.

Covers:
* Manifest cardinality (32 approved assets, 0 excluded), release metadata,
  2/3/4-person member distribution, scale-class distribution.
* Hash integrity + 8-pixel transparent padding on every v4 asset byte-for-byte.
* v3 release stays immutable: ``manifest()`` still returns exactly 53 assets
  with unchanged bytes/sha256.
* Shared catalog aggregates v3 + v4 without hardcoded assumptions about
  2-person-only or default-only contacts.
* Characters router exposes every v4 contact as a selectable composite with
  the correct bucket list, scale class and friendly display name (no giant
  underscore IDs in the UI).
* Sprite resolver returns the exact v4 bytes for direct filenames and
  does not collide with any v3 ID / runtime path.
* Scene director preserves v4 composite IDs and keeps the first-wins overlap
  rule working for 3- and 4-person composites.
* Portal shows 403 unique assets, 44 Family contacts, 91 bucket-tagged assets.
* Approval evidence is recorded accurately — twins batch quoted 'these are
  great', groups batch quoted 'A. Approve all six' + 'keep going'. The
  manifest never claims the v4 release has been publicly published.
"""

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parent
V3_MANIFEST = ROOT / "config" / "family_release_v3.json"
V4_MANIFEST = ROOT / "config" / "family_interactions_v4.json"


class TestFamilyInteractionsRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3 = json.loads(V3_MANIFEST.read_text(encoding="utf-8"))
        cls.v4 = json.loads(V4_MANIFEST.read_text(encoding="utf-8"))
        # Fresh scratch tree for catalog + router module loading so tests mirror
        # the pre-existing test_family_release.py pattern.
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.scratch = Path(cls.temp.name)
        (cls.scratch / "config").mkdir()
        for name in ("artwork_release_v1.json", "phonics_release_v2.json",
                     "props_release_v2.json", "family_release_v3.json",
                     "family_interactions_v4.json"):
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
        for legacy in ("mom.png", "mom_default.png", "dad.png", "dad_default.png",
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

    # ---------------------------------------------------------------- manifest
    def test_v4_manifest_shape_and_release_metadata(self):
        self.assertEqual(self.v4["release_id"], "family_interactions_v4")
        self.assertEqual(self.v4["status"], "approved_local_integration")
        self.assertEqual(len(self.v4["assets"]), 32,
                         "32 approved composites: 26 twin interactions + 6 four-person groups")
        self.assertEqual(self.v4["excluded_jobs"], [],
                         "All 32 approved jobs were in state 'downloaded'")

    def test_v4_approval_wording_is_accurate_and_not_overclaimed(self):
        """The approval field must quote the user's actual words
        ('these are great' for twins, 'A. Approve all six' + 'keep going'
        for groups) and must NOT claim the v4 release has been publicly
        published — public push is a separate step the user handles later.
        """
        approval = self.v4["approval"]
        self.assertIn("these are great", approval)
        self.assertIn("A. Approve all six", approval)
        self.assertIn("keep going", approval)
        self.assertIn("public publication", approval.lower(),
                      "Approval must call out that public publication is separate")
        # Each asset's per-asset approval statement must also stay honest.
        for asset in self.v4["assets"]:
            with self.subTest(asset=asset["id"]):
                statement = asset.get("approval_statement", "")
                self.assertIn("public publication", statement.lower())
                if asset.get("source_batch") == "twins":
                    self.assertIn("these are great", statement)
                else:
                    self.assertIn("keep going", statement)

    def test_v4_member_distribution(self):
        two = [a for a in self.v4["assets"] if a["member_count"] == 2]
        three = [a for a in self.v4["assets"] if a["member_count"] == 3]
        four = [a for a in self.v4["assets"] if a["member_count"] == 4]
        self.assertEqual(len(two), 24, "24 two-person composites in v4")
        self.assertEqual(len(three), 2,
                         "2 three-person composites (mom+twins, dad+twins)")
        self.assertEqual(len(four), 6,
                         "6 four-person group composites (3 adult-pairs × hug/play)")
        self.assertEqual(len(two) + len(three) + len(four), 32)

    def test_v4_scale_class_distribution(self):
        """Twin-only pairs stay toddler; Ryan+twin stays older_child; Ben+twin
        stays toddler; every composite that includes an adult sizes to adult."""
        by_scale = {"adult": 0, "older_child": 0, "toddler": 0, "pet": 0}
        for asset in self.v4["assets"]:
            by_scale[asset["scale_class"]] += 1
        self.assertEqual(by_scale["adult"], 24,
                         "All composites with an adult or grandparent size to adult")
        self.assertEqual(by_scale["older_child"], 2,
                         "Only the two cousin_ryan + twin composites are older_child")
        self.assertEqual(by_scale["toddler"], 6,
                         "4 levi+luca pairs + 2 cousin_younger+twin pairs = 6 toddler")
        self.assertEqual(by_scale["pet"], 0)

    def test_v4_hashes_padding_and_mode(self):
        for asset in self.v4["assets"]:
            with self.subTest(asset=asset["id"]):
                primary = ROOT / asset["runtime_path"]
                self.assertEqual(
                    hashlib.sha256(primary.read_bytes()).hexdigest(),
                    asset["sha256"],
                    f"Primary hash mismatch: {asset['runtime_path']}",
                )
                with Image.open(primary) as image:
                    self.assertEqual(image.mode, "RGBA")
                    alpha = image.getchannel("A")
                    self.assertEqual(
                        alpha.getbbox(),
                        (8, 8, image.width - 8, image.height - 8),
                        f"8px transparent padding required: {asset['runtime_path']}",
                    )
                    self.assertEqual(alpha.getextrema(), (0, 255))
                self.assertFalse(asset["processing"]["rgb_changes"])
                self.assertEqual(asset["processing"]["resampling"], "none")
                self.assertEqual(asset["processing"]["transparent_padding_each_side"], 8)

    def test_v4_does_not_collide_with_v3(self):
        v3_ids = {a["id"] for a in self.v3["assets"]}
        v3_paths = {a["runtime_path"] for a in self.v3["assets"]}
        for alias_list in (a.get("alias_runtime_paths", []) for a in self.v3["assets"]):
            v3_paths.update(alias_list)
        for asset in self.v4["assets"]:
            with self.subTest(asset=asset["id"]):
                self.assertNotIn(asset["id"], v3_ids,
                                 "v4 must not reuse a v3 asset ID")
                self.assertNotIn(asset["runtime_path"], v3_paths,
                                 "v4 must not clobber a v3 runtime path")

    def test_v3_release_bytes_and_metadata_are_immutable(self):
        """The v3 release stays byte-identical after v4 lands: every v3 asset
        must still match its recorded sha256 on disk and the manifest must
        still contain exactly 53 assets (41 solo + 12 contact)."""
        self.assertEqual(len(self.v3["assets"]), 53)
        solo = [a for a in self.v3["assets"] if a["category"] == "solo"]
        contact = [a for a in self.v3["assets"] if a["category"] == "contact"]
        self.assertEqual(len(solo), 41)
        self.assertEqual(len(contact), 12)
        for asset in self.v3["assets"]:
            with self.subTest(asset=asset["id"]):
                path = ROOT / asset["runtime_path"]
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    asset["sha256"],
                    f"v3 asset {asset['id']} was mutated by the v4 release",
                )

    def test_v4_manifest_has_no_private_data(self):
        """The manifest must not leak absolute workspace paths, Copilot
        conversation URLs, personal names, prompt bodies or runner logs."""
        text = V4_MANIFEST.read_text(encoding="utf-8")
        for forbidden in (
            "C:\\\\Users",
            "C:/Users",
            "/Users/",
            "copilot.cloud.microsoft/chat/conversation/",
            "file:///",
            "runner-stdout",
            "runner-stderr",
            "runner.log",
            "communication_log_id",
            "conversation_url",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text,
                                 f"Private substring {forbidden!r} leaked into v4 manifest")

    # ---------------------------------------------------------------- catalog
    def test_catalog_aggregates_v3_and_v4_without_assuming_two_people(self):
        """``family_catalog`` must expose both v3 and v4 contacts in one list
        and must not assume a 2-person default; three- and four-person
        composites survive with their full member list."""
        contacts = {c["id"]: c for c in self.family.contact_sprites()}
        self.assertEqual(len(contacts), 44, "12 v3 + 32 v4 = 44 contacts")
        three_person = contacts["contact_mom_levi_luca_holding_both_hands"]
        self.assertEqual(three_person["members"], ["mom", "levi", "luca"])
        self.assertEqual(three_person["member_count"], 3)
        four_person = contacts["contact_mom_dad_levi_luca_hug"]
        self.assertEqual(four_person["members"], ["mom", "dad", "levi", "luca"])
        self.assertEqual(four_person["member_count"], 4)
        # Scale classes mirror the manifest.
        self.assertEqual(contacts["contact_levi_luca_hug"]["scale_class"], "toddler")
        self.assertEqual(contacts["contact_cousin_ryan_levi_high_five"]["scale_class"], "older_child")
        self.assertEqual(contacts["contact_cousin_younger_luca_building_blocks_together"]["scale_class"], "toddler")
        self.assertEqual(four_person["scale_class"], "adult")
        # Catalog aggregation lists both release manifests.
        releases = [m["release_id"] for m in self.family.all_release_manifests()]
        self.assertEqual(releases, ["family_release_v3", "family_interactions_v4"])

    def test_catalog_scale_class_for_v4_composites(self):
        """``base_height_for``/``scale_class_for`` return the right size for
        every category of v4 composite (twin-pair toddler, Ryan+twin older
        child, Ben+twin toddler, grandparent-pair/parent-pair/single-adult+kid
        adult)."""
        cases = [
            ("contact_levi_luca_hug", "toddler", 520),
            ("contact_levi_luca_passing_toy", "toddler", 520),
            ("contact_cousin_ryan_levi_high_five", "older_child", 640),
            ("contact_cousin_ryan_luca_reading_together", "older_child", 640),
            ("contact_cousin_younger_levi_passing_toy", "toddler", 520),
            ("contact_mom_luca_hug", "adult", 760),
            ("contact_dad_cousin_younger_handholding", "adult", 760),  # v3 sanity check
            ("contact_mom_levi_luca_holding_both_hands", "adult", 760),
            ("contact_paternal_grandpa_paternal_grandma_levi_luca_hug", "adult", 760),
            ("contact_maternal_grandpa_maternal_grandma_levi_luca_play", "adult", 760),
            ("contact_mom_dad_levi_luca_play", "adult", 760),
        ]
        for cid, cls, base in cases:
            with self.subTest(contact=cid):
                self.assertEqual(self.family.scale_class_for(cid), cls)
                self.assertEqual(self.family.base_height_for(cid), base)

    def test_catalog_buckets_cover_all_v4_composites_without_double_counting(self):
        """Every v4 contact lives in at least one bucket, buckets are
        deduplicated across the same participant family, and the paternal-
        grandparent 4-person group collapses to one paternal_grandparents
        entry (not two)."""
        for asset in self.v4["assets"]:
            with self.subTest(asset=asset["id"]):
                buckets = self.family.buckets_for(asset["id"])
                self.assertGreater(len(buckets), 0)
                self.assertEqual(len(buckets), len(set(buckets)))
        # Specific bucket expectations.
        self.assertEqual(
            self.family.buckets_for("contact_mom_dad_levi_luca_hug"),
            ["levi", "luca", "mom", "dad"],
        )
        self.assertEqual(
            self.family.buckets_for("contact_paternal_grandpa_paternal_grandma_levi_luca_hug"),
            ["levi", "luca", "paternal_grandparents"],
            "Both paternal grandparents must collapse to a single bucket entry",
        )
        self.assertEqual(
            self.family.buckets_for("contact_maternal_grandpa_maternal_grandma_levi_luca_play"),
            ["levi", "luca", "maternal_grandparents"],
        )
        self.assertEqual(
            self.family.buckets_for("contact_cousin_ryan_levi_high_five"),
            ["levi", "auntie_cousins"],
        )

    # ---------------------------------------------------------- API endpoints
    def test_characters_endpoint_shows_v4_composites_with_friendly_names(self):
        response = self.client.get("/api/characters/all")
        self.assertEqual(response.status_code, 200)
        chars = {c["id"]: c for c in response.json()["characters"]}
        # Four-person group shows a friendly label, NOT a giant underscore ID.
        quad = chars["contact_mom_dad_levi_luca_hug"]
        self.assertEqual(quad["name"], "Mom & Dad & Levi & Luca — Hug")
        self.assertNotIn("contact_mom_dad_levi_luca_hug", quad["name"])
        self.assertEqual(quad["members"], ["mom", "dad", "levi", "luca"])
        self.assertEqual(quad["scale_class"], "adult")
        self.assertEqual(quad["stage_height_percent"], 72)
        self.assertEqual(quad["base_height_px"], 760)
        self.assertEqual(quad["family_buckets"], ["levi", "luca", "mom", "dad"])
        # Twin-pair composite sizes to toddler proportions.
        twin = chars["contact_levi_luca_hug"]
        self.assertEqual(twin["scale_class"], "toddler")
        self.assertEqual(twin["stage_height_percent"], 50)
        self.assertEqual(twin["base_height_px"], 520)
        # Ryan + twin sizes to older_child.
        ryan = chars["contact_cousin_ryan_levi_high_five"]
        self.assertEqual(ryan["scale_class"], "older_child")
        self.assertEqual(ryan["stage_height_percent"], 60)
        self.assertEqual(ryan["base_height_px"], 640)
        # The sidebar still carries 8 buckets in the expected order.
        bucket_ids = [b["id"] for b in response.json()["family_buckets"]]
        self.assertEqual(bucket_ids, [
            "levi", "luca", "mom", "dad",
            "paternal_grandparents", "maternal_grandparents",
            "auntie_cousins", "doggy",
        ])

    def test_sprite_endpoint_serves_v4_composites_directly(self):
        """Each v4 asset must be served from its exact runtime path with no
        rewrite or fallback kicking in. The resolver must not confuse v4
        contact IDs with any v3 contact or legacy group prefix."""
        sprites_dir = ROOT / "assets" / "sprites"
        samples = [
            "contact_levi_luca_hug.png",
            "contact_mom_luca_hug.png",
            "contact_mom_levi_luca_holding_both_hands.png",
            "contact_dad_levi_luca_holding_both_hands.png",
            "contact_cousin_younger_luca_building_blocks_together.png",
            "contact_mom_dad_levi_luca_hug.png",
            "contact_paternal_grandpa_paternal_grandma_levi_luca_hug.png",
            "contact_maternal_grandpa_maternal_grandma_levi_luca_play.png",
        ]
        for filename in samples:
            with self.subTest(filename=filename):
                resp = self.client.get(f"/api/characters/sprite/{filename}")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.content, (sprites_dir / filename).read_bytes())

    def test_v3_contact_composites_still_resolve_byte_identically(self):
        """Regression: no v3 contact filename is accidentally shadowed by
        the v4 release or by the resolver's longer-prefix matching."""
        sprites_dir = ROOT / "assets" / "sprites"
        for asset in self.v3["assets"]:
            if asset["category"] != "contact":
                continue
            with self.subTest(asset=asset["id"]):
                filename = Path(asset["runtime_path"]).name
                resp = self.client.get(f"/api/characters/sprite/{filename}")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.content, (sprites_dir / filename).read_bytes())

    # ---------------------------------------------------------- director rule
    def test_director_preserves_v4_four_person_composite_ids(self):
        """Director validation must not collapse a 4-person composite to
        default. The composite's own ``default`` pose stays intact and the
        unknown-pose reset path is per-composite."""
        for cid in (
            "contact_mom_dad_levi_luca_hug",
            "contact_mom_dad_levi_luca_play",
            "contact_paternal_grandpa_paternal_grandma_levi_luca_hug",
            "contact_paternal_grandpa_paternal_grandma_levi_luca_play",
            "contact_maternal_grandpa_maternal_grandma_levi_luca_hug",
            "contact_maternal_grandpa_maternal_grandma_levi_luca_play",
        ):
            with self.subTest(composite=cid):
                plan = self.director._validate_and_sanitize_plan(
                    {"characters": [{"name": cid, "pose": "default",
                                     "x_percent": 50, "y_percent": 86}]},
                    {},
                )
                self.assertEqual(plan["characters"][0]["name"], cid)
                self.assertEqual(plan["characters"][0]["pose"], "default")

    def test_director_first_wins_rule_still_works_for_four_person_composites(self):
        """First-wins overlap resolution must handle 4-member composites too.
        Picking the four-person mom+dad+levi+luca hug and then also staging a
        standalone mom OR a two-person contact_mom_levi_hug must drop both to
        prevent double-rendering any shared participant."""
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                {"name": "contact_mom_dad_levi_luca_hug", "pose": "default",
                 "x_percent": 50, "y_percent": 86},
                {"name": "contact_mom_levi_hug", "pose": "default",
                 "x_percent": 30, "y_percent": 86},  # overlaps mom+levi
                {"name": "mom", "pose": "default", "x_percent": 10},
                {"name": "levi", "pose": "default", "x_percent": 90},
                # dog is independent — must survive.
                {"name": "dog", "pose": "default", "x_percent": 70},
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertIn("contact_mom_dad_levi_luca_hug", names)
        self.assertNotIn("contact_mom_levi_hug", names,
                         "Overlapping two-person composite must be dropped")
        self.assertNotIn("mom", names)
        self.assertNotIn("levi", names)
        self.assertIn("dog", names)
        # No duplicate renders.
        self.assertEqual(len(names), len(set(names)))

    def test_director_three_person_composite_also_dedups_members(self):
        plan = self.director._validate_and_sanitize_plan({
            "characters": [
                {"name": "contact_mom_levi_luca_holding_both_hands", "pose": "default"},
                {"name": "mom", "pose": "default"},   # inside composite — drop
                {"name": "levi", "pose": "default"},  # inside composite — drop
                {"name": "dad", "pose": "default"},   # survives
            ],
        }, {})
        names = [c["name"] for c in plan["characters"]]
        self.assertIn("contact_mom_levi_luca_holding_both_hands", names)
        self.assertNotIn("mom", names)
        self.assertNotIn("levi", names)
        self.assertIn("dad", names)

    # -------------------------------------------------------- portal totals
    def test_portal_totals_after_v4_and_library_v5(self):
        """Portal must reach 403 unique assets after targeted-repairs v6,
        while preserving 44 Family contacts and 91 bucket-tagged assets."""
        spec = importlib.util.spec_from_file_location(
            "build_asset_portal", ROOT / "scripts" / "build_asset_portal.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = module.build()
        text = Path(output).read_text(encoding="utf-8")
        match = re.search(
            r'<script id="asset-data" type="application/json">(.*?)</script>',
            text, re.S)
        data = json.loads(match.group(1))
        self.assertEqual(len(data["assets"]), 403)
        family_contacts = [a for a in data["assets"] if a["category"] == "Family contacts"]
        self.assertEqual(len(family_contacts), 44)
        self.assertEqual(
            len([a for a in data["assets"] if a["category"] == "Family sprites"]), 41)
        self.assertEqual(
            len([a for a in data["assets"] if a["batch"] == "Library expansion v5"]), 100)
        self.assertEqual(
            len([a for a in data["assets"] if a["batch"] == "Targeted repairs v6"]), 29)
        with_bucket = [a for a in data["assets"] if a.get("family_buckets")]
        self.assertEqual(len(with_bucket), 91,
                         "6 twin sprites + 41 v3 solos + 12 v3 contacts + 32 v4 contacts")
        # Four-person group entries carry friendly readable chip names.
        by_id = {a["id"]: a for a in data["assets"]}
        self.assertEqual(by_id["contact_mom_dad_levi_luca_hug"]["name"], "Mom + Dad + Levi + Luca")
        self.assertIn("Mom + Dad + Levi + Luca",
                      by_id["contact_mom_dad_levi_luca_play"]["name"])
        self.assertNotIn("file:///", text)
        self.assertNotIn("copilot.cloud.microsoft/chat/conversation/", text)


if __name__ == "__main__":
    unittest.main()
