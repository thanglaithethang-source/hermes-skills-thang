# Local SFX & BGM Library

Last verified: 2026-07-11

## Primary Library Path

```
C:/Users/thang/Downloads/_projects/human-evolution-sweaty/
├── bgm/                        # Background music
│   ├── BGM_MIX_20min.wav      # Full mixed BGM (20:39, 48kHz, stereo)
│   └── bgm_seg_00..05.wav     # 6 phân đoạn BGM
├── sfx/                        # Sound effects by category
│   ├── animal_whoosh/         # 5 files — whoosh/transition sounds
│   ├── comedy_pop/            # 6 files — cartoon boing, ping, ding, ricochet, glass
│   ├── fire_disgust/          # 3 files — dragon roar, fire burning, rapid ricochet
│   ├── heat_warning/          # 3 files — alarm, buzz, beeping
│   ├── modern_room/           # 6 files — ambient, noise, door entry, beep ping
│   └── water_drip/            # 5 files — water drops, steam train, spooky drops
└── capcut_audio/              # Mirrors of sfx/ files (CapCut format)
```

## Total: ~34 audio files (28 SFX + 6 BGM segments)

## Usage Priority

1. **ALWAYS check this local library FIRST** before attempting online API searches
2. Do NOT waste time hunting for Freesound/Pixabay API keys on GitHub — all public code uses env vars, no leaked keys found
3. If additional SFX are needed beyond what's here, register at freesound.org directly (free, requires CAPTCHA)

## Import Workflow (via MCP)

```python
# Import individual files
media_pool(action='import_media', file_path='C:/Users/thang/Downloads/_projects/human-evolution-sweaty/sfx/comedy_pop/SoundBible - Boing cartoonish.wav')

# Place on timeline
media_pool(action='append_to_timeline', clip_infos=[{
    'clip_id': '<uuid>',
    'record_frame': <frame>,
    'start_frame': 0,
    'end_frame': <duration_frames>,
    'track_index': <track>,
    'media_type': 2  # audio
}])
```
