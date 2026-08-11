# ToonFlow — Knowledge Bank

> Source: HBAI-Ltd/Toonflow-app — GitHub (11.6k ⭐, Apache 2.0)
> Installed: D:\New folder\ToonFlow\ (819MB, v1.1.8)

## What It Is

AI short drama factory (AI 短剧工厂). Converts novels → scripts → storyboards → video.
Electron desktop app with embedded Express server + Vue 3 + TDesign UI.

## Architecture

```
ToonFlow.exe (Electron)
  └── Express server (port 2032)
       ├── SQLite database (%AppData%/Roaming/toonflow/db2.sqlite)
       ├── JWT auth (secret stored in o_setting table, key="tokenKey")
       └── Frontend (Vue 3 + TDesign, served from app.asar)
```

## API Endpoints

| Method | Path | Auth | Body |
|--------|------|------|------|
| POST | `/api/login/login` | No | `{username, password}` → `{token, name, id}` |
| * | `/api/*` | Bearer token | Header: `Authorization: Bearer <token>` |

Login whitelist: only `/api/login/login` skips auth middleware (line 258917 in app.js).

## Database

- **File:** `%AppData%/Roaming/toonflow/db2.sqlite`
- **ORM:** Knex (SQL query builder)
- **Key tables:** `o_user` (id, name, password — plaintext!), `o_setting` (key, value), `o_project`, `o_agentDeploy`, `o_vendorConfig`, plus ~20 more for projects/assets/scripts
- **Init:** `initDB.ts` creates 25 tables on first run
- **Default user:** `admin` / `admin123` (plaintext password)

## Login Flow (from source)

```
POST /api/login/login {username, password}
  → SELECT * FROM o_user WHERE name = username
  → Check password plaintext match
  → SELECT value FROM o_setting WHERE key = 'tokenKey'
  → JWT sign({id, name}, tokenKey, expiresIn: '180Days')
  → Return {token: "Bearer <jwt>", name, id}
```

## Server Control

- Server runs ONLY inside Electron process — cannot run standalone (requires asar-resolved modules)
- App must be launched via GUI (double-click exe) or `Start-Process` from PowerShell
- Server starts AFTER Electron main process initializes database
- Port 2032 listens only after full init (~5-15 seconds after app window appears)

## Key Files

| File | Purpose |
|------|---------|
| `ToonFlow.exe` | Electron main (214MB) |
| `resources/app.asar` | Bundled app code |
| `resources/app.asar.unpacked/` | Native modules (better-sqlite3, onnxruntime, sharp, sqlite3) |
| `resources/data/serve/app.js` | Express server bundle (10MB, 259K lines) |
| `resources/data/db2.sqlite` | Template database |
| `%AppData%/Roaming/toonflow/db2.sqlite` | Runtime database |
| `%AppData%/Roaming/toonflow/DIPS` | Chromium DIPS storage |

## Quick Start

```powershell
# Launch app
Start-Process 'D:\New folder\ToonFlow\ToonFlow.exe' -WorkingDirectory 'D:\New folder\ToonFlow'

# After app window appears (~15s), discover actual port:
netstat -ano | findstr "ToonFlow.exe"  # get PID
netstat -ano | findstr "LISTENING" | findstr "<PID>"  # get port

# Login:
curl -s -X POST http://127.0.0.1:<PORT>/api/login/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response: {"token":"Bearer eyJ...", "name":"admin", "id":1}

# Use token for all other API calls:
curl -s http://127.0.0.1:<PORT>/api/setting/loginConfig/getUser \
  -H "Authorization: Bearer <token>"
```

## Port Discovery

The documented port (2032) is NOT reliable. The actual port varies per launch. Discovery method:
1. `tasklist | grep ToonFlow` → get PID
2. `netstat -ano | grep <PID> | grep LISTENING` → get actual port
3. OR: query `netstat` for all LISTENING ports and match against ToonFlow PIDs

## Database Discovery

There are **two** `db2.sqlite` files:
- `%AppData%/Roaming/toonflow/db2.sqlite` — TOP-LEVEL (often empty, template)
- `%AppData%/Roaming/toonflow/data/db2.sqlite` — REAL database (26 tables after init)

Always target the `data/` subdirectory one. The top-level file may be a leftover from manual creation attempts.

## JWT Secret Extraction

If you need the token without going through the web UI:
```python
import sqlite3
db = sqlite3.connect(r'%AppData%\Roaming\toonflow\data\db2.sqlite')
secret = db.execute("SELECT value FROM o_setting WHERE key='tokenKey'").fetchone()[0]
# Then sign your own JWT: jwt.sign({id: 1, name: 'admin'}, secret, {expiresIn: '180Days'})
```
The secret key is an 8-character hex string (e.g., `9c06c964`), auto-generated on first DB init.

## AI Model Providers

Supports: Anthropic, DeepSeek, Google, OpenAI, xAI, plus custom vendors.
Video: Sora / Doubao (豆包). Image: Nano Banana Pro / GPT Image.
Agent types: scriptAgent, productionAgent, universalAi, ttsDubbing, decisionAgent, supervisionAgent.
