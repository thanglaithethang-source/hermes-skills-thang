# Playwright Chrome Connect — Tất cả phương pháp

**Ngày nghiên cứu:** 2026-07-22 | **Chrome:** 150.0.7871.129 | **Playwright:** 1.60.0 | **Windows 10**

## Tổng quan

Mục tiêu: kết nối Playwright vào Chrome 150 mà KHÔNG cần `--remote-debugging-port`.

Kết quả: **Playwright `launch(channel="chrome")` dùng pipe mode nội bộ** — không cần port, không cần script khởi động, không cần bridge.

## Phát hiện quan trọng

Khi kiểm tra mã nguồn Playwright (`_impl/_browser_type.py`), phát hiện:

```python
# connect_over_cdp() → gửi message "connectOverCDP" đến Playwright driver
response = await self._channel.send_return_as_dict(
    "connectOverCDP", TimeoutSettings.launch_timeout, params
)

# connect() → tạo JsonPipeTransport cho giao tiếp pipe nội bộ
pipe_channel = await local_utils._channel.send_return_as_dict("connect", ...)["pipe"]
transport = JsonPipeTransport(self._connection._loop, pipe_channel)
```

**Kết luận:** Playwright driver LUÔN dùng pipe mode nội bộ để giao tiếp với browser. Khi launch `channel="chrome"`, Playwright tự thêm `--remote-debugging-pipe` vào Chrome args, không mở port TCP nào.

---

## Bảng so sánh đầy đủ

| # | Phương pháp | Cần port? | Code | Kết quả test |
|---|------------|-----------|------|-------------|
| 0 | `launch(channel="chrome")` | ❌ KHÔNG (pipe nội bộ) | `p.chromium.launch(channel="chrome")` | ✅ Thành công |
| 1 | `connect_over_cdp` + port | ✅ CÓ | Launch Chrome với `--remote-debugging-port=9222` → `connect_over_cdp("http://127.0.0.1:9222")` | ✅ Thành công |
| 2 | `--remote-debugging-pipe` + bridge | ❌ KHÔNG (cần bridge) | Bridge Python chuyển pipe ↔ WebSocket → connect_over_cdp | ⚠️ Phức tạp, fragile |
| 3 | Selenium Wire | ✅ CÓ (tự quản lý) | `seleniumwire.webdriver.Chrome()` | ⚠️ Cần ChromeDriver + port |
| 4 | `launch_persistent_context` | ❌ KHÔNG (pipe nội bộ) | `p.chromium.launch_persistent_context(channel="chrome", user_data_dir=...)` | ✅ Thành công |

---

## Code mẫu từng phương pháp

### Phương pháp 0: launch(channel="chrome") — ⭐ KHUYẾN DÙNG

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",          # Tự tìm Chrome cài sẵn
        headless=False,            # Hiển thị cửa sổ
        args=["--disable-blink-features=AutomationControlled"],
    )
    print(f"Browser version: {browser.version}")  # 150.0.7871.129

    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    page.goto("https://httpbin.org/ip")
    print(page.content())
    browser.close()
```

### Phương pháp 1: connect_over_cdp (Chrome đã chạy với port)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Chrome phải đang chạy với --remote-debugging-port=9222
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    # LUÔN dùng 127.0.0.1, KHÔNG dùng localhost (Playwright resolve → IPv6 ::1)
    
    default_context = browser.contexts[0]
    page = default_context.pages[0] if default_context.pages else default_context.new_page()
    page.goto("https://httpbin.org/ip")
    print(page.content())
    browser.close()
```

### Phương pháp 2: --remote-debugging-pipe + bridge (nâng cao)

Chrome hỗ trợ `--remote-debugging-pipe` (CDP qua stdin/stdout). Nhưng Playwright `connect_over_cdp` CHỈ nhận WebSocket URL. Cần bridge:

```
Chrome (--remote-debugging-pipe)  ←stdin/stdout→  PipeBridge  ←ws://→  Playwright
```

```python
import subprocess, struct, json, threading, asyncio, websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def read_cdp_msg(stream):
    raw_len = stream.read(4)
    if not raw_len or len(raw_len) < 4: return None
    return json.loads(stream.read(struct.unpack("<I", raw_len)[0]))

def write_cdp_msg(stream, msg):
    raw = json.dumps(msg).encode()
    stream.write(struct.pack("<I", len(raw)))
    stream.write(raw)
    stream.flush()

async def pipe_bridge(chrome_proc, port=9223):
    async def handler(ws):
        async def ws2pipe():
            async for msg in ws:
                write_cdp_msg(chrome_proc.stdin, json.loads(msg))
        async def pipe2ws():
            while True:
                msg = read_cdp_msg(chrome_proc.stdout)
                if msg is None: break
                await ws.send(json.dumps(msg))
        await asyncio.gather(ws2pipe(), pipe2ws())
    async with websockets.serve(handler, "localhost", port):
        await asyncio.Future()  # run forever

# Launch Chrome với pipe
proc = subprocess.Popen(
    [CHROME, "--remote-debugging-pipe", "--user-data-dir=C:\\temp\\chrome-pipe",
     "--no-first-run", "about:blank"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
threading.Thread(target=lambda: asyncio.run(pipe_bridge(proc)), daemon=True).start()

# Connect Playwright qua bridge
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
    # ...
```

> ⚠️ Phương pháp này phức tạp, ít ổn định. Chỉ dùng khi thực sự cần pipe mode thủ công.

### Phương pháp 4: launch_persistent_context (giữ session)

```python
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(Path.home() / "playwright-chrome-profile"),
        channel="chrome",
        headless=False,
        viewport={"width": 1280, "height": 720},
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://httpbin.org/ip")
    print(page.content())
    context.close()
```

---

## Pitfall: Playwright `connect_over_cdp` + `localhost` → IPv6 fail

**Triệu chứng:** `curl http://localhost:9222/json/version` OK, nhưng `connect_over_cdp("http://localhost:9222")` báo `connect ECONNREFUSED ::1:9222`.

**Root cause:** Playwright resolve `localhost` → `::1` (IPv6) trước, nhưng Chrome CDP chỉ bind `127.0.0.1` (IPv4).

**Fix:** LUÔN dùng `http://127.0.0.1:9222`.

---

## Kết quả test thực tế (2026-07-22)

```
=== Method 0: launch(channel="chrome") ===
✅ Đã kết nối Chrome qua channel='chrome'
   Browser version: 150.0.7871.129
   Page title: (httpbin.org/ip response)
✅ Hoàn tất thành công!

=== Method 1: connect_over_cdp + port 9222 ===
✅ Đã kết nối!
   Browser contexts: 1
   Page title: (httpbin.org/ip response)
✅ Hoàn tất thành công!
```

---

## Kết luận

| Tình huống | Dùng |
|---|---|
| Bắt đầu automation mới | `launch(channel="chrome")` |
| Chrome ĐÃ chạy với `--remote-debugging-port` | `connect_over_cdp("http://127.0.0.1:9222")` |
| Chrome ĐÃ chạy, KHÔNG có port debug | Extension bridge hoặc restart Chrome với port |
| Cần giữ cookie/login giữa các lần chạy | `launch_persistent_context(channel="chrome", user_data_dir=...)` |
| Cần network interception phức tạp | Selenium Wire hoặc Playwright `page.route()` |
