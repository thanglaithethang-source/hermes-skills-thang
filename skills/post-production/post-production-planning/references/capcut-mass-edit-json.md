# Mass Edit via Direct JSON Manipulation (CapCut)

When the `run_job.py` pipeline is too rigid for complex blueprint-driven edits
(50+ SFX events, 7 BGM zones, 34 text callouts, 36 filter tracks), directly
edit `draft_content.json` with a single comprehensive Python script.

## Prerequisites

1. Stop CapCut: `Get-Process CapCut -ErrorAction SilentlyContinue | Stop-Process -Force`
2. Backup: copy `draft_content.json` to `backups/<timestamp>/`
3. Know timeline ID from `Timelines/<id>/` directory

## Timing Units (CRITICAL)

CapCut `target_timerange` uses **microseconds** (not nanoseconds):
- 1 second = 1,000,000
- 17:37.233 video → duration = 1,057,233,000

```python
def tc_to_us(tc):  # "00:02:40.866" → 160866000
    parts = tc.strip().split(':')
    return int(int(parts[0])*3600_000_000 + int(parts[1])*60_000_000 + float(parts[2])*1_000_000)
```

## Audio Materials (BGM/SFX)

Deep-copy from existing voice audio material, override:
```python
mat = copy.deepcopy(voice_template)
mat['id'] = new_uuid()
mat['type'] = 'extract_music'        # NEVER 'video_original_sound'
mat['category_name'] = 'local'
mat['local_material_id'] = ''
mat['path'] = absolute_windows_path   # 'C:/Users/.../assets/sfx/HIT.wav'
mat['duration'] = duration_us         # microseconds
```

Audio segment:
```python
seg = {
    'target_timerange': {'start': start_us, 'duration': dur_us},
    'source_timerange': {'start': 0, 'duration': min(dur_us, src_dur_us)},
    'render_timerange': {'start': 0, 'duration': 0},
    'volume': 10 ** (gain_db / 20),
    'last_nonzero_volume': 10 ** (gain_db / 20),
    'is_loop': True,   # BGM=True, SFX=False
    'clip': None, 'uniform_scale': None,
    'common_keyframes': [], 'visible': True,
}
```

## Filter Materials

```python
filter_mat = {
    'type': 'filter',
    'effect_id': '7028463716732079118',  # built-in warm
    'path': f'C:/Users/{user}/AppData/Local/CapCut/User Data/Cache/effect/{eid}',
    'value': 0.28,                       # PLAIN FLOAT — never dict!
}
# Cache dirs MUST exist:
os.makedirs(filter_mat['path'], exist_ok=True)
```

Built-in filter IDs (verified working, CapCut 8.9.1):
- warm: 7028463716732079118
- cool: 7028463716732079119
- contrast: 7028463716732079123
- soft: 7028463716732079126
- natural: 7028463716732079127

## SFX Track Strategy

Sếp prefers 2-3 shared audio tracks (not one per event):
- `SFX_PRIMARY` + `SFX_SECONDARY`, alternating
- Sort segments by `target_timerange.start`
- Set `render_index` sequentially

## Text Callout Segments

Fade in/out via `common_keyframes`:
```python
'common_keyframes': [{
    'type': 'text_opacity',
    'keyframe_list': [
        {'key': 'opacity', 'left_value': 0.0, 'right_value': 1.0,
         'left_time_offset': 0, 'right_time_offset': intro_ms * 1_000_000},
        {'key': 'opacity', 'left_value': 1.0, 'right_value': 0.0,
         'left_time_offset': (intro_ms + hold_ms) * 1_000_000,
         'right_time_offset': total_ms * 1_000_000},
    ]
}]
```

## Mirror Sync

After edit, copy to all 3 mirrors and verify SHA256 match:
```python
shutil.copy(draft_path, template_2_tmp)
shutil.copy(draft_path, timelines_content)
```

## Verify

```bash
python audit_capcut_draft.py --project <project_dir>
```
`missing_referenced_paths` for filter cache dirs is expected (CapCut downloads
filter binaries on first use). They are non-blocking if directories exist.
