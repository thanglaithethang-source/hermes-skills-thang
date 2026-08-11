# Game/Software Directory Cleanup Reference

Detailed reference for auditing and cleaning game/software directories that have been modded.

## Junk Identification Patterns

### Inside Game Folder

| Pattern | Type | Safe to Delete? | Check First |
|---------|------|-----------------|-------------|
| `_backup_*` | Pre-mod backup | Yes | Verify mod still applied |
| `_*.json` | Modding cache | Yes | Task is complete |
| `_*.txt` | Modding report | Yes | Task is complete |
| `*.py` (top-level) | One-off script | Yes | Task is complete |
| `*.zip` (top-level) | Intermediate archive | Yes | Already extracted |
| Empty dirs | Failed attempt | Yes | Confirm 0 files |

### Outside Game Folder (workspace)

| Pattern | Type | Safe to Delete? | Check First |
|---------|------|-----------------|-------------|
| `*_raw_files/` | Original source | Yes | Mod applied in game |
| `*_CDP/` | Draft translation | Yes | Final version exists |
| `*_DeepSeek/` | Failed attempt | Yes | Confirm 0 files |
| `*_FINAL_*.zip` | Audit archive | Yes | Folder version exists |
| `*_toolkit.zip` | Tool archive | Yes | Folder version exists |
| `download_urls*.txt` | URL list | Yes | Downloads complete |
| `test_key.py` | Test script | Yes | Task complete |

## Verification Before Cleanup

1. **Mod applied check**: Read a sample file from game's localisation/config dir
   - Look for non-English text (Vietnamese, etc.)
   - Check file timestamps are recent (not original game date)
2. **Final version exists**: If deleting draft/intermediate, confirm final version folder exists
3. **File count**: `find <final_dir> -type f | wc -l` should be > 0

## Approval Gate Pattern

Use `clarify` tool with choices:
- "Xóa hết N mục rác (~XXmb)"
- "Chỉ xóa file rác top-level"
- "Chỉ xóa cache + backup trong game folder"
- "Không xóa, chỉ báo cáo"

## Post-Cleanup Verification

1. Game data intact: `du -sh` matches expectation
2. Mod still applied: Read sample localisation file, check non-English text present
3. No _backup files remain: `find <game_dir> -maxdepth 1 -name "_*"` returns empty
4. Clean top-level: Only game folder + final mod folder + toolkit remain
