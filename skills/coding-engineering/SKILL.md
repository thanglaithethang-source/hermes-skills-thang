---
name: coding-engineering
description: Code reading, editing, debugging, testing, and integration.
version: 1.1.0
---

# Coding & Engineering

## Activation
When task involves: reading repos, editing code, building apps, debugging, writing scripts, API integration, software testing.

## Not for
Tasks that don't modify code or require code analysis.

## Workflow
1. Inspect repository structure
2. Read README and relevant docs
3. Identify conventions (lint, format, test framework)
4. Check git status and branch
5. Run baseline tests if available
6. Identify root cause / requirement
7. Design minimal patch
8. Implement change
9. Lint + format (if project convention)
10. Run relevant tests
11. Run real flow test
12. Audit diff (changed files, scope)
13. Check for regressions
14. Deliver with evidence

## Rules
- Minimum change necessary
- Preserve existing architecture
- No rewrites unless required
- No deleting features to dodge bugs
- No hard-coding secrets
- No mocking then claiming real system works

## Completion Criteria
- Syntax valid
- Tests pass (if exist)
- Real flow verified
- Diff reviewed
- No regressions
- Evidence: test output, diff summary, flow result

## Common Failures
- Skipping baseline → fixes wrong problem
- Changing too much at once → can't isolate errors
- Not running tests → regressions

## Platform-Specific Pitfalls
- **Windows path escaping in bash (git-bash):** Terminal paths with backslashes get mangled when quoted. Prefer forward slashes: `python "C:/Users/thang/.../script.py"`. `cd` also accepts forward slashes.
- **Windows rm blocked:** `rm -rf` may be blocked by Hermes approval system even for temp sandbox files. Use `write_file` or `patch` for cleanup or leave temp files — they're harmless.
