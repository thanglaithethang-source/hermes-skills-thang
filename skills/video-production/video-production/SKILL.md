---
name: video-production
description: "Sếp's video production workflow — CapCut-first, no subtitles/text overlays, color + effects only."
version: 1.0.0
author: agent
metadata:
  triggers:
    - "video editing"
    - "capcut"
    - "edit video"
    - "post-production"
    - "color grade"
    - "sfx"
    - "bgm"
  pitfalls:
    - "Do NOT add subtitles, captions, or text overlays unless Sếp explicitly asks."
    - "Do NOT default to DaVinci Resolve unless Sếp says so."
    - "CapCut CLI: 'capcut-cli' (npm) for V3; 'capcut' binary (renezander030/capcut-cli) for V4. They are NOT the same tool."
    - "SHA256 verification: use Python hashlib.sha256(), NOT subprocess with sha256sum on Windows git-bash — it adds \\ prefix artifact causing false mismatches."
    - "Synthetic SFX clone detection: after Freesound fallback, audit SHA256 uniqueness before trusting assets — >50% clones = slots don't have real distinct sounds."
    - "⚠️ CapCut force-stop DANGER: Stop-Process CapCut -Force can DELETE unsaved project files from disk. ALWAYS backup draft_content.json BEFORE killing CapCut. If project was never saved in UI, it exists only in runtime state. Safer: have Sếp save+close from UI. See capcut-draft-editing skill → references/clone-rebuild-pattern.md for recovery."
---

# Video Production — Sếp's Workflow

## Primary Tool

**CapCut** is the main video editor. Two CLI packages exist:

- `capcut-cli` (npm): `npm install -g capcut-cli@0.14.0`. Used for V3 blueprints. Commands: `capcut-cli enums`, etc.
- `capcut` binary (renezander030/capcut-cli, GitHub): Used for V4 blueprints. Commands: `capcut doctor`, `capcut describe`, `capcut batch`, `capcut lint`, `capcut render`, etc.

V4 blueprints require the `capcut` GitHub binary, not the npm `capcut-cli`. Verify which one is installed before starting V4 workflow.

- DaVinci Resolve: **only when Sếp explicitly requests it.**

## V4 Blueprint Workflow

Sếp's V4 blueprints (e.g. Ancient Menstruation) use a 3-phase architecture. See `post-production-planning` skill for the planning side. Key execution differences from V3:

- **Shot-aware, not cue-driven** — motion/effects map to real shot boundaries, not 409 SRT cues
- **Motion budget enforced** — ≤45% artificial motion global, per-beat caps
- **Word anchors must resolve** — 60 critical timestamps from actual word transcript (≥0.86 confidence)
- **Asset locking mandatory** — every music/SFX file needs sha256, license, source_url
- **Native render required for final** — proxy ffmpeg render is NOT proof of completion
- **Validator gate** — `validate_v4_package.py` must pass before any edit begins
- **Asset integrity audit** — trước execution, chạy full audit asset: file existence, SHA256 integrity (dùng Python `hashlib`, không dùng subprocess `sha256sum` trên Windows git-bash), SHA256 uniqueness (phát hiện clone), blueprint slot coverage. Xem `post-production-planning` skill → `references/asset-audit.md`.

## Hard Rules

1. **NO subtitles / captions / text overlays** — unless Sếp says otherwise.
2. **NO text on video** — Sếp prefers visual-only storytelling.
3. **Color + effects are the priority** — filters, color grading, motion, transitions.
4. **Audio**: SFX + BGM, ducking under voice if voice exists.

## Workflow

1. Inspect source footage and project files.
2. Determine edit points, color look, and audio needs.
3. Apply color/filter/effects in CapCut.
4. Add SFX and BGM from local library first.
5. Export in the requested format.
6. Verify output file: size, duration, codec, resolution, FPS.

## Open-Source Tool Landscape

Sếp's current stack: CapCut (primary), DaVinci Resolve (on request), MoneyPrinterTurbo, OpenMontage.

Relevant open-source repos evaluated (2026-07-25):

| Repo | Stars | Stack | Fit | Notes |
|------|-------|-------|-----|-------|
| short-video-factory (YILS-LIN) | 4970 | Electron+Vue+FFmpeg+EdgeTTS | PARTIAL | Auto short video marketing, batch mode, OpenAI-compatible API. No color grading, no Fusion effects, no AI video gen. AGPL-3.0. Has Windows .exe installer. |
| video-shotcraft (Vincentwei1021) | 1577 | TypeScript/Remotion | HIGH | AI video skill for Claude Code & Codex — code-driven video creation. Apache-2.0. Lightweight, no GPU needed. |
| pireel | 720 | TypeScript/WebCodecs | MEDIUM | Open-source CapCut alternative, MCP-drivable. Browser-based. AGPL-3.0. |
| AI-Youtube-Shorts-Generator (SaarD00) | 182 | Python+FFmpeg+Gemini | MEDIUM | Faceless Shorts factory. Python stack matches. MIT license. |

When Sếp asks "find open source that fits me": search GitHub API by category (ai video, video editing, automation), filter by stars + activity + license + tech stack match (Python/FFmpeg/TypeScript), then deep-inspect top candidates via REST API (README, dir structure, package.json, releases, issues). Present 3-4 picks with fit assessment.

## Local Asset Library

Dự án video thường nằm dưới `C:/Users/thang/Downloads/Whisk Downloads/người tối cổ/`.
Mỗi video là một thư mục con riêng (vd: `Những Kẻ Dị Biệt/`).

Asset library (SFX, BGM) thường được tạo làm shared library:
- Shared: `C:/Users/thang/Downloads/_projects/human-evolution-sweaty/sfx/` và `bgm/`
- Per-project: thư mục `sfx/`, `bgm/` trong thư mục dự án

Luôn kiểm tra sự tồn tại của `sfx/` và `bgm/` bằng terminal trước khi tham chiếu.
Nếu chưa có → dùng Freesound API để săn (xem `post-production-planning` skill + `references/sfx-hunting.md`).

Cấu trúc thư mục dự án điển hình:
```
C:/Users/thang/Downloads/Whisk Downloads/người tối cổ/<Tên video>/
├── <Tên video>.mp4        # video thô
├── <Tên video>.wav        # audio voiceover
├── <Tên video>.txt        # kịch bản prose
├── srt.srt                # subtitle timing
├── POST_PRODUCTION_PLAN.md # blueprint hậu kỳ (từ post-production-planning skill)
├── sfx/                   # sound effects (tạo nếu chưa có)
├── bgm/                   # background music (tạo nếu chưa có)
└── capcut_v3/             # CapCut execution pack (nếu có)
```

Legacy path (deprecated, có thể không tồn tại):
`C:/Users/thang/Downloads/_projects/human-evolution-sweaty/`

## Verification

### Build Audit (10 criteria)

After a CapCut build script runs, audit the resulting `draft_content.json` against the `POST_PRODUCTION_PLAN.md`:

1. **29 filter segments** — đúng số lượng, đúng timing (cross-reference plan's SECTION MAP)
2. **5 color worlds** — filter ID đúng (cool/warm/soft/contrast)
3. **Filter value** — phải là plain number (0.0-1.0), không phải object
4. **Video effects** — đúng timestamp, đúng effect ID
5. **Effect ID hợp lệ** — không null, không đoán
6. **SFX files** — tất cả tồn tại trên disk
7. **BGM files** — tất cả 8 zones tồn tại
8. **Ambience files** — tất cả zones tồn tại
9. **Audio materials** — `type="extract_music"`, absolute paths
10. **3 mirrors sync** — `draft_content.json`, `template-2.tmp`, `Timelines/*/draft_content.json` cùng MD5

**Pitfall — off-by-one chapter timing**: Build scripts that calculate chapter timestamps independently (instead of deriving from the plan's SECTION MAP) create 1-second gaps between consecutive chapters. Session 2026-07-22: 15/29 chapters in `build_capcut_0722.py` started 1s later than the plan. Always regenerate chapter timestamps FROM the plan, not from SRT cues.

### Output Verification

Always run `ffprobe` on final output and report:
- File size
- Duration
- Resolution
- FPS
- Video codec
- Audio codec / channels / sample rate

See `references/capcut-build-audit.md` for the 2026-07-22 timing gap case study and detection script.
See `references/github-repo-deep-inspection.md` for the remote repo evaluation pattern via GitHub REST API (no clone needed).
