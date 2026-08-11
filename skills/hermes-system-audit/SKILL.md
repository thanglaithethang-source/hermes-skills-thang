---
name: hermes-system-audit
description: Full-system health audit for Hermes Agent — skills inventory, toolsets status, models/providers, MCP servers, cron jobs, doctor diagnostics, desktop state. Use when Sếp asks "check lại toàn bộ", "audit hệ thống", "kiểm tra everything", "health check".
version: 1.0.0
---

# Hermes System Audit

Full-system health audit for Hermes Agent. Triggered when Sếp asks "check lại toàn bộ", "audit hệ thống", "kiểm tra everything", "health check", or similar.

## Audit Workflow

### Step 1: Skills inventory
```bash
hermes skills list          # full table: name, category, source, trust, status
```
Count total, note disabled ones, identify local vs builtin ratio.

### Step 2: Toolsets status
```bash
hermes tools list           # built-in + plugin toolsets, enabled/disabled
```
Note disabled toolsets (video, video_gen, x_search, context_engine, homeassistant, spotify, yuanbao).

### Step 3: Models & providers
```bash
hermes config show          # current model, provider, base_url, max turns
```
List all configured providers from `hermes model` menu (up to 35 options). Check which auth providers are logged in.

### Step 4: MCP servers
```bash
hermes mcp list             # name, transport, tools count, status
```
Verify each server is reachable and tools are discovered.

### Step 5: Cron jobs
```bash
hermes cron list            # scheduled jobs
```
Note if empty or has active jobs.

### Step 6: Doctor health check
```bash
hermes doctor               # comprehensive health report
```
Parse output into ✅ OK, ⚠ warnings, ❌ errors. Focus on:
- Python environment consistency
- SSL/CA certificates
- Required packages
- Config version
- Auth providers status
- External tools (git, ripgrep, docker, node.js)
- API connectivity results
- Workspace dependency advisories

### Step 7: Desktop apps
```python
computer_use(action='list_apps')   # running apps
computer_use(action='list_windows') # open windows
```

## Output Format

Present as structured report with these sections:

1. **MÔ HÌNH & PROVIDER** — current model, provider, available providers
2. **CÔNG CỤ (TOOLSETS)** — enabled/disabled counts
3. **KỸ NĂNG (SKILLS)** — total count, category breakdown, notable local skills
4. **CẤU HÌNH HỆ THỐNG** — paths, versions, API keys status, auth status
5. **MESSAGING PLATFORMS** — connected platforms
6. **CRON JOBS** — active/scheduled
7. **SYSTEM HEALTH** — doctor summary with actionable items
8. **WINDOWS DESKTOP** — running apps
9. **TỔNG KẾT & KHUYẾN NGHỊ** — strengths, issues, recommendations

## NPM Advisory Triage Pattern

When `hermes doctor` reports workspace dependency advisories:

### Understanding the warning format
```
⚠ web workspace deps (0 critical, 8 high, 0 moderate — build-tool advisory; clears via lockfile bump)
⚠ ui-tui workspace deps (0 critical, 7 high, 0 moderate — build-tool advisory; clears via lockfile bump)
```

### What these ARE
- **web/** = Hermes Web Dashboard (React + Vite) at `hermes-agent/web/`
- **ui-tui/** = Hermes Terminal UI (Ink/React CLI) at `hermes-agent/ui-tui/`
- These are **source code directories** of Hermes itself, not user projects

### Build-time vs Runtime impact
- Advisories come from `devDependencies` only (eslint, prettier, vitest, typescript, etc.)
- Hermes runtime uses **Python backend only** — never loads Node.js dependencies
- **Zero impact on functionality** — same as VS Code having vulnerable devDependencies

### When to act
- **Don't fix** unless Sếp explicitly wants clean audit output
- To fix: `cd <workspace-dir> && npm audit fix`
- Risk: may break build scripts during Hermes updates

### agent-browser missing
```
⚠ agent-browser not installed (run: npm install)
```
- Global npm package (`npm install -g agent-browser`) for advanced browser automation
- NOT required for basic `browser_*` tools (navigate, click, type, snapshot)
- Only needed for advanced scraping, dynamic content automation
- Safe to ignore unless Sếp specifically needs it

## Quick Audit (Lightweight)

When Sếp just wants a quick pulse check, skip Steps 7 and do a condensed report:
- Current model/provider
- Skills count (total/enabled)
- Toolsets (enabled/disabled)
- MCP servers status
- Doctor warnings only
- Top 3 recommendations