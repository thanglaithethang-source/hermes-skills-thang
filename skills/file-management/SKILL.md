---
name: file-management
description: File organization, renaming, moving, backup, sync, search, cleanup.
version: 1.0.0
---

# File Management

## Activation
When task involves: organizing files, renaming, moving, backing up, syncing, finding files, cleaning up data.

## Not for
Simple single-file operations (use file tools directly).

## Workflow
1. Inspect current directory structure
2. Define organization rules
3. Create manifest (list of files to process)
4. Check for name conflicts
5. BACKUP before any destructive operation
6. Execute in small batches
7. Verify count and checksums if applicable
8. Deliver with operation log

## Safety
- NEVER permanently delete without explicit Sếp approval
- Move to archive/trash instead of rm
- Verify before and after counts match expectations
- Keep operation log for rollback

## Completion Criteria
- Files at target locations
- Counts match
- No conflicts
- Backup exists
- Rollback path documented

## Common Failures
- Name collisions → check before moving
- Missing files after operation → verify counts
- Permission errors → check access before batch
