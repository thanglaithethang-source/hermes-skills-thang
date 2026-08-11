# Integration Audit — 2026-07-22

Full trace: `ChromeController` → TCP:19979 → Bridge Server → WS:19978 → Extension → CDP  
Cross-check: `HermesChromeController` → CDP:9222 → Playwright → Chrome

## Scope
All Python files in `C:\Users\thang\Downloads\_projects\hermes-chrome-extension`:
- `hermes_chrome.py` — `ChromeController` (TCP bridge)
- `chrome_send.py` — `ChromeBridge` (TCP bridge, CLI)
- `hermes_bridge_server.py` — Bridge server v3 (TCP ↔ WS, lock-free)
- `hermes_bridge_server_v2_debug.py` — Bridge server v2 (with asyncio.Lock, verbose)
- `hermes_bridge_server_old.py` — Bridge server v1 (uses `websockets` library)
- `hermes_chrome_controller.py` — `HermesChromeController` (Playwright CDP)
- `bridge.py` — Dead code (throws NotImplementedError)
- `background.js` — Chrome extension service worker
- `test_ws_client.py` — Simulated extension WS client
- `popup.js` — Extension popup (bypasses bridge, uses direct debugger)
- `manifest.json` — Extension manifest (MV3)
- `start_chrome_cdp.bat` / `start_bridge.bat` — Launcher scripts

## Results

### Bugs
| # | Severity | File:Line | Description | Verified |
|---|----------|-----------|-------------|----------|
| 1 | CRITICAL | `hermes_chrome.py:113` | Double `.get('result')` in `get_cookies()` → always empty dict | ✅ Simulated |
| 2 | MODERATE | `hermes_chrome.py:140-141` | Error double-wrapping in `capture_api_requests()` on disconnect | ✅ Traced |
| 3 | LOW | `hermes_bridge_server.py:95-101` | TOCTOU race on `ext_writer` (v3 lock-free; safe but noisy) | ✅ Analyzed |

### Inconsistencies
| # | Description | Affected files |
|---|-------------|---------------|
| 4 | `tabId` (camelCase) vs `tab_id` (snake_case) CLI arg naming | `hermes_chrome_controller.py` vs `chrome_send.py` |
| 5 | `bridge.py` always raises NotImplementedError — dead code | `bridge.py` |
| 6 | Docstring says `capture_api()` but method is `capture_api_requests()` | `hermes_chrome.py:14` |
| 7 | Three bridge server versions coexist (v1, v2, v3) | `hermes_bridge_server*.py` |
| 8 | `popup.js` directly attaches debugger (conflict with bridge-owned tabs) | `popup.js` |

### Missing Features (CDP path vs Extension path gap)
| Method | Extension path | CDP path |
|--------|:---:|:---:|
| `cdp()` — raw CDP command | ✅ | ❌ |
| `capture_api_requests()` — network monitoring | ✅ | ❌ |
| `get_cookies()` — session cookies | ✅ (broken) | ❌ |
| `download()` — tải file | ✅ | ❌ |

### Verified Working
- TCP protocol (json + `\n` framing) — consistent both sides ✅
- Bridge `command` → `type` normalization (`hermes_bridge_server.py:99`) ✅
- `navigate()` dual-key (`url`+`tabId` / `newUrl`) ✅
- `network_start`/`network_stop` flow (extension → CDP Network domain → capture) ✅
- WebSocket fragmented frame reassembly (bridge v3) ✅
- `test_ws_client.py` sends properly masked client frames ✅
- All Python files pass AST syntax check ✅
- No missing imports in `hermes_chrome.py` (stdlib only) ✅
- CDP launch script (`start_chrome_cdp.bat`) correctly kills+launches+verifies ✅
