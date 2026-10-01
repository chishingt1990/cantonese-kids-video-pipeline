# Cantonese Kids Video Studio - Visual & Storybook Style Guide

This guide is the source of truth for **new** backgrounds, characters, and educational stickers. It does not certify every existing asset as conforming. Background texture and character finish are deliberately different: watercolor environments, clean matte characters.

Reviewed against all **201 tracked images** on `main` at `3048052` on 2026-09-30: 16 backgrounds, 28 character/concept files (including 8 SVGs), 68 sprites, 88 stickers, and one project thumbnail. The review covered contact sheets of every image, rendered SVGs, full-size twin anchors, and image dimensions/alpha metadata. This is not a frame-by-frame review of every possible scene.

## 0. Reference Authority and Change Boundaries

1. Use the exact **current runtime anchors** in Section 2 for identity, proportions, clothes, and palette. Match a named file, not a remembered description of the character.
2. Apply this guide's finish, anatomy, transparency, and acceptance rules. An old artifact in an anchor is not permission to reproduce clipped edges, extraction damage, or a white halo.
3. Other poses are action references only after checking that they preserve the anchor identity. Do not use an off-model pose to redefine the character.
4. `assets/characters/*_cartoon.jpg`, `*_clean.png`, `variations/*`, and the eight SVGs are **historical/concept references**, not interchangeable runtime masters. `style_showcase.html` and `twins_options.html` retain historical descriptions and selection labels; those labels do not override the current sprite anchors or establish new approval.
5. Keep all existing artwork unchanged during guide/prompt preparation. Do not run restoration, recoloring, or bulk generation scripts to "bring everything into compliance."

If a requested change would alter an anchor's identity, outfit, family composition, or style, obtain a separate decision before generating it. No provider, quota, price, or privacy approval can be inferred from an old showcase page.

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
   - These are recurring indoor motifs, not mandatory decorations in every scene. Do not add windows or bunting to outdoor scenes merely to match a keyword list.
- **Stage Ground Line & Character Staging**:
   - Deliver a **1920x1080, 16:9, opaque RGB PNG**, matching the 16 existing backgrounds. The primary style references are `assets/backgrounds/bg_kitchen.png`, `bg_playroom.png`, and `bg_beach.png`.
   - Composition target: an unobstructed standing area around **y = 720-880 px** and a low-detail subtitle region around **y = 910-1050 px**. These are design targets, not enforced renderer bounds.
   - Actual runtime discrepancy: the renderer's missing-`y_percent` fallback is **880 px**, while the scene-director prompt specifies **88% = 950.4 px** at 1080p (truncated to 950 before animation). Do not equate these values or claim feet are automatically subtitle-safe. Review the actual staged scene and adjust placement explicitly.
   - Leave usable space for the intended cast. One to five characters is a composition goal, not proof that all five fit every existing background. Tables, tubs, shelves, playground equipment, and foreground foliage can occlude bodies or make feet appear to float.
   - Review a staged composite with subtitles before accepting a background. Do not bake people, captions, watermarks, or essential generated text into a new background; add text through the typography pipeline.

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

### Additional Existing Scenes
The catalog also contains `art_room`, `backyard_garden`, `duck_pond`, `farm_field`, `playground`, and `supermarket`. All 16 files use `assets/backgrounds/bg_<background_id>.png`. These six extend the same environment palette; they do not establish a different character style. Existing signs, packaging, and wall lettering are not templates for generating readable Cantonese.

---

## 2. Character Canon & Standardized Art Methodology

New characters/poses use a clean 2D storybook / preschool animation finish with warm expressions, rosy cheeks, and expressive dark eyes. Preserve the current family's likeness and relative proportions; do not redesign them as generic babies, anime characters, or 3D toys.

### Exact Runtime Identity Anchors

All paths below are relative to `assets/sprites/`. At the audited commit, each anchor is byte-identical to its `<character_id>_default.png` counterpart. They are separate tracked paths; identical bytes do not imply automatic synchronization.

| Runtime character ID | Identity reference | Existing anchor canvas | Identity/outfit lock |
|---|---|---|---|
| `levi` | `levi.png` | 359x919 | Upward-curving quiff; open smiling mouth; coral-red collared polo, navy shorts, visible white socks, blue sneakers with white soles. Preserve his facial silhouette and hair direction. |
| `luca` | `luca.png` | 325x933 | Straight segmented fringe with a single upward cowlick; gentle closed smile; yellow collared polo, navy shorts, blue sneakers with white soles and no tall visible socks. |
| `dad` | `dad.png` | 384x960 | Dark hair, rectangular glasses, blue polo, khaki trousers, gray shoes; match facial hair and facial features to the image rather than inventing extra stubble. |
| `mom` | `mom.png` | 442x970 | Side ponytail, lavender short-sleeved top, jeans, light shoes and existing accessories. An apron is a separately approved outfit, not the default. |
| `dog` | `dog.png` | 815x856 | White Japanese Spitz: upright pointed ears, fluffy silhouette, dark eyes/nose and curled fluffy tail. Keep white fur opaque. |
| `grandparents_paternal` | `grandparents_paternal.png` | See source file | Two-person group; preserve each face, glasses, blue/purple clothing and relative heights. |
| `grandparents_maternal` | `grandparents_maternal.png` | See source file | Two-person group; preserve grandfather's short hair and white shirt and grandmother's floral blouse/accessories. |
| `auntie_cousins` | `auntie_cousins.png` | See source file | Three-person group; preserve the exact member count, faces, glasses where present, outfits and relative heights. |

These eight IDs are the runtime sprite catalog, not the individual-person IDs in `config/characters.json`. Do not introduce a new character by merely inventing a filename.

Anchor sizes describe current files, **not mandatory output dimensions**. Levi/Luca anchors touch their canvas bounds; most other anchors have eight-pixel margins. Do not reproduce the zero-margin clipping risk in new exports.

### Standardized Art Rules & Quality Constraints
1. **Anchor References**: Supply the exact identity image for the requested character. Use the other twin only as a secondary consistency comparison, never as a face donor. Expressions may change with the action; skull shape, eyes, ears, hair silhouette, age impression and proportions must remain recognizable.
2. **Outlines**: Crisp, continuous dark chocolate/charcoal strokes. `#2d1a14` / `#1e293b` are palette cues, not exact sampled color requirements. Match apparent line weight to the anchor at the same displayed head size. No rough sketch contours or blurry watercolor fringes.
3. **Color & Shading**: Opaque, saturated matte fills with restrained broad cel-shading. Preserve skin tone, blush, clothing color families and lighting direction. Do not mechanically recolor a different character to match.
4. **No Specular Highlights / Glossiness**: No bright white streaks, plastic sheen or 3D shine on hair/shirts. Broad, subtle charcoal hair shading is acceptable. Small eye catchlights and actual white teeth/shoe soles are not prohibited gloss.
5. **No Paper Grain / Faded Wash**: New figures should not add chalky grain or watercolor bleed. Existing raster anchors contain some texture/tonal variation; match their likeness without amplifying those artifacts. Watercolor belongs primarily in the environment.
6. **Organic Props & Anatomy**: Redraw the whole action coherently: shoulder, elbow, wrist, hand grip, torso balance, hips, knees and feet. Held props must share the figure's perspective, contours and lighting. No pasted geometric props, disembodied hands, extra limbs/fingers, melted grips or unsupported objects. Stylized hands must remain consistent with the anchor, not become photorealistic.
7. **Real Pose Changes**: Tilting, mirroring, stretching or rotating the standing master alone does not create jumping, dancing, running or sleeping. Require an action-readable silhouette without a caption.
8. **Clean Alpha Cutout**: Use a true RGBA PNG, not white/checkerboard pixels painted behind the subject. Keep skin, clothes, eye whites, teeth, soles and dog fur opaque; transparency belongs outside the figure and in real gaps between limbs. Anti-alias the edge without white/colored fringes. No sticker border, glow, watermark, baked ground shadow, motion arrows or caption.
9. **Framing**: Preserve the entire silhouette, including hair tufts, fingers, shoes, tails and held props. After removing stray pixels, crop to the alpha bounds and add **eight transparent pixels on every side** for new exports. This is a new production convention, not a description of every legacy asset. Do not use vast transparent margins to fake airborne height.
10. **Direction & Mirroring**: Prefer a readable front or mild three-quarter view. Record facing direction. Runtime `flip` mirrors the entire sprite, including hair, hand dominance and props; do not rely on asymmetric text or left/right instructional details surviving it.

### Names, Age and Palette

Preserve the family labels: Levi (哥哥), Luca (細佬), Dad (爸爸), Mom (媽媽), Doggy (狗狗), paternal grandparents (爺爺、嫲嫲), maternal grandparents (公公、婆婆), and auntie/cousins (姑媽、表哥). The twins' intended age is roughly 2-3; do not shrink or enlarge their heads to force generic toddler proportions different from the anchors.

Levi red `#dc2626`, Luca yellow `#facc15`, navy `#1e3a8a`, and charcoal `#1c1917` / `#292524` are nominal palette cues. Source images include shading and compression, so use side-by-side visual matching rather than treating these hex values as exact skin/clothing samples. Default shirts have their own red/yellow collars, not the white collars in some legacy SVGs.

### Export, Scale and Grounding

- There is no fixed sprite canvas enforced by the renderer. Generate at useful source resolution (suggested working canvas **1024x1536**, or a wider canvas when the action needs it), then crop/pad as above. Do not upscale a tiny image merely to pass pixel-count checks.
- `render_service.py` scales the **whole PNG rectangle**, preserving aspect ratio before animation. Base heights at scale 1 are **760 px** for adults/groups, **520 px** for toddlers, and **320 px** for the dog.
- Placement is bottom-center of the image rectangle, not the feet, alpha bounds or a shared skeleton. Padding, raised arms, crouching and sitting therefore change apparent body size/grounding.
- Compare a candidate beside its default on a 1920x1080 stage. Match apparent head/body scale and adjust the scene's explicit scale/position where necessary. Record those settings with the review; do not distort the anatomy or silently change the renderer.
- A jumping sprite is an airborne body shape, not a jump animation. The scene must place it above the intended floor. A dancing sprite depicts one readable step, not an automatically animated dance.

### Current Automated Integrity Checks Are Not Visual Approval

`test_full_system.py`, `test_03_character_congruency`, checks API-listed poses for RGBA mode, **at least 70,000 pixels with alpha > 0**, **at least 25% occupied pixels over the entire canvas**, and **at least 65% non-near-black occupied pixels** (near-black means all RGB channels < 50).

Despite the test variable name `opaque_px`, alpha > 0 is **not** proof of opacity. These tests do not verify identity, correct poses, white-material preservation, transparent backgrounds, unclipped limbs, clean edges or stage alignment. Approval requires both technical and visual review; do not weaken checks or fill a background to make a candidate pass.

---

## 3. Educational Stickers & Word Badges Specification

### Visual Attributes
- **Scope**: The pill specification below applies to **word/vocabulary badges**, not every sticker. Letter and number teaching stickers are now glyph-shaped phonics stickers, not boxed toy blocks.
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

### Typography and Prop Quality Gates

- Use Traditional Chinese and authentic spoken Cantonese appropriate to the scene. Verify the wording and English meaning; do not infer them from internal IDs. Letter/number teaching blocks are a deliberate exception to bilingual pill layout.
- Render words with an installed font that actually contains the required glyphs. Inspect the raster output, not just the text string. Reject tofu boxes, missing glyphs, garbled text, clipping and internal identifiers such as `vocab_banana`.
- Props must depict the named object at useful stage size. A blank circle, generic star or missing emoji glyph is not an acceptable substitute for a bus, apple, duck or train.
- A sticker may use a restrained white die-cut outline/shadow; a character sprite may not. Avoid double borders when a prop is drawn as part of a character's hand-held action.
- Phonics letter/number stickers must be deterministic local font renders with transparent RGBA exteriors, vivid matte colored glyph fills, and a close white die-cut outline following the glyph contours. Do not use box, tile, circle, or pill backgrounds for alphabet/number stickers. Preserve interior counters/holes in glyphs such as `A`, `B`, `0`, and `8`; multi-digit numbers should be the union of digit contours with no enclosing badge.
- `get_or_render_sticker(..., force=False)` reuses an existing file (or matching `prop_` file). `force=True` can overwrite it; missing files can be generated at module import through `ensure_base_stickers()`. Do not delete the sticker directory or import the application as a read-only review shortcut.
- Repairs to existing stickers require their own reviewed replacement batch. Do not regenerate all stickers during character-pose preparation.

---

## 4. Naming, Candidate Isolation and Runtime Availability

### File Contract

Approved pose files use `assets/sprites/<character_id>_<pose_id>.png`, lowercase ASCII with underscores. The eight IDs are the anchor table above. `assets/sprites/<character_id>.png` is the identity reference; `_default.png` is the runtime default. Do not overwrite either for a new action.

Keep candidates, contact sheets, metadata and rejected attempts **outside** `assets/sprites`, `assets/characters`, `assets/stickers`, and `assets/backgrounds`. For this batch use a separate local review folder such as `design/2026-09-30-character-audit/candidates/` in the parent Clawpilot workspace, not a discoverable asset directory. Candidate names may include revisions there; promote only the approved final file to the exact runtime name.

The character API dynamically discovers `<character_id>_*.png`. Its current `temp_`/`test_` filename checks do **not** protect `levi_test_jumping.png` or `luca_temp_dancing.png`. Merely placing those files in the sprite directory can expose them in staging.

### Manual Selection Is Not Automatic Direction

`app/routers/characters.py` combines a static catalog with file discovery. Missing files are removed from the returned pose list; new matching files can appear with generic labels.

`app/services/scene_director_service.py` maintains a separate `CHARACTER_POSES` allowlist and a separate text prompt. Its AI-result validation changes unrecognized poses to `default`. Some deterministic heuristic branches use a wider pose vocabulary; this does not provide reliable support for arbitrary new poses.

As of the audited commit, **none** of `jumping`, `dancing`, or `brushing_teeth` is in the twin director allowlists. The six proposed files are also absent. Adding PNGs alone enables discovery, **not end-to-end automatic narrative selection**.

Promotion therefore has two distinct scopes:
1. Artwork-only: approved PNGs become manually selectable; review their staging explicitly.
2. Automatic direction: separately update both director allowlists/prompts and any intended heuristic mappings, with integration tests. Do not claim this happened as part of a documentation-only audit.

### Legacy Script Safety

Do not run `build_all_sprites.py`, `prepare_character_sprites.py`, `restore_and_link_authentic_sprites.py`, `standardize_and_fix_sprites.py`, or the `generate_*sprites.py` utilities as unattended batch preparation. They can write over canonical filenames, change colors or rebuild poses from historical concepts; several depend on another machine's hardcoded source paths.

In particular, `prepare_character_sprites.py` removes near-white pixels globally, including potential white interior details. Its comment is not evidence of a safe boundary-only mask. Border-connected extraction in other scripts is safer only when the white subject is genuinely enclosed; it still needs review. Never remove all white pixels to cut out white fur, shoes, teeth or a toothbrush.

---

## 5. Observed Legacy Exceptions (Not New-Asset Precedents)

This audit did not modify any of these images. A catalog entry or an old "approved" page label is not a present-day quality pass.

| Category | Evidence from the image review | Rule for new work |
|---|---|---|
| Twin identity drift | `levi_sad.png` / `levi_holding_book.png` have a broader, more rendered face/hair treatment than `levi.png`; `luca_crying.png` likewise differs from `luca.png`. | Keep the named runtime anchor as identity reference; use emotion/action only from off-model examples. |
| Palette and outline drift | `levi_playing_blocks.png` and `levi_playing_car.png` use visibly bright-blue shorts; `luca_playing_blocks.png` has particularly heavy black contours. | Match anchor navy and relative line weight. |
| Gloss and 3D drift | `dad_comforting_hug.png` and several book/emotion variants show stronger modeling/highlights than the clean anchors. | Do not use them as finish references for the first batch. |
| Rigid-transform actions | Several cheering/waving/playing variants retain a standing silhouette with tilt or added overlay; `levi_sleeping.png` / `luca_sleeping.png` remain upright rather than reclining. | Judge the visible action, not the filename; redraw the joints and balance. |
| Background removal/framing | Twins' default alpha bounds touch all four canvas edges; some other assets have soft pale edge/shadow residue. | Preserve complete silhouettes, eight-pixel export padding, and review on light/dark backgrounds. |
| Historical concepts | SVGs and JPG variations differ in head proportions, fringe, collars, shoes, texture and facial styling. | Do not mix styles or average the twins' identities. |
| Empty/placeholder-looking props | Examples include `prop_apple.png`, `prop_bus.png`, `prop_cookie.png` and `prop_train.png`; visible backing shapes/glyph failures do not read as the named object. | Reject at semantic visual review even if alpha/pixel tests pass. |
| Missing glyphs/internal text | `badge_vocab_A 係 Ap.png` / `badge_vocab_C 係 Ca.png` contain broken-looking glyphs; `vocab_banana.png` displays `vocab_banana` instead of a usable vocabulary label. | Inspect real rendered glyphs and meaning, not only filenames/metadata. |
| Duplicate/mixed badge systems | `sticker_*`, `badge_*`, `vocab_*` and `word_*` coexist with inconsistent layouts. | Select the badge or prop contract deliberately; do not require all objects to be pills. |
| Scene-specific composition | The 16 backgrounds vary in usable floor area and foreground clutter; the sample thumbnail embeds a completed scene and title. | Stage-test backgrounds; the thumbnail is not an isolated asset/reference master. |
| Expanded background overlays | Staging previews reveal large flat overlays in the six expanded scenes (`art_room`, `backyard_garden`, `duck_pond`, `farm_field`, `playground`, `supermarket`), sometimes retaining incompatible indoor context. Generic twin positions also intersect furniture in kitchen/dining/reading scenes. | Review environment coherence separately from palette. Retain originals, use action-specific placement, and request clear-floor variants only for lessons that need them. |

---

## 6. First Pose Batch: Reference-Grounded Prompt Pack

**Status:** the initial prompt pack below is retained as design history. A revised six-prompt pack was subsequently approved and executed through Copilot Designer, and the user approved all six resulting sprites plus six locally rendered badges for local integration. See Section 7 and `config/artwork_release_v1.json` for installed export provenance; do not treat the old preparation prompts as an instruction to regenerate them.

**Creative brief:** Create six distinct, full-body poses of the existing Levi and Luca for gentle preschool Cantonese lessons. Preserve their current identity and default clothing, produce clean matte RGBA cutouts, and make each action legible without text. Work from existing illustrated anchors, not raw family photos. No paid fallback or provider upload is authorized by this prompt pack.

### Reference Attachments

- Levi jobs: `assets/sprites/levi.png` is primary. `assets/sprites/luca.png` may be supplied only as a labeled secondary consistency reference.
- Luca jobs: `assets/sprites/luca.png` is primary; reverse the secondary relationship.
- Background context, if needed: `assets/backgrounds/bg_playroom.png` as **environment-only** context. Do not transfer its paper texture onto the child.
- Brushing-teeth props: `assets/stickers/prop_toothbrush_blue.png` for Levi, `prop_toothbrush_yellow.png` for Luca, as shape/color cues only. Redraw the brush with the hand; never paste the sticker or its outline into the figure.

### Shared Prompt (Prepend to Each Row)

> Create one full-body 2D preschool storybook character pose from the attached PRIMARY identity reference. Reproduce that child's facial silhouette, eye/ear shape, hair silhouette, skin tone, blush, head-to-body proportions, clothing cut, colors and blue shoes with white soles. Levi has his upward-curving quiff, red polo and visible white socks; Luca has his straight segmented fringe, one cowlick, yellow polo and no tall visible socks. Use only the identity specified for this job. Retain navy shorts and the shirt's own colored collar. Change the body and expression only as needed for the requested action. Draw anatomically coherent joints, hands and weight balance with the reference's dark clean outline, opaque matte fills and restrained cel-shading. Use an isolated transparent background and a readable front/mild three-quarter view. Include the complete hair, hands, feet and prop; do not crop. One child, one pose, no scene, text or graphic effects. Suggested working canvas 1024x1536; allow extra width for extended arms without squeezing the body.

### Six Complete Action Instructions

Append the relevant instruction to the shared prompt and use the matching primary anchor:

| Final filename after approval | Character/action instruction |
|---|---|
| `levi_jumping.png` | Levi making a small joyful hop, both feet airborne, knees gently bent, arms opened diagonally below head height, happy open smile. His pelvis, knees and soles must clearly describe a hop, not a rotated standing figure. Preserve the quiff and red outfit. No platform or motion lines. |
| `luca_jumping.png` | Luca making a small playful hop, both feet airborne with gently tucked knees, elbows bent and hands slightly out for balance, cheerful expression preserving his rounder features and cowlick. Keep the yellow outfit; do not copy Levi's face or hair. No platform or motion lines. |
| `levi_dancing.png` | Levi doing a gentle side-step dance, weight visibly on one planted foot, other foot lightly lifted sideways, knees soft and arms bent in a natural counterbalancing rhythm. Joyful but stable preschool movement. Keep hands below the top of his head and preserve the quiff/red polo. |
| `luca_dancing.png` | Luca doing a gentle toe-tap dance, one supporting foot flat, the other toe extended lightly forward, soft knees, small torso sway and bent elbows held apart. Clearly different from clapping, jumping or running. Preserve fringe, cowlick, yellow polo and facial identity. |
| `levi_brushing_teeth.png` | Levi standing still and gently brushing the front teeth with a small blue child-sized toothbrush. One hand grips the handle coherently near his chest; bristles meet the visible front teeth at the mouth edge, not deep inside the mouth. The other arm rests naturally. Keep both feet planted and use at most a tiny amount of foam, with no toothpaste tube or text. This is a calm supervised-routine illustration, not walking/running with a brush. |
| `luca_brushing_teeth.png` | Luca standing still and gently brushing the front teeth with a small yellow child-sized toothbrush. Draw a clear hand grip, wrist and elbow; bristles touch the visible front teeth at the mouth edge. The other hand rests by his side. Keep both feet planted, preserve cowlick/fringe and yellow clothing, and separate the brush silhouette from the shirt so it reads clearly. Minimal foam; no tube, swallowing action, walking or running. |

**Shared negative prompt / avoid list:** different child; twin identity swap; redesigned hair; changed age/head proportions; wrong shirt/shorts/shoes; white polo collar; photorealism; 3D plastic; glossy streaks; watercolor bleed; rough sketch lines; pale washed-out body; missing/extra/warped limbs or fingers; melted grip; floating prop; pasted sticker; rigid standing cutout rotated to simulate motion; unsafe toothbrush placement; cropped silhouette; white halo; die-cut border; ground shadow; checkerboard baked into image; text; logo; watermark; unreadable glyphs; glowing-brain/circuit overlays or unrelated stock-business imagery.

### Generation and Approval Sequence

1. Confirm an available image-capable provider, reference-image support, permitted use, included/free allowance and data-handling terms **before** any upload or generation. Text-only instructions do not guarantee likeness. This repository's existing compositing scripts are not a substitute for a verified image-generation connection.
2. Start with one candidate, `levi_jumping`, to calibrate identity, matte finish and action readability. Review it before spending requests on the remaining five. This is the preparation order, not a claim that a provider or quota is ready.
3. Save candidates to the isolated review folder. Record primary reference path/hash, exact prompt, provider/model if used, revision, source dimensions, facing direction and any extraction/export steps alongside them.
4. Inspect each candidate at full size and stage size against its anchor, over white, dark gray and checkerboard, then on the playroom scene. Check face/hair/clothes, complete anatomy, action silhouette, opaque white details, clean alpha edges and framing. Check brushing props at actual stage size.
5. Apply the eight-pixel export padding and existing integrity checks. Stage beside the default at the actual renderer base height; review head scale, feet, airborne position and subtitle clearance. Document any required scene scale/placement. A numeric pass cannot waive a visual failure.
6. Present the six candidates/contact sheet for explicit visual approval. Only then copy approved finals to the six runtime filenames; never overwrite the defaults or promote intermediate candidates. Commit/push and automatic-direction integration remain separate actions.

**Scope boundary:** approval of this batch is not approval of future generation requests, new outfits, identity redesign, voice work, pipeline merges or existing-asset replacements. Future external prompt/reference packs still require their own approval/privacy/cost gates.

---

## 7. Approved Starter Release

The user initially approved these twelve assets for local `main` integration. They are now part of the complete 60-asset release described in Section 8. Default identity anchors remain unchanged.

| Type | Runtime filenames / IDs |
|---|---|
| Twin sprites | `levi_jumping.png`, `luca_jumping.png`, `levi_dancing.png`, `luca_dancing.png`, `levi_brushing_teeth.png`, `luca_brushing_teeth.png` in `assets/sprites/` |
| Hygiene badges | `badge_routine_brush_teeth` (刷牙 / BRUSH TEETH), `badge_routine_wash_hands` (洗手 / WASH HANDS) |
| Meal/play badges | `badge_routine_eat` (食飯 / MEALTIME), `badge_play_together_v1` (一齊玩 / PLAY TOGETHER), `badge_take_turns_v1` (輪住玩 / TAKE TURNS) |
| Bedtime badge | `badge_bedtime_sleep` (瞓覺 / SLEEP) |

Badge filenames are their IDs plus `.png` under `assets/stickers/`. They use locally rendered Microsoft JhengHei glyphs, not generated lettering.

`config/artwork_release_v1.json` records approved file hashes, original-download hashes, reference hashes and export operations. It is a provenance manifest, not a replacement for the application's runtime catalogs. Original downloads and review artifacts remain outside runtime assets.

The six downloaded sprite originals had near-opaque interiors at alpha 253/254. Their derived production exports set alpha >= 250 to 255 and alpha <= 2 to zero, preserve intermediate edge alpha and all RGB values, crop the remaining alpha bounds, then add eight transparent pixels on every side. No recoloring, geometric distortion or resampling was applied during export. This operation is specific to this approved batch, not a rule to apply blindly to every image.

The six approved badge files were copied byte-for-byte, retaining their intentional border/shadow transparency. Do not run sprite alpha normalization on badges.

At a 520px whole-canvas sprite height, the reviewed static layouts use a bottom anchor of 800px for the airborne jumping pose and 880px for dancing/brushing, with the playroom or bathroom scene respectively. These are action-specific layout references, not global renderer changes; explicit scene placement still takes precedence. Static layouts do not replace review of actual motion and subtitles.

### Runtime Integration

- The pose picker discovers all six PNGs and labels the actions as Jumping / 跳起, Dancing / 跳舞, and Brushing Teeth / 刷牙.
- Both twins' director allowlists and the AI prompt include the new poses. Missing coordinates receive action-specific defaults; explicit valid coordinates remain unchanged.
- The offline director recognizes concrete Cantonese/English action cues. Existing sadness/comfort handling takes priority; toothbrushing takes priority over movement. Existing valid background selections are retained.
- Named-child scene tweaks can request the three new actions without changing the other child's pose or overwriting existing vertical placement.
- All six badges are registered with their exact Cantonese/English labels and existing compatible fallback theme names. Cached approved PNGs are reused unchanged. Matching lesson cues can select the approved badges, and AI plans referencing their IDs are normalized to the corresponding visible label.
- `test_artwork_release.py` exercises the APIs, director, cache preservation and export integrity in a temporary asset tree. The existing full-system badge test recognizes the approved higher-resolution images by dimensions, proportions and release hashes instead of imposing its legacy 120px source-height limit on them.

## 8. Complete Approved Asset Release

The complete release includes the six twin poses, six Cantonese badges and **48
approved props**: eight repairs and forty additions. There are **52 new PNGs and
eight intentional replacements** relative to the original `main` artwork.

Replaced prop IDs: `prop_apple`, `prop_cookie`, `prop_bus`, `prop_train`,
`prop_airplane`, `prop_duckling`, `prop_frog`, and `prop_bunny`. The matte apple
revision is used, not its glossy first trial. Earlier runtime versions remain in
Git history, and the release manifest records their prior hashes.

The forty additions cover eight animals, eight vehicles, eight fruits/vegetables,
eight foods/snacks and eight everyday objects. Exact IDs, Cantonese/English
labels, source hashes and production hashes are in `config/artwork_release_v1.json`.
Some generated tonal variation was accepted by the user; do not reinterpret this
as removal of the matte target for future generations.

Prop exports preserve their artwork and white materials: remove alpha <= 2
speckles, set near-opaque alpha >= 250 to 255, crop, downsample only when necessary
to fit within 1008x1008, and add eight transparent pixels per side. The source
images remain preserved outside the public release. Do not run legacy generators
over the approved prop PNGs.

The sticker catalog loads the 48 prop labels from the manifest. New prop names
and Cantonese labels are available to the AI director and offline object-learning
scenes. Approved prop regeneration is rejected explicitly; restore a missing
release PNG from version control rather than silently drawing a placeholder.

Open `generated-asset-portal.html` in a local clone, or `/asset-library` in the
studio. Rebuild with `python scripts\build_asset_portal.py`. The portal includes
only the 60 current release assets and uses repository-relative PNG links.
Superseded trials, account-specific conversation links and machine-specific paths
are excluded. No new backgrounds or unrelated video/voice pipeline changes are
part of this release.

## 9. Phonics and Prop Expansion

The portal now includes 189 assets across three manifests: 60 from the first
release, 73 glyph-shaped phonics stickers, and 56 further props.

Phonics glyphs have no enclosing box, tile, pill or circular backing. Their white
die-cut border follows the glyph outline; interior counters in letters/numbers
remain transparent. Uppercase and lowercase versions share a color. Catalog IDs
`block_a` through `block_z`, `block_lower_a` through `block_lower_z`, and
`block_0` through `block_20` retain the six original ABC/123 IDs for compatibility.
Font provenance uses font filenames rather than machine-specific paths.

The 56 props include five toys, eleven vehicles, thirteen fruits, twelve vegetables
and fifteen dishes. Toys and vehicles use three-quarter views to convey depth while
retaining illustrated outlines and matte-color intent, not photorealistic 3D.
Production exports preserve source colors, normalize near-opaque interiors,
remove barely visible exterior speckles, downsample only as needed to fit within
1008px content bounds, and add eight transparent pixels of padding.

Eight requests have no recovered output: teddy bear, toy robot, beach bucket set,
scooter, cherries, pink guava, lychee and siu mai plate. They are listed in
`config/props_release_v2.json` and must not appear as generated assets or placeholder
substitutions. Existing older assets with similar names remain unaffected.
