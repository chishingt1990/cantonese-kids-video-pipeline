"""Shared sticker category metadata for gallery, studio, and portal views."""

from __future__ import annotations

from typing import Any, Dict


UI_CATEGORY_LABELS = {
    "word": "WordBadges",
    "phonics": "Phonics",
    "vehicles": "Vehicles",
    "toys": "Toys",
    "shapes": "Shapes",
    "food": "FoodFruit",
    "animals": "Animals",
    "other": "OtherProps",
}

UI_CATEGORY_ORDER = tuple(UI_CATEGORY_LABELS.keys())

RELEASE_CATEGORY_TO_UI = {
    "vehicles": "vehicles",
    "toys": "toys",
    "shapes": "shapes",
    "fruit_vegetables": "food",
    "food_snacks": "food",
    "foodfruit": "food",
    "animals": "animals",
    "everyday_props": "other",
}

EXPLICIT_UI_CATEGORY_BY_ID = {
    # Reviewed word badges whose text collides with animal/food terms.
    "sticker_man_man_lai": "word",
    "badge_dog": "word",
    "badge_duckling": "word",
    "badge_mealtime": "word",
    "badge_spoon": "word",
    "vocab_banana": "word",
    # Empty tableware / party props are props, not food or vehicles.
    "prop_toddler_bowl": "other",
    "prop_sippy_cup": "other",
    "prop_milk_bottle": "other",
    "prop_balloon_red": "other",
    "prop_balloon_yellow": "other",
    "prop_balloon_blue": "other",
    "prop_balloon_green": "other",
    # Actual vehicle balloon remains a vehicle.
    "prop_hot_air_balloon": "vehicles",
    # Exact object semantics beat substring matches.
    "prop_starfruit": "food",
    "prop_toy_cat": "toys",
    "prop_toy_car": "toys",
    "prop_block_tower": "toys",
    "prop_fire_truck": "vehicles",
    "prop_kitty_cat": "animals",
    "prop_duckling": "animals",
    "prop_banana": "food",
    "prop_apple": "food",
    "prop_dim_sum_basket": "food",
    "prop_fruit_plate": "food",
    "prop_har_gow": "food",
    "prop_siu_mai": "food",
    "prop_egg_tart": "food",
    "prop_watermelon_slice": "food",
    "prop_strawberry": "food",
}


def effective_sticker_ui_category(sticker: Dict[str, Any]) -> str:
    """Return the single authoritative UI bucket for a sticker record."""
    sticker_id = str(sticker.get("id") or "").lower()
    sticker_type = str(sticker.get("type") or "").lower()
    kind = str(sticker.get("kind") or "").lower()
    release_category = str(sticker.get("category") or "").lower()

    if sticker_id in EXPLICIT_UI_CATEGORY_BY_ID:
        return EXPLICIT_UI_CATEGORY_BY_ID[sticker_id]

    # Role-before-topic: badges/words, phonics glyphs, and shape stickers are
    # exclusive even when their text contains animal/food/vehicle words.
    if sticker_type == "word" or sticker_id.startswith(("badge_", "word_", "vocab_")):
        return "word"
    if sticker_type in {"letter", "number", "block"} or sticker_id.startswith("block_"):
        return "phonics"
    if sticker_type == "shape" or kind == "shape" or sticker_id.startswith("shape_"):
        return "shapes"

    if release_category in RELEASE_CATEGORY_TO_UI:
        return RELEASE_CATEGORY_TO_UI[release_category]

    return "other"


def attach_sticker_category_metadata(sticker: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a sticker record with shared display category fields."""
    enriched = dict(sticker)
    ui_category = effective_sticker_ui_category(enriched)
    enriched["ui_category"] = ui_category
    enriched["display_category"] = UI_CATEGORY_LABELS[ui_category]
    return enriched
