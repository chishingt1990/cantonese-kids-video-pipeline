# Cantonese Kids Video Studio - Visual & Storybook Style Guide

This style guide documents the canonical visual specifications for backgrounds, characters, and educational stickers, grounded in the art style established by `bg_kitchen.png`, `bg_playroom.png`, and `bg_beach.png`.

---

## 1. Background Visual Specification (Storybook Watercolor)

### Core Aesthetic Principles
- **Medium**: Soft watercolor wash on textured paper with fine, warm sepia pencil line art.
- **Lighting & Mood**: Warm, cheerful, inviting daytime natural sunlight or cozy bedtime starry night.
- **Color Palette**:
  - *Warm Wall Pastels*: Buttercream yellow (`#FFFBEB`), pale apricot cream (`#FEF3C7`), soft warm beige.
  - *Natural Wood Tones*: Honey birch, warm maple, natural light oak (`#D97706` / `#B45309`).
  - *Accent Pastels*: Powder blue (`#BAE6FD`), sage/mint green (`#A7F3D0`), soft coral rose (`#FECDD3`), lavender (`#E9D5FF`).
- **Signature Architectural Motif**:
  - Arched wooden frame windows (`arched window`) overlooking sunny green gardens, blue skies, or crescent moons.
  - Cheerful triangular pennant bunting banners strung across the upper wall.
  - Rounded toddler-safe corners on all furniture (chairs, shelves, tables).
- **Stage Ground Line & Character Staging**:
  - Floor baseline sits comfortably at **$y \approx 720\text{px} - 880\text{px}$** (on a 1920x1080 canvas).
  - Keeps the bottom **$910\text{px} - 1050\text{px}$** zone clear for the Layer 100 forefront bilingual subtitle pill.
  - Provides open space across the horizontal width for 1 to 5 characters to move, stand, sit, and interact naturally without clutter.

### Master Preset Scenes
1. `kitchen`: Arched window, butter-yellow cabinets, wooden dining table with fruit bowl, two toddler high chairs (polka dot & floral).
2. `playroom`: Arched window with outdoor tree, colorful foam puzzle playmat, low wooden table, toy shelf with teddy bears and ABC blocks, rainbow stacker.
3. `beach`: Golden sandy shore with detailed sandcastle, bright red shovel and blue sun pail, gentle turquoise ocean waves, warm smiling sun, distant palm island.
4. `living_room`: Arched wooden window with garden view, cozy off-white sofa with pastel cushions, soft playmat, potted green plant, sun/moon framed picture.
5. `nursery`: Nighttime setting with dark blue starry sky and smiling crescent moon visible through arched window, pastel crib with teddy bear, glowing star night lamp, fluffy white cloud rug.
6. `park`: Rolling green grass meadow, shady oak tree, picnic blanket with wicker snack basket, soft fluffy white clouds, warm sunny sky.
7. `mountains`: Gentle rolling wildflower hills (pink, yellow, blue blossoms), meandering dirt path, distant lavender peaks under soft blue morning sky.
8. `bathroom`: Arched wooden window, clawfoot toddler bathtub overflowing with bubbly foam and yellow rubber duckies, pastel mosaic tiles, wooden towel rack.
9. `dining`: Dim sum family banquet, round wooden dining table with steaming bamboo dim sum baskets, teapot, teacups, fruit platter, framed dim sum wall art.
10. `reading_nook`: Cozy storytime corner, low wooden bookshelves filled with picture books, bean bag cushions, warm floor rug, soft warm reading lamp.

---

## 2. Character Canon & Standardized Art Methodology

All characters are rendered in a consistent, clean 2D storybook / preschool animation style with warm, friendly facial expressions, rosy cheeks, and expressive dark eyes.

### Standardized Art Rules & Quality Constraints
1. **Anchor References**: All new sprite variations must directly ground their facial structure, palette swatches, and line weights from the canonical anchor portraits (`dad.png`, `mom.png`, `dog.png`, `levi.png`, `luca.png`).
2. **Outlines**: Crisp, bold, solid dark chocolate/charcoal strokes (`#2d1a14` / `#1e293b`). No rough pencil sketch lines or blurry watercolor fringes.
3. **Color & Shading**: Solid, saturated matte colors with smooth, subtle 2-tone cel-shading.
4. **No Specular Highlights / Glossiness**: No bright white specular streaks, plastic sheen, or glossy shine on hair or shirts. Hair is solid matte dark charcoal/black (`#1c1917` / `#292524`).
5. **No Paper Grain / Faded Wash**: Character figures are opaque and vibrant without chalky paper grain or washed-out watercolor textures.
6. **Organic Props & Anatomy**: Any held prop (storybook, banana, tea cup, toy) must be an organically drawn, fully integrated part of the illustration matching the character's line weight and lighting—never flat geometric CAD shapes pasted over a standing sprite.
7. **Clean Alpha Cutout**: Sprites must have true transparent backgrounds with smooth anti-aliased edges and tight bounding boxes. Human and animal characters must NOT have white sticker die-cut borders or outer contour halos.

### Character Specifics:
- **🧒 Levi (哥哥)**: 2–3 years old. Matte dark hair with upward curving quiff, solid coral-red polo (`#dc2626`), navy shorts (`#1e3a8a`), royal blue sneakers.
- **👦 Luca (細佬)**: 2–3 years old. Matte dark hair with straight bangs and top cowlick, solid sunshine-yellow polo (`#facc15`), navy shorts, royal blue sneakers.
- **👨 Dad (爸爸)**: Youthful father (late 20s / early 30s), modern thin rectangular glasses, friendly neat stubble, smiling crescent eyes, slate-blue polo/crewneck (`#475569` / `#3b82f6` blend), khaki chinos, grey canvas sneakers.
- **👩 Mom (媽媽)**: Silky dark hair in a low side ponytail, gentle caring smile, coral apron or lavender knit with jeans.
- **🐕 Doggy (狗狗 - Japanese Spitz)**: Pure white fluffy cloud fur, alert prick ears, dark button nose, anime sparkling eyes, rosy blush cheeks, holding items naturally in mouth or sitting attentively.
- **👴👵 Paternal Grandparents (爺爺 & 嫲嫲)**: 爺爺 wears royal blue polo and glasses; 嫲嫲 wears soft magenta/lavender blouse and glasses.
- **👴👵 Maternal Grandparents (公公 & 婆婆)**: 公公 wears white tee and buzz cut; 婆婆 wears floral/white blouse and beaded bracelet.
- **👩👦 Auntie & Cousins (姑媽 & 表哥)**: Modern family look, cool glasses, cargo shorts.

---

## 3. Educational Stickers & Word Badges Specification

### Visual Attributes
- **Shape**: Snug, content-proportional rounded pill badge (pill radius $\approx 46\%$ of badge height).
- **Typography Lockup**:
  - **Spoken Cantonese**: Prominent top Chinese text (e.g. `多謝`, `早晨`, `好乖！`, `抱抱`) rendered in bold rounded Gothic / Microsoft JhengHei.
  - **English Subtitle**: Centered directly beneath in clear uppercase, sized harmoniously ($\approx 40\%$ of Chinese font size).
  - **Centering**: Chinese and English lines are vertically centered together as a single balanced typography unit. No awkward empty space at the bottom.
- **Styling**:
  - Pure white outer die-cut border with a soft warm gaussian drop shadow.
  - Inner pastel watercolor fill matching theme colors (`amber`, `gold`, `rose`, `emerald`, `sky`, `purple`, `pink`).
  - Warm sepia contour outline (`outline_color`) matching the picture-book illustration pencil line art.
  - Tiny decorative star motifs on the left and right flanks.
