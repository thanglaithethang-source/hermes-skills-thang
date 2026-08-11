---
name: system-diagnostics
description: System troubleshooting, tool failure, dependency errors, config issues, performance problems.
version: 1.1.0
---

# System Diagnostics

## Activation
When task involves: system errors, tool failures, dependency problems, config not working, poor performance, missing permissions.

## Workflow
1. Collect environment info (OS, version, paths, env vars)
2. Reproduce the error
3. Read logs
4. Isolate the failing component
5. Identify root cause
6. Design minimal fix
7. BACKUP before changes
8. Apply fix
9. Re-test
10. Record lesson if reusable

## Diagnostic Commands
- `hermes --version` → Hermes version
- `hermes doctor` → health check
- `hermes config` → current config
- `hermes config path` → config file location
- Check logs: `~/.hermes/logs/`
- Check permissions, env vars, dependencies

## Rules
- Never fix blindly
- One change at a time when debugging
- Record what was tried and what worked
- If root cause unknown, say so — don't guess

## Completion Criteria
- Error reproduced and understood
- Root cause identified OR documented as unknown
- Fix applied and verified
- No regressions
- Lesson saved if reusable

## Common Patterns
- Missing env vars → check .env and exports
- Permission denied → check file ownership
- Port conflict → check running services
- Version mismatch → check compatibility
- **Windows file association broken** (double-click flashes cmd) → see `references/windows-file-association-debug.md`

## Hermes-Specific Diagnostics
- **Memory char limits:** USER.md capped at 1,375 chars, MEMORY.md at 2,200 chars. Use batch operations (memory tool `operations` array) for atomic add+remove. Entries separated by `§` delimiter in files.
- **Tool bloat analysis:** Each enabled toolset injects its full tool description into system prompt. `computer_use` adds ~2,000 tokens alone. Measure via `hermes tools list`. Disable unused toolsets with `hermes tools disable <name>` — takes effect on `/reset`.
- **Skill index bloat:** All enabled skills listed with descriptions in system prompt. No config toggle to disable. Source code change required for lazy skill listing.
- **State.db inspection:** `sqlite3` may not be installed on Windows. Use Python: `python -c "import sqlite3; db = sqlite3.connect('<path>'); print(db.execute('SELECT name FROM sqlite_master').fetchall())"`. WAL files may need checkpoint before reading.
- **Config discovery:** `hermes config path` returns exact config location.
