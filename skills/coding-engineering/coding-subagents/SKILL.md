---
name: coding-subagents
description: "Set up and manage CLI coding agents (Codex, OpenCode) as Hermes sub-agents — model config, auth, Gemini integration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [sub-agent, codex, opencode, gemini, setup]
    related_skills: [codex, opencode, hermes-agent]
---

# Coding Sub-Agents

Set up and configure CLI coding agents that Hermes orchestrates as sub-agents.

## OpenCode + Gemini

Two methods to use Gemini models with OpenCode:

### Method 1: AI Studio API Key (FREE, stable — RECOMMENDED)

Google AI Studio provides free API keys with generous limits:
- **Gemini 3.x Flash: ~1,500 requests/day (RPD)**
- Gemini 2.5 Flash: 1,500 RPD, 15 RPM
- Gemini 2.5 Pro: 50 RPD, 2 RPM

Setup:
1. Sếp gets key at https://aistudio.google.com/apikey
2. Agent sets it: `terminal(command="export GEMINI_API_KEY=<key>")` or add to `~/.hermes/.env`
3. Add model definitions to `~/.config/opencode/opencode.jsonc`:
```json
{
  "provider": {
    "google": {
      "models": {
        "gemini-3-flash": { "name": "Gemini 3 Flash" },
        "gemini-3-pro": { "name": "Gemini 3 Pro" }
      }
    }
  }
}
```
4. Verify: `opencode run "Reply OK" --model=google/gemini-3-flash`

**DO NOT confuse with Google Cloud (Vertex AI)** which only gives ~20 requests on trial. AI Studio is the correct free tier.

### Method 2: Antigravity OAuth Plugin (UNSTABLE)

Uses Google OAuth to access Antigravity quota. No API key needed. Cài đặt:

```bash
npm i -g opencode-antigravity-auth@latest
opencode plugin opencode-antigravity-auth -g
opencode auth login  # interactive — user picks Google, browser opens
```

Config at `~/.config/opencode/opencode.jsonc` needs:
- `"plugin": ["opencode-antigravity-auth@latest"]`
- Model definitions with `antigravity-` prefix under `provider.google.models`
- Available models: `antigravity-gemini-3-flash`, `antigravity-gemini-3-pro`, `antigravity-claude-sonnet-4-6`, `antigravity-claude-opus-4-6-thinking`
- Accounts stored in `~/.config/opencode/antigravity-accounts.json`

**Known issue:** Plugin is unofficial — frequently returns `Unexpected server error`. Google may block/rate-limit anytime. Prefer Method 1.

Test connectivity:
```bash
# Fast text check
opencode run "Reply exactly: OK" --model=google/antigravity-gemini-3-flash

# If error, plugin is down — no fix on our side, wait or switch to API key
```

## Codex Model Config

Codex config lives at `~/.codex/config.toml`. Do not assume the model catalog from memory: verify the installed CLI and its local model cache first.

```bash
codex --version
python -c "import json; d=json.load(open(r'C:\\Users\\thang\\.codex\\models_cache.json')); print([(m['slug'], m.get('visibility'), m.get('supported_in_api')) for m in d['models']])"
```

For the verified current Codex catalog, Luna is the model slug `gpt-5.6-luna` (display name `GPT-5.6-Luna`, visible and API-supported). `max` is a reasoning-effort level, not a separate model name. Use it explicitly:

```bash
codex -m gpt-5.6-luna -c model_reasoning_effort=max
```

Persistent config:

```toml
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
```

Reasoning levels are model/catalog-dependent; verify `supported_reasoning_levels` in `models_cache.json` instead of documenting a fixed universal list. A model slug and a reasoning level must not be conflated (for example, “Luna Max” means Luna + `max` effort unless the catalog explicitly exposes a model with that exact slug).

Test: `codex exec --sandbox workspace-write "Write hello.py. Exit."`

## Sub-Agent Execution Rules

- Codex: `pty=true`, `--sandbox workspace-write` (NEVER `--yolo` without Sếp approval)
- OpenCode: `opencode run` for one-shot (no pty), `opencode` for interactive (pty=true, background=true)
- After sub-agent finishes: `git diff` review before reporting to Sếp
- NEVER auto-commit/push sub-agent output — Sếp reviews first
- Task >10 files estimated: ask Sếp before delegating
