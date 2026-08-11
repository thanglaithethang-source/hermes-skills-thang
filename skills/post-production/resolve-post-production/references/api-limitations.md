# MCP API Limitations — Verified Against Resolve 19.0.0b.50

Last verified: 2026-07-11 | MCP server v2.60.0 | Python 3.10

## Transform / Motion

| Feature | Status | Detail |
|---------|--------|--------|
| `set_transform` | ✓ Working | Sets ZoomX, ZoomY, Pan, Tilt, Rotation, etc. on timeline item |
| `get_transform` | ✓ Working | Reads back current transform values |
| `add_keyframe` | ✗ BROKEN | Returns `'NoneType' object is not callable` — Resolve API `AddKeyframe` method unavailable via scripting on transform properties |
| Keyframe animation | ✗ NOT POSSIBLE | Cannot create zoom-in/out, pan, punch-in with keyframes via MCP. Fallback: UI automation or manual |
| Static zoom | ✓ Possible | Use `set_transform` to set a single zoom value for entire clip (e.g., 1.0→1.15 globally) |

## Render

| Feature | Status | Detail |
|---------|--------|--------|
| `prepare_render_job` | ✓ Working | Creates job + sets target_dir, custom_name. Requires `require_temp_target=False` for non-temp paths |
| `add_job` | ⚠ Flaky | May fail without prior Deliver page switch |
| `set_settings` | ✓ Working | Sets MarkIn, MarkOut, TargetDir, OutputFilename directly |
| `set_format_and_codec` | ✗ NOT WORKING | Always fails — format stays at default (MOV). Cannot switch to MP4 via API |
| `safe_set_render_settings` | ⚠ Readback issue | `applied: null` for all settings — settings may apply but readback fails |
| `start` | ✓ Working | Starts render job(s). Multiple jobs render sequentially |
| `get_job_status` | ✓ Working | Returns `Đang kết xuất` / `Hoàn thành` with percentage |
| `delete_job` / `delete_all_jobs` | ✓ Working | Clean up before creating new jobs |
| Render format | MOV only | Currently limited to QuickTime MOV + H.264 due to format/codec API failure |

## Workflow: Render a clip range

```python
# 1. Clean up old jobs
render(action='delete_all_jobs')

# 2. Create job with settings
render(action='prepare_render_job',
    target_dir='C:/path/to/output/',
    custom_name='my_render',
    require_temp_target=False,
    settings={'MarkIn': 86400, 'MarkOut': 87119})

# 3. Start render
render(action='start')

# 4. Poll until done
render(action='get_job_status')
```

## Color

| Feature | Status | Detail |
|---------|--------|--------|
| `probe_grade_item` | ✓ Working | Full grade state inspection |
| `set_cdl` | ✓ Working | Slope/Offset/Power/Saturation per node. Format: `{NodeIndex: 1, Slope: {R,G,B}, Offset: {R,G,B}, Power: {R,G,B}, Saturation: N}` |
| `probe_node_graph` | ✓ Working | Node graph structure |
| `grade_version_snapshot` | ✓ Working | Version management |
| `get_color_info` | ✗ NOT AN ACTION | Use `probe_grade_item` instead |

## SFX / Media Pool

| Feature | Status | Detail |
|---------|--------|--------|
| `import_to_pool` (folder) | ⚠ Returns 0 | Importing folder path via `media_storage` may return 0. Use `media_pool.import_media` with individual file paths instead |
| `import_media` (single file) | ✓ Working | Import individual files reliably |
| `append_to_timeline` positioned | ✓ Working | Positioned mode: `{clip_id, start_frame, end_frame, record_frame, track_index, media_type}` |
| `record_frame_mode='absolute'` | ✗ DO NOT USE | Causes double-offset. `record_frame` is already relative to timeline start by default. Using absolute mode adds 86400 twice, pushing SFX far past video end. **Always use default relative mode.** |
| `add_track` | ✓ Working | Add audio/video tracks before placing SFX |

### SFX record_frame calculation

```python
# CORRECT — relative to timeline start (default mode)
record_frame = int(seconds * fps)  # e.g. 30 * 24 = 720 for 00:30 @24fps

# WRONG — do NOT use record_frame_mode='absolute'
# It adds the timeline start offset (86400) on top of your already-calculated frame
```

### SFX clip_infos format (positioned mode)

```python
clip_infos = [{
    'clip_id': '<full-uuid>',        # or media_pool_item_id
    'start_frame': 0,                # source in-point (usually 0)
    'end_frame': duration_frames,    # source out-point (e.g. 11 for 12-frame clip)
    'record_frame': target_frame,    # relative to timeline start
    'track_index': 2,                # 1-based audio track
    'media_type': 2                  # 1=video, 2=audio
}]
```

## Node Graph / OFX

| Feature | Status | Detail |
|---------|--------|--------|
| `AddSerialPort()` | ✗ NOT IN API | Resolve 19.0.0b.50 public API không expose method này. Không thể thêm serial node qua scripting. |
| `AddNode()` / graph mutation | ✗ NOT IN API | Node graph chỉ có read-only methods (GetNumNodes, GetLUT, SetLUT, GetNodeLabel, SetNodeEnabled). Không có API để thêm/xóa node. |
| OFX Plugin (Glow, Grain, Vignette) | ✗ NOT IN API | Không có API để thêm ResolveFX hoặc OFX plugins qua script. Phải làm manual trên Color page. |
| UI automation Alt+S | ⚠ Unreliable | Gửi Alt+S qua computer_use để thêm serial node không ổn định, dễ bị từ chối hoặc không hiệu quả. |
| Workaround: Single-node CDL | ✓ Viable | Gộp tất cả grade (cinematic look + contrast + saturation) vào 1 node CDL duy nhất — API set_cdl hoạt động tốt. |

## Key Takeaways

1. **No keyframe animation possible** via MCP — transforms are static-only. For dynamic zoom/pan, use Resolve UI or find alternative API path.
2. **No node graph mutation** — Cannot add/remove nodes or OFX plugins via scripting in Resolve 19.0.0b.50. Gộp tất cả grade vào 1 node CDL.
3. **Render is MOV-only** — `set_format_and_codec` API is broken. Accept MOV output; convert to MP4 via ffmpeg post-render if needed.
4. **Always verify** with `server.log` — `hermes mcp test` lies about connectivity.
5. **Python 3.10 is mandatory** on Windows — 3.11+ crashes on fusionscript import.
6. **Local SFX library > API hunting** — Sếp has a complete local SFX+BGM library. Đừng mất thời gian tìm API key Freesound/Pixabay trên GitHub; kiểm tra local library trước. Xem `references/local-sfx-library.md`.
7. **SFX record_frame is RELATIVE** — Never use `record_frame_mode='absolute'`. It double-offsets by timeline start (86400), pushing SFX past video end.
8. **Adjustment clips on V3 are NOT scriptable** — `insert_generator` always goes to V1 and ripples the timeline. `duplicate_clips`/`move_clips` fail for generators (GetTrackTypeAndIndex returns None). Use Color page keyframed grades or manual UI for section-specific color.
9. **Audio volume API is broken** — `set_audio` Volume returns false, `SetTrackProperty('audio', 1, 'Volume', -1.0)` returns NoneType error, `GetProperty('Volume')` returns None. Voice processing must be done manually on Fairlight page.
10. **Fusion text overlays fully work** — `add_comp` → `add_tool` (TextPlus + Merge) → `set_text_plus` → `connect` pipeline confirmed. Use for text callouts, labels, formulas.

## Fusion (MCP)

| Feature | Status | Detail |
|---------|--------|--------|
| `timeline_item_fusion.add_comp` | ✓ Working | Creates Fusion composition on timeline item |
| `fusion_comp.add_tool` | ✓ Working | TextPlus, Merge, Background, other Fusion tools |
| `fusion_comp.set_text_plus` | ✓ Working | Set StyledText, Style, Size, Center |
| `fusion_comp.set_input` | ✓ Working | Set individual tool inputs |
| `fusion_comp.connect` | ✓ Working | Wire tools together: `{source: 'Tool.Output', target: 'Tool.Input'}` |
| `fusion_comp.disconnect` | ✓ Working | Remove connection from tool input |
| `fusion_comp.probe` | ✓ Working | Full node graph inspection |

### Fusion text overlay pipeline
```python
# 1. Create comp on clip
timeline_item_fusion('add_comp', track_type='video', track_index=1, item_index=0)

# 2. Add TextPlus + Merge
fusion_comp('add_tool', tool_type='TextPlus', name='MY_TEXT')
fusion_comp('add_tool', tool_type='Merge', name='MERGE_MY')

# 3. Set text content
fusion_comp('set_text_plus', text='HELLO WORLD', style='Bold', size=0.06, center=True)

# 4. Wire pipeline: MediaIn1 → Merge(bg) + Text(fg) → MediaOut1
fusion_comp('connect', source='MediaIn1.Output', target='MERGE_MY.Background')
fusion_comp('connect', source='MY_TEXT.Output', target='MERGE_MY.Foreground')
fusion_comp('connect', source='MERGE_MY.Output', target='MediaOut1.Input')
```

## Color — Adjustment Clips / V3

| Feature | Status | Detail |
|---------|--------|--------|
| `insert_generator('Adjustment Clip')` | ⚠ V1 ONLY | Always inserts on lowest-numbered video track (V1). RIPPLES the timeline, splitting the main clip. Does NOT accept track parameter. |
| `duplicate_clips` on generator | ✗ BROKEN | `GetTrackTypeAndIndex` returns None for Adjustment Clips — duplicate/move fail |
| `move_clips` on generator | ✗ BROKEN | Same root cause — cannot re-track generators via scripting |
| Section-specific color via V3 | ✗ NOT SCRIPTABLE | Must use Color page keyframes or manual UI to apply per-section grades on single clip |
| Workaround: Global CDL | ✓ Viable | Apply one CDL to entire clip, or split clip into sections beforehand |
| Workaround: Color page keyframes | ⚠ Manual | Add dynamic keyframes on Color page for exposure/contrast changes over time |

## Audio

| Feature | Status | Detail |
|---------|--------|--------|
| `timeline_item.set_audio` Volume | ✗ BROKEN | Returns `Volume: false` — Resolve scripting API does not support setting audio volume on timeline items |
| `timeline.SetTrackProperty('audio', 1, 'Volume', -1.0)` | ✗ BROKEN | Returns `'NoneType' object is not callable` |
| `GetProperty('Volume')` on timeline item | ✗ Returns None | Cannot read audio volume via scripting |

## Timeline Operations — Generators

| Feature | Status | Detail |
|---------|--------|--------|
| `insert_generator` on specific track | ✗ NOT POSSIBLE | Always goes to V1 — no track parameter exists in Resolve API |
| Generator clip re-tracking | ✗ BROKEN | `GetTrackTypeAndIndex` returns None for all generators (Adjustment Clip, Fusion Generator, Title, etc.) → `duplicate_clips`/`move_clips` fail |
| Workaround: Insert at timeline end | ⚠ Partial | Insert generator past video end (frame > 113778), then it won't ripple main clip. But still can't move to V3. |
