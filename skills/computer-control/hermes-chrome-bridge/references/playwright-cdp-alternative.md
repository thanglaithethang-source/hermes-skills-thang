# Playwright connectOverCDP — Giải pháp thay thế Extension Bridge

**Ngày phân tích:** 2026-07-21 | **Chrome:** 150.0.7871.129 | **Windows 10**

## Bối cảnh

Extension WebSocket bridge có các vấn đề về độ ổn định:
- Service worker bị terminate sau 30s idle
- WebSocket `permessage-deflate` incompatibility
- Cần bridge server riêng (TCP + WebSocket)
- Reconnect không đáng tin cậy

Playwright `connect_over_cdp` loại bỏ tất cả các vấn đề trên bằng cách kết nối trực tiếp vào CDP port của Chrome.

## So sánh 3 giải pháp

| Tiêu chí | CDP WebSocket raw | **Playwright connectOverCDP** | Chrome DevTools MCP |
|---|---|---|---|
| Độ phức tạp | Trung bình — tự code CDP | **Thấp — ~80 dòng Python** | Thấp — config MCP |
| Độ ổn định | Phụ thuộc code tự viết | **Cao — battle-tested** | Trung bình-cao |
| Kế thừa session | ✅ | ✅ | ✅ |
| Auto-wait/retry | ❌ Không có | ✅ Built-in | ⚠️ Không rõ |
| Số dòng code | ~300-500 | **~30-50 wrapper** | ~20 config |
| Yêu cầu | websocket-client | Playwright (đã có) | Clone repo + uv sync |
| Network monitoring | CDP Network.* (tự code) | page.on("request")/page.route() | get_network_requests() |
| Phụ thuộc external | Không | Không | MCP server process |

## Tại sao chọn Playwright connectOverCDP

1. **Đã có sẵn** — Playwright 1.60 đã cài trên hệ thống
2. **API trưởng thành** — auto-wait, retry, selector engine mạnh
3. **Code ít nhất** — mapping 1:1 với API extension hiện tại
4. **Không extension** — bỏ hẳn bridge server, WebSocket handshake issues
5. **Session hoàn hảo** — `browser.contexts[0]` giữ nguyên cookies/login

## Hạn chế cần lưu ý

1. Playwright docs ghi nhận CDP connection "lower fidelity" hơn native Playwright protocol. Nhưng các chức năng cơ bản (click, type, screenshot, JS eval) hoạt động tốt.
2. Cần Chrome launch với `--remote-debugging-port=9222` — phải đóng Chrome trước. Script `start_chrome_cdp.bat` tự động hóa việc này.
3. Một số tính năng nâng cao của Playwright (video recording, tracing) không hoạt động qua CDP.

## Mapping API đầy đủ

| Extension API | Playwright equivalent | CDP raw equivalent |
|---|---|---|
| `list_tabs` | `[p.url for p in browser.contexts[0].pages]` | `GET /json` |
| `get_current_tab` | `browser.contexts[0].pages[-1]` | `GET /json` → last |
| `navigate(url)` | `page.goto(url)` | `Page.navigate` |
| `click(selector)` | `page.click(selector)` | `DOM.querySelector` → `Input.dispatchMouseEvent` |
| `type(text, selector)` | `page.fill(selector, text)` | `Input.insertText` |
| `screenshot()` | `page.screenshot(path=...)` | `Page.captureScreenshot` |
| `execute_js(code)` | `page.evaluate(code)` | `Runtime.evaluate` |
| `get_dom(selector)` | `page.locator(selector).inner_html()` | `DOM.getDocument` → parse |
| `get_text(selector)` | `page.locator(selector).inner_text()` | `DOM.getDocument` → extract |
| `scroll(amount)` | `page.evaluate("window.scrollBy(0,amount)")` | `Input.dispatchMouseEvent` (wheel) |
| `press_key(key)` | `page.keyboard.press(key)` | `Input.dispatchKeyEvent` |
| `new_tab(url)` | `context.new_page()` + `goto(url)` | `PUT /json/new?url=...` |
| `close_tab(id)` | `page.close()` | `GET /json/close/{id}` |

## File liên quan trong project

- `hermes_chrome_controller.py` — Controller chính (~200 dòng, drop-in replacement cho `chrome_send.py`)
- `start_chrome_cdp.bat` — Script launch Chrome với debug port
- `ALTERNATIVES_ANALYSIS.md` — Phân tích chi tiết 3 giải pháp

## Migration path nhanh

```bash
# 1. Launch Chrome với CDP
start_chrome_cdp.bat

# 2. Test kết nối
python hermes_chrome_controller.py ping

# 3. Dùng thay cho chrome_send.py
python hermes_chrome_controller.py navigate --url https://google.com
python hermes_chrome_controller.py execute_js --code "document.title"
```

Hoặc trong code Python:
```python
# Thay thế import cũ:
# from chrome_send import send_command
# ↓
from hermes_chrome_controller import send_command

# API giữ nguyên — không cần sửa code gọi
result = send_command({'type': 'list_tabs'})
```
