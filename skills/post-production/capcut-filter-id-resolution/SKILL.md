---
name: capcut-filter-id-resolution
description: "Resolve correct filter/effect IDs for CapCut 8.9.1 Việt hóa — which IDs work, which don't, and the UI-first verification workflow. Load alongside capcut-production-executor when applying filters or effects."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [capcut, filter, effect, id-resolution, compatibility]
    related_skills: [capcut-production-executor]
---

# CapCut Filter & Effect ID Resolution (8.9.1 Việt hóa)

## TL;DR

| Source | Status | When |
|--------|--------|------|
| `capcut_effect_map.json` built-in filter IDs (7028463716…) | ❌ **DO NOT WORK** | Confirmed 2026-07-22 by Sếp |
| `capcut-cli enums --filters` output | ❌ **DO NOT WORK** | Same source as above |
| `video-effect-schema.md` 11 effect IDs (7621…) | ✅ **WORKING** | Confirmed 2026-07-22 by Sếp |
| JianYing filter IDs (7127…) | ⚠️ **UNTESTED** | Not verified on 8.9.1 |
| IDs from Sếp's UI-applied test project | ✅ **ONLY RELIABLE SOURCE** | Ground truth |

## The Problem

`capcut-cli enums` dumps CapCut's internal enum table. On CapCut 8.9.1 Việt hóa, the runtime uses DIFFERENT effect_id values than what the enum table reports. This mismatch means:

- Built-in filter `warm` → enum says `7028463716732079118` → CapCut 8.9.1 ignores it
- Video effect `Bokeh ánh sáng` → real ID `7624056975843691783` → works correctly

The root cause appears to be the Việt hóa (Vietnamese localization) build using a different material registry than the international version.

## Correct Resolution Workflow

```
Need filter/effect ID for CapCut 8.9.1 Việt hóa
  → Has Sếp applied this through UI before?
    → YES: extract real ID from that project's draft_content.json
    → NO: BLOCKED — ask Sếp to:
        1. Create a scratch project in CapCut
        2. Apply the desired filter/effect through UI
        3. Save + close CapCut
        4. Tell agent to read draft_content.json
  → NEVER: guess, use capcut_effect_map.json, or capcut-cli enums for filters
```

## Extracting Real IDs from a Test Project

```python
import json
path = r'C:\Users\thang\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\<project>\draft_content.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filters
for mat in data['materials'].get('effects', []):
    print(f"FILTER: effect_id={mat['effect_id']}, name={mat['name']}, platform={mat.get('platform')}")

# Video effects
for mat in data['materials'].get('video_effects', []):
    print(f"EFFECT: effect_id={mat['effect_id']}, name={mat['name']}, platform={mat.get('platform')}")
```

## Known-Working IDs (from Sếp's manual test, 2026-07-18)

### Video Effects (✅ verified 2026-07-22, cache re-checked 2026-08-01)

| effect_id | Name (VN) | Use case | Cache (2026-08-01) |
|-----------|-----------|----------|---------------------|
| 7621232812833738037 | Nhiệt tầm nhìn | Warm/intense scenes | ❌ MISSING — do NOT use |
| 7647134741937851666 | Gợn sóng hồng | Cool/dreamy scenes | ✅ 90 files |
| 7624056975843691783 | Bokeh ánh sáng | Soft/beautiful moments | ✅ 9 files |
| 7621462433843973377 | Thịnh nộ anime | Tension/anger | ✅ 147 files |
| 7595633358164561160 | Ảnh đại diện ánh tím | Mystical/soft | ✅ 195 files |
| 7628092028760395026 | Nhiễu cổ điển | Vintage/gritty | ✅ 38 files |
| 7626431887875018005 | Phơi sáng mạnh | High energy | ✅ 38 files |
| 7644838045182627090 | Đổi màu luân phiên | Psychedelic/shift | ✅ 60 files |
| 7510138014480338193 | Tàng hình | Transitions | ✅ 285 files |
| 7618918113102564629 | Đèn flash camera | Impact/punch | ✅ 38 files |
| 7612674469726883090 | Nhiễu analog | Retro/distorted | ✅ 113 files |

**⚠️ Cache can be cleared between sessions.** Always verify `Cache/effect/<effect_id>/` has files before using any ID — even "verified working" ones. If cache is missing, pick another ID from the table that currently has cache.

### Built-in Filters

❌ **NONE verified working on 8.9.1 Việt hóa as of 2026-07-22.** 

IDs from capcut_effect_map.json that DO NOT work:
- warm: 7028463716732079118
- cool: 7028463716732079119
- bw: 7028463716732079120
- sepia: 7028463716732079121
- vivid: 7028463716732079122
- contrast: 7028463716732079123
- faded: 7028463716732079124
- dramatic: 7028463716732079125
- soft: 7028463716732079126
- vintage: 7028463716732079117
- 7028463716732079127: DOES NOT EXIST (used by old projects — always wrong)

## Effect Material Schema (video_effects — ✅ working)

```json
{
  "id": "<UUID>",
  "effect_id": "<real ID from above table>",
  "resource_id": "<same as effect_id>",
  "name": "<Vietnamese name>",
  "type": "video_effect",
  "sub_type": "0",
  "bind_segment_id": "",
  "transparent_params": "",
  "path": "C:/Users/thang/AppData/Local/CapCut/User Data/Cache/effect/<effect_id>",
  "value": 1.0,
  "category_id": "1111",
  "category_name": "Hiệu ứng video",
  "platform": "all",
  "apply_target_type": 2,
  "source_platform": 1,
  "version": "",
  "item_effect_type": 0,
  "adjust_params": [
    {"name": "effects_adjust_speed", "value": 0.33333333333333, "default_value": 0.33333333333333}
  ],
  "time_range": null,
  "formula_id": "",
  "apply_time_range": null,
  "render_index": 0,
  "track_render_index": 0,
  "common_keyframes": [],
  "request_id": "<UUID>",
  "algorithm_artifact_path": "",
  "disable_effect_faces": [],
  "covering_relation_change": 0,
  "enable_mask": true,
  "effect_mask": [],
  "enable_video_mask_stroke": true,
  "enable_video_mask_shadow": true,
  "aigc_current_artifact_path": "",
  "aigc_current_artifact_cnt": 0
}
```

## Effect Track Schema (✅ working)

```json
{
  "id": "<UUID>",
  "type": "effect",
  "segments": [{
    "id": "<UUID>",
    "material_id": "<video_effect_material_uuid>",
    "target_timerange": {"start": <start_us>, "duration": <dur_us>},
    "source_timerange": {"start": 0, "duration": <dur_us>},
    "render_timerange": {"start": 0, "duration": 0},
    "clip": null,
    "uniform_scale": null,
    "visible": true,
    "...": "standard segment fields"
  }],
  "attribute": 0,
  "is_placeholder": false,
  "template_id": "",
  "template_scene": "default"
}
```

## Effect Beat-Layering Technique (✅ proven 2026-07-22)

When adding effects to a project that already has filter beats:

1. Map each filter color world to an effect type:
   - Warm → bokeh / exposure / thermal
   - Cool → pink_ripple / color_shift
   - Contrast → anime_rage / classic_noise
   - Soft → purple / bokeh
   - Vintage → analog_noise / flash
   - Faded → classic_noise / invisible
   - Dramatic → anime_rage / exposure

2. For each filter track segment, create a matching effect track with the SAME `target_timerange` (same start + duration)

3. Each effect gets its own track (type: "effect") with one segment

4. Effect segments use `clip: null` and `uniform_scale: null` (not objects)

5. Sync all 3 mirrors after adding effects

6. Verify: audio count, text count, and base video unchanged

## Filter Material Schema (materials.effects — ⚠️ IDs unknown)

When real filter IDs are obtained from CapCut UI, the material schema should follow the pattern from `capcut-production-executor` references. Key requirements:
- `value` MUST be a plain number (0.0–1.0), NEVER an object
- `platform` likely `"all"` (not `"capcut"`) per real-capcut-schema
- `type: "filter"`
- Filter segments use `clip: null`, `uniform_scale: null` per real-capcut-schema

## Effect Intensity — "Gia vị" Preference

Sếp prefers effects as **gia vị (seasoning), not full coverage**. Effects should be subtle accents, not overwhelming overlays. Default `value` should be **0.12** (not 0.3+). If Sếp says "phủ full" or effect too strong, reduce to 0.08. This was explicitly requested 2026-08-01: "tao muốn hiệu ứng nó chỉ là gia vị thôi chứ không phải là phủ full."

## Common Pitfalls

1. **Using capcut_effect_map.json filter IDs → silent failure.** Filters appear in timeline but don't render. No error, just no color change.
2. **Setting `clip` and `uniform_scale` as objects on effect/filter segments.** CapCut 8.9.1 expects `null` for these on non-video segments.
3. **Using `platform: "capcut"` instead of `"all"`.** Real CapCut 8.9.1 writes `"all"` for both filters and effects.
4. **Forgetting to stop CapCut before editing.** File locks cause write failures or silent overwrites.
5. **Trusting "verified working" IDs without checking cache.** Cache dirs can be cleared between sessions. On 2026-08-01, Nhiệt tầm nhìn (7621232812833738037) had NO cache despite being in the "verified" list. Always walk the cache dir and count files before using any ID.
