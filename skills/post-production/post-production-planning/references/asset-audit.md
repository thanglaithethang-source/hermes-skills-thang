# Asset Audit Procedure — Audio (SFX + BGM)

Use this when V4 assets need auditing before execution. Covers file existence, size, SHA256 integrity, SHA256 uniqueness, and blueprint slot coverage.

## When to Run

- Before Phase B (EXECUTE) in V4 workflow
- After any asset download/generation batch
- When blueprint status says UNBOUND but registry says BOUND_SYNTHETIC (status inconsistency)

## Inputs Required

Three files must exist:
1. `runtime/ASSET_REGISTRY.json` — registry with `sfx[]` and `bgm[]` entries (file_path, sha256, status, license, etc.)
2. `06_SFX_BINDING_REQUIRED.json` — blueprint SFX slots with `slots[].slot` names
3. `05_MUSIC_BINDING_REQUIRED.json` — blueprint BGM slots with `slots[].slot` names

## Audit Checks

### 1. File Existence & Type
```python
sfx_files = sorted([f for f in os.listdir(sfx_dir)])
bgm_files = sorted([f for f in os.listdir(bgm_dir)])
```
- Count SFX .wav files on disk vs registry entries
- Count BGM .wav files on disk vs registry entries
- Flag any non-.wav files

### 2. File Sizes
- SFX: all should be > 500 bytes (flag if any are tiny stubs)
- BGM: all should be > 10000 bytes
- **Warn if all SFX are identical size** — signals template-generated clones rather than distinct sounds

### 3. SHA256 Integrity (Registry vs Disk)

**CRITICAL**: Do NOT use `subprocess` with `sha256sum` on Windows git-bash — it adds a `\` prefix artifact to the hash. Use Python `hashlib` directly:

```python
import hashlib

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

for entry in reg['sfx'] + reg['bgm']:
    fname = os.path.basename(entry['file_path'])
    actual = sha256_file(os.path.join(asset_dir, fname))
    if actual != entry['sha256']:
        # FAIL — registry hash doesn't match disk
```

All 58 hashes must match byte-for-byte. Any mismatch = corruption or stale registry.

### 4. SHA256 Uniqueness (Duplicate Detection)

This is the most revealing check. Count unique SHA256 hashes among the registry entries:

```python
from collections import Counter
sfx_sha_counter = Counter(e['sha256'] for e in reg['sfx'])
unique_sha = len(sfx_sha_counter)
print(f"Unique SHA256 among {len(reg['sfx'])} SFX: {unique_sha}")
```

**This often reveals that synthetic SFX generation produced identical copies.** In the Ancient Menstruation project: 31 of 51 SFX (61%) shared ONE hash — only 7 unique sounds across 51 files. This means 31 files are byte-identical duplicates, NOT distinct sound effects.

- SFX: target ≥ 30 unique hashes for a 51-file set (≥60% variety)
- BGM: all 7 should be unique (different moods/zones)

### 5. Blueprint Slot Coverage

Cross-reference blueprint slots with registry asset IDs:

```python
bp_sfx_slots = {s['slot'] for s in bp_sfx['slots']}
reg_sfx_ids = {e['asset_id'] for e in reg['sfx']}

missing_in_reg = bp_sfx_slots - reg_sfx_ids   # blueprint requires, registry lacks
extra_in_reg = reg_sfx_ids - bp_sfx_slots      # registry has, blueprint doesn't need

assert len(missing_in_reg) == 0, f"SFX slots without assets: {missing_in_reg}"
assert len(extra_in_reg) == 0, f"SFX assets without slots: {extra_in_reg}"
```

Same for BGM. Should be 1:1. Any mismatch = plan/registry out of sync.

### 6. License & Source Fields
- Every entry must have `license` populated (not empty/null)
- Every entry must have `source_url` — flag if `"synthetic"` (means Freesound/real source failed)
- All-synthetic is a red flag for audio quality

### 7. Blueprint ↔ Registry Status Consistency
- Blueprint says `UNBOUND` → Registry should say something compatible (not `BOUND_SYNTHETIC`)
- If blueprint slots are `UNBOUND` but registry entries are `BOUND_SYNTHETIC`, the two are out of sync — resolve before execution

## Python Audit Script Pattern

```python
import json, os, hashlib
from collections import Counter

base = "<project_dir>"
reg = json.load(open(os.path.join(base, "runtime/ASSET_REGISTRY.json")))
bp_sfx = json.load(open(os.path.join(base, "blueprint/06_SFX_BINDING_REQUIRED.json")))
bp_bgm = json.load(open(os.path.join(base, "blueprint/05_MUSIC_BINDING_REQUIRED.json")))

# 1. Existence
sfx_on_disk = len([f for f in os.listdir(os.path.join(base, "assets/sfx")) if f.endswith('.wav')])
bgm_on_disk = len([f for f in os.listdir(os.path.join(base, "assets/bgm")) if f.endswith('.wav')])
assert sfx_on_disk == len(reg['sfx']), f"SFX count mismatch: {sfx_on_disk} vs {len(reg['sfx'])}"
assert bgm_on_disk == len(reg['bgm']), f"BGM count mismatch: {bgm_on_disk} vs {len(reg['bgm'])}"

# 2. SHA256 integrity (hashlib, NOT subprocess)
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

for cat, dir_name in [('sfx', 'sfx'), ('bgm', 'bgm')]:
    for entry in reg[cat]:
        actual = sha256_file(os.path.join(base, 'assets', dir_name, os.path.basename(entry['file_path'])))
        assert actual == entry['sha256'], f"{entry['asset_id']}: hash mismatch"

# 3. SHA256 uniqueness
sha_counts = Counter(e['sha256'] for e in reg['sfx'])
unique_count = len(sha_counts)
pct_most = sha_counts.most_common(1)[0][1] / len(reg['sfx']) * 100
print(f"SFX unique hashes: {unique_count}/{len(reg['sfx'])} — top hash: {pct_most:.0f}%")

# 4. Blueprint coverage
bp_sfx_slots = {s['slot'] for s in bp_sfx['slots']}
reg_sfx_ids = {e['asset_id'] for e in reg['sfx']}
assert bp_sfx_slots == reg_sfx_ids, f"Slot/asset mismatch: missing={bp_sfx_slots - reg_sfx_ids}, extra={reg_sfx_ids - bp_sfx_slots}"

# 5. Fields
for e in reg['sfx'] + reg['bgm']:
    assert e.get('license'), f"{e['asset_id']}: missing license"
    assert e.get('source_url'), f"{e['asset_id']}: missing source_url"

print("AUDIT PASSED")
```
