"""Shared runtime catalog derived from ``config/family_release_v3.json``.

This module is the single source of truth for the new family-expansion release:
individual relative character IDs, their new pose vocabularies, contact
sprite entries (with members metadata and composite scale class), and
display-name/pose labels.

The scene director, characters router, render service and asset portal all
import from this module instead of hardcoding the new IDs so that:

* Legacy group IDs (``grandparents_paternal``, ``grandparents_maternal``,
  ``auntie_cousins``) remain untouched and still render.
* New individual IDs (``paternal_grandpa``, ``paternal_grandma``,
  ``maternal_grandpa``, ``maternal_grandma``, ``aunt_sister``,
  ``cousin_ryan``, ``cousin_younger``) are real selectable characters with
  their approved pose list surviving director validation.
* Contact sprite IDs (``contact_*``) carry explicit member and composite scale
  metadata so renderer scale classification does not accidentally treat them as
  toddlers, and the heuristic director does not duplicate inner participants.
* The legacy aliases ``auntie`` and ``cousin_ben`` are documented alongside the
  real IDs they resolve to.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "family_release_v3.json"

# Legacy group IDs that this release does not modify. They remain selectable
# so prior episodes keep rendering with their original composite art.
LEGACY_GROUP_IDS: tuple = ("grandparents_paternal", "grandparents_maternal", "auntie_cousins")

# User-facing filename aliases. The resolver maps these to the real runtime
# character ID so that generated scripts referring to the batch nicknames
# ("auntie_waving.png", "cousin_ben_showing_toy.png") still resolve.
#
# IMPORTANT: an alias prefix must never swallow a longer canonical prefix. For
# example, the ``auntie`` -> ``aunt_sister`` rewrite must NOT fire for
# ``auntie_cousins_default.png`` because ``auntie_cousins`` is itself a
# tracked legacy runtime ID. ``_PROTECTED_CANONICAL_PREFIXES`` lists the
# canonical prefixes that start with an alias token and therefore must take
# precedence over the alias.
FILENAME_ALIAS_PREFIXES: Dict[str, str] = {
    "auntie": "aunt_sister",
    "cousin_ben": "cousin_younger",
}
_PROTECTED_CANONICAL_PREFIXES: tuple = ("auntie_cousins",)

# Base pixel heights for each scale class on the 1920x1080 render canvas.
# These values are declared in config/family_release_v3.json but exposed here
# so render_service does not need to reparse the manifest at frame time.
BASE_HEIGHT_PX: Dict[str, int] = {
    "adult": 760,
    "older_child": 640,
    "toddler": 520,
    "pet": 320,
}

# Stage-canvas height percentages used by ``app/static/app.js`` for the
# interactive editing stage. These mirror the historical hardcoded choices
# (adults 72%, toddlers 50%, dog 30%) and extend them with the new
# ``older_child`` class (~60%) so Ryan is not drawn at the toddler size.
# Exposed via /api/characters/all so the frontend consumes a single source
# of truth instead of re-hardcoding adult/toddler lists.
STAGE_HEIGHT_PERCENT: Dict[str, int] = {
    "adult": 72,
    "older_child": 60,
    "toddler": 50,
    "pet": 30,
}

# Legacy per-character scale class so render_service picks the right base
# height for both pre-existing and new IDs via one shared map. Values match
# the historical hard-coded classification in render_service.load_sprite.
LEGACY_SCALE_CLASS: Dict[str, str] = {
    "dad": "adult",
    "mom": "adult",
    "grandparents_paternal": "adult",
    "grandparents_maternal": "adult",
    "auntie_cousins": "adult",
    "levi": "toddler",
    "luca": "toddler",
    "dog": "pet",
    "family_dog": "pet",
    "spitz": "pet",
}

# Display metadata for the characters router. Keyed by runtime character ID.
NEW_CHARACTER_DISPLAY: Dict[str, Dict[str, str]] = {
    "paternal_grandpa": {
        "name": "Grandpa (爺爺)",
        "role": "Paternal Grandfather",
        "outfit": "Plaid Polo & Grey Trousers",
        "hair": "Dark hair silvering at temples; thin rectangular glasses",
    },
    "paternal_grandma": {
        "name": "Grandma (嫲嫲)",
        "role": "Paternal Grandmother",
        "outfit": "Magenta Top & White Long Sleeves",
        "hair": "Short brownish-grey bob with gold-rimmed oval glasses",
    },
    "maternal_grandpa": {
        "name": "Grandpa (公公)",
        "role": "Maternal Grandfather",
        "outfit": "White Graphic Tee & Comfortable Trousers",
        "hair": "Close-cropped salt-and-pepper buzz cut",
    },
    "maternal_grandma": {
        "name": "Grandma (婆婆)",
        "role": "Maternal Grandmother",
        "outfit": "White Tee with Beaded Bracelet",
        "hair": "Short salt-and-pepper pixie cut with soft bangs",
    },
    "aunt_sister": {
        "name": "Auntie (姑媽)",
        "role": "Auntie",
        "outfit": "Cozy Knit Sweater or Casual Tee",
        "hair": "Dark hair tied back with chic dark rounded glasses",
    },
    "cousin_ryan": {
        "name": "Cousin Ryan (表哥)",
        "role": "Older Boy Cousin (6-7 years)",
        "outfit": "Athletic Tee & Shorts",
        "hair": "Short dark boy cut with sporty frame glasses",
    },
    "cousin_younger": {
        "name": "Cousin Ben (表弟)",
        "role": "Younger Toddler Cousin (2-3 years)",
        "outfit": "Blue Tee & Comfy Shorts",
        "hair": "Soft toddler hair with fun blue sunglasses",
    },
}

# Pretty label for a two- or three-member contact sprite composite.
_RUNTIME_DISPLAY = {
    "mom": "Mom",
    "dad": "Dad",
    "paternal_grandpa": "爺爺",
    "paternal_grandma": "嫲嫲",
    "maternal_grandpa": "公公",
    "maternal_grandma": "婆婆",
    "aunt_sister": "姑媽",
    "cousin_ryan": "Ryan",
    "cousin_younger": "Ben",
    "levi": "Levi",
    "luca": "Luca",
}


def _load() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def manifest() -> dict:
    """Return the parsed family release manifest. Cached for process lifetime."""
    return _load()


@lru_cache(maxsize=1)
def pose_labels() -> Dict[str, str]:
    return dict(manifest()["pose_labels"])


@lru_cache(maxsize=1)
def contact_action_labels() -> Dict[str, str]:
    return dict(manifest()["contact_action_labels"])


@lru_cache(maxsize=1)
def individual_poses() -> Dict[str, List[str]]:
    """Return ``{runtime_character_id: [pose_id, ...]}`` from the release manifest.

    "default" is always first; downloaded poses are listed in the order they
    appear in the manifest so the UI pose picker stays stable.
    """
    by_char: Dict[str, List[str]] = {}
    for asset in manifest()["assets"]:
        if asset["category"] != "solo":
            continue
        cid = asset["character_id"]
        pose = asset["pose"]
        bucket = by_char.setdefault(cid, [])
        if pose not in bucket:
            bucket.append(pose)
    for poses in by_char.values():
        if "default" in poses:
            poses.remove("default")
            poses.insert(0, "default")
    return by_char


@lru_cache(maxsize=1)
def contact_sprites() -> List[dict]:
    """Return contact entries ``[{id, runtime_path, members, action, scale_class}, ...]``."""
    result = []
    for asset in manifest()["assets"]:
        if asset["category"] != "contact":
            continue
        result.append({
            "id": asset["id"],
            "runtime_path": asset["runtime_path"],
            "action": asset["action"],
            "members": [m["runtime_character_id"] for m in asset["members"]],
            "member_roles": [m["age_role"] for m in asset["members"]],
            "scale_class": asset["scale_class"],
        })
    return result


@lru_cache(maxsize=1)
def scale_class_map() -> Dict[str, str]:
    """Return ``{character_or_contact_id: scale_class}`` merging legacy + release.

    Contact IDs are included so renderers can size composites correctly.
    """
    result = dict(LEGACY_SCALE_CLASS)
    for asset in manifest()["assets"]:
        if asset["category"] == "solo":
            result[asset["character_id"]] = asset["scale_class"]
        else:
            result[asset["id"]] = asset["scale_class"]
    return result


def base_height_for(char_or_contact_id: str) -> int:
    """Pick the renderer base height. Unknown IDs fall back to the toddler base
    (520 px) to match the previous ``else: base_h = 520`` default.
    """
    cls = scale_class_map().get(char_or_contact_id, "toddler")
    return BASE_HEIGHT_PX.get(cls, BASE_HEIGHT_PX["toddler"])


def stage_height_percent_for(char_or_contact_id: str) -> int:
    """Pick the frontend stage-canvas height percentage. Unknown IDs fall back
    to the toddler 50% default so new characters without a classification are
    not accidentally rendered at adult size.
    """
    cls = scale_class_map().get(char_or_contact_id, "toddler")
    return STAGE_HEIGHT_PERCENT.get(cls, STAGE_HEIGHT_PERCENT["toddler"])


def scale_class_for(char_or_contact_id: str) -> str:
    """Return the ``adult/older_child/toddler/pet`` class, defaulting to ``toddler``."""
    return scale_class_map().get(char_or_contact_id, "toddler")


def contact_members(contact_id: str) -> Optional[List[str]]:
    """Return the member list of a contact sprite, or None if not a contact."""
    for entry in contact_sprites():
        if entry["id"] == contact_id:
            return list(entry["members"])
    return None


def is_contact_id(name: str) -> bool:
    return name.startswith("contact_") and contact_members(name) is not None


def filename_alias_resolution(filename: str) -> Optional[str]:
    """Resolve legacy filename aliases (``auntie_*.png`` -> ``aunt_sister_*.png``;
    ``cousin_ben_*.png`` -> ``cousin_younger_*.png``). Returns the resolved
    filename or ``None`` if no alias prefix matches.

    Canonical prefixes that happen to START with an alias token (e.g. the
    legacy group ID ``auntie_cousins``) are protected: this function returns
    ``None`` for them so the resolver serves the real file instead of a
    nonexistent ``aunt_sister_cousins_*.png`` rewrite.
    """
    # Protect canonical IDs that start with an alias token so the alias does
    # not rewrite a legacy group filename into a nonexistent one.
    for canonical in _PROTECTED_CANONICAL_PREFIXES:
        if filename.startswith(f"{canonical}_") or filename == f"{canonical}.png":
            return None
    for alias_prefix, real_prefix in FILENAME_ALIAS_PREFIXES.items():
        token = f"{alias_prefix}_"
        if filename.startswith(token):
            return f"{real_prefix}_{filename[len(token):]}"
    return None


def known_character_prefixes() -> List[str]:
    """Return filename prefix list ordered longest-first so the resolver matches
    ``paternal_grandpa`` before falling back to any shorter token.
    """
    prefixes = set(LEGACY_GROUP_IDS) | {
        "dad", "mom", "dog", "levi", "luca",
    }
    for asset in manifest()["assets"]:
        if asset["category"] == "solo":
            prefixes.add(asset["character_id"])
    # Include contact prefix and alias prefixes so filename classification
    # does not accidentally split e.g. ``cousin_ben`` into a bare ``cousin``.
    prefixes.add("contact")
    prefixes.update(FILENAME_ALIAS_PREFIXES.keys())
    return sorted(prefixes, key=len, reverse=True)


def contact_display_name(contact_id: str) -> str:
    """Human-readable member list, e.g. ``Mom & Levi — Shared Hug``."""
    for entry in contact_sprites():
        if entry["id"] == contact_id:
            parts = " & ".join(_RUNTIME_DISPLAY.get(m, m) for m in entry["members"])
            action = contact_action_labels().get(entry["action"], entry["action"].title())
            return f"{parts} — {action}"
    return contact_id


def new_character_display(char_id: str) -> Optional[Dict[str, str]]:
    return NEW_CHARACTER_DISPLAY.get(char_id)
