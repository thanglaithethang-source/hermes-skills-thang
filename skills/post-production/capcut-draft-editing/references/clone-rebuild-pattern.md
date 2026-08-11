# Clone-Rebuild Pattern — CapCut Project Recovery

When a CapCut project is lost (deleted after force-stop, corrupted, or needs a
clean start), this pattern builds a valid project from a known-good template.

## When to Use

- Project files vanished from disk after CapCut was force-stopped
- Need a fresh project with no legacy content
- Creating a draft_content.json from scratch failed (schema too complex)

## Step-by-Step (2026-07-23, verified working)

### 1. Clone a valid existing project

```python
import shutil
TEMPLATE = "C:/Users/thang/AppData/Local/CapCut/User Data/Projects/com.liveditor.draft/TRIBE_CANCELLED_V12_FINAL_LOCK"
NEW_PROJ = "C:/Users/thang/AppData/Local/CapCut/User Data/Projects/com.liveditor.draft/MY_NEW_PROJECT"
if os.path.exists(NEW_PROJ):
    shutil.rmtree(NEW_PROJ)
shutil.copytree(TEMPLATE, NEW_PROJ)
# Remove old timeline mirrors to avoid stale references
tl_dir = NEW_PROJ + "/Timelines"
for d in os.listdir(tl_dir):
    shutil.rmtree(tl_dir + "/" + d)
```

### 2. Clean the draft

```python
import json
with open(NEW_PROJ + "/draft_content.json") as f:
    draft = json.load(f)

draft["tracks"] = []
for key in ["videos","audios","effects","video_effects","beats","speeds","transitions","texts"]:
    if key in draft["materials"]:
        draft["materials"][key] = []
draft["name"] = "New Project Name"
draft["id"] = str(uuid.uuid4()).upper()
```

### 3. Add content

- **Video material**: `type: "video"`, path to MP4, duration in nanoseconds
- **Audio materials** (SFX/BGM): `type: "extract_music"`, `category_name: "local"`, absolute WAV path
- **Voiceover**: same as audio but with full duration

### 4. Create tracks with segments

Segment template key fields:
```python
seg = {
    "id": uid(), "material_id": mat_id,
    "target_timerange": {"start": start_ns, "duration": dur_ns},
    "source_timerange": {"start": 0, "duration": dur_ns},
    "render_timerange": {"start": 0, "duration": 0},
    "volume": vol, "last_nonzero_volume": vol,
    "visible": True,
    "clip": {"scale":{"x":1,"y":1}, "rotation":0, "transform":{"x":0,"y":0}, ...},
    "uniform_scale": {"on": True, "value": 1.0},
    "caption_info": {"capcut_draft_caption_info": None},
    "cartoon": {"style": "none"},
    # ... 40+ other fields (copy from a real segment)
}
```

Track structure:
- Track 0: `type: "video"` — 1 segment covering full duration
- Track 1: `type: "audio"` — voiceover (1 segment, full duration)
- Track 2: `type: "audio"` — BGM zones
- Track 3: `type: "audio"` — SFX primary (even-indexed beats)
- Track 4: `type: "audio"` — SFX secondary (odd-indexed beats)

### 5. Sync mirrors

```python
shutil.copy2(draft_path, NEW_PROJ + "/template-2.tmp")
tl_id = str(uuid.uuid4()).upper()
tl_path = NEW_PROJ + "/Timelines/" + tl_id
os.makedirs(tl_path)
shutil.copy2(draft_path, tl_path + "/draft_content.json")
```

Verify SHA256:
```python
h1 = sha256_file(draft_path)
h2 = sha256_file(NEW_PROJ + "/template-2.tmp")
h3 = sha256_file(tl_path + "/draft_content.json")
assert h1 == h2 == h3
```

### 6. Update draft_meta_info.json

Must include `draft_materials` array referencing the video material UUID and file path.

## Key Time Unit

CapCut uses **nanoseconds** internally. Convert SRT timestamps:
```python
# "00:01:23,456" → nanoseconds
h, m, s, ms = 0, 1, 23, 456
ns = ((h*3600 + m*60 + s) * 1000 + ms) * 1_000_000
```

## Pitfalls

- Never create draft_content.json from scratch — schema has 60+ interdependent material categories
- Always nuke old Timelines/ subdirectories to avoid stale mirror references
- Audio path must use forward slashes: `C:/Users/...` not `C:\Users\...`
- BGM volume ~0.25, SFX volume ~0.75 to avoid clipping with voiceover
- draft_meta_info.json must reference the same video material UUID as draft_content.json
