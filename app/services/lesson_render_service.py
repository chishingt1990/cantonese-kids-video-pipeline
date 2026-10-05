"""Lesson renderer: the generalized Old MacDonald video engine.

Takes a scene plan (lesson_templates.build_scenes) + karaoke caption lines
(lesson_timing_service.build_timeline) + the parent's audio, and renders a
1920x1080 MP4 with:

  - sticker keyframe animation (position/scale easing within a scene)
  - transitions: cut / fade / slide between scenes
  - vocabulary badge images top-center (fade on on/off, solid while on)
  - word-by-word karaoke captions (yellow highlight, centered pill)
  - pinned family characters

This is a direct generalization of the hand-built farm video
(animate_full_video.py, Oct 2026) — same visual language, driven by data.
"""
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FULL_W, FULL_H, FULL_FPS = 1920, 1080, 30


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _font(size):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _scaled(img, h):
    w = max(1, int(img.width * h / img.height))
    return img.resize((w, max(1, h)), Image.LANCZOS)


def _paste(base, img, cx, bottom_y):
    base.paste(img, (int(cx - img.width / 2), int(bottom_y - img.height)),
               img if img.mode == "RGBA" else None)


def _with_alpha(img, a):
    c = img.copy()
    arr = np.array(c)
    arr[..., 3] = (arr[..., 3].astype(float) * a).astype(np.uint8)
    return Image.fromarray(arr)


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _interp_keyframes(keyframes, t_frac):
    """keyframes: [[t_frac, x_pct, y_pct, h_px], ...] -> (x, y, h)."""
    kf = sorted(keyframes, key=lambda k: k[0])
    if t_frac <= kf[0][0]:
        return kf[0][1], kf[0][2], kf[0][3]
    if t_frac >= kf[-1][0]:
        return kf[-1][1], kf[-1][2], kf[-1][3]
    for (t0, x0, y0, h0), (t1, x1, y1, h1) in zip(kf, kf[1:]):
        if t0 <= t_frac <= t1:
            k = _ease((t_frac - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k,
                    h0 + (h1 - h0) * k)
    return kf[-1][1], kf[-1][2], kf[-1][3]


class LessonRenderer:
    def __init__(self, scenes, caption_lines, opts=None):
        o = opts or {}
        self.preview = bool(o.get("preview", False))
        self.W = 960 if self.preview else FULL_W
        self.H = 540 if self.preview else FULL_H
        self.FPS = 15 if self.preview else int(o.get("fps", FULL_FPS))
        self.scenes = sorted(scenes, key=lambda s: s["start"])
        self.caption_lines = caption_lines
        self.root = _project_root()
        self.sticker_dir = os.path.join(self.root, "assets", "stickers")
        self.bg_dir = os.path.join(self.root, "assets", "backgrounds")
        self.sprite_dir = os.path.join(self.root, "assets", "sprites")
        self._img_cache = {}
        self._cap_cache = {}
        self.font_cap = _font(64 if not self.preview else 40)

    # -- asset loading ---------------------------------------------------
    def _load(self, path):
        if path not in self._img_cache:
            self._img_cache[path] = Image.open(path).convert("RGBA")
        return self._img_cache[path]

    def _sticker(self, src):
        p = src if os.path.isabs(src) else os.path.join(self.sticker_dir, src)
        if not os.path.exists(p):
            # Fall back to sprites directory (family characters)
            p2 = os.path.join(self.sprite_dir, os.path.basename(src))
            if os.path.exists(p2):
                p = p2
        return self._load(p)

    def _badge(self, src):
        return self._sticker(src)

    def _sprite(self, src):
        p = src if os.path.isabs(src) else os.path.join(self.sprite_dir, src)
        return self._load(p)

    def _bg(self, name):
        p = os.path.join(self.bg_dir, f"bg_{name}.png")
        if not os.path.exists(p):
            p = os.path.join(self.bg_dir, "bg_living_room.png")
        key = "bg:" + p
        if key not in self._img_cache:
            self._img_cache[key] = Image.open(p).convert("RGB").resize(
                (self.W, self.H), Image.LANCZOS)
        return self._img_cache[key]

    # -- scene lookup (gap-hold: during gaps, hold nearest started scene) --
    def _scene_at(self, t):
        si = next((i for i, s in enumerate(self.scenes)
                   if s["start"] <= t < s["end"]), None)
        if si is None:
            if t < self.scenes[0]["start"]:
                si = 0
            else:
                si = max(i for i, s in enumerate(self.scenes)
                         if s["start"] <= t)
        return si, self.scenes[si]

    # -- karaoke ----------------------------------------------------------
    def _caption_words(self, li):
        if li in self._cap_cache:
            return self._cap_cache[li]
        cap = self.caption_lines[li]
        ws = cap["words"] if isinstance(cap, dict) else cap[2]
        _ls = cap["start"] if isinstance(cap, dict) else cap[0]
        if not ws:
            self._cap_cache[li] = []
            return []
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        widths = []
        for _, w in ws:
            bb = tmp.textbbox((0, 0), w, font=self.font_cap)
            widths.append(max(1, bb[2] - bb[0]))
        gap = 18 if not self.preview else 10
        word_h = 90 if not self.preview else 56
        text_y = 13 if not self.preview else 8
        total = sum(widths) + gap * (len(widths) - 1)
        x = (self.W - total) / 2
        out = []
        for (_, w), wd in zip(ws, widths):
            imgs = []
            for color in ((255, 255, 255, 255), (255, 215, 80, 255)):
                timg = Image.new("RGBA", (wd + 20, word_h), (0, 0, 0, 0))
                ImageDraw.Draw(timg).text((10, text_y), w,
                                          font=self.font_cap, fill=color)
                imgs.append(timg)
            out.append((x, imgs[0], imgs[1]))
            x += wd + gap
        self._cap_cache[li] = (out, word_h)
        return self._cap_cache[li]

    def _draw_captions(self, base, t):
        li = next((i for i, (ls, le, _w) in
                   enumerate([(c["start"], c["end"], c["words"])
                              for c in self.caption_lines])
                   if ls <= t < le), None)
        if li is None:
            return
        words = self._caption_words(li)
        if not words:
            return
        line_words, word_h = words
        y_base = self.H - (200 if not self.preview else 110)
        x0 = line_words[0][0] - 30
        x1 = (line_words[-1][0] + line_words[-1][1].width + 10)
        d = ImageDraw.Draw(base)
        d.rounded_rectangle([x0, y_base, x1, y_base + word_h], radius=28,
                            fill=(0, 0, 0, 110))
        _ls, _le, ws = (self.caption_lines[li]["start"],
                        self.caption_lines[li]["end"],
                        self.caption_lines[li]["words"])
        for (x, wi, yi), (ws_s, _wt) in zip(line_words, ws):
            base.paste(wi, (int(x) - 10, y_base), wi)
            if t >= ws_s - 0.05:
                base.paste(yi, (int(x) - 10, y_base), yi)

    # -- frame -------------------------------------------------------------
    def frame_at(self, t):
        si, sc = self._scene_at(t)
        start, end = sc["start"], sc["end"]
        frame = self._bg(sc.get("background", "living_room")).copy()
        frame = frame.convert("RGBA")
        sx = self.W / FULL_W  # scale factor for positions/sizes

        # Pinned family characters.
        for c in sc.get("characters", []):
            try:
                img = _scaled(self._sprite(c["src"]),
                              int(c.get("h_px", 500) * sx))
                _paste(frame, img, c.get("x_pct", 50) / 100 * self.W,
                       c.get("y_base_pct", 96) / 100 * self.H)
            except Exception:
                pass

        # Stickers with keyframes + transitions.
        transition = sc.get("transition_in", "fade")
        prev = self.scenes[si - 1] if si > 0 else None
        TR = 0.5
        dur = max(0.01, end - start)
        for j, st in enumerate(sc.get("stickers", [])):
            try:
                img_src = self._sticker(st["src"])
            except Exception:
                continue
            t_frac = (t - start) / dur
            x_pct, y_pct, h_px = _interp_keyframes(st.get("keyframes",
                [[0, 50, 80, 400], [1, 50, 80, 400]]), t_frac)
            img = _scaled(img_src, max(1, int(h_px * sx)))
            cx = x_pct / 100 * self.W
            by = y_pct / 100 * self.H
            alpha = 1.0
            fi = st.get("fade_in", 0.3)
            fo = st.get("fade_out", 0.3)
            if t - start < fi:
                alpha = min(alpha, _ease((t - start) / fi))
            if end - t < fo:
                alpha = min(alpha, _ease((end - t) / fo))

            if transition == "cut" or not prev or t - start >= TR:
                if alpha < 1:
                    img = _with_alpha(img, alpha)
                _paste(frame, img, cx, by)
            elif transition == "slide" and j < len(prev.get("stickers", [])):
                # Interpolate from the previous scene's matching sticker.
                pst = prev["stickers"][j]
                px, py, ph = _interp_keyframes(pst.get("keyframes",
                    [[0, 50, 80, 400], [1, 50, 80, 400]]), 1.0)
                k = _ease((t - start) / TR)
                try:
                    pimg = _scaled(self._sticker(pst["src"]),
                                   max(1, int((ph + (h_px - ph) * k) * sx)))
                except Exception:
                    pimg = img
                _paste(frame, pimg,
                       (px + (x_pct - px) * k) / 100 * self.W,
                       (py + (y_pct - py) * k) / 100 * self.H)
            else:  # fade: crossfade from previous scene's stickers
                k = _ease((t - start) / TR)
                if prev:
                    for pst in prev.get("stickers", []):
                        try:
                            pimg = self._sticker(pst["src"])
                            px, py, ph = _interp_keyframes(pst.get(
                                "keyframes", [[0, 50, 80, 400],
                                              [1, 50, 80, 400]]), 1.0)
                            pimg = _scaled(pimg, max(1, int(ph * sx)))
                            _paste(frame, _with_alpha(pimg, 1 - k),
                                   px / 100 * self.W, py / 100 * self.H)
                        except Exception:
                            pass
                if alpha * k > 0:
                    _paste(frame, _with_alpha(img, alpha * k), cx, by)

        # Vocabulary badge: solid while on, fade only on on/off edges.
        badge = sc.get("badge_image")
        if badge:
            try:
                bi = _scaled(self._badge(badge), int(220 * sx))
                prev_on = bool(prev and prev.get("badge_image")) if prev else False
                nxt = self.scenes[si + 1] if si + 1 < len(self.scenes) else None
                next_on = bool(nxt and nxt.get("badge_image"))
                a = 1.0
                if not prev_on and t - start < 0.4:
                    a = _ease((t - start) / 0.4)
                if not next_on and end - t < 0.4:
                    a = min(a, _ease((end - t) / 0.4))
                _paste(frame, _with_alpha(bi, a) if a < 1 else bi,
                       self.W / 2, int(290 * sx))
            except Exception:
                pass

        self._draw_captions(frame, t)
        return frame.convert("RGB")


def render_lesson(scenes, caption_lines, audio_path, out_path,
                  opts=None) -> dict:
    """Render the full video. Returns {"status", "output", "duration"}."""
    o = opts or {}
    r = LessonRenderer(scenes, caption_lines, o)
    if not scenes:
        return {"status": "error", "detail": "no scenes"}
    t_end = max(s["end"] for s in scenes) + float(o.get("tail", 1.5))
    n = int(t_end * r.FPS)
    tmpdir = (o.get("frames_dir")
              or os.path.join(r.root, "assets", "outputs", "lesson_frames"))
    os.makedirs(tmpdir, exist_ok=True)
    for f in os.listdir(tmpdir):
        if f.endswith(".jpg"):
            os.remove(os.path.join(tmpdir, f))
    for i in range(n):
        r.frame_at(i / r.FPS).save(os.path.join(tmpdir, f"f{i:05d}.jpg"),
                                   quality=88)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(r.FPS),
         "-i", os.path.join(tmpdir, "f%05d.jpg"),
         "-i", audio_path,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-c:a", "aac", "-shortest", out_path],
        check=True)
    return {"status": "success", "output": out_path,
            "duration": round(t_end, 2),
            "resolution": f"{r.W}x{r.H}", "fps": r.FPS}
