import numpy as np
from PIL import Image, ImageFilter
from collections import deque

def isolate_sprite_from_white_bg(image_path: str, output_path: str, threshold: int = 35) -> str:
    """
    Isolates a character sprite from a white/light background using a boundary-seeded
    flood fill that respects dark outer contour lines, preserving interior white/light colors
    (such as white fur, white shirts, eye whites). Applies subtle edge anti-aliasing.
    """
    im = Image.open(image_path).convert('RGB')
    arr = np.array(im)
    h, w, _ = arr.shape

    # Distance from white (255, 255, 255)
    diff = np.max(np.abs(arr.astype(int) - 255), axis=2)

    visited = np.zeros((h, w), dtype=bool)
    is_bg = np.zeros((h, w), dtype=bool)

    queue = deque()
    # Seed from all 4 borders
    for x in range(w):
        queue.append((0, x))
        queue.append((h - 1, x))
    for y in range(h):
        queue.append((y, 0))
        queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        if visited[y, x]:
            continue
        visited[y, x] = True

        if diff[y, x] < threshold:
            is_bg[y, x] = True
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    if diff[ny, nx] < threshold:
                        queue.append((ny, nx))

    # Build alpha mask: 0 for bg, 255 for sprite
    alpha = np.where(is_bg, 0, 255).astype(np.uint8)

    # Edge anti-aliasing: smooth 1-pixel boundary
    alpha_im = Image.fromarray(alpha, mode='L')
    alpha_im = alpha_im.filter(ImageFilter.SMOOTH_MORE)
    smooth_alpha = np.array(alpha_im)

    rgba = np.dstack([arr, smooth_alpha])
    # Keep strictly outer bg 0
    rgba[is_bg, 3] = 0

    out_im = Image.fromarray(rgba, 'RGBA')

    # Crop to bounding box with 10px margin
    bbox = out_im.getbbox()
    if bbox:
        left = max(0, bbox[0] - 10)
        top = max(0, bbox[1] - 10)
        right = min(w, bbox[2] + 10)
        bottom = min(h, bbox[3] + 10)
        out_im = out_im.crop((left, top, right, bottom))

    out_im.save(output_path, 'PNG', optimize=True)
    return output_path
