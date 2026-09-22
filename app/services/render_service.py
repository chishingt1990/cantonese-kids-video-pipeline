import os
import subprocess
import threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.services.audio_service import mix_scene_audio, get_audio_duration
from app.services.sticker_service import get_or_render_sticker

# In-memory job registry
JOBS = {}

def get_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/msjhbd.ttc" if bold else "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/seguiemj.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

def render_project_video(project_data: dict, job_id: str, output_path: str):
    JOBS[job_id] = {"status": "rendering", "progress": 0, "error": None}
    
    try:
        scenes = project_data.get("scenes", [])
        total_duration = sum(s.get("duration_sec", 6) for s in scenes)
        fps = 30
        width, height = 1920, 1080
        total_frames = int(total_duration * fps)
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 1. Dynamically gather scene voice recordings and mix master audio with ukulele BGM
        voice_paths = []
        durations = []
        for idx, s in enumerate(scenes):
            s_num = s.get("scene_number", idx + 1)
            dur = float(s.get("duration_sec", 6))
            durations.append(dur)
            
            # Resolve exact audio filename from audio_url if present
            clip_name = None
            if s.get("audio_url"):
                raw_url = s["audio_url"].split("?")[0]
                clip_name = os.path.basename(raw_url)
            if not clip_name:
                clip_name = f"scene_{s_num:02d}_voice.wav"
            v_clip = os.path.join(project_root, "assets", "outputs", "audio_clips", clip_name)
            if not os.path.exists(v_clip):
                v_clip = os.path.join(project_root, "assets", "outputs", "audio_clips", f"scene_{s_num:02d}_voice.wav")
            voice_paths.append(v_clip if os.path.exists(v_clip) else None)
            
        audio_path = os.path.join(project_root, "assets", "outputs", f"episode_{job_id}_master.wav")
        try:
            mix_scene_audio(voice_paths, durations, audio_path)
        except Exception as e:
            print(f"Warning: dynamic audio mixing failed, falling back to static audio: {e}")
            audio_path = os.path.join(project_root, "assets", "outputs", "episode_01_master_audio.wav")
        
        # 2. Setup FFmpeg pipe
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
        ]
        
        if os.path.exists(audio_path):
            ffmpeg_cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "192k"])
            
        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "22",
            output_path
        ])
        
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # Subtitle Options & Fonts
        sub_opts = project_data.get("subtitle_options", {})
        font_size_cn = int(sub_opts.get("font_size_cn", 52))
        font_size_en = int(sub_opts.get("font_size_en", 26))
        pill_style = sub_opts.get("pill_style", "warm_cream")

        font_chinese = get_font(font_size_cn, bold=True)
        font_english = get_font(font_size_en, bold=False)
        font_vocab = get_font(36, bold=True)
        font_jyutping = get_font(30, bold=False)
        
        frame_idx = 0
        
        # Cache loaded backgrounds and character sprites
        bg_cache = {}
        sprite_cache = {}
        
        def load_bg(bg_name):
            if bg_name in bg_cache:
                return bg_cache[bg_name]
            bg_file = os.path.join(project_root, "assets", "backgrounds", f"bg_{bg_name}.png")
            if not os.path.exists(bg_file):
                bg_file = os.path.join(project_root, "assets", "backgrounds", "bg_living_room.png")
            if os.path.exists(bg_file):
                im = Image.open(bg_file).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            else:
                im = Image.new("RGB", (width, height), (255, 248, 235))
            bg_cache[bg_name] = im
            return im

        def load_sprite(char_name, pose):
            key = f"{char_name}_{pose}"
            if key in sprite_cache:
                return sprite_cache[key]
            
            candidates = [
                os.path.join(project_root, "assets", "sprites", f"{key}.png"),
                os.path.join(project_root, "assets", "sprites", f"{char_name}_{pose.replace('drinking_', '')}.png") if "drinking" in pose else None,
                os.path.join(project_root, "assets", "sprites", f"{char_name}_tea.png") if "tea" in pose or "drink" in pose else None,
                os.path.join(project_root, "assets", "sprites", f"{char_name}_default.png"),
                os.path.join(project_root, "assets", "sprites", f"{char_name}.png")
            ]
            im = None
            for c_path in candidates:
                if c_path and os.path.exists(c_path):
                    try:
                        im = Image.open(c_path).convert("RGBA")
                        break
                    except Exception:
                        pass
            sprite_cache[key] = im
            return im
            
        for s_idx, scene in enumerate(scenes):
            bg_name = scene.get("background", "living_room")
            bg_base = load_bg(bg_name)
            
            chars = scene.get("characters", [])
            cantonese = scene.get("cantonese", "")
            jyutping = scene.get("jyutping", "")
            english = scene.get("english", "")
            vocab = scene.get("vocab_highlight", "")
            speaker = (scene.get("speaker") or "").lower()
            
            scene_duration = scene.get("duration_sec", 6)
            scene_frames = int(scene_duration * fps)
            
            # Speaker bias for Ken Burns subtle camera pan
            speaker_bias_x = 0.0
            if "dad" in speaker or any(c.get("name") == "dad" and c.get("x_percent", 50) < 40 for c in chars):
                speaker_bias_x = -0.08
            elif "mom" in speaker or any(c.get("name") == "mom" and c.get("x_percent", 50) > 60 for c in chars):
                speaker_bias_x = 0.08

            for f in range(scene_frames):
                time_sec = f / fps
                t_norm = f / max(1, scene_frames - 1)
                
                # 1. Ken Burns Smooth Camera Motion (Smoothstep 1.0x -> 1.07x push-in)
                ease = t_norm * t_norm * (3.0 - 2.0 * t_norm)
                cam_scale = 1.0 + 0.07 * ease
                bg_w = int(width * cam_scale)
                bg_h = int(height * cam_scale)
                bg_zoomed = bg_base.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
                crop_x = int((bg_w - width) * (0.5 + speaker_bias_x))
                crop_y = int((bg_h - height) * 0.5)
                crop_x = max(0, min(crop_x, bg_w - width))
                crop_y = max(0, min(crop_y, bg_h - height))
                frame = bg_zoomed.crop((crop_x, crop_y, crop_x + width, crop_y + height)).convert("RGB")

                # 2. Ukulele 116 BPM Downbeat Rhythmic Bounce & Squash
                # 116 BPM ~= 1.9333 Hz
                phase_bpm = 2.0 * np.pi * 1.9333 * time_sec
                bob_y = int(-abs(np.sin(phase_bpm / 2.0)) * 6.0)
                squash_y = 1.0 + 0.016 * np.sin(phase_bpm)
                squash_x = 1.0 / np.sqrt(max(0.7, squash_y))

                # 3. Build Unified Z-Sorted Render Queue
                render_queue = []
                for c in chars:
                    render_queue.append({
                        "type": "char",
                        "layer": int(c.get("layer", 1)),
                        "y": float(c.get("y_percent", 82.0)),
                        "data": c
                    })
                for s in scene.get("stickers", []):
                    render_queue.append({
                        "type": "sticker",
                        "layer": int(s.get("layer", 2)),
                        "y": float(s.get("y_percent", 24.0)),
                        "data": s
                    })
                render_queue.sort(key=lambda item: (item["layer"], item["y"]))

                for item in render_queue:
                    if item["type"] == "char":
                        c = item["data"]
                        c_name = c.get("name", "levi")
                        c_pose = c.get("pose", "default")
                        c_pos = c.get("position", "center")
                        sp = load_sprite(c_name, c_pose)
                        if sp:
                            if c_name in ["dad", "mom", "grandparents_paternal", "grandparents_maternal", "auntie_cousins"]:
                                base_h = 760
                            elif c_name in ["dog", "family_dog", "spitz"]:
                                base_h = 320
                            else:
                                base_h = 520
                            
                            c_scale = float(c.get("scale", 1.0))
                            target_h = int(base_h * c_scale * squash_y)
                            aspect = sp.width / sp.height
                            target_w = int(target_h * aspect * squash_x)
                            resized_sp = sp.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            
                            if c.get("flip"):
                                resized_sp = resized_sp.transpose(Image.FLIP_LEFT_RIGHT)

                            # Active Speaker Head Nod / Tilt
                            if c_name in speaker:
                                tilt_deg = float(1.8 * np.sin(2.0 * np.pi * 2.2 * time_sec))
                                resized_sp = resized_sp.rotate(tilt_deg, expand=True, resample=Image.Resampling.BICUBIC)
                                
                            if "x_percent" in c:
                                x = int(width * (float(c["x_percent"]) / 100.0) - resized_sp.width / 2)
                            elif c_pos == "left":
                                x = int(width * 0.28 - resized_sp.width / 2)
                            elif c_pos == "right":
                                x = int(width * 0.72 - resized_sp.width / 2)
                            elif c_pos == "far_left":
                                x = int(width * 0.15 - resized_sp.width / 2)
                            elif c_pos == "far_right":
                                x = int(width * 0.85 - resized_sp.width / 2)
                            else:
                                x = int(width * 0.50 - resized_sp.width / 2)
                                
                            if "y_percent" in c:
                                ground_y = int(height * (float(c["y_percent"]) / 100.0))
                            else:
                                ground_y = 880
                            y = ground_y - resized_sp.height + bob_y
                            frame.paste(resized_sp, (x, y), resized_sp)

                    elif item["type"] == "sticker":
                        s = item["data"]
                        # 4. Elastic Squash-and-Stretch Pop-In Entrance
                        f_enter = int(fps * 0.35)
                        if f >= f_enter:
                            if f < f_enter + 18:
                                tau = (f - f_enter) / 18.0
                                # Damped harmonic spring: shoots up to 1.28x then settles
                                s_spring = 1.0 - np.exp(-7.0 * tau) * np.cos(14.0 * tau) + 0.35 * np.exp(-9.0 * tau) * np.sin(14.0 * tau)
                                pop_mult = max(0.01, float(s_spring))
                            else:
                                pop_mult = 1.0
                                
                            try:
                                st_path = get_or_render_sticker(s)
                                if st_path and os.path.exists(st_path):
                                    st_img = Image.open(st_path).convert("RGBA")
                                    s_scale = float(s.get("scale", 1.0)) * pop_mult
                                    st_w = int(st_img.width * s_scale)
                                    st_h = int(st_img.height * s_scale)
                                    if st_w > 4 and st_h > 4:
                                        resized_st = st_img.resize((st_w, st_h), Image.Resampling.LANCZOS)
                                        # Secondary gentle floating
                                        float_y = int(4.0 * np.sin(2.0 * np.pi * 0.5 * time_sec))
                                        base_rot = float(s.get("rotation_deg", 0.0))
                                        rot = base_rot + float(2.0 * np.cos(2.0 * np.pi * 0.4 * time_sec))
                                        if abs(rot) > 0.5:
                                            resized_st = resized_st.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
                                        sx = int(width * (float(s.get("x_percent", 50.0)) / 100.0) - resized_st.width / 2)
                                        sy = int(height * (float(s.get("y_percent", 24.0)) / 100.0) - resized_st.height / 2) + float_y
                                        frame.paste(resized_st, (sx, sy), resized_st)
                            except Exception:
                                pass

                # 5. Forefront Subtitle Pill with Soft Fade In / Fade Out
                alpha_sub = min(1.0, f / 8.0)
                if f > scene_frames - 8:
                    alpha_sub = min(alpha_sub, max(0.0, (scene_frames - f) / 8.0))
                    
                if alpha_sub > 0.05:
                    box_y = height - 170 # 910px
                    sub_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    s_draw = ImageDraw.Draw(sub_overlay)
                    s_draw.rounded_rectangle([190, box_y + 8, width - 190, height - 22], radius=28, fill=(0, 0, 0, int(60 * alpha_sub)))
                    sub_overlay = sub_overlay.filter(ImageFilter.GaussianBlur(10))
                    frame.paste(sub_overlay, (0, 0), sub_overlay)

                    draw = ImageDraw.Draw(frame)
                    if pill_style == "translucent_dark":
                        pill_fill = (25, 25, 30, int(220 * alpha_sub))
                        pill_outline = (255, 255, 255, int(80 * alpha_sub))
                        text_cn_color = (255, 255, 255)
                        text_en_color = (220, 220, 220)
                    elif pill_style == "pastel_amber":
                        pill_fill = (255, 251, 235, int(245 * alpha_sub))
                        pill_outline = (245, 158, 11, int(220 * alpha_sub))
                        text_cn_color = (120, 53, 15)
                        text_en_color = (180, 83, 9)
                    else:  # warm_cream (default)
                        pill_fill = (255, 255, 255, int(240 * alpha_sub))
                        pill_outline = (245, 158, 11, int(180 * alpha_sub))
                        text_cn_color = (40, 35, 30)
                        text_en_color = (100, 100, 100)

                    draw.rounded_rectangle([200, box_y, width - 200, height - 30], radius=24, fill=pill_fill, outline=pill_outline, width=2)
                    
                    # Bilingual Subtitles (Clean Spoken Cantonese + English)
                    draw.text((width // 2, box_y + 22), cantonese, fill=text_cn_color, font=font_chinese, anchor="mt")
                    draw.text((width // 2, box_y + 82), english, fill=text_en_color, font=font_english, anchor="mt")
                    
                    # Top Vocab badge
                    if vocab:
                        left_occupied = any(float(c.get("x_percent", 50)) < 28 for c in chars)
                        if left_occupied:
                            draw.rounded_rectangle([width - 380, 50, width - 60, 140], radius=16, fill=(255, 248, 235), outline=(245, 158, 11), width=3)
                            draw.text((width - 220, 95), f"★ {vocab}", fill=(180, 83, 9), font=font_vocab, anchor="mm")
                        else:
                            draw.rounded_rectangle([60, 50, 380, 140], radius=16, fill=(255, 248, 235), outline=(245, 158, 11), width=3)
                            draw.text((220, 95), f"★ {vocab}", fill=(180, 83, 9), font=font_vocab, anchor="mm")
                
                # Pipe to ffmpeg
                proc.stdin.write(frame.tobytes())
                frame_idx += 1
                
                if frame_idx % 15 == 0:
                    JOBS[job_id]["progress"] = int((frame_idx / total_frames) * 100)
        
        proc.stdin.close()
        proc.wait()
        
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["progress"] = 100
        JOBS[job_id]["video_path"] = output_path
        JOBS[job_id]["video_filename"] = os.path.basename(output_path)
    except Exception as e:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["error"] = str(e)

def start_render_job(project_data: dict, job_id: str, output_path: str):
    t = threading.Thread(target=render_project_video, args=(project_data, job_id, output_path), daemon=True)
    t.start()
