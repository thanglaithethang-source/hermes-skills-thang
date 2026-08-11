# Coding Agent CLI Model Compatibility

## Codex (OpenAI) — ChatGPT Account

Tested with codex-cli v0.144.2, auth: chatgpt.

**Supported:** `gpt-5.6-sol` (default, heavy), `gpt-5.5` (lighter, recommended for cost)
**Blocked:** `gpt-5.6-sol-mini`, `gpt-5-sol` — "not supported with ChatGPT account"

Config: `~/.codex/config.toml` — keys `model`, `model_reasoning_effort`
Override: `-c model="X" -c model_reasoning_effort="Y"`
`--full-auto` deprecated → use `--sandbox workspace-write`

Sếp's current default: `model = "gpt-5.5"`, `model_reasoning_effort = "medium"`

## Gemini CLI — DEAD for individuals

Google killed Gemini CLI free-tier (~v0.46.0+). Error: "This client is no longer supported for Gemini Code Assist for individuals. Migrate to Antigravity." No official Antigravity CLI exists — only Antigravity IDE (desktop). Even `GEMINI_API_KEY` env var doesn't bypass the tier check.

## OpenCode + Antigravity Auth (Gemini via Google OAuth)

Alternative to dead Gemini CLI. Use OpenCode CLI with `opencode-antigravity-auth` plugin to access Gemini 3 Pro/Flash + Claude Opus/Sonnet through Google OAuth (no API key needed).

### Installation

```bash
npm i -g opencode-ai@latest
npm i -g opencode-antigravity-auth@latest
opencode plugin opencode-antigravity-auth -g
```

### Config: `~/.config/opencode/opencode.jsonc`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-antigravity-auth@latest"],
  "provider": {
    "google": {
      "models": {
        "antigravity-gemini-3-flash": { ... },
        "antigravity-gemini-3-pro": { ... },
        "antigravity-claude-sonnet-4-6": { ... },
        "antigravity-claude-opus-4-6-thinking": { ... }
      }
    }
  }
}
```

### Auth

```bash
opencode auth login   # Select "Google", browser opens for OAuth
```

Multi-account: run again for each Google account. Accounts stored in `~/.config/opencode/antigravity-accounts.json`.

### Usage

```bash
opencode run "task" --model=google/antigravity-gemini-3-flash
# Variants: --variant=minimal|low|medium|high (Gemini), low|max (Claude thinking)
```

### Pitfalls

- **Unstable:** unofficial plugin, server-side errors intermittent. Text replies work more often than tool-use tasks.
- **⚠️ Account risk:** Google may ban accounts using this plugin. Use established accounts.
- Windows config path: `~/.config/opencode/` (not `%APPDATA%`)
