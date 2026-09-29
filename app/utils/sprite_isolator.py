from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def isolate_sprite(image: Image.Image, threshold: int = 35, padding: int = 10) -> Image.Image:
    """Remove only boundary-connected white from opaque art, retaining enclosed whites.

    Existing transparency is authoritative (including palette transparency). For
    opaque inputs, recover edge coverage and remove a white matte where a nearby
    darker foreground pixel explains the blend; never blur white into the alpha.
    """
    if not 0 < threshold <= 255:
        raise ValueError("threshold must be between 1 and 255")
    if padding < 0:
        raise ValueError("padding must be nonnegative")
    rgba = np.array(image.convert("RGBA"))
    h, w = rgba.shape[:2]
    if np.all(rgba[:, :, 3] == 255):
        rgb = rgba[:, :, :3]
        light = np.max(255 - rgb, axis=2) < threshold
        background = np.zeros((h, w), dtype=bool)
        queue = deque()

        def seed(y, x):
            if light[y, x] and not background[y, x]:
                background[y, x] = True
                queue.append((y, x))

        for x in range(w):
            seed(0, x)
            seed(h - 1, x)
        for y in range(h):
            seed(y, 0)
            seed(y, w - 1)
        while queue:
            y, x = queue.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w:
                    seed(ny, nx)

        rgba[background, 3] = 0
        edge = np.zeros((h, w), dtype=bool)
        edge[1:] |= background[:-1]
        edge[:-1] |= background[1:]
        edge[:, 1:] |= background[:, :-1]
        edge[:, :-1] |= background[:, 1:]
        edge &= ~background
        ys, xs = np.nonzero(edge)
        if len(ys):
            colors = rgb[ys, xs].astype(np.float32)
            reference = colors.copy()
            strength = np.sum((255 - reference) ** 2, axis=1)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = np.clip(ys + dy, 0, h - 1), np.clip(xs + dx, 0, w - 1)
                    neighbor = rgb[ny, nx].astype(np.float32)
                    score = np.sum((255 - neighbor) ** 2, axis=1)
                    better = (score > strength) & ~background[ny, nx]
                    reference[better] = neighbor[better]
                    strength[better] = score[better]
            coverage = np.clip(
                np.sum((255 - colors) * (255 - reference), axis=1)
                / np.maximum(strength, 1),
                0,
                1,
            )
            predicted = 255 + coverage[:, None] * (reference - 255)
            recover = (
                (coverage > 0.05)
                & (coverage < 0.98)
                & (np.max(np.abs(predicted - colors), axis=1) < 12)
            )
            ey, ex = ys[recover], xs[recover]
            alpha = coverage[recover]
            unmatted = (colors[recover] - 255 * (1 - alpha[:, None])) / alpha[:, None]
            rgba[ey, ex, :3] = np.clip(np.rint(unmatted), 0, 255).astype(np.uint8)
            rgba[ey, ex, 3] = np.rint(alpha * 255).astype(np.uint8)
        rgba[background, :3] = 0

    result = Image.fromarray(rgba)
    bbox = result.getchannel("A").getbbox()
    if bbox:
        result = result.crop((
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(w, bbox[2] + padding),
            min(h, bbox[3] + padding),
        ))
    return result


def isolate_sprite_from_white_bg(image_path: str, output_path: str, threshold: int = 35) -> str:
    """File adapter; approved asset destinations also obey maintenance staging."""
    requested = Path(output_path).absolute()
    destination = requested.resolve()
    assets = Path(__file__).resolve().parents[2] / "assets"
    masters = assets / "characters"
    if destination.is_relative_to(masters.resolve()):
        raise ValueError("Master character artwork is read-only")
    if destination == Path(image_path).resolve():
        raise ValueError("Sprite extraction must not overwrite its source")
    if requested.is_relative_to(assets) or destination.is_relative_to(assets.resolve()):
        from scripts.maintenance_guard import output_path as guarded_output_path

        output_path = str(guarded_output_path(requested))
        destination = Path(output_path)
    if destination.resolve() == Path(image_path).resolve():
        raise ValueError("Sprite extraction must not overwrite its source")
    if destination.exists() and destination.stat().st_nlink > 1:
        raise ValueError("Sprite extraction must not overwrite a shared file")
    with Image.open(image_path) as image:
        result = isolate_sprite(image, threshold=threshold)
    result.save(output_path, "PNG", optimize=True)
    return output_path
