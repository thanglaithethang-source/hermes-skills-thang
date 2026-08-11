# V4 Blueprint Architecture — Production-Grade Output Reference

This is what a V4-level POST_PRODUCTION_PLAN should cover. Based on the
"Ancient Menstruation" V4 blueprint (2026-07-22).

## V3 → V4: What Changed

| V3 problem | V4 solution |
|---|---|
| 409 SRT cues as edit units | 36 story beats + real shot map |
| Motion on ~71% cues | Global cap 45%; per-beat caps |
| 70 arbitrary motion names | 9 fully quantified primitives |
| Cue-start timing for punches | 60 word-level anchors (≥0.86 confidence) |
| Semantic music/SFX placeholders | Real files: sha256, license, source_url mandatory |
| Filter slug guessing | Native CapCut calibration required |
| Proxy render as proof | Native CapCut render required for PRO_FINAL_PASS |
| Two CLI adapters | Single `capcut` binary only |

## Architecture: 3 Phase Gates

### Phase A — INSPECT & LOCK (read-only)
Do NOT edit draft during this phase.

1. Close CapCut, clone draft → `WORK_V4`
2. Run full inspection: doctor/describe/version/diagnose/info/tracks/segments/materials/timeline/lint
3. Resolve source mode (multi-segment vs flattened)
4. Generate word-level transcript from actual audio
5. Detect scenes if flattened source
6. Extract contact sheets at 20%/50%/80% per shot
7. AI vision audit → SHOT_MAP.jsonl
8. Map 36 story beats to real shots
9. Resolve ALL 60 word anchors with real transcript (confidence ≥0.86)
10. Bind ALL music/SFX to local files with sha256 + license
11. Query + lock exact CapCut enum slugs
12. Native-calibrate text and color samples
13. Generate EXECUTION_PLAN_LOCKED.jsonl
14. Run validator → only proceed when READY_TO_EXECUTE=true

### Phase B — EXECUTE
Snapshot before each pass. Pass order:
1. P1 MOTION
2. P2 TEXT
3. P3 COLOR/EFFECT
4. P4 MUSIC
5. P5 SFX/FOLEY
6. P6 MIX/FINALIZE

After each pass: lint + diff + proxy render. Critical Fail → restore.

### Phase C — NATIVE RENDER & QA
1. Open WORK_V4 in CapCut app
2. Export native MP4
3. Audit: filter, effect, text, transition, frame accuracy, loudness, dropout, black frame, desync
4. Only native render gets PRO_FINAL_PASS status

## Motion Budget System

Mandatory limits per beat:
- Global: artificial motion ≤45% of all shots
- Never >2 artificial-motion shots in a row
- Never repeat same primitive 3 shots in a row (except STATIC)
- Native motion score >0.35 → force STATIC_HOLD
- Sensitive beats (B22-B23, B32, B35-B36) have even lower caps

## 9 Locked Motion Primitives

1. STATIC_HOLD — preserve source motion
2. PUSH_SLOW — scale 1.0→1.025, min 2200ms
3. PUSH_MEDIUM — scale 1.0→1.045, min 1300ms
4. PULL_SLOW — scale 1.03→1.0, min 2200ms
5. PAN_LR — position -0.02→+0.02, min 2600ms
6. PAN_RL — position +0.02→-0.02, min 2600ms
7. PUNCH_IN_HOLD — scale 1.0→1.065, word-anchored, 700ms+
8. MICRO_SHAKE — 110ms, position+rotation jitter, explicit allowlist only
9. OPACITY_PULSE — alpha 1.0→0.84→1.0, 90ms

## Word Anchor Resolution (Critical)

- 60 anchors, all must resolve from actual word transcript
- Match confidence ≥0.86
- Cue hint is search window only, NOT final timing
- Transient must land ±2 frames from resolved word start
- Punches at: "Bro. That is not science", "Trust me, bro", "My period product? Sheep", final line — require silence gap after

## Asset Locking

Execution plan must NEVER contain semantic placeholders.

### Music required fields
file_path, sha256, source_url, license, measured_bpm, first_downbeat_ms, loop_in_ms, loop_out_ms, approved_gain_db

### SFX required fields
file_path, sha256, source_url, license, trim_in_ms, trim_out_ms, gain_db, pan, fade_out_ms

No suitable asset → skip that SFX. Never substitute with random sounds.

## Text Callouts

- Hard cap: 34 events total
- Two style families: SERIF_HISTORY, SANS_PUNCH
- Max 2 lines, 5% safe area, no bounce/typewriter
- Each requires native template calibration

## Color/Effect

- 7 look families: MYTH_PANIC, SCHOLAR_SATIRE, PLINY_APOCALYPSE, PRACTICAL_WARM, MOON_TIME, MODERN_AD, FINAL_CINEMATIC
- Max strength 0.16–0.28 depending on family
- Must query exact slug, create calibration sample, native-render, then lock
- No filter if native calibration unavailable
- One dominant effect max at any time
- Opacity glitch ≤90ms, micro-shake ≤110ms, flash ≤2 frames
- BANNED: spin, cube, 3D slide, presentation transitions

## Audio Standards

- Voice higher than music by 12–21dB
- Duck only at locked anchors
- Never cut mid-musical-phrase
- Max 1 Hero SFX per anchor
- No meme SFX
- Integrated -14 LUFS, True peak ≤ -1 dBTP, mono-compatible
- Music tail ~2s after final line

## Cultural Safety (Moon Lodge / Indigenous content)

- No generic headdress
- No tipi without verification
- No fantasy shaman look
- No invented ritual
- No generic "tribal" montage
- Fallback: neutral details — fire, rest, hands, food, night, community

## QA Gates

### Critical (any = fail)
- draft/media errors
- voice desync
- unresolved anchor/asset/slug
- target operation doesn't exist
- timeline drift >100ms
- clipping
- factually wrong text
- cultural misrepresentation
- no native render claiming final

### Major
- reset at cue instead of shot boundary
- >1 primary motion per shot
- motion budget exceeded
- crop removing face/hands/material/embedded text
- punchline off >2 frames
- unapproved filter
- music phrase cut
- voice masking
- text outside safe area

### Pass criteria
- Critical=0, Major=0, Minor≤5
- 36/36 beats covered, 60/60 anchors resolved
- Every shot has exactly one motion decision (including STATIC)
- Asset registry locked, slugs validated
- Native CapCut render audited

## CLI Tool: `capcut`

The V4 blueprint uses the `capcut` binary from `renezander030/capcut-cli` (GitHub),
NOT the npm `capcut-cli` package. These may be different tools. Key commands:
`doctor`, `describe`, `version`, `diagnose`, `info`, `tracks`, `segments`,
`materials`, `timeline`, `lint`, `batch`, `export-srt`, `caption`,
`detect-scenes`, `diff`, `render`, `restore`, `make-preset`.

## Honest Limitations

1. **Native render** — CLI cannot render natively. Requires opening CapCut GUI.
2. **Native calibration** — filter/effect appearance cannot be verified through CLI proxy.
3. **Enum slugs** — depends on whether `capcut` CLI exposes filter/effect enumeration.
