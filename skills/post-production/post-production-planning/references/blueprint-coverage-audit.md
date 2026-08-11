# Blueprint Coverage Audit — Draft vs. V4 Blueprint

How to verify a CapCut `draft_content.json` against a V4 post-production
blueprint. This is the QA step between Phase B (EXECUTE) and Phase C
(NATIVE RENDER) — confirms every beat, anchor, callout, look, and zone
is structurally present before opening CapCut.

## When to Run

After Phase B execution completes but BEFORE opening CapCut for native
render. Run this from Python via terminal — it reads the draft JSON
directly, no CapCut CLI needed.

## Prerequisites

- `draft_content.json` path (typically under `CapCut/User Data/Projects/com.lveditor.draft/<project>/`)
- Blueprint directory with: `01_STORY_BEATS_36.json`, `02_WORD_ANCHORS_60_UNRESOLVED.json`, `04_TEXT_CALLOUTS_34.json`, `07_COLOR_LOOK_POLICY.json`, `00_MASTER_BLUEPRINT_V4.md`

## Audit Steps

### 1. Track type inventory

```python
import json
with open(draft_path, 'r', encoding='utf-8') as f:
    d = json.load(f)

tracks = d['tracks']
for i, t in enumerate(tracks):
    print(f"Track[{i}]: type={t['type']}, segments={len(t.get('segments',[]))}")
```

Expected: 1 video, 8-10 audio (1 voice + 7 BGM zones + 1-2 SFX), 1 text,
36 filter tracks. Motion/animation tracks must be present if Phase B P1
has been executed.

### 2. Filter → Story Beat mapping

Each beat in `01_STORY_BEATS_36.json` has `start_us`/`end_us`. Compare
against each filter track segment's `target_timerange.start` and
`target_timerange.duration`:

```python
effects = d['materials']['effects']
beats = [load beats JSON...]

for i, (eff, beat) in enumerate(zip(effects, sorted_beats)):
    eff_name = eff['name']        # look family
    eff_value = float(eff['value'])  # strength
    eff_dur = int(eff['duration'])   # should match beat (end-start)
    # compare against beat definition
```

Verify: exact family name match, strength ≤ blueprint max, duration
within ±10ms of beat duration from JSON `start_us`/`end_us`.

### 3. Text callout verification

Text content lives in `d['materials']['texts']`, not in track segments.
Each text material has: `id`, `content`, `style`, `font_size`, `color`.

```python
texts = d['materials']['texts']
for i, t in enumerate(texts):
    print(f"[{i}] \"{t['content']}\" style={t.get('style','?')}")
```

Compare all 34 callouts from `04_TEXT_CALLOUTS_34.json` against content
strings. Use regex search across the raw JSON to catch any that python
dict access might miss. Each callout has `callout_id` (maps to anchor)
and `style_family` (SERIF_HISTORY or SANS_PUNCH).

### 4. SFX inventory vs anchor requirements

SFX live in `d['materials']['audios']` with names starting with "SFX_".
Blueprint anchors have `sfx_slot` field — some are "SFX_NONE".

```python
audios = d['materials']['audios']
sfx_names = [a['name'] for a in audios if a['name'].startswith('SFX_')]
```

Count anchors needing SFX: total 60 anchors minus those with SFX_NONE
(A06, A10, A14, A46 = 4) = 56 SFX slots needed.

Check placement: SFX segments on the timeline (audio tracks). A segment
at `target_timerange.start == 0` is an unplaced placeholder.

Duplicate SFX names are intentional — the blueprint uses the same SFX
material for multiple anchors (e.g., SFX_STAMP_DRY used by A07, A21, A47).

### 5. BGM zone boundaries

BGM tracks are audio tracks with material names like M1, M2, etc.
Each zone should transition at exact beat boundaries:

```python
bgm_tracks = [t for t in tracks if t['type'] == 'audio']
# Skip track[0] (voice) and SFX tracks; check tracks 2-8
for t in bgm_tracks[1:8]:
    seg = t['segments'][0]
    start = seg['target_timerange']['start']
    end = start + seg['target_timerange']['duration']
    print(f"BGM {start/1e6:.1f}s → {end/1e6:.1f}s")
```

Zone boundaries should match beat transitions at:
- Zone 1→2: B07 end / B08 start
- Zone 2→3: B12 end / B13 start
- Zone 3→4: B16 end / B17 start
- Zone 4→5: B21 end / B22 start
- Zone 5→6: B23 end / B24 start
- Zone 6→7: B26 end / B27 start

Final BGM tail should extend ~2s past the last word (17:37.133 → ~17:39.133).

### 6. Motion track check

Motion/animation tracks are a separate track type. If Phase B P1 has
been executed, expect track(s) with `type` in ("animation", "motion",
"transition", "effect"). Zero motion tracks = Phase B P1 not executed.

### 7. Report compilation

Output a PASS/WARN/FAIL matrix:

| Category | Check |
|---|---|
| Story Beats | 36 filter tracks at correct timing with correct look+strength |
| Word Anchors | 56 SFX materials, 49-56 placed, 0-7 unplaced |
| Text Callouts | 34/34 content present, no extra 35th |
| Look Families | 7 families with correct strength values |
| BGM Zones | 7 zones at correct boundaries, 2s tail |
| Motion | Tracks present (PASS) or absent (FAIL) |
| Hard Caps | text≤34, SFX≤1/anchor |
| Cultural Safety | B22-B23 use MOON_TIME at ≤0.18 |

## Common Pitfalls

- **Text content not in segment.content**: CapCut stores text in
  `materials.texts[]`, not as a segment field. The segment's
  `material_id` links to the material. Don't look at `s['content']`.

- **Filter materials in `materials.effects`**: This is the "effects"
  bucket inside materials, but it contains FILTERS (confusingly).
  Video effects live in `materials.video_effects`.

- **Filter value is a float, not dict**: `"value": "0.28"` (string
  in JSON, parse as float). Never `{"intensity": 0.28}`.

- **SFX at start=0 are placeholders**: These are material slots that
  exist but haven't been positioned on the timeline yet. Count them
  separately from placed SFX.

- **Don't open CapCut during audit**: CapCut locks the draft files.
  Run the audit with CapCut closed.
