"""Deterministic local renderer for glyph-shaped phonics stickers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
STICKER_DIR = ROOT / "assets" / "stickers"
DEFAULT_FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FALLBACK_FONTS = [
    DEFAULT_FONT,
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]

LETTER_COLORS = [
    ("berry", "#D81B60"),
    ("coral", "#E85D3F"),
    ("orange", "#F28C28"),
    ("gold", "#D8A000"),
    ("lime", "#74A82A"),
    ("emerald", "#14996B"),
    ("teal", "#008C95"),
    ("sky", "#1687D9"),
    ("blue", "#3367D6"),
    ("indigo", "#5E5CE6"),
    ("violet", "#8E44AD"),
    ("magenta", "#C13FA0"),
]

NUMBER_COLORS = [
    ("rose", "#D81B60"),
    ("blue", "#1687D9"),
    ("emerald", "#14996B"),
    ("orange", "#F28C28"),
    ("violet", "#8E44AD"),
    ("gold", "#D8A000"),
    ("teal", "#008C95"),
]

PHONICS_STYLE_CATEGORY = "glyph_diecut_v2"


def _hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def resolve_font_path() -> Path:
    for font in FALLBACK_FONTS:
        if font.exists():
            return font
    raise FileNotFoundError("No supported bold Latin font found for phonics stickers.")


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(resolve_font_path()), size)


def _text_bbox(content: str, font: ImageFont.FreeTypeFont, stroke_width: int) -> tuple[int, int, int, int]:
    draw = ImageDraw.Draw(Image.new("RGBA", (8, 8), (0, 0, 0, 0)))
    return draw.textbbox((0, 0), content, font=font, stroke_width=stroke_width)


def _fit_font(content: str, max_width: int, max_height: int, stroke_width: int) -> ImageFont.FreeTypeFont:
    for size in range(max(max_width, max_height), 96, -4):
        font = _font(size)
        left, top, right, bottom = _text_bbox(content, font, stroke_width)
        if right - left <= max_width and bottom - top <= max_height:
            return font
    return _font(96)


def _exterior_mask(mask: Image.Image) -> Image.Image:
    binary = mask.point(lambda pixel: 255 if pixel else 0)
    width, height = binary.size
    for x in range(width):
        if binary.getpixel((x, 0)) == 0:
            ImageDraw.floodfill(binary, (x, 0), 128, thresh=0)
        if binary.getpixel((x, height - 1)) == 0:
            ImageDraw.floodfill(binary, (x, height - 1), 128, thresh=0)
    for y in range(height):
        if binary.getpixel((0, y)) == 0:
            ImageDraw.floodfill(binary, (0, y), 128, thresh=0)
        if binary.getpixel((width - 1, y)) == 0:
            ImageDraw.floodfill(binary, (width - 1, y), 128, thresh=0)
    return binary.point(lambda pixel: 255 if pixel == 128 else 0)


def _expand_small_silhouette(image: Image.Image, scale: int) -> Image.Image:
    alpha = image.getchannel("A")
    solid = alpha.point(lambda pixel: 255 if pixel > 128 else 0)
    solid_bbox = solid.getbbox()
    full_bbox = alpha.getbbox()
    if not solid_bbox or not full_bbox:
        return image
    longest = max(solid_bbox[2] - solid_bbox[0], solid_bbox[3] - solid_bbox[1])
    target = int(image.width * 0.72)
    if longest >= target:
        return image
    crop = image.crop(full_bbox)
    factor = target / longest
    max_factor = (image.width - 16 * scale) / max(crop.size)
    factor = min(factor, max_factor)
    if factor <= 1.0:
        return image
    resized = crop.resize(
        (round(crop.width * factor), round(crop.height * factor)),
        Image.Resampling.LANCZOS,
    )
    expanded = Image.new("RGBA", image.size, (0, 0, 0, 0))
    expanded.alpha_composite(resized, ((image.width - resized.width) // 2, (image.height - resized.height) // 2))
    return expanded


def render_glyph_sticker(content: str, color_hex: str, size: int = 220) -> Image.Image:
    """Render one transparent RGBA glyph sticker with a close white die-cut outline."""
    if not content:
        raise ValueError("Glyph sticker content cannot be empty.")

    scale = 4
    canvas_size = size * scale
    stroke = 8 * scale
    shadow_blur = 3 * scale
    max_width = canvas_size - 24 * scale
    max_height = canvas_size - 24 * scale
    if len(content) > 1:
        max_width = canvas_size - 18 * scale
        max_height = canvas_size - 34 * scale

    font = _fit_font(content, max_width, max_height, stroke)
    bbox = _text_bbox(content, font, stroke)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (canvas_size - text_w) // 2 - bbox[0]
    y = (canvas_size - text_h) // 2 - bbox[1]

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    glyph_alpha = Image.new("L", (canvas_size, canvas_size), 0)
    glyph_draw = ImageDraw.Draw(glyph_alpha)
    glyph_draw.text(
        (x, y),
        content,
        font=font,
        fill=255,
        stroke_width=stroke,
        stroke_fill=255,
    )
    shadow_alpha = glyph_alpha.filter(ImageFilter.GaussianBlur(shadow_blur))
    shadow_alpha = ImageChops.multiply(shadow_alpha, _exterior_mask(glyph_alpha))
    shadow = Image.new("RGBA", (canvas_size, canvas_size), (55, 38, 30, 0))
    shadow.putalpha(shadow_alpha.point(lambda pixel: min(pixel, 70)))
    canvas.alpha_composite(shadow)

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (x, y),
        content,
        font=font,
        fill=_hex_to_rgba(color_hex),
        stroke_width=stroke,
        stroke_fill=(255, 255, 255, 255),
    )
    canvas = _expand_small_silhouette(canvas, scale)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def catalog_records() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for index, codepoint in enumerate(range(ord("A"), ord("Z") + 1)):
        upper = chr(codepoint)
        lower = upper.lower()
        color_name, color_hex = LETTER_COLORS[index % len(LETTER_COLORS)]
        records.append({
            "id": f"block_{lower}",
            "type": "letter",
            "kind": "letter",
            "label": f"字母 {upper} (Letter {upper})",
            "chinese": f"字母 {upper}",
            "english": f"Letter {upper}",
            "content": upper,
            "letter": upper,
            "case": "uppercase",
            "color_theme": color_name,
            "color": color_hex,
            "style_category": PHONICS_STYLE_CATEGORY,
        })
        records.append({
            "id": f"block_lower_{lower}",
            "type": "letter",
            "kind": "letter",
            "label": f"細楷 {lower} (Lowercase {lower})",
            "chinese": f"細楷 {lower}",
            "english": f"Lowercase {lower}",
            "content": lower,
            "letter": lower,
            "case": "lowercase",
            "color_theme": color_name,
            "color": color_hex,
            "style_category": PHONICS_STYLE_CATEGORY,
        })
    for number in range(21):
        color_name, color_hex = NUMBER_COLORS[number % len(NUMBER_COLORS)]
        records.append({
            "id": f"block_{number}",
            "type": "number",
            "kind": "number",
            "label": f"數字 {number} (Number {number})",
            "chinese": f"數字 {number}",
            "english": f"Number {number}",
            "content": str(number),
            "number": str(number),
            "color_theme": color_name,
            "color": color_hex,
            "style_category": PHONICS_STYLE_CATEGORY,
        })
    return records


def catalog_ids() -> set[str]:
    return {record["id"] for record in catalog_records()}


def render_catalog(output_dir: Path | str = STICKER_DIR, force: bool = False) -> List[Dict[str, Any]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rendered: List[Dict[str, Any]] = []
    for record in catalog_records():
        path = output / f"{record['id']}.png"
        if force or not path.exists():
            image = render_glyph_sticker(record["content"], record["color"])
            image.save(path, format="PNG")
        rendered.append(record | {
            "runtime_path": str(path.relative_to(ROOT)).replace(os.sep, "/") if path.is_relative_to(ROOT) else str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "dimensions": list(Image.open(path).size),
            "source_font": str(resolve_font_path()),
        })
    return rendered


def release_manifest_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    manifest_records = []
    for record in records:
        manifest_records.append({
            "id": record["id"],
            "kind": record["kind"],
            "content": record["content"],
            "label": record["label"],
            "style_category": record["style_category"],
            "runtime_path": record["runtime_path"],
            "sha256": record["sha256"],
            "source_font": record["source_font"],
            "provenance": "Deterministic local Pillow text render; no AI image generation.",
            "dimensions": record["dimensions"],
            "color": record["color"],
        })
    return manifest_records
