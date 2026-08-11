# ToonFlow — Detailed Reference

Source: `C:\Users\thang\Downloads\_projects\ToonFlow-1.1.8-win-x64-setup.exe` (252MB installer)
Installed: `D:\New folder\ToonFlow\` (819MB)
GitHub: `HBAI-Ltd/Toonflow-app` — ⭐11.6k, 🍴2.1k, Apache 2.0

## What It Is

AI短剧工厂 — one-stop AI short drama production:
**Novel → Script → Storyboard → AI images/video → Final short drama**

## Architecture

- Electron desktop app (TypeScript + Node.js)
- AI SDK: Anthropic, DeepSeek, Google, OpenAI, xAI
- Native modules: better-sqlite3, onnxruntime-node, sharp, sqlite3
- Docker support (port 10588)

## Key Features

- **Infinite canvas** — drag-drop, non-linear workflow
- **3-layer Agent** — decision/execution/supervision
- **Persistent memory** — ONNX vector retrieval, cross-session
- **Programmable providers** — write TypeScript to add models, no source changes
- **Skill files** — prompts as Markdown, hot-reload
- **Multi-language UI** — Vietnamese available

## Launch

```bash
cmd.exe /c start "" "D:\New folder\ToonFlow\ToonFlow.exe"
```

Or double-click `ToonFlow.exe` in Explorer.

## Login

Default: `admin` / `admin123`

## Setup Required

After first login → Settings → configure:
- **Text model:** Claude/DeepSeek/OpenAI API key + endpoint
- **Image model:** Nano Banana Pro / GPT Image
- **Video model:** Sora / Doubao (豆包)

## Demo Cost Reference

2-minute short drama, ~2 hours:
- Text (Claude Opus 4.6): ¥10
- Video (Seedance 2.0): ¥120
- Image (GPT Image 2): <¥1
- **Total: ~¥130 (~450K VND)**

## Uninstall

`D:\New folder\ToonFlow\Uninstall ToonFlow.exe`
