# CapCut Build Audit — Timing Gap (2026-07-22)

## Pattern: Plan-to-Script Off-by-One

When a build script's CHAPTERS array is hand-coded with independently calculated
timestamps (rather than generated from the plan's SECTION MAP), systematic
**off-by-one-second gaps** appear between chapters.

### The Session 0722 Case

- **15/29 chapters** had start times **1 second later** in `build_capcut_0722.py`
  than in `MASTER_POST_PRODUCTION_PLAN.md`.
- The plan shows seamless boundaries (C02 ends at 31s → C03 starts at 31s).
- The script has gaps (C02 ends at 31s → C03 starts at 32s → 1s silence).

| Chapter | Plan Start | Script Start | Delta |
|---------|-----------|-------------|-------|
| C03 | 31s | 32s | +1 |
| C05 | 60s | 61s | +1 |
| C06 | 70s | 71s | +1 |
| C08 | 91s | 92s | +1 |
| C09 | 110s | 111s | +1 |
| C10 | 130s | 131s | +1 |
| C11 | 144s | 145s | +1 |
| C13 | 177s | 178s | +1 |
| C15 | 223s | 224s | +1 |
| C16 | 235s | 236s | +1 |
| C20 | 325s | 326s | +1 |
| C23 | 452s | 453s | +1 |
| C25 | 528s | 529s | +1 |
| C27 | 645s | 646s | +1 |
| C29 | 800s | 801s | +1 |

### Root Cause

Build script author calculated timestamps from SRT cues independently instead
of deriving them from the plan's SECTION MAP. The plan IS the ground truth.

### Detection Script

```python
import json, re

# Parse plan's SECTION MAP
plan_chapters = {}
with open('POST_PRODUCTION_PLAN.md') as f:
    for line in f:
        m = re.match(r'\| (C\d+) \| .*? \| .*? \| (\d{2}:\d{2})–(\d{2}:\d{2})', line)
        if m:
            ch, start, end = m.groups()
            plan_chapters[ch] = (mmss_to_s(start), mmss_to_s(end))

# Read build script CHAPTERS or draft_content.json filters
# Cross-reference: if plan[ch][0] != build[ch][0] → FLAG
```

### Fix

Regenerate CHAPTERS from the plan's SECTION MAP timestamps directly.
Do not recalculate from SRT cues. The plan is the spec — the build script
is a mechanical translation of it.

### Prevention

After writing a build script, audit every chapter start/end against the plan's
SECTION MAP. The 10-criteria audit checklist in `video-production` skill covers
this as criterion #1.
