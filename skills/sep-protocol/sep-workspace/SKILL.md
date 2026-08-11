---
name: sep-workspace
description: "Sếp's production toolbox — MoneyPrinterTurbo, OpenMontage, Hermes Bridge, ToonFlow, veo-automation. How to launch, configure, and operate each tool."
version: 1.0.0
---

# Sếp's Production Workspace

Root: `C:\Users\thang\Downloads\_projects\`

Five production tools Sếp keeps active. When Sếp says "dùng tool X" or "chạy Y", this skill tells you exactly how.

## Quick Reference

| Tool | Type | Launch | Key Detail |
|---|---|---|---|
| MoneyPrinterTurbo | AI video generator | `python cli.py --video-subject "..."` | DeepSeek v4 Pro, Pixabay |
| OpenMontage | Agentic video production | Agent reads `AGENT_GUIDE.md` → pipeline | 13 pipelines, 85 tools |
| Hermes Bridge | Chrome CDP control | `python -B hermes_bridge_server.py` | raw WS:19978 + TCP:19979, CDP Controller alternative available |
| ToonFlow | AI short drama factory | `D:\New folder\ToonFlow\ToonFlow.exe` | admin/admin123 |
| veo-automation | Google Flow auto | Already loaded in Chrome | labs.google/* |

## Windows Execution Patterns

- MSYS bash CANNOT run `.exe` directly (Permission denied). Use `cmd.exe /c "..."`
- Launch GUI apps: `cmd.exe /c start "" "path\to\app.exe"`
- NSIS installers: `/S` for silent, `/D=path` for target dir
- Use `$USERPROFILE` (Windows path) in terminal, not `$HOME` (MSYS path), when passing to Windows commands
- **Double-click `.py` không chạy / nháy cmd:** Có 4 nguyên nhân gốc: (1) Store app hijack UserChoice, (2) Zone.Identifier chặn file tải về, (3) cp1252 crash với tiếng Việt, (4) Python.File progid bị mất hoàn toàn. Xem hướng dẫn chẩn đoán và fix đầy đủ tại `system-diagnostics` skill → `references/windows-file-association-debug.md`. KHÔNG tạo .bat wrapper như workaround — fix root cause.

## MoneyPrinterTurbo

Path: `_projects/MoneyPrinterTurbo/`
Python: `.venv/Scripts/python` (3.11)
Config: `config.toml` — DeepSeek v4 Pro via ai-box.vn, Pixabay, Pexels, Gemini 2.5 Flash

**CLI mode** — fastest for one video:
```
.venv/Scripts/python cli.py --video-subject "chủ đề" [--options]
```
Key options: `--video-source`, `--video-aspect`, `--voice-name`, `--bgm-type`, `--subtitle-enabled`, `--video-count`, `--stop-at`

**Web UI mode** — for batch:
```
.venv/Scripts/python main.py
→ http://127.0.0.1:8080/docs
```

See: `references/moneyprinterturbo.md`

## OpenMontage

Path: `_projects/OpenMontage/`
Python: `.venv/Scripts/python`
Config: `config.yaml` — Anthropic provider, mp4/h264/AAC, 1080p30

**Architecture:** Agent reads pipeline YAML → stage director skills → calls 85 tools. Python is tools+persistence only.

**13 pipelines:** animated-explainer, animation, cinematic, talking-head, character-animation, screen-demo, clip-factory, podcast-repurpose, hybrid, avatar-spokesperson, localization-dub, documentary-montage, framework-smoke

**Entry:** Always read `AGENT_GUIDE.md` first. It routes you to the right pipeline and skills.

See: `references/openmontage.md`

## Hermes Bridge (Chrome Extension)

Path: `_projects/hermes-chrome-extension/`

Hai giải pháp kiểm soát Chrome, dùng chung hoặc riêng:

### A. Extension Bridge (ổn định, đang chạy)

Bridge server v3: raw asyncio WebSocket port 19978 (extension) + TCP port 19979 (Hermes client).
Extension loaded unpacked trong Chrome (ID: `klghdnedebacaciemlnhchdghkoodgke`), tự reconnect.

**Launch:**
```bash
python -B hermes_bridge_server.py   # -B = không __pycache__ (CRITICAL!)
```
→ "READY" → extension auto-connect ("Hermes Bridge v1.0.0")

**Commands:** `python -B chrome_send.py <action> [--key val]`
Actions: ping, list_tabs, get_current_tab, navigate, click, type, screenshot, execute_js, get_dom, scroll, press_key, download, new_tab, close_tab, network_start, network_stop, cdp_command, reload_self

**CRITICAL pitfalls (HARD RULES):**
- **`__pycache__/` destroys extension** — Chrome cấm thư mục `_*`. Luôn `python -B`. `start_bridge.bat` đã set `PYTHONDONTWRITEBYTECODE=1`.
- **KHÔNG dùng `websockets` library** — không tương thích Chrome permessage-deflate. Bridge dùng raw TCP WebSocket.
- **KHÔNG dùng `asyncio.Lock()`** — gây deadlock trên Windows. V3 dùng global variable trực tiếp.
- **Network.enable chỉ gọi 1 lần** — removed khỏi `ensureDebuggerAttached` domains, chỉ gọi từ `handleNetworkStart`.
- **WS fragmentation phải handle** — `read_frame()` reassemble continuation frames, nếu không mất data >125 bytes.
- **Port 19978 dễ bị process cũ chiếm** — kill sạch trước start. Triệu chứng: server start OK nhưng extension không connect.
- **CDP debugger cần force-detach** — sau reload extension, `ensureDebuggerAttached` catch "already attached" → detach → re-attach.

**Network monitoring (bắt API của bất kỳ web nào):**
```bash
python -B chrome_send.py network_start --tabId <id>
# reload page hoặc tương tác
python -B chrome_send.py network_stop --tabId <id>
# → danh sách request với URL, method, headers, postData, status
```

**Diagnostic khi extension không kết nối:**
1. `netstat -ano | grep 19978` → tìm PID lạ → `taskkill /F /PID <pid>`
2. `ls __pycache__` → nếu có → `rm -rf __pycache__` → reload extension
3. Reload extension (🔄) → đợi 3-10s → `python -B chrome_send.py ping`
4. Nếu vẫn fail: restart bridge server + reload extension

### B. CDP Controller (mạnh hơn, cần restart Chrome 1 lần)

`hermes_chrome_controller.py` — Playwright `connect_over_cdp`. Không extension, không bridge server.

**Setup 1 lần:** `start_chrome_cdp.bat` (kill Chrome + restart với `--remote-debugging-port=9222`)

**Dùng:** `python hermes_chrome_controller.py <action> [--key val]`

| | Extension Bridge | CDP Controller |
|---|---|---|
| Cần extension | Có | Không |
| Cần bridge server | Có | Không |
| Cần restart Chrome | Không | Có (1 lần) |
| Độ ổn định | Đã fix | Production-grade |

Full details: `references/hermes-bridge.md`

## ToonFlow

Installed: `D:\New folder\ToonFlow\ToonFlow.exe` (819MB, Electron app)
Login: `admin` / `admin123`

**Pipeline:** novel → script → storyboard → AI images/video → final short drama
**AI backends:** Claude, DeepSeek, Google, OpenAI, xAI (configure in-app)
**Video models:** Sora / Doubao
**Image models:** Nano Banana Pro / GPT Image

**Launch:** `cmd.exe /c start "" "D:\New folder\ToonFlow\ToonFlow.exe"`

See: `references/toonflow.md`

## AI Model Selection

All ai-box.vn models tested and ranked (quality, speed, cost): `references/ai-box-models.md`

## veo-automation-custom ("FLOW BY THANG")

Path: `_projects/veo-automation-custom/`
Already loaded in Chrome as "Flow Automation - Auto Flow on Google Flow"
Operates on `labs.google/*` — auto VEO + Nano Banana generation.

No action needed; extension is installed and active.

## Pitfalls

- MoneyPrinterTurbo: `.venv/Scripts/python`, not system python (3.11 vs 3.14)
- OpenMontage: config method is `OpenMontageConfig.load()`, tool list via `list_all()`
- Hermes Bridge: Chrome must be running with extension loaded. **Always `python -B`** — `__pycache__/` kills the extension. KHÔNG dùng `asyncio.Lock()` trong bridge server. Dùng `start_bridge.bat` cho one-click launch. Có CDP Controller (`hermes_chrome_controller.py`) làm alternative không cần extension.
- ToonFlow: needs API keys configured in-app (Settings → Providers)
- All .exe: run via `cmd.exe /c`, not directly in MSYS bash
