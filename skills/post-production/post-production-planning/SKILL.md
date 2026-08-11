---
name: post-production-planning
description: "Creative post-production blueprint from script — color worlds, transitions, SFX beat-map, BGM mood zones. Tool-agnostic planning before Resolve or CapCut execution."
version: 1.0.0
---

# Post-Production Planning

Tạo blueprint hậu kỳ sáng tạo từ kịch bản (SRT + prose). Đây là giai đoạn PLANNING — trước khi giao cho executor (resolve-post-production hoặc capcut-production-executor).

## When to Use

- Sếp đưa kịch bản + SRT → cần plan hậu kỳ
- Sếp nói "lập plan", "kế hoạch hậu kỳ", "blueprint"
- Cần thiết kế màu sắc, filter, transition, SFX, nhạc nền cho video

KHÔNG dùng skill này để:
- Thực thi trong Resolve/CapCut (dùng skill executor tương ứng)
- Sửa lỗi render/export
- Tạo EDIT_PLAN.json cho CapCut (đó là bước sau, từ blueprint này)

### RANH GIỚI NGHIÊM NGẶT (verified 2026-07-31)

Khi Sếp nói "lập plan" / "plan hậu kỳ" / "blueprint" → CHỈ lập POST_PRODUCTION_PLAN.md. KHÔNG:
- Load skill executor (capcut-production-executor, resolve-post-production)
- Search file video thô
- Bắt đầu hunt SFX/BGM
- Bất kỳ bước thực thi nào

Chỉ khi Sếp nói "thực hiện" / "execute" / "build" → mới load executor + bắt đầu thực thi. Vi phạm ranh giới này = Sếp sửa lại.

## Nguyên Tắc Sáng Tạo (BẮT BUỘC)

Đây là user preference đã verified:

1. **CẤM MÁY MÓC** — mỗi section có treatment riêng, không lặp lại công thức. Không section nào giống section nào về filter, transition, hay effect.
2. **Màu sắc kể chuyện** — chia thành các "thế giới màu" (color worlds) dựa trên không gian và cảm xúc, không dựa trên thời lượng.
3. **Filter + hiệu ứng PHẢI có lý do kể chuyện** — mỗi effect phải trả lời: "cái này giúp kể câu chuyện như thế nào?"
4. **SFX theo BEAT kịch bản** — mỗi SFX phải có timestamp chính xác từ SRT + lý do cảm xúc. Với video hài/meme, áp dụng retention-driven strategy: 5-layer model (gaming, tech, comedic, cinematic, ambience) + pattern interrupt + silence bomb + callback SFX. Xem `references/creative-audio-strategy.md`.
5. **Nhạc nền thở theo nhịp kịch bản** — chia thành mood zones, mỗi zone có BPM, instrumentation, energy level riêng. Với video meme/slang, áp dụng bait-and-switch, ironic contrast, và callback motif. Xem `references/creative-audio-strategy.md`.
6. **Transition là công cụ kể chuyện** — mỗi transition phải có lý do narrative, không phải bộ sưu tập hiệu ứng.

## Pipeline

1. PHÂN TÍCH KỊCH BẢN — đọc SRT + prose, xác định emotional arc, tone, style
2. Phân đoạn thành SECTION (10-30 section, mỗi section có mood + tempo riêng)
3. Thiết kế COLOR WORLDS (3-6 thế giới màu, gán vào từng section)
4. Thiết kế FILTER + EFFECT cho từng section (không section nào giống nhau)
5. Thiết kế TRANSITION giữa các section (mỗi kiểu dùng đúng 1 lần)
6. Thiết kế SFX BEAT MAP (mỗi SFX: timestamp, file nguồn, lý do cảm xúc)
7. Thiết kế BGM MOOD ZONES (mỗi zone: mood, BPM, instrumentation, energy, EQ/ducking)
8. Tổng hợp TIMELINE OVERVIEW → POST_PRODUCTION_PLAN.md

**BUILD ASSET LIBRARY** (SFX + BGM) là bước EXECUTE, không phải bước PLAN. Chỉ hunt SFX/BGM khi Sếp nói "thực hiện" / "build" / "execute". Xem `references/sfx-hunting.md` và `templates/hunt_sfx_bgm_template.py`.

## Blueprint Format

File output: `POST_PRODUCTION_PLAN.md` gồm các phần:

### 1. SECTION MAP
Bảng phân đoạn kịch bản: tên section, timestamp, sub range, mood, nội dung chính.

### 2. COLOR WORLDS
Mỗi thế giới màu gồm:
- Tên + cảm xúc
- Đặc trưng thị giác
- Áp dụng cho section nào
- Công thức color grading cụ thể: Temperature, Tint, Contrast, Saturation, Highlights, Shadows, Exposure, Vignette
- Gợi ý filter tương ứng (Resolve: CDL nodes; CapCut: filter preset)

### 3. FILTER + EFFECT THEO SECTION
Mỗi section có:
- Filter áp dụng (thế giới màu nào)
- Effect sáng tạo (visual effect cụ thể, có lý do kể chuyện)
- Key moments được nhấn bằng effect đặc biệt

### 4. TRANSITIONS
Bảng tất cả transition:
- Từ section nào → đến section nào
- Kiểu transition (match cut, whip pan, dip to black, iris reveal, glitch, cross-dissolve...)
- Cảm xúc/lý do kể chuyện
- **Quy tắc cứng:** mỗi kiểu transition chỉ dùng 1 lần trong toàn bộ video

### 5. SFX BEAT MAP
- AMBIENCE LAYER: SFX nền chạy liên tục (lửa, room tone, gió...)
- BEAT SFX: Danh sách SFX đánh dấu khoảnh khắc, mỗi cái có: timestamp, sub#, file nguồn (từ local library), cảm xúc
- Số lượng: ~3-4 SFX mỗi phút cho documentary; ~5-7 SFX/phút cho video hài/meme giữ retention
- Với video meme: phân SFX thành 5 layer (gaming, tech, comedic, cinematic, ambience) + chọn 3-4 callback SFX xuyên suốt. Xem `references/creative-audio-strategy.md`.

### 6. BGM MOOD ZONES
Mỗi zone:
- Timestamp range + section áp dụng
- Mood + BPM + Energy (1-10)
- Instrumentation
- Key (Major/Minor)
- Processing: EQ, Reverb, Ducking, Volume
- Điểm đặc biệt (fade out, silence, transition...)
- Với video meme/slang: chọn zone template từ `references/creative-audio-strategy.md` (Boss Battle Intro, 8-Bit Dungeon, Elevator, Trust Me Bro Orchestra, Discord Meltdown, MacGyver Theme, Lofi Beats, Corporate Plastic, Power Anthem). Áp dụng bait-and-switch ít nhất 1 lần.

### 7. TIMELINE OVERVIEW
Sơ đồ tổng quan: section → color world → transition → SFX → music zone — tất cả trên cùng một timeline.

## Công Cụ Phân Tích

- SRT: dùng để lấy timestamp chính xác cho SFX và transition
- Prose/script: dùng để xác định mood và emotional arc
- Local SFX library: kiểm tra trước, không săn online nếu local có
- Local BGM: nếu có sẵn file mix, cắt theo mood zones
- Freesound API: dùng để search + download SFX. Token: `r7EZFGAUP9iKxnPLLghnZ7WuWdUkjMGFAmbeh9Xs`. Search bằng broad category queries ngắn (cartoon pop, whoosh, drum hit) — queries dài trả về 0 results. Download HQ MP3 preview từ CDN URL (`cdn.freesound.org/previews/...`) hoạt động (tested 2026-07-22, 101 files/177MB trong ~3 phút với ThreadPoolExecutor 5-8 workers). Với BGM, không dùng `filter=duration` vì giảm kết quả quá nhiều — sort bằng duration thủ công sau search. File không tìm thấy → sinh synthetic bằng Python `wave` module (sine/tone/noise).
- **Hunt script template**: `templates/hunt_sfx_bgm_template.py` — copy vào project, custom slot definitions, chạy. Đã proven 99% SHA256 uniqueness với 120 SFX slots (2026-07-22). Pipeline: define slots → ThreadPool Freesound hunt → synthetic fallback → registry → SHA256 audit. **NO FFMPEG** (2026-07-31): Freesound MP3 lưu trực tiếp, synthetic WAV dùng Python `wave` module.
- **BGM synthetic generation**: sinh mood zones bằng layered tones (sine/triangle/square) với LFO modulation + fade in/out. Xem `references/bgm-synthetic-generation.md` để có 9 zone templates proven.
- Pixabay API: search video/music OK nhưng download bị 403 hotlink block. Không rely vào Pixabay cho audio download.
- Pexels API: hiện không hoạt động (403 error 1010 — key hết hạn).

## Kiểm Tra Trước Khi Delivery

- [ ] Tất cả section có treatment riêng biệt (không section nào copy section khác)
- [ ] Mỗi transition là duy nhất (không lặp kiểu)
- [ ] Tất cả SFX có timestamp chính xác từ SRT
- [ ] Tất cả SFX có file nguồn verified (tồn tại trên disk)
- [ ] BGM mood zones khớp với emotional arc của kịch bản
- [ ] Không có yếu tố máy móc/rập khuôn
- [ ] Plan đủ chi tiết để executor thực thi mà không cần đoán
- [ ] (V4) Shot map có shot boundary từ visual cut thật, không từ cue SRT
- [ ] (V4) Motion budget không vượt 45% toàn cục, per-beat caps được tôn trọng
- [ ] (V4) Asset registry có sha256 + license cho từng file nhạc/SFX
- [ ] (V4) SHA256 uniqueness audit: ≥30 unique hashes cho 51 SFX; tất cả BGM unique (phát hiện file clone do synthetic generation)
- [ ] (V4) Blueprint ↔ Registry status consistency: UNBOUND slots phải match với registry state, không để mismatch trước execution
- [ ] (V4) Word anchors có search window + yêu cầu confidence ≥0.86
- [ ] (V4) Cultural safety: không generic Indigenous imagery nếu chưa verify
- [ ] (V4) **Blueprint coverage audit**: chạy audit so sánh `draft_content.json` với tất cả file blueprint (beats, anchors, callouts, looks, BGM zones) — verify filter timing match beat boundaries, SFX materials khớp anchor requirements, text callouts đúng nội dung, look families đúng strength, BGM zone boundaries khớp beat transitions, motion tracks hiện diện nếu Phase B P1 completed. Xem `references/blueprint-coverage-audit.md` để có script pattern Python và bảng PASS/WARN/FAIL.

## Pitfalls

- **"Lập plan" = CHỈ lập plan, không làm gì khác.** Khi Sếp nói "lập plan hậu kỳ" / "lập plane" / "kế hoạch hậu kỳ" → chỉ đọc kịch bản + SRT + viết POST_PRODUCTION_PLAN.md. KHÔNG search file video, KHÔNG inspect project structure, KHÔNG săn SFX/BGM, KHÔNG mở CapCut, KHÔNG chạy ffprobe. Những việc đó thuộc giai đoạn EXECUTE (khi Sếp nói "thực hiện"). Lỗi thực tế (2026-07-31): agent đọc xong kịch bản rồi bắt đầu tìm video thô trong folder, inspect project structure, check file tồn tại — Sếp cắt ngang "MÀY CHỈ CÓ NHIỆM VỤ LẬP PLANE HẬU KÌ". Plan phase = đọc script + SRT + xuất blueprint. Done.
- **NGHIÊM CẤM DÙNG FFMPEG ĐỂ LÀM ÂM THANH.** Sếp cấm tuyệt đối (2026-07-31). Freesound MP3 lưu trực tiếp, KHÔNG convert sang WAV bằng ffmpeg. Synthetic SFX/BGM dùng Python `wave` module. Template `hunt_sfx_bgm_template.py` đã patch no-ffmpeg. **Lưu ý:** `capcut-production-executor` skill (protected, manually-authored) vẫn còn Audio Material Creation Workflow bước 2 yêu cầu `ffmpeg -i input.mp3 -ar 48000 -ac 2 output.wav` — IGNORE bước đó. Lưu MP3 trực tiếp, CapCut đọc được cả MP3 và WAV.
- **Đừng thiết kế transition trước khi phân tích script** — transition phải xuất phát từ narrative, không phải từ bộ sưu tập có sẵn.
- **Đừng gán một màu cho toàn bộ video** — kịch bản có emotional arc, màu sắc phải đi theo.
- **Đừng nhồi SFX vào mọi khoảng trống** — khoảng lặng cũng là một công cụ.
- **Đừng để nhạc chạy xuyên suốt không ngừng** — những khoảnh khắc silence có sức mạnh lớn hơn nhạc.
- **Đừng dùng chung một kiểu transition** — mỗi lần chuyển cảnh là một cơ hội kể chuyện khác nhau.
- **Freesound BGM: không dùng duration filter** — `&filter=duration:[10.0 TO *]` giảm kết quả về 0. Search không filter rồi sort bằng duration trong code.
- **Download SFX song song** — 101 files tuần tự mất 5+ phút dễ timeout. ThreadPoolExecutor 5-8 workers giảm còn ~2 phút.
- **Mass-edit CapCut JSON**: khi blueprint có 50+ event, dùng script Python trực tiếp sửa `draft_content.json` (xem `references/capcut-mass-edit-json.md`) thay vì qua `run_job.py`. Nhớ sync 3 mirrors.
- **Windows git-bash SHA256 artifact**: `subprocess` gọi `sha256sum` trên git-bash thêm prefix `\` vào hash → tất cả báo mismatch. Luôn dùng Python `hashlib.sha256()` thay vì subprocess khi audit asset integrity. Xem `references/asset-audit.md` để có script pattern đầy đủ.
- **Synthetic SFX clone detection**: khi Freesound fail và fallback sang synthetic generation bằng `wave` module, kết quả thường ra hàng loạt file byte-identical. Audit SHA256 uniqueness ngay sau generation — nếu >50% SFX share cùng 1 hash, các slot đó chưa thực sự có asset riêng biệt.

## Example

Xem blueprint mẫu trong `references/example-gary-rib-thief.md` — kịch bản 16 phút, 23 section, 5 color worlds, 23 unique transitions, 60 SFX beats, 8 BGM zones.

Xem cấu trúc dự án thực tế và pipeline đầy đủ (script → plan → CapCut pack → export) trong `references/project-structure.md`.

Xem quy trình audit draft_content.json ở cấp CapCut JSON (time unit, BGM zone, SFX overlap, look family, audio path integrity) trong `references/blueprint-audit-checklist.md` — bổ trợ cho `references/blueprint-coverage-audit.md` ở cấp blueprint element coverage.

## V4 Blueprint (Production-Grade)

Khi Sếp yêu cầu blueprint chất lượng production, áp dụng kiến trúc V4 (chi tiết trong `references/v4-blueprint-architecture.md`):

- **Shot-aware, không cue-driven** — 36 story beats + real shot map, không dùng 409 cue SRT làm đơn vị edit
- **Word-level alignment** — 60 word anchors, match confidence ≥0.86 từ transcript thật; cue hint chỉ là search window
- **Asset locking** — nhạc/SFX có sha256, license, source_url; không semantic placeholder; không asset phù hợp → bỏ slot đó
- **Motion budget** — global ≤45%, per-beat caps riêng; 9 locked primitives (không tên preset tùy tiện)
- **3-phase gate**: INSPECT & LOCK (read-only) → EXECUTE → NATIVE RENDER & QA
- **Native render required** — proxy ffmpeg không phải bằng chứng; phải export từ CapCut app thật mới được PRO_FINAL_PASS
- **Cultural safety**: không generic Indigenous imagery nếu chưa verify nguồn cụ thể
