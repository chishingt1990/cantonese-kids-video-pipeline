import os
import shutil
import numpy as np
from PIL import Image, ImageFilter

CHAR_DIR = 'assets/characters'
SPRITE_DIR = 'assets/sprites'
os.makedirs(SPRITE_DIR, exist_ok=True)

# 1. Update master character images for Levi and Luca
brain_dir = 'C:/Users/chish/.gemini/antigravity/brain/706d91eb-30af-4825-a9a0-115b05e85ba1'
shutil.copy(f'{brain_dir}/levi_style_aligned_opt2.jpg', f'{CHAR_DIR}/levi_cartoon.jpg')
shutil.copy(f'{brain_dir}/luca_style_aligned_final.jpg', f'{CHAR_DIR}/luca_cartoon.jpg')
print("Updated levi_cartoon.jpg and luca_cartoon.jpg in assets/characters")

# 2. Function to create clean RGBA cutouts with soft anti-aliased alpha borders
def create_clean_sprite(src_path, dst_path, is_dog=False):
    im = Image.open(src_path).convert('RGB')
    arr = np.array(im).astype(float)
    h, w, _ = arr.shape
    
    # Background detection (white or near white)
    # Background in our cartoon concepts is pure white [255, 255, 255] or slight off-white > 245
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    
    if is_dog:
        # Dog is white fur, but dog outline is dark charcoal
        # Flood fill or threshold based on distance from corners
        # Since background is uniformly > 248, let's use corner-seeded floodfill
        is_bg = (r > 245) & (g > 245) & (b > 245)
    else:
        is_bg = (r > 240) & (g > 240) & (b > 240)
        
    # Create binary mask: 1 = character, 0 = background
    mask = (~is_bg).astype(np.uint8) * 255
    mask_im = Image.fromarray(mask, mode='L')
    
    # Soft edge feathering (radius 1) for anti-aliasing against any scene background
    mask_smooth = mask_im.filter(ImageFilter.GaussianBlur(0.8))
    
    # Construct RGBA image
    rgba = im.convert('RGBA')
    rgba.putalpha(mask_smooth)
    
    # Crop to tight bounding box with 10px padding
    bbox = rgba.getbbox()
    if bbox:
        pad = 8
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad)
        )
        cropped = rgba.crop(crop_box)
    else:
        cropped = rgba
        
    cropped.save(dst_path, format='PNG')
    print(f"Saved sprite: {dst_path} ({cropped.size[0]}x{cropped.size[1]})")

characters = [
    ('dad_cartoon.jpg', 'dad.png', False),
    ('mom_cartoon.jpg', 'mom.png', False),
    ('levi_cartoon.jpg', 'levi.png', False),
    ('luca_cartoon.jpg', 'luca.png', False),
    ('dog_cartoon.jpg', 'dog.png', True),
    ('grandparents_paternal_cartoon.jpg', 'grandparents_paternal.png', False),
    ('grandparents_maternal_cartoon.jpg', 'grandparents_maternal.png', False),
    ('auntie_cousins_cartoon.jpg', 'auntie_cousins.png', False)
]

for src, dst, is_dog in characters:
    src_full = os.path.join(CHAR_DIR, src)
    dst_full = os.path.join(SPRITE_DIR, dst)
    if os.path.exists(src_full):
        create_clean_sprite(src_full, dst_full, is_dog)
    else:
        print(f"Warning: {src_full} not found")

print("All character sprites created successfully!")
