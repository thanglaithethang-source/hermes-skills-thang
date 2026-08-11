# Hermes Bridge — Detailed Reference

Path: `C:\Users\thang\Downloads\_projects\hermes-chrome-extension\`

## Architecture

```
Hermes Agent ← TCP:19979 → Bridge Server (Python asyncio) ← WS:19978 → Chrome Extension ← CDP → Chrome Tabs
```

Extension ID: `klghdnedebacaciemlnhchdghkoodgke` (loaded unpacked)
Bridge server: raw asyncio — tự implement WebSocket framing, KHÔNG dùng `websockets` library.

## Bridge Server Evolution

| Version | Approach | Status |
|---------|----------|--------|
| v1 | `websockets` library | ❌ incompatible with Chrome permessage-deflate |
| v2 | Raw asyncio + `asyncio.Lock()` | ❌ deadlock on Windows |
| v3 | Raw asyncio, no lock, WS fragmentation | ✅ current |

## Key Files

| File | Role |
|---|---|
| `hermes_bridge_server.py` | Bridge server v3: WS port 19978 + TCP port 19979 |
| `chrome_send.py` | Python client qua TCP, auto-generates requestId |
| `background.js` | Extension MV3 service worker: CDP, message handler, network monitoring |
| `hermes_chrome_controller.py` | Alternative: Playwright `connect_over_cdp` (no extension needed) |
| `start_bridge.bat` | One-click launcher with `PYTHONDONTWRITEBYTECODE=1` |
| `start_chrome_cdp.bat` | Restart Chrome with `--remote-debugging-port=9222` |

## CRITICAL Pitfalls (HARD RULES)

### 0. PORT CONFLICT — silent failure #1
Zombie Python process chiếm port 19978 → bridge server mới không bind được → extension kết nối tới zombie → mọi thứ im lặng fail.
```bash
netstat -ano | grep 19978       # tìm PID lạ
taskkill /F /PID <pid>          # kill zombie
```

### 1. `__pycache__/` DESTROYS the extension
Python tạo `__pycache__/` khi chạy script trong extension dir. Chrome CẤM thư mục `_*`.
**Rule:** LUÔN `python -B`. `start_bridge.bat` đã set `PYTHONDONTWRITEBYTECODE=1`.
```bash
rm -rf __pycache__   # nếu đã lỡ tạo → reload extension trong chrome://extensions
```

### 2. KHÔNG dùng `websockets` library
Chrome extension gửi `Sec-WebSocket-Extensions: permessage-deflate` → `websockets` library xử lý sai → message không đến được.
**Rule:** Bridge server tự implement raw WebSocket framing.

### 3. KHÔNG dùng `asyncio.Lock()`
Gây deadlock trên Windows trong bridge server v2. V3 dùng global variable trực tiếp (asyncio single-threaded an toàn).

### 4. Network.enable CHỈ gọi 1 lần
Phiên bản cũ gọi `Network.enable` trong `ensureDebuggerAttached` domains list + `handleNetworkStart` → double-call → CDP deadlock 30s.
**Fix:** Removed `'Network.enable'` khỏi domains list trong `ensureDebuggerAttached`. Chỉ gọi từ `handleNetworkStart`.

### 5. WebSocket fragmentation
`read_frame()` phải reassemble continuation frames (FIN bit). Không có → mất data với response >125 bytes (screenshot, DOM lớn).

### 6. CDP debugger "already attached"
Sau extension reload, debugger cũ vẫn attached. `ensureDebuggerAttached` catch lỗi → detach → re-attach.

## Diagnostic Flow (extension không kết nối)

```
1. netstat -ano | grep 19978        → tìm PID lạ → kill
2. ls __pycache__                   → nếu có → rm -rf → reload extension
3. Reload extension (chrome://extensions, nút 🔄)
4. Đợi 3-10s → python -B chrome_send.py ping
5. Nếu vẫn fail → restart bridge server + reload extension
6. Nếu service worker bị terminate (>30s idle) → click icon extension trên toolbar
```

## Network Monitoring (API Reverse Engineering)

Bắt tất cả XHR/fetch requests qua CDP Network domain:

```python
send_command({'type': 'network_start', 'tabId': tab_id})
# reload page hoặc tương tác
time.sleep(5)
send_command({'type': 'network_stop', 'tabId': tab_id})
# → [{url, method, status, headers, postData, responseHeaders, ...}]
```

Đã test thành công: NotebookLM (batchexecute RPC), YouTube (youtubei API), ChatGPT (backend-api).

## CDP Controller Alternative

`hermes_chrome_controller.py` dùng Playwright `connect_over_cdp` — không cần extension, không cần bridge server.
Cần Chrome restart 1 lần với `--remote-debugging-port=9222` (dùng `start_chrome_cdp.bat`).

```bash
python hermes_chrome_controller.py ping
python hermes_chrome_controller.py navigate --url https://google.com
python hermes_chrome_controller.py execute_js --code "document.title"
```

## All Commands

ping, list_tabs, get_current_tab, navigate (url+tabId hoặc newUrl), click (selector hoặc x+y), type, screenshot, execute_js, get_dom, get_text, scroll, press_key, download, new_tab, close_tab, network_start, network_stop, cdp_command, reload_self

## Python API

```python
from chrome_send import send_command
send_command({'type': 'ping'})
send_command({'type': 'navigate', 'newUrl': 'https://example.com'})
send_command({'type': 'execute_js', 'tabId': 123, 'code': 'document.title'})
```
