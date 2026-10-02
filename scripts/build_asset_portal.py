"""Rebuild the portable approved-asset gallery without importing the application."""

import base64
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "animals": "Animals", "vehicles": "Vehicles",
    "fruit_vegetables": "Fruits & vegetables", "food_snacks": "Food & snacks",
    "everyday_props": "Everyday props",
    "toys": "Toys",
}
CATEGORY_ORDER = [
    "All assets", "Sprites", "Family sprites", "Family contacts", "Cantonese badges",
    "Letters", "Numbers",
    "Toys", "Animals", "Vehicles", "Fruits & vegetables", "Food & snacks", "Everyday props",
]

# Simplified family-browsing buckets used by the portable asset portal and the
# studio Family Member Palette. Multi-person contact composites belong to the
# union of every participant's bucket, so e.g. ``contact_mom_levi_hug`` shows
# up in both the Mom and Levi buckets without being duplicated as an asset.
FAMILY_BUCKET_ORDER = [
    "levi", "luca", "mom", "dad",
    "paternal_grandparents", "maternal_grandparents",
    "auntie_cousins", "doggy",
]
FAMILY_BUCKETS = {
    "levi":                  {"label": "Levi",                   "emoji": "👦"},
    "luca":                  {"label": "Luca",                   "emoji": "👶"},
    "mom":                   {"label": "Mom",                    "emoji": "👩"},
    "dad":                   {"label": "Dad",                    "emoji": "👨"},
    "paternal_grandparents": {"label": "Paternal grandparents",  "emoji": "👴"},
    "maternal_grandparents": {"label": "Maternal grandparents",  "emoji": "👵"},
    "auntie_cousins":        {"label": "Auntie & cousins",       "emoji": "🧑‍🤝‍🧑"},
    "doggy":                 {"label": "Doggy",                  "emoji": "🐶"},
}
_SOLO_TO_BUCKET = {
    "levi": "levi", "luca": "luca", "mom": "mom", "dad": "dad",
    "dog": "doggy", "family_dog": "doggy", "spitz": "doggy",
    "paternal_grandpa": "paternal_grandparents",
    "paternal_grandma": "paternal_grandparents",
    "maternal_grandpa": "maternal_grandparents",
    "maternal_grandma": "maternal_grandparents",
    "aunt_sister": "auntie_cousins",
    "cousin_ryan": "auntie_cousins",
    "cousin_younger": "auntie_cousins",
    "grandparents_paternal": "paternal_grandparents",
    "grandparents_maternal": "maternal_grandparents",
    "auntie_cousins": "auntie_cousins",
}


def _buckets_for_members(member_ids):
    seen = {}
    for mid in member_ids:
        bucket = _SOLO_TO_BUCKET.get(mid)
        if bucket is not None and bucket not in seen:
            seen[bucket] = None
    return [b for b in FAMILY_BUCKET_ORDER if b in seen]


def preview(path: Path, size: int) -> str:
    with Image.open(path) as source:
        image = source.convert("RGBA")
        bounds = image.getchannel("A").getbbox()
        if bounds:
            image = image.crop(bounds)
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, "WEBP", quality=88, method=5)
    return "data:image/webp;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def build() -> Path:
    manifest = json.loads((ROOT / "config" / "artwork_release_v1.json").read_text(encoding="utf-8"))
    phonics_path = ROOT / "config" / "phonics_release_v2.json"
    phonics_manifest = json.loads(phonics_path.read_text(encoding="utf-8")) if phonics_path.exists() else None
    expansion = json.loads((ROOT / "config" / "props_release_v2.json").read_text(encoding="utf-8"))
    family_path = ROOT / "config" / "family_release_v3.json"
    family_manifest = json.loads(family_path.read_text(encoding="utf-8")) if family_path.exists() else None
    family_v4_path = ROOT / "config" / "family_interactions_v4.json"
    family_v4_manifest = json.loads(family_v4_path.read_text(encoding="utf-8")) if family_v4_path.exists() else None
    badges = {
        "badge_routine_brush_teeth": ("刷牙", "BRUSH TEETH"),
        "badge_routine_wash_hands": ("洗手", "WASH HANDS"),
        "badge_routine_eat": ("食飯", "MEALTIME"),
        "badge_play_together_v1": ("一齊玩", "PLAY TOGETHER"),
        "badge_take_turns_v1": ("輪住玩", "TAKE TURNS"),
        "badge_bedtime_sleep": ("瞓覺", "SLEEP"),
    }
    assets = []
    for asset in manifest["assets"] + expansion["assets"]:
        relative = asset["runtime_path"]
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"Asset path must stay within the repository: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError(f"Manifest hash mismatch: {relative}")
        kind = asset["kind"]
        sprite_family_buckets: list = []
        if kind == "sprite":
            category = "Sprites"
            name = asset["id"].replace("_", " ").title()
            subtitle = "Approved twin pose"
            note = "Approved pose with normalized interior opacity and eight-pixel padding. Default character identity references are unchanged."
            reference = preview(ROOT / asset["primary_reference"]["repository_relative_path"], 160)
            # Pre-release twin sprites (``levi_jumping``, ``luca_dancing``,
            # ``*_brushing_teeth`` …) must appear in the Levi / Luca family
            # buckets alongside the family-expansion v3 solo assets so Levi's
            # bucket shows his own 3 poses + his 3 contact composites, not
            # just the contacts.
            sprite_char = asset["id"].split("_", 1)[0]
            sprite_family_buckets = _buckets_for_members([sprite_char])
        elif kind == "badge":
            category = "Cantonese badges"
            name, subtitle = badges[asset["id"]]
            note = "Approved local typography export. Traditional Chinese glyphs were rendered using Microsoft JhengHei; lettering is not AI-generated."
            reference = None
        elif kind == "prop":
            category = CATEGORIES[asset["category"]]
            name, subtitle = asset["name"], asset["chinese"]
            note = asset["review_note"]
            reference = None
        else:
            raise ValueError(f"Unsupported release asset kind: {kind}")
        with Image.open(path) as image:
            dimensions = list(image.size)
            has_transparency = image.convert("RGBA").getchannel("A").histogram()[0] > 0
        assets.append({
            "id": asset["id"], "name": name, "category": category,
            "batch": "Prop expansion v2" if asset in expansion["assets"] else "Approved props" if kind == "prop" else "Family sprites" if kind == "sprite" else "Cantonese badges",
            "order": 3 if kind == "prop" else 2, "notes": note, "flagged": kind == "prop",
            "history": False, "status": "installed", "subtitle": subtitle,
            "dimensions": dimensions, "sourceDimensions": asset.get("source_size", dimensions),
            "provider": asset["provider"], "alpha": "Transparent exterior · RGBA" if has_transparency else "Opaque background",
            "path": relative, "url": quote(relative, safe="/"), "installedUrl": None,
            "prompt": json.dumps({
                "release": expansion["release_id"] if asset in expansion["assets"] else manifest["release_id"], "asset_id": asset["id"],
                "sha256": asset["sha256"], "source_sha256": asset["source_sha256"],
                "processing": asset["processing"], "replaces_existing_asset": bool(asset.get("previous_runtime_sha256")),
            }, ensure_ascii=False, indent=2),
            "thumb": preview(path, 360), "large": preview(path, 1040), "reference": reference,
            "family_buckets": sprite_family_buckets,
        })
    if phonics_manifest:
        for asset in phonics_manifest["assets"]:
            relative = asset["runtime_path"]
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError(f"Asset path must stay within the repository: {relative}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Phonics manifest hash mismatch: {relative}")
            if asset["kind"] not in {"letter", "number"}:
                raise ValueError(f"Unsupported phonics asset kind: {asset['kind']}")
            with Image.open(path) as image:
                dimensions = list(image.size)
                has_transparency = image.convert("RGBA").getchannel("A").histogram()[0] > 0
            category = "Letters" if asset["kind"] == "letter" else "Numbers"
            assets.append({
                "id": asset["id"], "name": asset["label"], "category": category,
                "batch": "Phonics stickers", "order": 4, "notes": "Local font-rendered glyph sticker with transparent exterior, white die-cut outline, and no box/tile background.",
                "flagged": False, "history": False, "status": "installed",
                "subtitle": f"Content: {asset['content']}",
                "dimensions": dimensions, "sourceDimensions": dimensions,
                "provider": "Local Pillow font render",
                "alpha": "Transparent exterior · RGBA" if has_transparency else "Opaque background",
                "path": relative, "url": quote(relative, safe="/"), "installedUrl": None,
                "prompt": json.dumps({
                    "release": phonics_manifest["release_id"], "asset_id": asset["id"],
                    "sha256": asset["sha256"], "source_font": Path(asset["source_font"]).name,
                    "provenance": asset["provenance"], "style_category": asset["style_category"],
                    "color": asset["color"],
                }, ensure_ascii=False, indent=2),
                "thumb": preview(path, 360), "large": preview(path, 1040), "reference": None,
            })
    if family_manifest:
        for asset in family_manifest["assets"]:
            relative = asset["runtime_path"]
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError(f"Asset path must stay within the repository: {relative}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Family manifest hash mismatch: {relative}")
            for alias in asset.get("alias_runtime_paths", []):
                alias_path = (ROOT / alias).resolve()
                if not alias_path.is_relative_to(ROOT):
                    raise ValueError(f"Alias path must stay within the repository: {alias}")
                if hashlib.sha256(alias_path.read_bytes()).hexdigest() != asset["sha256"]:
                    raise ValueError(f"Family alias hash mismatch: {alias}")
            with Image.open(path) as image:
                dimensions = list(image.size)
                has_transparency = image.convert("RGBA").getchannel("A").histogram()[0] > 0
            if asset["category"] == "solo":
                category = "Family sprites"
                name = asset["character_id"].replace("_", " ").title()
                subtitle = asset["pose"].replace("_", " ").title()
                members_tag = asset["character_id"]
                asset_buckets = _buckets_for_members([asset["character_id"]])
            else:
                category = "Family contacts"
                members = " + ".join(m["runtime_character_id"] for m in asset["members"])
                name = members.replace("_", " ").title()
                subtitle = asset["action"].replace("_", " ").title()
                members_tag = members
                asset_buckets = _buckets_for_members(
                    [m["runtime_character_id"] for m in asset["members"]]
                )
            reference = None
            ref_paths = asset.get("primary_reference", {}).get("repository_relative_paths", [])
            if ref_paths:
                reference = preview(ROOT / ref_paths[0], 160)
            assets.append({
                "id": asset["id"], "name": name, "category": category,
                "batch": "Family expansion v3",
                "order": 2, "notes": (
                    "Approved family-expansion v3 export. Alpha<=2 cleared, alpha>=250 set to 255, "
                    "crop to alpha bbox, eight-pixel transparent padding; no RGB changes or resampling."
                ),
                "flagged": False, "history": False, "status": "installed",
                "subtitle": subtitle,
                "dimensions": dimensions, "sourceDimensions": asset.get("source_size", dimensions),
                "provider": asset["provider"],
                "alpha": "Transparent exterior · RGBA" if has_transparency else "Opaque background",
                "path": relative, "url": quote(relative, safe="/"), "installedUrl": None,
                "prompt": json.dumps({
                    "release": family_manifest["release_id"], "asset_id": asset["id"],
                    "sha256": asset["sha256"], "source_sha256": asset["source_sha256"],
                    "processing": asset["processing"], "category": asset["category"],
                    "pose_or_action": asset["pose"],
                    "members": members_tag,
                    "scale_class": asset["scale_class"],
                    "alias_runtime_paths": asset.get("alias_runtime_paths", []),
                }, ensure_ascii=False, indent=2),
                "thumb": preview(path, 360), "large": preview(path, 1040), "reference": reference,
                "family_buckets": asset_buckets,
            })
    if family_v4_manifest:
        for asset in family_v4_manifest["assets"]:
            relative = asset["runtime_path"]
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError(f"Asset path must stay within the repository: {relative}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Family interactions v4 manifest hash mismatch: {relative}")
            if asset["category"] != "contact":
                raise ValueError(
                    f"Family interactions v4 only ships contact composites, got: {asset.get('category')}"
                )
            with Image.open(path) as image:
                dimensions = list(image.size)
                has_transparency = image.convert("RGBA").getchannel("A").histogram()[0] > 0
            member_ids = [m["runtime_character_id"] for m in asset["members"]]
            # Compose a human-friendly chip label from the member list (e.g.
            # "Mom + Dad + Levi + Luca") instead of the long underscore ID so
            # the four-person group entries don't produce giant visible IDs.
            name = " + ".join(member_ids).replace("_", " ").title()
            action_label = asset["action"].replace("_", " ").title()
            subtitle = action_label
            asset_buckets = _buckets_for_members(member_ids)
            reference = None
            ref_paths = asset.get("primary_reference", {}).get("repository_relative_paths", [])
            if ref_paths:
                reference = preview(ROOT / ref_paths[0], 160)
            assets.append({
                "id": asset["id"], "name": name, "category": "Family contacts",
                "batch": "Family interactions v4",
                "order": 2, "notes": (
                    "Approved family-interactions v4 export. Alpha<=2 cleared, alpha>=250 set to 255, "
                    "crop to alpha bbox, eight-pixel transparent padding; no RGB changes or resampling. "
                    f"Member count: {asset.get('member_count', len(member_ids))}; "
                    f"scale class: {asset['scale_class']}."
                ),
                "flagged": False, "history": False, "status": "installed",
                "subtitle": subtitle,
                "dimensions": dimensions, "sourceDimensions": asset.get("source_size", dimensions),
                "provider": asset["provider"],
                "alpha": "Transparent exterior · RGBA" if has_transparency else "Opaque background",
                "path": relative, "url": quote(relative, safe="/"), "installedUrl": None,
                "prompt": json.dumps({
                    "release": family_v4_manifest["release_id"], "asset_id": asset["id"],
                    "sha256": asset["sha256"], "source_sha256": asset["source_sha256"],
                    "processing": asset["processing"], "category": asset["category"],
                    "action": asset["action"],
                    "members": " + ".join(member_ids),
                    "member_count": asset.get("member_count", len(member_ids)),
                    "scale_class": asset["scale_class"],
                    "source_batch": asset.get("source_batch"),
                }, ensure_ascii=False, indent=2),
                "thumb": preview(path, 360), "large": preview(path, 1040), "reference": reference,
                "family_buckets": asset_buckets,
            })
    if len(assets) != len({a["id"] for a in assets}):
        raise ValueError("Duplicate IDs in release manifest")
    categories = [category for category in CATEGORY_ORDER if category == "All assets" or any(a["category"] == category for a in assets)]
    # Build the family-bucket metadata that the portal uses for the sub-nav.
    # Counts are the number of UNIQUE assets per bucket; a composite that
    # appears in two buckets is counted once in each but still a single
    # asset in the ``All assets`` grid.
    family_buckets_meta = []
    for bid in FAMILY_BUCKET_ORDER:
        entry = {"id": bid, **FAMILY_BUCKETS[bid],
                 "count": sum(1 for a in assets if bid in (a.get("family_buckets") or []))}
        family_buckets_meta.append(entry)
    template = (Path(__file__).parent / "asset_portal_template.html").read_text(encoding="utf-8")
    if template.count("__ASSET_DATA__") != 1:
        raise ValueError("Portal template must have exactly one data marker")
    data = json.dumps({"assets": assets, "categories": categories,
                       "family_buckets": family_buckets_meta,
                       "excluded": expansion["excluded_unrecovered_ids"]}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    result = template.replace("__ASSET_DATA__", data)
    if "file:///" in result or "C:\\\\" in result or "copilot.cloud.microsoft/chat/" in result:
        raise ValueError("Portal must not contain private local paths or conversation URLs")
    output = ROOT / "generated-asset-portal.html"
    output.write_text(result, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build())
