---
name: toonflow-control
description: "Install, discover, login, and control ToonFlow (AI短剧工厂) via its REST API — no GUI needed."
version: 1.0.0
platforms: [windows]
---

# ToonFlow Control

ToonFlow is an Electron desktop app (AI short-drama factory) that runs an Express server
on a dynamic port. Control it 100% via REST API after extracting its JWT secret from SQLite.

## When to Use

- Sếp wants to create AI-generated short dramas (novel → script → storyboard → video)
- Sếp asks to install, configure, or control ToonFlow
- Need to automate ToonFlow operations without GUI

## Architecture

```
Electron app (ToonFlow.exe)
  → Express server on random port (NOT fixed 2032 — find via netstat)
  → SQLite database at %APPDATA%/toonflow/data/db2.sqlite
  → JWT auth with secret in o_setting table (key='tokenKey')
  → 140+ REST API endpoints — ALL use POST method
```

## Installation

1. Download latest Windows installer from GitHub Releases:
   `https://github.com/HBAI-Ltd/Toonflow-app/releases`
2. Install to `D:\New folder\ToonFlow\` (or any path)
3. First launch MUST be via GUI (double-click .exe) — this inits the database
4. Default credentials: `admin` / `admin123`

## Discovery (every session — port changes)

```bash
# 1. Find the port
PID=$(tasklist | grep ToonFlow | head -1 | awk '{print $2}')
PORT=$(netstat -ano | grep $PID | grep LISTENING | awk '{print $2}' | cut -d: -f2 | head -1)

# 2. Get token
TOKEN=$(curl -s -X POST "http://127.0.0.1:$PORT/api/login/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
```

## API Basics

- **All endpoints use POST** (even GET-like queries)
- Auth header: `Authorization: Bearer <token>`
- Response format: `{"code": 200, "data": ..., "message": "成功"}`
- Login endpoint is whitelisted (no auth needed)

## Key API Endpoints

See `references/api-catalog.md` for full list (140+ endpoints).

### Project Management
- `POST /api/project/addProject` — create project
- `POST /api/project/getProject` — list projects
- `POST /api/project/delProject` — delete project

### Novel & Script
- `POST /api/novel/addNovel` — import novel
- `POST /api/novel/event/generateEvents` — extract chapter events
- `POST /api/scriptAgent/getPlanData` — get ScriptAgent plan

### Production
- `POST /api/production/storyboard/addStoryboard` — create storyboard
- `POST /api/production/workbench/generateVideo` — generate video clip
- `POST /api/production/workbench/batchGenerateVideo` — batch generate

### Vendor Configuration
- `POST /api/setting/vendorConfig/getVendorList` — list vendors
- `POST /api/setting/vendorConfig/updateVendorInputs` — set API keys
- `POST /api/setting/vendorConfig/enableVendor` — toggle vendor on/off

### Agent Configuration
- `POST /api/setting/agentDeploy/getAgentDeploy` — list agents
- `POST /api/setting/agentDeploy/deployAgentModel` — assign model to agent

## Vendors (11 built-in)

All disabled by default. Need API key to enable:
- **ToonFlow中转** — Seedance, Wan, Kling, Vidu (via api.toonflow.net)
- **火山引擎(豆包)** — Seedance, Seedream (Volcengine)
- **可灵AI** — Kling v1→v3
- **MiniMax(海螺)** — 海螺2.3
- **AtlasCloud MASS** — GPT Image, Nano Banana, Seedance, Wan
- **Vidu** — ViduQ1→Q3

## Pitfalls

1. **Port is NOT fixed at 2032** — it changes each launch. Always find via netstat.
2. **Database is at `data/db2.sqlite`**, NOT the root `db2.sqlite`. The root one stays empty.
3. **MSYS bash cannot run .exe directly** — use `cmd.exe /c start "" "path.exe"` or PowerShell `Start-Process`.
4. **First launch must be GUI** — Electron app initializes DB only when launched via double-click.
5. **All APIs are POST** — GET requests return 404.
6. **Do NOT over-explain blockers** — if stuck, find another path immediately.
