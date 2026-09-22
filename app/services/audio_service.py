import os
import wave
import numpy as np

def get_audio_duration(file_path: str) -> float:
    if not os.path.exists(file_path):
        return 0.0
    try:
        with wave.open(file_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0

def mix_scene_audio(voice_paths: list, durations: list, output_master_path: str):
    """Mixes scene audio with background ukulele and auto-ducking."""
    sr = 44100
    total_duration = sum(durations)
    total_samples = int(total_duration * sr)
    master = np.zeros(total_samples, dtype=np.float32)
    
    # 1. Synthesize soft acoustic ukulele BGM (C - G - Am - F)
    t = np.linspace(0, total_duration, total_samples, endpoint=False)
    chords = [
        [261.63, 329.63, 392.00],  # C
        [196.00, 246.94, 293.66],  # G
        [220.00, 261.63, 329.63],  # Am
        [174.61, 220.00, 261.63]   # F
    ]
    bgm = np.zeros(total_samples, dtype=np.float32)
    chord_len = int(2.0 * sr)
    for i in range(0, total_samples, chord_len):
        c = chords[(i // chord_len) % len(chords)]
        sub_len = min(chord_len, total_samples - i)
        sub_t = t[i:i+sub_len] - t[i]
        for note in c:
            bgm[i:i+sub_len] += 0.04 * np.sin(2 * np.pi * note * sub_t) * np.exp(-1.5 * (sub_t % 0.5))
    
    # 2. Place voice clips and build ducking envelope
    duck_mask = np.ones(total_samples, dtype=np.float32)
    cur_idx = 0
    for idx, dur in enumerate(durations):
        dur_samples = int(dur * sr)
        v_path = voice_paths[idx] if idx < len(voice_paths) else None
        if v_path and os.path.exists(v_path):
            try:
                with wave.open(v_path, "rb") as wf:
                    n = wf.getnframes()
                    raw = wf.readframes(n)
                    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    clip_len = min(len(arr), dur_samples)
                    master[cur_idx:cur_idx+clip_len] += arr[:clip_len]
                    duck_mask[cur_idx:cur_idx+clip_len] = 0.25
            except Exception:
                pass
        cur_idx += dur_samples
    
    # Smooth ducking
    from scipy.ndimage import uniform_filter1d
    duck_smooth = uniform_filter1d(duck_mask, size=int(0.5 * sr))
    
    # Combine
    final_mix = master + (bgm * duck_smooth)
    peak = np.max(np.abs(final_mix))
    if peak > 0.95:
        final_mix = final_mix / peak * 0.95
    
    out_int16 = (final_mix * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(output_master_path), exist_ok=True)
    with wave.open(output_master_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(out_int16.tobytes())
