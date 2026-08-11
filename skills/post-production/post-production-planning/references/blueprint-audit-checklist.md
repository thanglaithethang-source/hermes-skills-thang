# CapCut Draft Blueprint Compliance Audit

Complete audit procedure for cross-referencing a `draft_content.json` against
a V4 production blueprint. Used after execution to verify the draft implements
the blueprint correctly.

## Time Unit (CRITICAL)

CapCut uses **microseconds** (µs) for all timing fields. Divide by `1e6` for seconds.

```
duration: 1057233333  →  1057.233s  =  17:37.233
source_timerange.start: 0  →  0.000s
source_timerange.duration: 500000  →  0.500s
target_timerange.duration: 160866000  →  160.866s  =  2:40.866
```

Using the wrong divisor (1e9 for ns, 1e3 for ms) produces garbage timestamps.
Discovered by cross-referencing against blueprint SRT timings — this is NOT
documented in CapCut's schema.

## Phase 1: Structure Discovery

```python
# Top-level keys and counts
print('Track count:', len(tracks))
for t in tracks:
    print(f'  type={t["type"]} segments={len(t.get("segments",[]))}')
print('Material buckets:', {k: len(v) for k, v in data['materials'].items()
      if isinstance(v, list) and len(v) > 0})
```

Verify: `materials.effects` has all filters, `materials.video_effects` should be empty.

## Phase 2: Material Reference Resolution

```python
all_ids = set()
for cat in ['audios','effects','texts','videos']:
    for m in data['materials'].get(cat, []):
        all_ids.add(m['id'])
for t in tracks:
    for seg in t.get('segments', []):
        if seg.get('material_id','') not in all_ids:
            # TRUE failure
```

**DO NOT flag `extra_material_refs`.** These point to `speeds`,
`placeholder_infos`, `canvases`, `sound_channel_mappings`, `material_colors`,
`vocal_separations` — internal CapCut bookkeeping. All resolve within CapCut's
namespace.

## Phase 3: BGM Zone Timing

Verify each M1-M7 zone start/end in microseconds against blueprint:

```python
bp_ranges = [
    ('M1', 0,           160866000),
    ('M2', 160866000,   288400000),
    ('M3', 288400000,   419300000),
    ('M4', 419300000,   588800000),
    ('M5', 588800000,   676500000),
    ('M6', 676500000,   782966000),
    ('M7', 782966000,   1059233000),
]
```

Tolerance: ±5ms start, ±200ms end (end varies with audio file length).
**PASS**: start matches to 0ms. **WARN**: end offset 5–200ms. **FAIL**: start >5ms.

## Phase 4: Filter Track / Look Family Coverage

All 36 filter tracks continuous and sequential (no gaps, no overlaps).
Verify 7 look families present: MYTH_PANIC, SCHOLAR_SATIRE, PLINY_APOCALYPSE,
PRACTICAL_WARM, MOON_TIME, MODERN_AD, FINAL_CINEMATIC.

Each filter material: `value` as plain float (not dict), `path` to Cache/effect/.

## Phase 5: SFX Timing & Overlap

Identify all SFX events (audio materials with `SFX_` prefix).
Sort by `target_timerange.start`.

**FAIL**: Multiple SFX at t=0.000 (segments never assigned anchor timestamps).
**FAIL**: SFX overlapping >100ms on same track.
**WARN**: SFX count deviates from blueprint (e.g., 56 vs 51 = +5 extras).

## Phase 6: Text Callout Audit

Count: 34 text materials + 34 text segments expected.

**DO NOT flag** `target_timerange.duration` of ~1820s with `render_timerange={0,0}`.
Normal CapCut 8.9.1 behavior for persistent text overlays.

## Phase 7: Audio Path Integrity

All audio paths absolute Windows paths, files exist on disk.
No CapCut placeholder patterns (`##_draftpath_placeholder_*`).

## Phase 8: Banned Content

- `materials.transitions` empty
- `materials.stickers` empty
- No `spin`, `cube`, `3d_slide`, `presentation` in effect names/IDs

## Phase 9: Voice Track

One audio segment with `material.type = "video_original_sound"`,
covering 0 → full draft duration.

## Phase 10: Count Compliance

| Metric | Expected |
|---|---|
| BGM zones (M[1-7].wav) | 7 |
| SFX events | 51 |
| Text callouts | 34 |
| Look families | 7 |
| Filter tracks | 36 |
| Audio tracks | 10 (voice + 7 BGM + 2 SFX) |

## Common Failures Found in Production

1. **SFX cluster at t=0** — deep-copied from template, anchors never assigned
2. **Filter `value` as dict** — `{"intensity": 0.7}` instead of `0.7`; all filters dropped
3. **Wrong time unit** — treating µs as ns → timestamps off by 1000×
4. **M7 end offset** — audio 100ms shorter than blueprint tail; pad or shift
5. **Text segments overlong** — normal, don't flag without keyframe evidence
