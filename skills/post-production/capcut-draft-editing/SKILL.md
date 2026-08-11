---
name: capcut-draft-editing
description: "Practical CapCut draft_content.json editing — filter/effect ID verification, schema pitfalls, cache diagnostics, and proven workflows from production sessions. Companion to capcut-production-executor."
version: 1.0.0
metadata:
  hermes:
    tags: [capcut, draft, filter, effect, json-editing]
    related_skills: [capcut-production-executor]
---

# CapCut Draft Editing — Production Lessons

Practical companion to `capcut-production-executor`. Captures filter/effect ID
verification, schema pitfalls, and workflow lessons from real editing sessions.

## When to Use

- Editing `draft_content.json` directly (filters, effects, audio)
- Filter/effect not rendering in CapCut
- Need to verify whether an effect_id actually works
- Batch-replacing materials across tracks

## Critical Rule: Never Trust effect_map IDs

**`capcut_effect_map.json` and `capcut-cli enums` IDs are WRONG for CapCut 8.9.1 Việt hóa.**

Verified 2026-07-22: All 10 built-in filter IDs (7028463716...) have cache dirs
that are EMPTY — no asset files downloaded. CapCut will not render filters
using these IDs.

### Quick Cache Check

Before using any effect_id, verify the cache dir has actual files:
```
C:\Users\<user>\AppData\Local\CapCut\User Data\Cache\effect\<effect_id>\
```

If the dir is empty or only has dirs but no files → the ID won't render.

### Working Effect Types

| Type | Status | Source |
|------|--------|--------|
| Video effects (11 IDs) | ✅ Working | CapCut online server — has cache assets |
| JianYing filters (5 IDs) | ⚠️ Fallback | Need manual cache dirs; assets download on open |
| Built-in filters (10 IDs) | ❌ Broken | Empty cache — DO NOT USE |

## User Intent: "All Filters Fail"

When Sếp says filters/effects fail, the correct action is:
1. **Replace ALL filter materials**, not just the obviously bad ones
2. Don't assume some IDs are "probably correct" — if any fail, all may fail
3. Prefer JianYing as fallback (Sếp's preference)
4. Video effects use different IDs (from online server) — they're independent

DO NOT: replace only the ones with invalid IDs and leave the rest.
Lesson from 2026-07-22: replaced 10 bad IDs, left 26 "good" ones → all still failed.

## Filter Material Schema (for JianYing)

```json
{
  "id": "<UUID>",
  "type": "filter",
  "sub_type": "jianying",
  "effect_id": "<jianying_id>",
  "resource_id": "<same>",
  "third_resource_id": "<same>",
  "name": "JY_<NAME>",
  "report_name": "<Name>",
  "path": "C:/Users/thang/AppData/Local/CapCut/User Data/Cache/effect/<id>",
  "value": 0.22,
  "md5": "",
  "is_vip": false,
  "platform": "jianying",
  "category_name": "",
  "local_material_id": "",
  "category_id": ""
}
```

## Filter Segment Schema

Filter segments MUST have `clip` and `uniform_scale` as objects (not null):
```json
"clip": {"scale": {"x":1,"y":1}, "rotation":0, "transform": {"x":0,"y":0}, "flip": {"vertical":false,"horizontal":false}, "alpha":1},
"uniform_scale": {"on": true, "value": 1.0}
```

## Effect Segment Schema (video_effects)

Effect segments should have `clip: null` and `uniform_scale: null` (opposite of filters).

## JianYing Filter Reference

| Key | effect_id | Name | Use | Cache (2026-08-01) |
|-----|-----------|------|-----|---------------------|
| abg | 7127679308897832206 | ABG | Warm orange | ❌ 0 files |
| ke1 | 7127819154018536741 | KE1 | Neutral balanced | ❌ 0 files |
| kv5d | 7127578859217620254 | KV5D | Cinematic cool | ❌ 0 files |
| vhs3 | 7127669764905782542 | VHS III | Gritty tension | ❌ 0 files |
| ditto | 7195816046077496635 | Ditto | Soft dreamy | ❌ 0 files |

**⚠️ As of 2026-08-01, ALL JianYing filter cache dirs are empty.** Assets only download when Sếp opens CapCut and applies the filter through UI. If Sếp hasn't done this, JianYing replacement will also fail silently. Prefer the filter→effect conversion strategy instead.

Beat-color mapping: warm→abg/ke1, cool→kv5d/vhs3, contrast→vhs3/abg,
soft→ditto/ke1, vintage→vhs3/ditto, faded→ditto/kv5d, dramatic→vhs3/abg.

## Workflow: Convert Filter Tracks → Effect Tracks

When all built-in filter IDs are broken AND JianYing cache is empty, convert filter tracks to effect tracks entirely. This is a third strategy beyond "replace with JianYing" or "rebuild segments."

1. Stop CapCut (check `tasklist /FI "IMAGENAME eq CapCut.exe"` first)
2. Backup draft_content.json
3. Map each old filter material_id → color group (COLOR_A/B/C/D/E)
4. Map each color group → a video effect ID with verified cache (see `capcut-filter-id-resolution` table)
5. Create new `video_effect` materials in `materials.video_effects[]` (one per color group, using the schema from `capcut-filter-id-resolution`)
6. For each filter track:
   - Change `type` from `"filter"` to `"effect"`
   - Replace `material_id` in each segment with new video_effect material UUID
   - Leave `clip: null` and `uniform_scale: null` AS-IS (correct for effects!)
7. Remove old filter materials from `materials.effects[]` (keep non-filter types like sharpen/clear/particle)
8. Write + sync 3 mirrors
9. Verify: 0 filter tracks, 0 bad material refs, all video_effect IDs have cache, video/audio tracks unchanged

**Key insight**: This strategy inverts the schema. Filter segments need `clip`/`uniform_scale` as objects; effect segments need `null`. By converting track type, existing `null` values become correct.

See `capcut-draft-repair` → `references/session-20260801-project-0731.md` for full transcript.

## Workflow: Batch Replace Filters

1. Stop CapCut (`Stop-Process CapCut -Force`)
2. Backup draft_content.json
3. Read current filter materials to get old material_ids (preserve these!)
4. Map each old material_id → new filter (keep same UUID, replace fields)
5. Update segment material_ids to match
6. Create cache dirs: `Cache/effect/<jianying_id>/`
7. Write + sync 3 mirrors
8. Verify: mirror hashes match, audio/text/video_effects count unchanged

## Adding Background Music (SBG) Tracks

When Sếp asks for nhạc nền (SBG), use **Incompetech (Kevin MacLeod)** — CC BY 4.0, royalty-free, YouTube-safe 100%. No copyright strikes. Only requirement: credit in YouTube description.

### Download URL pattern
```
https://incompetech.com/music/royalty-free/mp3-royaltyfree/<Track%20Name>.mp3
```
URLs use `%20` for spaces. Server returns `Content-Disposition: attachment` + `application/octet-stream`.

### Meme/Joker BGM tracks (Sếp's vibe: "slang meme joker")

| File | Track | Vibe | Size |
|------|-------|------|------|
| SBG_MONKEYS_SPINNING.mp3 | Monkeys Spinning Monkeys | Playful/mischievous | ~5MB |
| SBG_SNEAKY_SNITCH.mp3 | Sneaky Snitch | Sneaky/suspense comedy | ~5.5MB |
| SBG_FLUFFING_A_DUCK.mp3 | Fluffing a Duck | Goofy/comedy | ~2.7MB |
| SBG_WALLPAPER.mp3 | Wallpaper | Quirky/absurd | ~8.8MB |

### SBG audio material schema

Clone from existing audio material structure. Key fields:
- `type`: `"audio"` (not `"video_original_sound"`)
- `name`: `"SBG_<TRACK_NAME>"`
- `path`: forward-slash path to MP3
- `duration`: estimated in microseconds (file_size_bytes * 8 / 128000 * 1000000 for 128kbps MP3)
- `copyright_limit_type`: `"none"`

### SBG track schema

- `type`: `"audio"`, `name`: `"SBG"`
- Loop segments with `is_loop: true` to fill video duration
- `volume`: **0.15** (gia vị — background only, not overpowering SFX/voice)
- Each segment: `source_timerange.start=0`, `target_timerange` covers its portion

### Credit text for YouTube description
```
Music: Monkeys Spinning Monkeys by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0
http://creativecommons.org/licenses/by/4.0/
```

## Pitfalls

1. **Trusting capcut_effect_map.json** — FATAL. Always verify cache dirs first.
2. **Partial replacement** — if Sếp says "all fail", replace ALL filters.
3. **clip/uniform_scale confusion** — filters need objects, effects need null.
4. **Forgetting cache dirs** — JianYing filters need manual dir creation.
5. **Not syncing mirrors** — 3 files must be byte-identical.
6. **⚠️ Force-stopping CapCut can DELETE unsaved projects (2026-07-23).** The "new" project's entire draft_content.json vanished from disk after `Stop-Process CapCut -Force`. CapCut holds projects in runtime state until explicitly saved — killing the process wipes the in-memory draft. **ALWAYS read draft JSON into memory BEFORE killing CapCut.** If the project was never saved in CapCut UI, it may not exist on disk at all. Safer workflow: have Sếp save + close from UI. See `references/clone-rebuild-pattern.md` for recovery.
7. **Clone-rebuild pattern:** When a project is lost or needs a fresh start, clone an existing valid CapCut project directory (e.g. TRIBE_CANCELLED), nuke its content (tracks, segments, materials), then rebuild with proper materials + segments + tracks. Creating a valid CapCut draft_content.json from scratch is near-impossible — the schema has 60+ material categories with interdependent UUIDs. Cloning preserves the skeleton. See `references/clone-rebuild-pattern.md`.
8. **curl cannot write to paths with Unicode characters (2026-08-01).** `curl -o "/c/Users/thang/.../người tối cổ/..."` silently fails (exit 23 = write error) even though the directory exists and is writable. **Fix**: download to a clean ASCII path first (e.g. `C:/Users/thang/Downloads/`), then `cp` to the Unicode destination. Python `shutil.copy2` handles Unicode paths fine — only curl has this issue on Windows git-bash.
