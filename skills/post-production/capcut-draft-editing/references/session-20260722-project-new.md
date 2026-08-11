# Session 2026-07-22 — Project "new" Filter/Effect Fix

## Timeline

1. **Discovered**: 36 filter tracks in project "new", 10 using fake ID 7028463716732079127
2. **First fix**: Replaced 10 bad IDs, rebuilt all 36 segments (added clip/uniform_scale)
3. **Sếp feedback**: "màu và hiệu ứng đều fail" — all filters still broken
4. **Root cause**: All 10 built-in filter IDs (7028463716...) have EMPTY cache dirs
5. **Second fix**: Replaced ALL 36 with JianYing filters
6. **Effects**: Added 36 video effect tracks (verified IDs) — confirmed working
7. **Final**: 84 tracks total, 3 mirrors synced

## Cache Investigation

```
Cache/effect/7028463716732079118/ → EMPTY (warm)
Cache/effect/7028463716732079119/ → EMPTY (cool)
Cache/effect/7028463716732079123/ → EMPTY (contrast)
Cache/effect/7028463716732079126/ → EMPTY (soft)
Cache/effect/7028463716732079127/ → EMPTY (fake ID)

Cache/effect/7624056975843691783/ → HAS FILES (bokeh — verified working)
Cache/effect/7621232812833738037/ → HAS FILES (thermal — verified working)
```

227 total cache dirs. Built-in filter dirs exist but contain zero files.
Video effect dirs contain config.json + algorithm assets.

## What Works

- ✅ 11 video effect IDs from `video-effect-schema.md` — have cache assets
- ⚠️ 5 JianYing filter IDs — cache dirs created, assets may download on open
- ❌ 10 built-in filter IDs from `capcut_effect_map.json` — broken

## JianYing Distribution Applied

| Filter | Count | Beat mapping |
|--------|-------|-------------|
| ABG | 12 | Warm, Contrast-alt, Dramatic-alt |
| VHS III | 10 | Cool-alt, Contrast, Vintage, Dramatic |
| KE1 | 6 | Warm-alt, Soft-alt, fallback |
| KV5D | 5 | Cool, Faded-alt |
| Ditto | 3 | Soft, Vintage-alt, Faded |

## Schema Fixes Applied

- Filter segments: `clip` + `uniform_scale` set to objects (were null)
- Effect segments: `clip` + `uniform_scale` set to null (correct per real-capcut-schema)
- Effect materials: full schema from `video-effect-schema.md` with all 20+ fields
- JianYing materials: `sub_type: "jianying"`, `platform: "jianying"`

## Key Lesson

**Never assume some IDs are correct.** When Sếp says "all fail", audit EVERY material.
Cache dir emptiness is a reliable diagnostic signal.
