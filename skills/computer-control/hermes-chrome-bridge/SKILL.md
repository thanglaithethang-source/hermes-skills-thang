---
name: hermes-chrome-bridge
description: Connect Hermes Agent to Chrome via CDP. Three approaches — Playwright launch(channel="chrome") for fresh instances (pipe mode, no port), Playwright connect_over_cdp for already-running Chrome, or legacy Hermes Bridge extension. All inherit user session and cookies.
version: 2.1.0
platforms: [windows]
metadata:
  tags: [chrome, browser, cdp, automation, playwright, extension, bridge]
---

# Hermes Chrome Bridge

Ba phương pháp kiểm soát Chrome từ Hermes Agent:

| Phương pháp | Khi dùng | Cần port? | Cần extension? | Độ ổn định |
|---|---|---|---|---|
| **Playwright `launch(channel="chrome")`** | ⭐ Khởi động Chrome mới | ❌ KHÔNG (pipe nội bộ) | ❌ Không | ⭐⭐⭐⭐⭐ |
| **Playwright `connect_over_cdp`** | Chrome đã chạy sẵn + port | ✅ Cần port | ❌ Không | ⭐⭐⭐⭐ |
| Extension WebSocket bridge | Chrome đã chạy sẵn, không port | ❌ Không | ✅ Có | ⭐⭐⭐ |

Cả ba đều kế thừa toàn bộ session/cookie/login của Sếp (kết nối vào Chrome profile thật).

> **Quan trọng:** Playwright khi launch `channel="chrome"` TỰ ĐỘNG dùng `--remote-debugging-pipe` nội bộ (CDP qua stdin/stdout). Bạn không cần mở port, không cần script khởi động Chrome, không cần bridge — Playwright làm hết. Đây là cách chính thức, ổn định nhất.

---

## Quick Start — Pre-flight check & kết nối trong 30 giây

Khi Sếp yêu cầu "kết nối Chrome", KHÔNG khởi động lại ngay. Kiểm tra trạng thái trước:

```bash
# 1. Chrome đang chạy?
tasklist | grep -i chrome | head -5

# 2. Bridge server đang listen? (Extension mode)
netstat -ano | grep -E "19978|19979"

# 3. CDP port 9222 đang bind? (Playwright CDP mode)
netstat -ano | grep 9222
```

**Nếu bridge server CHƯA chạy** (port 19979 không LISTENING):
```bash
cd "$HOME/Downloads/_projects/hermes-chrome-extension"
PYTHONDONTWRITEBYTECODE=1 python -B hermes_bridge_server.py &
sleep 2
netstat -ano | grep -E "19978|19979"  # verify
```

**Nếu ping trả về "No response"** (bridge server đang LISTENING nhưng extension SW đã chết):
```bash
# 1. Tìm bridge server PID
BRIDGE_PID=$(netstat -ano | grep "19979.*LISTENING" | awk '{print $5}' | head -1)

# 2. Kill + restart bridge server (background)
taskkill /F /PID $BRIDGE_PID
cd "$HOME/Downloads/_projects/hermes-chrome-extension"
PYTHONDONTWRITEBYTECODE=1 python -B hermes_bridge_server.py &  # background

# 3. Đợi extension auto-reconnect (2-3 giây)
sleep 3

# 4. Verify lại
python -B chrome_send.py ping
```
Extension tự động reconnect khi bridge server restart — KHÔNG cần click icon, KHÔNG cần computer_use.

> **QUAN TRỌNG:** KHÔNG dùng `computer_use` để click icon extension hay bất kỳ thao tác Chrome nào. Dùng TERMINAL/CODE cho mọi tương tác Chrome. Sếp đã cấm computer_use cho Chrome — bridge + CDP + execute_js làm được hết.

**Verify kết nối** (cả 2 phải OK):
```bash
python -B chrome_send.py ping       # extension phản hồi?
python -B chrome_send.py list_tabs   # thấy tabs?
```

Nếu ping OK → Chrome đã kiểm soát. Chọn phương pháp phù hợp bên dưới cho automation cụ thể.

---

## Phương pháp 0: Playwright launch(channel="chrome") — KHÔNG CẦN PORT ⭐

**Đây là cách đơn giản và ổn định nhất.** Playwright tự tìm Chrome đã cài trên máy, tự launch, tự quản lý vòng đời. Dùng **pipe mode nội bộ** — CDP qua stdin/stdout, không mở cổng TCP nào.

### Khi nào dùng
- Bắt đầu automation từ đầu (không có Chrome đang chạy)
- Muốn code ngắn nhất, không cần script khởi động Chrome
- Cần giữ session/profile của Sếp (dùng `--user-data-dir` hoặc `launch_persistent_context`)

### Code mẫu

```python
from playwright.sync_api import sync_playwright

# Cách 1: Launch cơ bản — Playwright tự quản lý mọi thứ
with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",       # Tự tìm Chrome cài sẵn
        headless=False,         # Hiển thị cửa sổ
    )
    page = browser.new_page()
    page.goto("https://httpbin.org/ip")
    print(page.content())
    browser.close()
```

```python
# Cách 2: Persistent context — giữ cookie/login giữa các lần chạy
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(Path.home() / "playwright-chrome-profile"),
        channel="chrome",
        headless=False,
    )
    page = context.new_page()
    page.goto("https://example.com")
    context.close()
```

### Cách hoạt động

```
Playwright (Python)
    │
    ▼ subprocess.Popen + pipe
Chrome (launch với --remote-debugging-pipe nội bộ)
    │
    ▼ CDP qua stdin/stdout (Playwright driver)
Chrome Tabs
```

### Xác nhận
- **Đã test thành công** trên Windows 10, Chrome 150.0.7871.129, Playwright 1.60.0 (2026-07-22)
- `browser.version` → `"150.0.7871.129"`
- Không cần `--remote-debugging-port`, không cần `taskkill`, không cần script PowerShell

### Hạn chế
- Playwright kiểm soát toàn bộ vòng đời browser — khi `browser.close()` thì Chrome tắt
- Không connect vào Chrome instance ĐANG CHẠY SẴN (dùng Phương pháp 1 cho trường hợp đó)
- Cần Playwright đã cài (`pip install playwright`)

Chi tiết đầy đủ về các phương pháp thay thế (pipe bridge, Selenium Wire): `references/playwright-chrome-connect-methods.md`.

---

## Phương pháp 1: Playwright connectOverCDP — Chrome ĐÃ CHẠY SẴN

**Dùng khi Chrome đã được launch với `--remote-debugging-port`.** Dùng Playwright kết nối trực tiếp vào Chrome qua CDP.

### Cách hoạt động

```
Hermes Agent
    │
    ▼ Python (playwright.chromium.connect_over_cdp)
Chrome (--remote-debugging-port=9222)
    │
    ▼ CDP native
Chrome Tabs (kế thừa session/profile của Sếp)
```

### Khởi động Chrome

```powershell
# Cách 1: Script PowerShell tự động (khuyến nghị cho Chrome 150+)
# Kill all Chrome → clean locks → main User Data → verify → auto-fallback temp dir
powershell -ExecutionPolicy Bypass -File scripts/fix-chrome-9222.ps1

# Cách 2: start_chrome_cdp.bat (legacy, có thể fail với Chrome 150)
start_chrome_cdp.bat

# Cách 3: Thủ công với temp user-data-dir (đảm bảo hoạt động)
$td = "$env:TEMP\chrome-debug-9222"; rm -r -fo $td -ea 0; mkdir $td -fo | Out-Null
taskkill /f /im chrome.exe 2>$null; Start-Sleep 2
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --remote-debugging-port=9222 --remote-allow-origins=* `
    --user-data-dir="$td" --no-first-run
```

> **Chrome 150 caveat**: Main User Data directory có thể suppress `--remote-debugging-port` ngay cả sau khi kill+clean locks. Dùng `--user-data-dir=<temp>` để bypass. Chi tiết: xem pitfall "Chrome 150 từ chối --remote-debugging-port".

### Gửi lệnh

```bash
# CLI (tương thích ngược với chrome_send.py)
python hermes_chrome_controller.py ping
python hermes_chrome_controller.py list_tabs
python hermes_chrome_controller.py navigate --url https://google.com
python hermes_chrome_controller.py click --selector "button.submit" --tab_id 0
python hermes_chrome_controller.py execute_js --code "document.title"
python hermes_chrome_controller.py screenshot
```

```python
# Python
from hermes_chrome_controller import get_controller, send_command

# Cách 1: dùng send_command API (tương thích với code cũ)
result = send_command({'type': 'list_tabs'})
result = send_command({'type': 'navigate', 'url': 'https://google.com'})

# Cách 2: dùng controller object trực tiếp
ctrl = get_controller()
ctrl.navigate("https://google.com")
ctrl.click("#submit")
ctrl.screenshot(path="/tmp/shot.png")
title = ctrl.execute_js("document.title")["result"]
```

### Yêu cầu

- **Playwright** (`pip install playwright`) — đã có sẵn trên hệ thống
- Chrome launch với `--remote-debugging-port=9222`
- Không cần extension, không cần bridge server

### Mapping API

| `chrome_send.py` (legacy) | `hermes_chrome_controller.py` | Ghi chú |
|---|---|---|
| `send_command({type: 'ping'})` | `send_command({type: 'ping'})` | API tương thích |
| `send_command({type: 'list_tabs'})` | `send_command({type: 'list_tabs'})` | |
| `send_command({type: 'navigate', url: ...})` | `send_command({type: 'navigate', url: ...})` | |
| `send_command({type: 'click', selector: ...})` | `send_command({type: 'click', selector: ...})` | |
| `send_command({type: 'type', text: ..., selector: ...})` | `send_command({type: 'type', text: ..., selector: ...})` | |
| `send_command({type: 'screenshot', format: ...})` | `send_command({type: 'screenshot', format: ...})` | |
| `send_command({type: 'execute_js', code: ...})` | `send_command({type: 'execute_js', code: ...})` | |

Chi tiết so sánh 3 phương pháp (CDP raw, Playwright, MCP) xem `references/playwright-cdp-alternative.md`.

---

## Phương pháp 3: Extension WebSocket bridge (LEGACY)

Kết nối Hermes Agent với Chrome thông qua Chrome Extension + CDP. Extension chạy trong Chrome, kế thừa toàn bộ session/cookie/login của Sếp. Hermes gửi lệnh qua TCP → Bridge Server → WebSocket → Extension → CDP.

## Kiến trúc (legacy)

```
Hermes Agent
    │
    ▼ TCP:19979
Bridge Server (hermes_bridge_server.py)
    │
    ▼ WebSocket:19978
Chrome Extension (Hermes Bridge)
    │
    ▼ CDP (chrome.debugger)
Chrome Tabs
```

## Project location

`C:\Users\thang\Downloads\_projects\hermes-chrome-extension`

Extension ID: `klghdnedebacaciemlnhchdghkoodgke`

### Các file quan trọng

| File | Mục đích | Phương pháp |
|---|---|---|
| `hermes_chrome_controller.py` | Controller mới, drop-in replacement cho `chrome_send.py` | Playwright |
| `start_chrome_cdp.bat` | Script launch Chrome với `--remote-debugging-port=9222` | Playwright |
| `chrome_send.py` | Gửi lệnh qua TCP bridge server | Extension (legacy) |
| `hermes_bridge_server.py` | Bridge server TCP ↔ WebSocket | Extension (legacy) |
| `background.js` | Chrome extension service worker | Extension (legacy) |
| `ALTERNATIVES_ANALYSIS.md` | Phân tích chi tiết 3 giải pháp thay thế | Reference |

## Khởi động

```bash
# Cách 1: Script .bat
start_bridge.bat

# Cách 2: Python trực tiếp
cd C:\Users\thang\Downloads\_projects\hermes-chrome-extension
python hermes_bridge_server.py
```

Bridge server mở 2 port:
- **19978** — WebSocket server cho extension kết nối
- **19979** — TCP server cho Hermes gửi lệnh

Extension tự động reconnect mỗi 3 giây nếu mất kết nối. Service worker được giữ alive bằng alarm 30 giây.

## Gửi lệnh

### CLI
```bash
python chrome_send.py ping
python chrome_send.py list_tabs
python chrome_send.py get_current_tab
python chrome_send.py navigate --url https://google.com --tabId 123
python chrome_send.py click --selector "button.submit" --tabId 123
python chrome_send.py type --text "hello" --selector "input" --tabId 123
python chrome_send.py screenshot --format jpeg --quality 50
python chrome_send.py execute_js --code "document.title"
python chrome_send.py scroll --amount 300
python chrome_send.py press_key --key Enter
python chrome_send.py get_dom --selector body --maxDepth 3
python chrome_send.py new_tab --url https://example.com
python chrome_send.py close_tab --tabId 123
```

### Python
```python
from chrome_send import send_command

# Không cần tabId — tự lấy current tab nếu không có
result = send_command({'type': 'list_tabs'})
result = send_command({'type': 'navigate', 'url': 'https://google.com'})
result = send_command({'type': 'click', 'selector': 'button.submit', 'tabId': 123})
result = send_command({'type': 'screenshot', 'format': 'jpeg', 'quality': 50})
result = send_command({'type': 'execute_js', 'code': 'document.title'})
```

## Các lệnh hỗ trợ

| Command | Mô tả | Params chính |
|---------|-------|-------------|
| `ping` | Kiểm tra kết nối | — |
| `list_tabs` | Liệt kê tất cả tabs | — |
| `get_current_tab` | Lấy tab đang active | — |
| `navigate` | Điều hướng / mở tab mới | `url`, `tabId`, `newUrl` |
| `click` | Click theo selector hoặc tọa độ | `selector`, `tabId`, `x`, `y` |
| `type` | Gõ text | `text`, `selector`, `tabId` |
| `screenshot` | Chụp màn hình (base64) | `format`, `quality`, `tabId` |
| `get_dom` | Đọc cấu trúc DOM | `selector`, `maxDepth`, `tabId` |
| `get_text` | Đọc text content | `selector`, `tabId` |
| `execute_js` | Thực thi JavaScript | `code`, `tabId` |
| `scroll` | Cuộn trang | `amount`, `selector`, `tabId` |
| `press_key` | Nhấn phím | `key`, `tabId` |
| `download` | Tải file | `url`, `filename` |
| `new_tab` | Mở tab mới | `url` |
| `close_tab` | Đóng tab | `tabId` |
| `reload_self` | Reload extension | — |
| `cdp_command` | Gửi CDP command trực tiếp | `method`, `params`, `tabId` |
| `network_start` | Bắt đầu bắt network requests | `tabId` |
| `network_stop` | Dừng + trả về captured requests | `tabId` |

## Network Monitoring — Bắt API calls từ web bất kỳ

Extension có khả năng bắt tất cả network requests qua CDP Network domain.

```python
from chrome_send import send_command
import time

tab_id = 142066066
send_command({'type': 'network_start', 'tabId': tab_id})
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'location.reload()'})
time.sleep(5)
r = send_command({'type': 'network_stop', 'tabId': tab_id})
for req in r.get('requests', []):
    print(f"{req['method']} {req['status']} {req['url'][:120]}")
    if req.get('postData'): print(f"  Body: {req['postData'][:200]}")
```

## API Reverse Engineering Workflow

Dùng cho **mọi web app** — thay vì click giao diện, giao tiếp thẳng với backend API:

1. **Bắt API**: `network_start` → trigger action → `network_stop`
2. **Lấy auth**: `execute_js` → `document.cookie` + tìm token trong localStorage
3. **Replay**: Gọi lại bằng Python `requests` với cookies/auth từ Chrome
4. **Automate**: Viết script gọi API trực tiếp, không cần browser

## Pitfall: KHÔNG dùng computer_use cho Chrome — dùng terminal/bridge

Sếp đã sửa nhiều lần: khi cần kiểm soát Chrome, DÙNG CODE (terminal → chrome_send.py / CDP qua bridge), KHÔNG dùng `computer_use` (desktop automation). Code-based nhanh hơn, chính xác hơn, không steal focus, không phụ thuộc GUI state.

**Workflow khi ping "No response" (service worker chết):**
1. `netstat -ano | grep 19979 | grep LISTENING` → lấy bridge PID
2. `taskkill /F /PID <pid>` → kill bridge cũ
3. Chạy lại `python -B hermes_bridge_server.py` (background, notify_on_complete=false)
4. Đợi 3s → extension tự reconnect (log: `[WS] Extension connected`)
5. `python -B chrome_send.py ping` → verify

KHÔNG click icon extension bằng computer_use. KHÔNG dùng computer_use cho bất kỳ thao tác Chrome nào khi đã có bridge.

## Pitfall: `Network.enable` double-enable gây treo (background.js L85)

**Triệu chứng:** `network_start` luôn timeout 30s, nhưng `cdp_command` (Runtime.evaluate, Page.captureScreenshot) và `list_tabs`/`ping` vẫn hoạt động bình thường.

**Root cause:** `Network.enable` bị gọi 2 lần trên cùng một tab:
1. **Lần 1** (background.js `ensureDebuggerAttached`, domains list): enable `Network.enable` khi lần đầu attach debugger — OK
2. **Lần 2** (background.js `handleNetworkStart` → `sendCDP`): gọi `Network.enable` lần nữa vì tab đã có trong `activeDebuggerTabs`, `ensureDebuggerAttached` return ngay — **TREO**

Trong Chrome CDP (đặc biệt MV3 Service Worker), gọi `Network.enable` khi domain đã được enable sẵn khiến `chrome.debugger.sendCommand` return Promise không bao giờ settle → `handleNetworkStart` không bao giờ gửi `network_started` response → bridge server timeout.

**Fix:** Xóa `'Network.enable'` khỏi domains list trong `ensureDebuggerAttached`:
```javascript
// TRƯỚC (gây treo):
const domains = ['Page.enable', 'Runtime.enable', 'DOM.enable', 'Input.enable', 'Network.enable'];

// SAU (đã fix):
const domains = ['Page.enable', 'Runtime.enable', 'DOM.enable', 'Input.enable'];
```

`Network.enable` chỉ nên được gọi duy nhất từ `handleNetworkStart`. Các lệnh khác (`cdp_command`, `click`, `screenshot`, ...) không cần Network domain để hoạt động.

## Pitfall: KHÔNG dùng `websockets` library

**Lỗi:** Python `websockets` library không tương thích với Chrome extension WebSocket. Chrome gửi extension `permessage-deflate` trong handshake, `websockets` library accept nhưng xử lý sai → message không đến được.

**Giải pháp:** Bridge server dùng **raw asyncio TCP** — tự implement WebSocket handshake và frame parsing. KHÔNG accept `permessage-deflate` extension trong handshake response.

Chi tiết xem `references/websocket-raw-implementation.md`.

## Pitfall: Keepalive ping/pong noise

Extension gửi text-level keepalive ping `{type: 'ping', timestamp: ...}` mỗi 20 giây. Nếu bridge server respond bằng text `{type: 'pong', ...}`, extension không recognize type `pong` → gửi error `{type: 'error', error: 'Unknown command: pong'}` → tạo noise cycle vô ích mỗi 20s.

**Fix:** Server IGNORE text-level ping từ extension. Chrome's internal WebSocket protocol-level ping/pong (opcode 0x9/0xA) đã handle keepalive ở tầng transport. Hoặc nếu muốn respond, thêm `case 'pong': break;` vào `handleMessage` trong `background.js`.

## Pitfall: Concurrent writes to ext_writer — DO NOT use asyncio.Lock

Vấn đề tưởng tượng: nhiều coroutine ghi vào `ext_writer` gây frame interleaving.

**Sự thật:** asyncio là single-threaded cooperative multitasking. `writer.write()` + `await writer.drain()` là atomic trong thực tế (không có `await` giữa `write` và `drain` để yield). `asyncio.Lock()` tạo ra DEADLOCK trên Windows khi dùng trong `async with` pattern với nhiều connection handler — bridge server v2 bị hỏng hoàn toàn vì lock.

**Fix đúng:** KHÔNG dùng lock. Bridge server v3 bỏ lock, hoạt động ổn định. Nếu thực sự cần synchronization, dùng `asyncio.Queue` thay vì `Lock`.

## Pitfall: __pycache__ breaks Chrome extension loading

**Lỗi:** Python tạo thư mục `__pycache__/` khi chạy script trong thư mục extension. Chrome từ chối load extension với thư mục bắt đầu bằng `_`:
```
Cannot load extension with file or directory name __pycache__.
Filenames starting with "_" are reserved for use by the system.
```

**Fix:**
1. Luôn dùng `python -B` khi chạy script trong thư mục extension
2. Set `PYTHONDONTWRITEBYTECODE=1` trong môi trường
3. Script `start_bridge.bat` đã được cấu hình sẵn `set PYTHONDONTWRITEBYTECODE=1`
4. Nếu lỡ tạo: `rm -rf __pycache__/` rồi reload extension

## Pitfall: Bridge server phải có `if __name__ == '__main__'` guard

Bridge server dùng `asyncio.run(main())` ở module level → khi import (vd: để test) sẽ chạy server và bind port. Luôn bọc trong:
```python
if __name__ == '__main__':
    asyncio.run(main())
```

## Pitfall: WebSocket fragmentation — phải reassemble continuation frames

**Triệu chứng:** Lệnh có response lớn (screenshot, get_dom, network_captures) luôn timeout 30s, nhưng ping/list_tabs nhỏ vẫn OK.

**Root cause:** Chrome WebSocket fragment message > ~125 bytes thành nhiều frame (FIN=0). Bridge server `read_frame` gốc không check FIN bit → mỗi fragment được parse như 1 message riêng → `json.loads()` fail trên fragment đầu → `except: continue` → response bị nuốt → TCP client timeout.

**Fix:** `read_frame` phải reassemble continuation frames:
```python
async def read_frame(reader):
    header = await reader.readexactly(2)
    opcode = header[0] & 0x0F
    fin = (header[0] & 0x80) != 0
    # ... read first payload ...
    # Reassemble continuation frames
    while not fin:
        ch = await reader.readexactly(2)
        cfin = (ch[0] & 0x80) != 0
        # ... read continuation payload, append ...
        fin = cfin
    return opcode, payload
```
Verification script: `scripts/verify_fragmentation.py`.

## Pitfall: Chrome 150 từ chối `--remote-debugging-port`

**Triệu chứng:** Chrome khởi động bình thường nhưng `curl localhost:9222/json/version` return `connection refused`. `netstat` không thấy port 9222. Chrome process chạy (PID alive) nhưng port KHÔNG bind.

**Root cause:** Chrome 150 trên Windows bỏ qua `--remote-debugging-port` trong các trường hợp:
- Có instance Chrome khác đang chạy (không có flag) → instance mới chỉ mở tab trong instance cũ, không bind port
- Profile bị lock → Chrome fallback sang profile khác không có flag
- **NGAY CẢ SAU KHI kill+clean lock files**, Chrome 150 vẫn có thể bỏ qua flag khi dùng User Data directory chính — Chrome detect session state cũ và suppress `--remote-debugging-port`
- Cần thêm `--remote-allow-origins=*` (Chrome 140+)

### Workflow KHÔNG hoạt động (đã test 2026-07-22)

Kill toàn bộ chrome.exe + xóa lockfile/SingletonLock → start với main User Data:
```powershell
taskkill /F /IM chrome.exe
Remove-Item "$env:LOCALAPPDATA\Google\Chrome\User Data\lockfile" -Force
Start-Process 'chrome.exe' -ArgumentList '--remote-debugging-port=9222', '--remote-allow-origins=*'
```
→ **Thất bại**: Chrome PID alive, port 9222 KHÔNG bind. Chrome bỏ qua flag vì detect profile state.

### Workflow HOẠT ĐỘNG (confirmed 2026-07-22)

**Dùng main profile + `--remote-allow-origins=*`:**

```powershell
# Kill all Chrome
taskkill /F /IM chrome.exe 2>$null; Start-Sleep -Seconds 3

# Start with main profile + required flags
Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' `
    -ArgumentList '--remote-debugging-port=9222', '--remote-allow-origins=*'
Start-Sleep -Seconds 8

# Verify
curl http://127.0.0.1:9222/json/version
```

→ **Thành công**: port 9222 bind, session/profile của Sếp được giữ nguyên (bookmarks, extensions, logins, cookies).

```powershell
$tempDir = "$env:TEMP\chrome-debug-9222"
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

taskkill /F /IM chrome.exe 2>$null
Start-Sleep -Seconds 2

Start-Process 'chrome.exe' -ArgumentList `
    '--remote-debugging-port=9222',
    '--remote-allow-origins=*',
    '--no-first-run',
    '--no-default-browser-check',
    "--user-data-dir=$tempDir"
Start-Sleep -Seconds 8

# Verify
netstat -ano | Select-String ":9222.*LISTENING"
curl http://127.0.0.1:9222/json/version
```

→ **Thành công**: port 9222 bind trên 127.0.0.1, CDP endpoint hoạt động.

**Script tự động**: `scripts/fix-chrome-9222.ps1` — kill, clean locks, start với main User Data, verify, auto-fallback sang temp dir nếu fail. Chạy: `powershell -ExecutionPolicy Bypass -File scripts/fix-chrome-9222.ps1`

### Trade-off

- ✅ **Temp profile**: debug port luôn hoạt động, ổn định
- ❌ **Temp profile**: không có bookmarks, extensions, logins, history của Sếp
- Nếu cần real profile + debug port → dùng Extension bridge (Method 2), không cần `--remote-debugging-port`

Chi tiết chẩn đoán: `references/chrome-150-debug-port.md`.

## Pitfall: Playwright `connect_over_cdp` dùng IPv6 `::1` thay vì `127.0.0.1`

**Triệu chứng:** `curl http://localhost:9222/json/version` OK, nhưng Playwright báo `connect ECONNREFUSED ::1:9222`.

**Root cause:** Playwright resolve `localhost` → `::1` (IPv6) trước, nhưng Chrome CDP chỉ bind trên `127.0.0.1` (IPv4). `connect_over_cdp("http://localhost:9222")` → fail.

**Fix:** Luôn dùng `http://127.0.0.1:9222` thay vì `http://localhost:9222`:
```python
CDP_URL = "http://127.0.0.1:9222"  # NOT localhost
browser = pw.chromium.connect_over_cdp(CDP_URL)
```

## Pitfall: `hermes_chrome.py` `get_cookies()` luôn trả về empty dict (double `.get('result')`)

**Triệu chứng:** `ctrl.get_cookies(tab_id)` luôn trả về `{}` dù tab có cookies.

**Root cause:** `hermes_chrome.py:113` gọi `.get('result', {}).get('result', {}).get('value', '')` — NHƯNG extension trả về `{type: 'js_result', result: {type: 'string', value: 'cookie_string'}}`. Một `.get('result')` đã tới CDP result object `{type, value}`. `.get('result')` thứ hai trên object đó trả về `{}` (không có key 'result') → `.get('value')` luôn là `''`.

**Fix:**
```python
# TRƯỚC (broken — line 113):
raw = r.get('result', {}).get('result', {}).get('value', '')

# SAU (fixed):
raw = r.get('result', {}).get('value', '')
```

**Confirmed:** Simulation confirmed double `.get('result')` path always yields empty string.

## Pitfall: `bridge.py` là dead code — `send_to_extension()` luôn raise `NotImplementedError`

File `bridge.py` trong project không hoạt động. `send_to_extension()` raise `NotImplementedError` với message hướng dẫn dùng WebSocket bridge. `send_via_cdp()` là stub rỗng (`pass`). File này gây confusion cho người mới đọc codebase. Nên xóa hoặc thêm comment `# DEPRECATED — use hermes_chrome.py or hermes_chrome_controller.py instead`.

## Pitfall: CLI argument naming inconsistency — `tabId` vs `tab_id`

| File | Key dùng |
|------|----------|
| `hermes_chrome.py` (TCP bridge) | `tabId` (camelCase) |
| `chrome_send.py` (TCP bridge CLI) | `tabId` (camelCase — từ `--tabId`) |
| `hermes_chrome_controller.py` (CDP CLI) | `tab_id` (snake_case — từ `--tab_id`) |
| `background.js` (extension) | `tabId` (camelCase) |

Khi switch giữa 2 CLI, phải đổi `--tabId` → `--tab_id`. Nên thống nhất về camelCase (`tabId`) vì đó là convention của extension protocol.

## Pitfall: Error double-wrapping khi extension không connect trong `capture_api_requests()`

Khi extension không connect, bridge server trả về `{'error': 'Extension not connected'}` (KHÔNG có key `type`). `hermes_chrome.py` `capture_api_requests()` check `r.get('type') != 'network_started'` → `None != 'network_started'` → `True` → return `{'error': {'error': 'Extension not connected'}}`. Error bị wrap 2 lớp, mất context.

## Pitfall: `HermesChromeController` (CDP) missing methods so với extension path

| Method | Extension path (`ChromeController`) | CDP path (`HermesChromeController`) |
|--------|:---:|:---:|
| `cdp()` — raw CDP command | ✅ | ❌ |
| `capture_api_requests()` — network monitoring | ✅ | ❌ |
| `get_cookies()` — session cookies | ✅ (broken, see pitfall above) | ❌ |
| `download()` — tải file | ✅ | ❌ |

Khi cần các tính năng này với CDP mode, phải dùng Playwright API trực tiếp hoặc gọi CDP qua `page.evaluate()` / `page.route()`.

## Pitfall: Stale debugger sau khi extension reload

Sau khi extension reload (`reload_self` hoặc reload thủ công), Chrome vẫn giữ debugger attachment cũ. Extension mới không attach được → lỗi "Another debugger is already attached".

**Fix trong `ensureDebuggerAttached`:**
```javascript
try {
    await chrome.debugger.attach({ tabId }, '1.3');
} catch(err) {
    if (err.message.includes('already attached')) {
        try { await chrome.debugger.detach({ tabId }); } catch(e) {}
        await chrome.debugger.attach({ tabId }, '1.3');
    } else { throw err; }
}
```

### Extension không kết nối (ping "No response")
- Service worker bị terminate sau 30s idle. Bridge server vẫn LISTENING nhưng extension không connected.
- **FIX ĐÃ VERIFIED**: Kill bridge server PID + restart `hermes_bridge_server.py` → extension tự reconnect sau 2-3 giây → ping lại.
- KHÔNG dùng computer_use để click icon — không cần thiết, Sếp đã cấm computer_use cho Chrome.
- Kiểm tra log bridge server: nếu thấy `[WS] Extension connected` → đã kết nối thành công.

### TCP timeout
- Đảm bảo bridge server đang chạy: `netstat -ano | grep 19979`
- Extension phải connected (kiểm tra log bridge server)
- Mỗi command phải có `requestId` (chrome_send.py tự thêm)

### Port conflict
```bash
netstat -ano | grep -E "19978|19979"
taskkill /F /PID <pid>
```

### Debugging deep-dive
Xem `references/debugging-guide.md` — simulated client, common failure modes, bridge server evolution (v1→v2→v3).
Xem `references/code-audit-2026-07-21.md` — 20 issues found by 3-subagent audit.
Xem `references/integration-audit-2026-07-22.md` — full trace audit (ChromeController → TCP → Bridge → WS → Extension; 10 findings).
Chạy `scripts/verify_fragmentation.py` để test WS fragmentation reassembly.
