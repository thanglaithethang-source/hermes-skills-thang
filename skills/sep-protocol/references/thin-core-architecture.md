# Hermes Thin-Core Architecture

Architecture blueprint for minimizing system prompt bloat. Source: Sếp, 2026-07-11.

## Problem

Hermes default injects ~8,000+ tokens into every session:
- All tool descriptions (18 toolsets × 100-2,000 tokens each)
- Full skill index (40+ skills with descriptions)
- Platform operating rules
- Environment hints

## Solution: Thin Core + Structured Memory + On-Demand Skills

### Desired Token Budget

| Component | Target |
|-----------|--------|
| System core | 1,500–2,500 |
| User profile | 300–700 |
| Operating rules | 500–1,500 |
| Active project context | 1,000–3,000 |
| One loaded skill | 1,000–4,000 |
| Session summary | 300–1,000 |
| **Total startup** | **3,000–6,000** |

### What to Load at Startup

1. `SYSTEM_CORE.md` — role, loop, rules
2. `USER_PROFILE.md` — Sếp's preferences
3. `OPERATING_RULES.md` — confirmed standards
4. `ACTIVE_PROJECTS.md` — current project state
5. Recent portion of `DECISIONS.md`

**Never load the full skills directory at startup.** Search and load only the relevant skill when receiving a task.

### Practical Levers (Hermes Config)

**Profile-based MCP isolation — biggest win for heavy MCP servers:**

MCP servers with 30+ tools (e.g. DaVinci Resolve) can add 15-20k tokens alone. Keep them out of the default profile:

```bash
# Create dedicated profile with MCP
hermes profile create resolve --clone-from default
# Then from default, remove the heavy MCP
hermes mcp remove davinci-resolve
```

Default profile stays lean; `hermes -p resolve` for MCP-heavy sessions. Agent automatically spawns `hermes -p <profile> chat -q "..."` when those tools are needed. See `resolve-post-production` skill for full pattern.

**Toolset reduction — moderate win:**

```bash
# Disable heavy toolsets (saves ~4,000-5,000 tokens)
hermes tools disable browser
hermes tools disable image_gen
hermes tools disable tts
hermes tools disable delegation
hermes tools disable cronjob
hermes tools disable session_search
hermes tools disable skills     # load manually with /skill
hermes tools disable clarify
hermes tools disable todo
hermes tools disable code_execution
hermes tools disable vision
hermes tools disable computer_use  # ~2,000 tokens alone
hermes tools disable memory
```

Keep only: `web`, `terminal`, `file` + re-enable task-specific tools when needed.

**Changes take effect on `/reset` (new session).**

### What Config CANNOT Fix (and workarounds)

| Bloat source | Reason | Workaround |
|-------------|--------|------------|
| MCP tool schemas | Each MCP tool adds its full JSON schema | **Profile isolation** — keep heavy MCP servers in dedicated profiles |
| Tool descriptions | Hardcoded in `tools/*.py` — no compact mode | Disable unused toolsets via `hermes tools disable` |
| Full skill index injection | Framework auto-injects | Cannot disable; minimize via curator archiving of stale skills |
| Platform operating rules | Auto-generated from host detection | Cannot disable |

### Multi-Agent Routing

| Task | Role |
|------|------|
| Understand + plan | Strong reasoning model |
| Write + fix code | Strong coding model |
| Computer control | Stable tool-use agent |
| Audit | Model independent of executor |
| Memory summarization | Lightweight, low-cost model |

Default: 1 Planner + 1 Executor + 1 Auditor. Never chain 5 models on a small task.

### Memory Discipline

After each task, only record 4 types:
1. **Decision** — architectural choices made
2. **Verified** — what was confirmed working
3. **Failure** — what broke and root cause
4. **Reusable rule** — pattern that applies beyond this task

Never save: full transcripts, raw terminal output, 10 versions of plans, rejected ideas, duplicate rules.

### Core Principles

```
RETRIEVE BEFORE REASONING
INSPECT BEFORE MODIFYING
VERIFY BEFORE CLAIMING
BACKUP BEFORE DESTRUCTIVE ACTION
AUDIT WITH REAL EVIDENCE
SAVE DECISIONS, NOT CONVERSATIONS
```
