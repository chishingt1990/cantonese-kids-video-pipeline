# Animated Video Workflow

How to produce an animated kids video (AI-animated scenes + karaoke), as established with the Happy Song video (Oct 2026). This is the cost-conscious version — read the cost notes before generating.

## When to use this vs. static compositing

- **Static compositing** (numbers video style): code-composited sprites, karaoke, no AI video. ~1-2% of weekly quota. Use by default.
- **AI-animated scenes** (happy song style): AI video clips for motion. ~7-14% of weekly quota. Use only when the user explicitly wants animated motion.

## Workflow

### 1. Preview slides (code-composited)

Build 1920×1080 stills with PIL: background + transparent character PNGs + title banner. One per scene/verse. These are the animation source frames.

- Character PNGs must have transparent backgrounds (AI image gen returns white — strip with PIL threshold).
- Verify: no white boxes, correct characters, correct poses.

### 2. Animate with character-lock prompting

Use `media.generate_video` with the preview slide as the input image.

**Critical prompt pattern** (learned Oct 10, 2026 — first attempt without this had visible character drift and all 5 clips had to be regenerated):

> Animate this exact scene with minimal motion: [describe the motion]. CRITICAL: preserve every character's appearance exactly as shown — same faces, same hairstyles, [list distinguishing features per character: glasses, shirts, etc.]. Do not redesign, restyle, or alter any character. Only add subtle [motion] motion. [Background] remains completely static.

Key insight: name each character's distinguishing features explicitly. Generic "keep characters the same" is not enough.

**Generate exactly one clip per unique scene.** If EN and CT verses share scenes, reuse the same clips — do not generate duplicates. (Happy Song: 5 scenes = 5 clips, reused across 10 verses.)

### 3. Clip specs and normalization

- AI clips come out at **1248×704 @ 24fps** — not 1920×1080 @ 30fps.
- Upscale to 1920×1080 and conform to 30fps during segment build (ffmpeg `scale` + `fps` filters).
- Clips are ~10 seconds each.

### 4. Verse segmentation

- Transcribe the recording with **faster-whisper** (`small`, `cpu`, `int8`, `word_timestamps=True`). This is the proven tool — do not substitute.
- Determine verse boundaries from word timestamps. Fold spoken bridges/intros into adjacent verses.
- Save words to `<project>/happy_words.json` (or equivalent).

### 5. Segment assembly

- For each verse: loop its scene clip with **ping-pong** (forward + reverse) to fill the exact verse duration. This avoids visible loop seams.
- Use exact `-frames:v` counts (not `-t`) so karaoke stays frame-aligned.
- Overlay **karaoke** via ASS subtitles: sung words yellow (`&H003CDCFF&`), upcoming words white, on a dark caption bar. Correct Whisper mishearings in display text.
- Add **title banners** per verse (e.g. "Verse 1: Clap Your Hands / 拍拍手").
- Concatenate segments, mux original audio as AAC.

### 6. Output and upload

- Output: 1920×1080, 30fps, h264 + aac.
- **File size warning**: AI-animation grain compresses poorly. Happy Song came out at 159MB, which **exceeds the browser upload grant size limit**. Compress with `ffmpeg -crf 26 -preset medium` before uploading (got it to 84MB).
- Upload via browser task to YouTube as Unlisted, made-for-kids, Cantonese (Hong Kong), Education category. Never upload without explicit user approval.

## Cost discipline

- One AI video clip per unique scene. Never generate the same scene twice.
- Get the character-lock prompt right on the first attempt — a failed batch doubles the cost.
- Prefer static compositing unless the user asks for animation.
- Do not run exploratory/analysis passes that consume significant tokens without being asked.

## Build intermediates

Keep in `<project>/build/`: reversed clips, per-verse segments, ASS subtitle files. Enables re-render without regenerating AI clips.
