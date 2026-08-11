# Cấu Trúc Dự Án Video Thực Tế

Dự án video của Sếp nằm dưới:
`C:/Users/thang/Downloads/Whisk Downloads/người tối cổ/<Tên video>/`

## File điển hình trong một dự án

```
<Tên video>/
├── <Tên video>.mp4              # Video thô (thường 1920×1080, 30fps, H.264)
├── <Tên video>.wav              # Audio voiceover (WAV)
├── <Tên video>.txt              # Kịch bản prose (full script)
├── srt.srt                      # Subtitle timing (373+ cues)
├── POST_PRODUCTION_PLAN.md      # Output của post-production-planning skill
├── YEF_*_TIMEMAP.txt            # Timemap (có thể có sẵn, 1-indexed)
├── YEF_*_PACKAGING_PACK.txt     # Title, thumbnail, description, tags
├── YEF_*_IMAGE_PROMPTS_SPACED.txt  # Image generation prompts
├── <TEN>_CAPCUT_PRO_EXECUTION_PACK_V*.zip  # CapCut execution pack (downstream)
├── capcut_v3/                   # Giải nén từ execution pack ZIP
│   ├── CAPCUT_PRO_EXECUTION_BLUEPRINT_V3.md
│   ├── EXECUTION_SPEC_373_PRO.json
│   ├── BEAT_MAP_373_PRO.csv
│   ├── SPECIAL_CUES_62_PRO.csv
│   ├── VISUAL_BINDING_373.csv
│   ├── GAP_BEHAVIOR_MAP_374.csv
│   ├── ASSET_MANIFEST_COMPLETE.csv
│   └── ...
├── sfx/                         # Sound effects (tạo nếu chưa có)
└── bgm/                         # Background music (tạo nếu chưa có)
```

## Pipeline đầy đủ

```
Script (.txt) + SRT (.srt)
        │
        ▼
POST_PRODUCTION_PLAN.md   ← post-production-planning skill
  (Color worlds, transitions, SFX beat map, BGM zones)
        │
        ▼
CapCut Execution Pack     ← capcut-production-executor skill
  (Beat map, visual binding, asset manifest, command templates)
        │
        ▼
CapCut Project            ← Thực thi trong CapCut Pro
        │
        ▼
Final MP4 Export + QC     ← ffprobe verify
```

## Lưu ý

- POST_PRODUCTION_PLAN.md là creative blueprint (tool-agnostic)
- CapCut Execution Pack là machine-readable spec cho CapCut agent
- Hai artifact này bổ trợ nhau, không thay thế nhau
- Khi Sếp nói "có video thô" → kiểm tra MP4 trong thư mục dự án
- Khi Sếp nói "lập plan" → tạo POST_PRODUCTION_PLAN.md, KHÔNG tự động execute
