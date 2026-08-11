---
name: project-audit-handover
description: "Audit abandoned project directories — identify what's still relevant, clean up junk, verify kept projects work, learn to control them."
version: 1.0.0
platforms: [windows]
---

# Project Audit & Handover

Khi Sếp yêu cầu kiểm tra một thư mục chứa nhiều dự án cũ (từ trước khi reset Hermes), mục tiêu: xác định cái nào còn dùng → giữ lại → verify hoạt động → học cách kiểm soát.

## Pipeline

1. **Liệt kê toàn bộ** thư mục + dung lượng (`du -sh`)
2. **Đối chiếu với skills hiện tại** — search skills folder xem có tham chiếu đến path nào không
3. **Phân loại**: CÒN DÙNG (có skill tham chiếu, hoặc Sếp xác nhận) vs RÁC
4. **Báo cáo Sếp** — bảng phân loại rõ ràng, có dung lượng, ngày cuối
5. **Xóa rác**, giữ lại theo lệnh Sếp
6. **Verify từng dự án giữ lại**: chạy thử, fix nếu gãy
7. **Học cách kiểm soát**: CLI, API, port, config, credentials

## Game/Software Directory Cleanup Pattern

When auditing a directory containing a game or software with applied mods (e.g. D:\hoi4):

1. **Scan top-level**: `du -sh` per item, identify game folder vs modding artifacts
2. **Check if mod is applied**: read a sample localisation/config file inside the game folder — look for non-English text or modified content with recent timestamps
3. **Identify junk types**:
   - `_backup_*` dirs inside game folder — pre-mod backups, safe to delete if mod works
   - `_*.json` cache files — modding caches, safe to delete
   - `*.py` scripts — one-off modding scripts, safe to delete
   - `*.zip` — intermediate archives already extracted, safe to delete
   - Empty dirs — failed attempts (e.g. DeepSeek folder with 0 files)
   - `*_raw_files/` — original source before modification, safe if mod applied
4. **Verify mod still applied** before proposing cleanup
5. **Use `clarify` tool** as approval gate — present table with path/size/reason
6. **Delete** only after approval, echo OK/FAIL per item
7. **Post-cleanup verify**: game data intact, mod still applied, no _backup files remain

## Bitmap Font Regeneration (Clausewitz Engine Games)

When a game mod (Vietnamese localization) has broken fonts — tiny glyphs, missing chars, cut-off diacritics — regenerate bitmap fonts from Windows TTFs. Full technique in `references/bitmap-font-regeneration.md`.

Key steps: map original font faces to Windows TTFs → render all chars (ASCII + Latin Extended-A/B + Vietnamese diacritics) → shelf-pack into DDS texture atlas → write BMFont .fnt with correct page reference → backup originals first.

## Pitfalls

- **Không tự quyết định giữ/xóa** — luôn hỏi Sếp trước khi xóa
- **Không báo cáo suông** — phải chạy thử thực tế (import module, gọi CLI --help, curl API)
- **Không claim "đã kiểm soát" nếu chưa gọi được API/CLI thành công**
- MSYS bash không chạy được .exe trực tiếp (Permission denied) → dùng `cmd.exe /c`
- **Backup dir trong .curator_backups trùng tên skill** → gây skill_view ambiguous. Đổi tên backup dir hoặc xóa backup cũ.
- **Không xóa game data** — luôn verify mod applied trước khi đề nghị xóa backup/cache
- **Backup dir trong .curator_backups trùng tên skill** → gây skill_view ambiguous. Đổi tên backup dir hoặc xóa backup cũ. (Đã xảy ra với complex_task_orchestrator backup.)

## Dependencies & Build Issues

- Electron app thiếu node_modules → thử `npm install --legacy-peer-deps` nếu `yarn` lỗi
- Nếu build quá lâu/nặng → tải bản cài đặt từ GitHub Releases nhanh hơn
- `corepack` lỗi trên nvm4w → `npm install -g yarn` rồi `yarn install`

## Verification Checklist

- [ ] CLI chạy được (--help, version)
- [ ] Config load OK (API keys, provider)
- [ ] Web server port xác định (netstat)
- [ ] API test được (curl)
- [ ] Auth/credentials rõ ràng (token, login mặc định)
