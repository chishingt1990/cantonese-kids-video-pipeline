# Prop Sticker Style Guide (supplement to STYLE_GUIDE.md)

Covers all `assets/stickers/prop_*.png`: vehicles, food, fruit, animals,
toys, household objects, and every other prop category.

Derived from surveying the 227 prop stickers on main (Oct 2026).
Canonical references: `prop_double_decker_bus.png` (objects),
`prop_apple.png` (food), `prop_cow.png` / `prop_turtle.png` (animals).

## Universal Rules (all props)

- **Colors**: Solid, clean, saturated colors with smooth cel-shading for
  3D volume. Subtle gradient transitions, never flat single-tone.
- **Outlines**: Thick, bold dark chocolate brown (`#2d1a14`), consistent weight.
- **Background**: Transparent PNG alpha. NO white sticker die-cut border.
- **Texture**: NONE. No paper grain, no watercolor, no colored-pencil strokes,
  no wood grain. Clean digital illustration.
- **Proportions**: Realistic, NOT chibi/squished.
- **Detail**: High. Realistic features for the object type (mirrors, grilles,
  seeds, stems, etc.). Toddler-recognizable but not simplified to blobs.
- **Windows** (vehicles): Light blue with white shine streaks; may show
  interior (seats, steering wheel).
- **No text** on the prop, except where functionally required
  (e.g. racing number on a race car).

## Faces

- **Objects (vehicles, food, fruit, toys, household items): NO faces.**
  No eyes, no smile, no anthropomorphization.
- **Animals: YES — cute simple cartoon faces.** Plain oval dark eyes
  (no anime sparkle highlights), small curved smile, optional pink cheeks.
  Friendly, not kawaii.

## What NOT to do

- No white sticker border / die-cut outline
- No faces on non-animal props
- No anime/kawaii styling (no sparkle eyes, no blush on objects)
- No paper texture, grain, or painterly effects
- No chibi proportions
- No watercolor washes
- No photorealism or 3D rendering

## Generation Prompt Template

When generating a new prop, use this as the style block:

> Clean polished cartoon illustration, solid saturated colors with smooth
> cel-shading for 3D depth. Thick dark brown outlines. Transparent background,
> NO white sticker border. NO face [or: cute simple cartoon face for animals].
> NO paper texture, NO grain, NO painterly effects. Realistic proportions,
> NOT chibi. Highly detailed. No text.

Reference image: `assets/stickers/prop_double_decker_bus.png` (objects)
or `assets/stickers/prop_turtle.png` (animals).
