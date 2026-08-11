---
name: hermes-messaging-setup
description: "Connect messaging platforms (Telegram, Discord, Slack, etc.) to Hermes Gateway — bot tokens, env vars, allowlists, and verification."
version: 1.0.0
metadata:
  hermes:
    tags: [hermes, gateway, messaging, telegram, discord, setup]
---

# Hermes Messaging Platform Setup

Connect a messaging platform to the Hermes Gateway so the agent can receive and respond to messages from that platform.

## Triggers

- User says "connect Telegram", "add Discord bot", "setup WhatsApp", "check if Telegram is connected"
- Any task involving hooking up a new messaging platform to Hermes
- User provides a bot token for any supported platform

## Supported Platforms

Telegram, Discord, Slack, WhatsApp, iMessage, Signal, SMS, Email, Matrix, Mattermost, Microsoft Teams, LINE, SimpleX, ntfy, Google Chat, and more. Most share the same setup pattern below.

---

## Workflow

### 1. Get the token/credentials from the user

Each platform needs its own credentials. Common ones:

| Platform | What you need | From |
|----------|--------------|------|
| Telegram | Bot token | [@BotFather](https://t.me/BotFather) |
| Discord | Bot token | Discord Developer Portal → Bot |
| Slack | Bot token + signing secret | api.slack.com |

### 2. Save token to `.env` via `hermes config set`

```
hermes config set <PLATFORM>_BOT_TOKEN "<token>"
```

This writes to `~/.hermes/.env`, NOT to `config.yaml`.

**PITFALL: `hermes config set` maps the key to an environment variable name (uppercased). It does NOT support nested YAML paths like `messaging.telegram.bot_token`.** Trying a dotted path will fail with `ValueError: Invalid environment variable name`.

**PITFALL: Directly editing `config.yaml` via `patch` or `write_file` tools is blocked by Hermes security.** Always use `hermes config set` for credentials.

Common env var names (check gateway logs or platform adapter source for exact names):
- Telegram: `TELEGRAM_BOT_TOKEN`
- Discord: `DISCORD_BOT_TOKEN`
- Slack: `SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET`

### 3. Restart the gateway

```
hermes gateway restart
```

The gateway reads `.env` at startup. Without restart, the new token is invisible.

### 4. Verify connection

Check the gateway logs:

```
grep -i "telegram\|discord\|connected" ~/AppData/Local/hermes/logs/gateway.log | tail -15
```

Look for:
- `Connecting to <platform>...`
- `Connected to <platform>`
- `✓ <platform> connected`
- `set_my_commands OK` (Telegram-specific — confirms bot commands registered)

Also verify via `hermes config show` — the platform should show "configured" under Messaging Platforms.

### 5. Configure allowlist (REQUIRED)

The gateway defaults to **denying all unknown senders**. Until you configure an allowlist, the bot will receive messages but refuse to respond.

Two options:

**Option A — Allow specific users only (recommended):**
```
hermes config set TELEGRAM_ALLOWED_USERS "<your_telegram_user_id>"
```
Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot). Restart gateway after.

**Option B — Allow everyone (not recommended):**
```
hermes config set GATEWAY_ALLOW_ALL_USERS "true"
```
This lets anyone who finds your bot interact with it.

### 6. Test

Send a message to the bot from the allowed account. The gateway should respond within seconds.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Platform shows "not configured" | Token missing or wrong env var name | Check `hermes config show`; verify token in `.env` |
| Bot online but no response | Allowlist not configured | Set `TELEGRAM_ALLOWED_USERS` or `GATEWAY_ALLOW_ALL_USERS` |
| "Connecting... attempt N/8" repeating | Token invalid or network blocked | Verify token with BotFather; check firewall |
| Gateway crashes after token set | Token format wrong | Regenerate token from platform |

## Verification Checklist

- [ ] `hermes config show` shows platform as "configured"
- [ ] Gateway logs show "✓ <platform> connected"
- [ ] Allowlist configured (specific users or allow-all)
- [ ] Test message from allowed account gets a response
