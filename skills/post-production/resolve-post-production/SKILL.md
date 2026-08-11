---
name: resolve-post-production
description: "Post-production workflow SOP for DaVinci Resolve — từ kịch bản đến final render, có audit và QC"
version: 1.5.0
---

# DaVinci Resolve Post-Production Workflow

Đây là SOP hậu kỳ video chuyên nghiệp cho DaVinci Resolve.

## Nguyên tắc cốt lõi

1. Audio (voice-over) là trục chính của timeline
2. Kịch bản + Audio + SRT là nguồn sự thật cho nội dung
3. Blueprint là nguồn sự thật cho hậu kỳ
4. DaVinci Resolve là môi trường thực thi chính
5. Fusion cho compositing và motion graphics
6. Fairlight cho SFX, nhạc nền, creative audio
7. Color Page cho color correction và grading
8. FFmpeg CHỈ cho phân tích kỹ thuật và QC
9. Cấm SFX và nhạc nền bằng FFmpeg
10. Không claim COMPLETED nếu chưa có bằng chứng thực tế

## Phân chia công cụ

### FFmpeg - CHỈ dùng cho:
- Đọc codec, resolution, FPS, duration
- Kiểm tra audio stream, channel, sample rate
- Phân tích peak và loudness
- Trích frame, tạo thumbnail/contact sheet
- Kiểm tra black frame, freeze frame, silence
- QC file render cuối bằng ffprobe

### FFmpeg - CẤM dùng cho:
- SFX, nhạc nền, sound design
- EQ, compression sáng tạo, reverb
- Ducking, automation volume, mix
- Burn hiệu ứng vào video
- Dựng final timeline
- Thay thế Resolve Edit/Fusion/Fairlight/Color

### DaVinci Resolve Edit Page:
- Tạo project, Media Pool, bin, timeline
- Cắt dựng, chọn source range, sắp xếp clip
- J-cut, L-cut, cutaway, B-roll
- Transition, title, subtitle
- Keyframe transform, crop, opacity

### Fusion:
- Motion graphics, Text+, lower third, title animation
- Mask, reveal, tracking, compositing
- Glow, blur, particles, camera movement
- Phải kiểm tra: node connection, parameter, keyframe, mask, frame range, MediaOut

### Fairlight:
- Toàn bộ SFX và nhạc nền
- EQ, compression, limiter, noise reduction
- Voice isolation, automation, ducking
- Bus routing, stereo placement, fade, crossfade

### Color Page:
- Color management, exposure, white balance
- Shot matching, scene matching, creative look
- Qualifier, power window, tracking
- Noise reduction, grain, broadcast-safe QC

### Deliver Page:
- Final master render
- FFmpeg chỉ dùng QC sau render

## Audio Track Layout

```
A1  — Voice-over chính
A2  — Voice backup/alternate
A3  — Dialogue bổ sung
A4  — Primary SFX
A5  — Transition SFX
A6  — Foley
A7  — Ambience
A8  — Music main
A9  — Music secondary
A10 — Music accent/stem
```

## Visual Track Layout

```
V1 — Main footage
V2 — B-roll
V3 — Overlay
V4 — Graphics
V5 — Fusion/title
V6 — Caption/highlight
V7 — Adjustment clips
```

## Pipeline (11 bước + GATE bắt buộc)

1. **Đọc & hiểu kịch bản** → SCRIPT_ANALYSIS.md
2. **Phân tích audio thu âm** → VOICE_ANALYSIS.md
3. **Kiểm tra SRT** → SRT_AUDIT.md
4. **Phân đoạn nội dung** → section/beat/sentence/shot
5. **Tạo blueprint** → POST_PRODUCTION_BLUEPRINT (XLSX/CSV/MD). Dùng `post-production-planning` skill để tạo blueprint sáng tạo — color worlds, transitions, SFX beat map, BGM mood zones. Skill này bao quát cả Resolve và CapCut.
6. **Audit blueprint** → kiểm tra đầy đủ, sửa trước khi dựng
7. **Thực thi trong Resolve** → backup → dựng → SFX → color → mix
8. **QC** → nội dung, hình ảnh, âm thanh, color, timeline
9. **Fix & reverify** → sửa lỗi → kiểm tra lại
10. ⛔ **GATE: SẾP DUYỆT TIMELINE** — Sếp phải kiểm tra và xác nhận timeline trên Resolve trước khi render. TUYỆT ĐỐI CẤM tự render khi chưa có lệnh rõ ràng của Sếp. Vi phạm = xóa file ngay. Agent phải hỏi rõ ràng "Sếp duyệt timeline chưa?" và chỉ tiếp tục khi Sếp xác nhận. Không được render dù chỉ 1 frame preview nếu chưa có lệnh. File render không được duyệt phải bị xóa ngay lập tức.
11. **Render & QC final** → render → ffprobe → audit (CHỈ sau khi Sếp duyệt)

## Profile Usage

Khi làm việc từ default profile (không có MCP), agent phải spawn `hermes -p resolve` để có đủ 34 Davinci tools. Chi tiết: `references/profile-mcp-isolation.md`.

## MCP Setup & Troubleshooting

### Yêu cầu hệ thống
- **Python 3.10** bắt buộc cho Windows — fusionscript binary không tương thích Python 3.11+
- Resolve phải chạy TRƯỚC khi MCP server khởi động
- Preferences > General > "External scripting using" phải set thành "Local"

### Cấu hình MCP trong Hermes (`resolve/config.yaml`)
```yaml
mcp_servers:
  davinci-resolve:
    command: C:/Users/thang/AppData/Local/Programs/Python/Python310/python.exe
    args:
      - C:/Users/thang/davinci-mcp/src/server.py
      - --connect-timeout
      - '15'
    env:
      RESOLVE_SCRIPT_LIB: D:\davinci\fusionscript.dll   # nếu Resolve không ở C:\Program Files
    enabled: true
```

### Path detection & non-standard installs
`get_resolve_paths()` trong `platform.py` hardcode `C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`. Nếu Resolve cài ở đường dẫn khác (VD: `D:\davinci`), import fusionscript sẽ fail với `DLL load failed`.

**Fix:** Patch `platform.py` để thêm auto-detect từ process + fallback paths, HOẶC set `env.RESOLVE_SCRIPT_LIB` trong MCP config để bypass hoàn toàn path detection.

### Verify MCP thực sự hoạt động
`hermes mcp test` chỉ xác nhận server process khởi động — KHÔNG xác nhận kết nối được tới Resolve API. Luôn test bằng tool call thực tế:
```
hermes -p resolve chat -q "Gọi resolve_control action='get_version'"
```
Chỉ khi trả về `DaVinci Resolve Studio 19.x` mới là kết nối thành công.

### Các lỗi thường gặp
| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `DLL load failed while importing fusionscript` | Sai Python version hoặc sai path | Python 3.10 + `RESOLVE_SCRIPT_LIB` env |
| `Resolve not found at C:\...\Resolve.exe` | Resolve cài ở non-standard path | Patch `platform.py` fallback |
| MCP test 34 tools, tool call vẫn lỗi | Server khởi động nhưng fusionscript import fail → degraded mode (32 tools) | Kiểm tra log `server.log` |

Chi tiết lỗi + reproduction: `references/windows-mcp-pitfalls.md`.

### API Limitations (verified Resolve 19.0.0b.50, MCP v2.60.0)

Không phải mọi thao tác đều khả dụng qua MCP. Đã xác nhận:

| Feature | Status | Fallback |
|---------|--------|----------|
| `add_keyframe` (zoom/pan/punch-in) | ✗ BROKEN — `'NoneType' object is not callable` | `set_transform` static zoom toàn clip, hoặc UI automation |
| `set_format_and_codec` (MP4/H.264) | ✗ MOV only | Chấp nhận MOV; convert bằng ffmpeg nếu cần |
| `safe_set_render_settings` readback | ⚠ `applied: null` | Dùng `set_settings` trực tiếp thay vì safe wrapper |
| `import_to_pool` folder path | ⚠ Returns 0 | Import từng file qua `media_pool.import_media` |
| Online SFX/music search | ✗ Cần API key | **ƯU TIÊN: local library** `C:/Users/thang/Downloads/_projects/human-evolution-sweaty/sfx/` (28 files, đủ dùng). Chỉ tìm online nếu local thiếu. |
| `add_serial_node` / `AddSerialPort()` | ✗ NOT IN API | Resolve 19.0.0b.50 không có API thêm node. Gộp tất cả grade vào 1 node CDL |
| OFX Plugin (Glow/Grain/Vignette) | ✗ NOT IN API | Không thể thêm qua script; phải làm manual trên Color page |

Chi tiết đầy đủ: `references/api-limitations.md`.

## Pitfalls

- **Đừng săn API key Freesound trên GitHub** — tất cả code public dùng `os.getenv()`, không có key thật bị leak. Vào thẳng freesound.org đăng ký (cần CAPTCHA) hoặc dùng local library: `references/local-sfx-library.md`. **Khi Sếp nói đã cấp key nhưng `$ENV` trống:** đừng dừng lại — key thường nằm ở `~/.hermes/*.key`, session history (`session_search`), hoặc profile `MEMORY.md`. Xem `references/api-key-discovery.md`.
- **Sếp nói bỏ captions → bỏ ngay**, không hỏi lại. Tập trung vào color filter + Fusion effects.
- **Resolve 19 API giới hạn node graph** — không thêm được node/OFX qua script. Chấp nhận single-node CDL grade, đừng loop retry.
- **`computer_use` Alt+S không ổn định** trên Color page — không dùng làm phương án chính để thêm node.

### Render Pipeline (MCP)

```python
# Xóa job cũ → tạo job mới → set range → render → poll
render('delete_all_jobs')
render('prepare_render_job', target_dir='C:/path/output/', custom_name='my_render',
       require_temp_target=False, settings={'MarkIn': 86400, 'MarkOut': 113777})
render('start')
render('get_job_status')  # poll đến khi 'Hoàn thành'
```

### SFX Placement (MCP)

⚠ **PITFALL: `record_frame` is RELATIVE to timeline start, NOT absolute.**  
Do NOT use `record_frame_mode='absolute'` — it double-offsets by the timeline start frame (86400), pushing all SFX far past video end. Always use the default relative mode. Compute `record_frame = seconds × fps` (e.g., `30 × 24 = 720` for 00:30 @24fps).

```python
# CORRECT — relative mode (default)
timeline('add_track', track_type='audio', index=2)
media_pool('append_to_timeline', clip_infos=[{
    'clip_id': '<uuid>', 'record_frame': 720,  # 30s @24fps = 720
    'start_frame': 0, 'end_frame': 11,          # clip duration - 1
    'track_index': 2, 'media_type': 2}])
# DO NOT add record_frame_mode='absolute'
```

### Color CDL (MCP)

```python
timeline_item_color('set_cdl', track_type='video', track_index=1, item_index=0,
    cdl={'NodeIndex': 1, 'Slope': {'R': 1.1, 'G': 1.0, 'B': 1.0},
         'Offset': {'R': 0.02, 'G': 0.0, 'B': 0.0},
         'Power': {'R': 0.98, 'G': 1.0, 'B': 1.0}, 'Saturation': 1.05})
```

## Shot Rules

- Mặc định 16:9, mỗi shot tối đa 5 giây
- Shot dài hơn 5s phải có lý do rõ ràng
- Không cắt liên tục chỉ để đạt giới hạn
- Ưu tiên nhịp nội dung và cảm xúc

## SFX Rules

- Phải xuất phát từ nội dung
- Phân loại: narrative, physical, transition, UI, emotional accent, ambience, impact, riser, whoosh, foley
- Mỗi SFX phải trả lời: phục vụ gì, có cần thiết, ở frame nào, có che voice không
- Không lạm dụng whoosh/boom/impact

## Music Rules

- Chia thành section: hook, setup, development, tension, reveal, climax, resolution, CTA
- Mỗi section: mood, BPM, energy, instrumentation, điểm bắt đầu/kết thúc
- Ducking theo voice, automation trong Resolve

## QC Checklist

### Nội dung: hình đúng lời, visual hỗ trợ ý, không sai dữ kiện
### Hình ảnh: không black frame, không freeze, không flash, không crop sai
### Âm thanh: voice rõ, nhạc không che voice, SFX không quá lớn, không clipping
### Color: exposure ổn, white balance ổn, skin tone hợp lý, shot match
### Timeline: không gap, không overlap, không clip ngoài phạm vi
### Render: đúng codec/resolution/FPS/duration, có video+audio stream

## Project Cleanup (hủy dự án)

Khi Sếp yêu cầu xóa/hủy dự án Resolve, phải dọn SẠCH TẤT CẢ artifact, không bỏ sót.

### Vị trí cần kiểm tra và xóa:

| Vị trí | Pattern | Ghi chú |
|--------|---------|---------|
| `~/davinci-output/` | Toàn bộ thư mục con của dự án | Render, state, assets |
| `~/Resolve_Output/` | Toàn bộ thư mục con của dự án | Assets, audio stems, BGM, kế hoạch |
| `~/Downloads/` | `*BACKUP*.drp`, `*_BACKUP_*` | Project backup files |
| `~/Videos/` | `*render*`, `*FINAL*`, `*davinci*` | Stray render files |

### Quy trình:

1. Dùng `find` quét toàn bộ `~/` tìm file/thư mục liên quan đến dự án (theo RUN_ID, tên project)
2. Xóa từng vị trí một, xác nhận từng bước
3. Không đụng vào MCP tool files (`.drp` template, fixture) — chỉ xóa project artifacts
4. Báo cáo tổng dung lượng đã giải phóng
5. Project trong Resolve database chỉ xóa được khi Resolve đang chạy (qua MCP `project_manager delete_project`)

### Pitfall:

- Agent trước đây render ra nhiều thư mục khác nhau (`davinci-output/`, `Resolve_Output/`) — phải kiểm tra TẤT CẢ, không chỉ một chỗ
- File `.drp` trong `davinci-mcp/` hoặc `tools/` là template của tool — KHÔNG ĐƯỢC XÓA

## Trạng thái

Chỉ dùng: PLANNED, EXECUTING, VERIFYING, FIXING, COMPLETED, PARTIALLY_COMPLETED, BLOCKED, FAILED, NOT_VERIFIED

## Evidence

Mỗi giai đoạn lưu: blueprint, timeline report, screenshot, Fusion node graph, color still, waveform, ffprobe report, audit report
