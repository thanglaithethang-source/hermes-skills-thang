# BGM Synthetic Generation — Layered Tone Mood Zones

Sinh nhạc nền synthetic bằng Python `wave` module khi không có sẵn loop/royalty-free.
Dùng cho video meme/slang/joke cần nhạc nền có identity riêng biệt cho từng zone.

## Why Synthetic

- Freesound BGM previews quá ngắn (30-120s) và chất lượng không đồng đều
- Pixabay audio download bị 403 block
- Cần mood chính xác theo kịch bản (không generic)
- File WAV 24kHz mono nhẹ, tương thích CapCut

## Core Pattern: `gen_bgm_zone()`

```python
def gen_bgm_zone(filepath, dur_sec, freqs, amp=0.15, wave_type="sine"):
    """Generate BGM zone as layered tones with LFO + fade in/out."""
    n = int(SR * dur_sec)
    samples = [0.0] * n

    for freq in freqs:
        for i in range(n):
            t = i / SR
            mod = 0.7 + 0.3 * math.sin(2 * math.pi * 0.3 * t)  # 0.3 Hz LFO
            if wave_type == "sine":
                val = math.sin(2 * math.pi * freq * t)
            elif wave_type == "triangle":
                phase = (freq * t) % 1.0
                val = 4.0 * abs(phase - 0.5) - 1.0
            elif wave_type == "square":
                val = 1.0 if (freq * t) % 1.0 < 0.5 else -1.0
            samples[i] += (amp / len(freqs)) * mod * val * 32767

    # 1.5s fade in/out
    fade_frames = int(SR * 1.5)
    for i in range(min(fade_frames, n)):
        samples[i] *= (i / fade_frames)
    for i in range(min(fade_frames, n)):
        samples[n - 1 - i] *= (i / fade_frames)
```

## Parameters

| Parameter | Effect | Range |
|-----------|--------|-------|
| `freqs` | Harmonic content. 3-5 frequencies = chord. More = richer. | Lower = deeper, higher = brighter |
| `amp` | Per-layer amplitude. Lower for more layers. | 0.05 (ambient) — 0.20 (driving) |
| `wave_type` | Timbre. `sine` = smooth/pure. `triangle` = warm/analog. `square` = harsh/chiptune. | — |
| `dur_sec` | Zone duration = section length from script. | Usually 30-275s |

## Zone Templates (Proven 2026-07-22)

These 9 templates were used for the Ancient Menstruation 17:37 video with good results.
Each maps to a specific emotional arc and meme strategy (see `creative-audio-strategy.md`).

### M1: Boss Battle Intro (Epic Orchestral)
```
freqs = [55, 65, 82, 110]      # D2-A2-D3 — power chord in D minor
amp = 0.18
wave_type = "sine"
dur = 28s
```
Deep, dramatic buildup. Over-the-top epic for ironic humor.

### M2: 8-Bit Debuff Dungeon (Chiptune RPG)
```
freqs = [262, 330, 392, 523]    # C4-E4-G4-C5 — C major arpeggio
amp = 0.12
wave_type = "square"
dur = 40s
```
Retro game feel. Square wave for authentic chiptune timbre.

### M3: Elevator to Ancient Rome (Smooth Jazz)
```
freqs = [175, 220, 262, 349]    # F3-A3-C4-F4 — F major chord
amp = 0.10
wave_type = "sine"
dur = 87s
```
Smooth, detached. Ironic contrast for historical documentary mockery.

### M4: Trust Me Bro Orchestra (Baroque → Circus)
```
freqs = [196, 247, 294, 392]    # G3-B3-D4-G4 — G major chord
amp = 0.13
wave_type = "triangle"
dur = 133s
```
Triangle wave gives warm-but-slightly-off "old instrument" feel.
Longest zone — covers the entire Aristotle roast chapter.

### M5: Discord Server Meltdown (Breakcore/Glitch)
```
freqs = [110, 165, 220, 330]    # A2-E3-A3-E4 — A power chord
amp = 0.10
wave_type = "square"
dur = 138s
```
Square wave for harsh, digital chaos. Represents "group chat meltdown."

### M6: MacGyver Ancient (Funk/Spy Thriller)
```
freqs = [165, 196, 247, 330]    # E3-G3-B3-E4 — E minor chord
amp = 0.10
wave_type = "triangle"
dur = 162s
```
Triangle wave for warm, clever, resourceful energy.

### M7: Lofi Moon Lodge (Ambient Chill)
```
freqs = [294, 370, 440, 587]    # D4-F#4-A4-D5 — D major chord
amp = 0.08
wave_type = "sine"
dur = 88s
```
Low amplitude, sine wave for gentle, warm, spiritual mood.

### M8: Corporate Plastic (Stock Music)
```
freqs = [262, 330, 392, 523]    # C4-E4-G4-C5 — C major (aggressively)
amp = 0.09
wave_type = "triangle"
dur = 106s
```
Overly clean, plastic, fake-happy. Ironic cringe for consumer culture critique.

### M9: Power Anthem Blood (Post-Rock Cinematic)
```
freqs = [123, 147, 196, 247]    # B2-D3-G3-B3 — B minor/G major ambiguous
amp = 0.12
wave_type = "sine"
dur = 275s
```
Longest zone — emotional build-up for finale. Key ambiguity (Bm→DM) mirrors dark→hopeful arc.

## File Sizes (Reference — 24kHz mono WAV)

| Zone | Duration | File size |
|------|----------|-----------|
| M1 (28s) | 28s | ~1.3 MB |
| M2 (40s) | 40s | ~1.8 MB |
| M3 (87s) | 87s | ~4.0 MB |
| M4 (133s) | 133s | ~6.1 MB |
| M5 (138s) | 138s | ~6.3 MB |
| M6 (162s) | 162s | ~7.4 MB |
| M7 (88s) | 88s | ~4.0 MB |
| M8 (106s) | 106s | ~4.9 MB |
| M9 (275s) | 275s | ~1.8 MB (note: long duration but low amplitude) |

## Pitfalls

- **Quá nhiều layers**: 3-5 frequencies là đủ. Nhiều hơn = muddy, clip.
- **Amplitude quá cao**: tổng amp > 0.25 gây clipping khi tất cả layers cộng dồn.
- **Square wave ở high freq**: square wave trên 500Hz = piercing, khó chịu. Chỉ dùng square cho zone cần harshness (M2 chiptune, M5 chaos).
- **Không fade in/out**: file WAV cắt đột ngột gây pop/click khi CapCut loop.
- **Sai key cho mood**: major key cho nội dung buồn/phê phán = sai tone. Ngược lại, minor key cho đoạn upbeat = sai.
- **File quá lớn cho short zone**: M1 28s mà amplitude 0.18 + nhiều layers = 1.3MB OK. Nhưng nếu 0.25+ = có thể clip.
