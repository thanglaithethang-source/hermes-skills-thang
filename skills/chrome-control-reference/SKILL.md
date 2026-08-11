---
name: chrome-control-reference
description: Tài liệu tham khảo về audit findings, pitfalls, và fixes cho chrome-cdp-control skill. KHÔNG dùng trực tiếp — load chrome-cdp-control để kiểm soát Chrome.
version: 1.0.0
---

# Chrome Control — Reference & Pitfalls

Đây là tài liệu bổ trợ cho skill `chrome-cdp-control`. Load `chrome-cdp-control` để kiểm soát Chrome.

## Quick pitfalls

1. `__pycache__/` làm Chrome từ chối load extension → luôn `python -B`
2. Chrome 150 cần `--remote-allow-origins=*` + `--user-data-dir` riêng
3. `127.0.0.1` không `localhost` (Playwright IPv6 bug)
4. Playwright sync API không chạy trong asyncio → dùng subprocess
5. `network_start` cần CDP attach lần đầu (có thể chậm)
6. `document.cookie` không lấy httpOnly → cần CDP Network.getCookies

## Fixed issues (đã resolve)

- WS fragmentation: `read_frame()` reassembles continuation frames
- Network.enable double-call: removed from auto-domains, only in handleNetworkStart
- asyncio.Lock deadlock: v3 bridge server is lock-free
- Force-detach: stale debugger auto-detached before re-attach
- pong case: background.js cleanly ignores pong
- CDP_URL: 127.0.0.1 not localhost
- __name__ guard: bridge server importable without running

## Known unfixed issues (từ 4-model audit)

- 🔴 Frame size DoS in bridge server (64-bit length unbounded)
- 🔴 Selector injection in background.js (XSS via CDP)
- 🔴 get_cookies() wrong response path
- 🟡 pending dict leak, no WS read timeout, double connect()

## v4.0 Debugger Detach Fix (test 2026-07-25)

Background.js updated to v4 with 3 fixes for debugger detach issue:

### Fix 1: ensureDebuggerAttached — Runtime.evaluate ping
v3 chỉ check `activeDebuggerTabs.has(tabId)` → trả true ngay cả khi debugger đã bị Chrome detach silently. v4 ping bằng `Runtime.evaluate('1')` — test CẢ debugger attachment LẪN page accessibility. Nếu "Cannot access" → throw (restricted page, không retry). Nếu other error → re-attach.

### Fix 2: sendCDP — retry trên mọi error trừ "Cannot access"
v3 chỉ retry khi error chứa "Detached" hoặc "not attached". v4 retry trên MỌI error, trừ "Cannot access chrome-extension:// URL" (restricted page, retry không giúp).

### Fix 3: handleNavigate — waitForPageLoad
v3 trả về ngay sau `chrome.tabs.update()` → page chưa load xong. v4 đợi `tab.status === 'complete'` (poll 500ms, timeout 30s).

### PITFALL: KHÔNG auto re-attach trên onDetach event
Test thực tế: auto re-attach trong `chrome.debugger.onDetach` listener gây **reload loop** — extension connect/disconnect liên tục, bridge server overload. **Đã revert.** Chỉ xóa `activeDebuggerTabs.delete(tabId)` trong onDetach.

### PITFALL: KHÔNG refresh Runtime.enable trong onEvent cho SPA navigation
Test thực tế: gọi `Runtime.enable` trong `Page.frameNavigated` event cũng gây reload loop. **Đã revert.**

### LIMITATION: Manifest V3 Service Worker lifecycle
Chrome Manifest V3 service worker bị kill sau ~30s không hoạt động. Extension auto-reconnect nhưng kết nối mất.

**Triệu chứng:** Bridge log hiện `[WS] Extension connected` rồi `[WS] Extension disconnected` ngay sau.

**Workaround khi cần chạy command:**
1. KHÔNG restart bridge server lung tung — nó vẫn chạy, extension sẽ auto-reconnect sau vài giây
2. Đợi log `[WS] Extension connected` rồi chạy command NGAY (cửa sổ ~10-30s)
3. Giữ popup extension mở (click icon trên toolbar) → service worker không bị kill khi popup active
4. Nếu mất kết nối hoàn toàn: kill bridge server sạch (kill process + đợi TIME_WAIT hết), start lại
5. Hoặc dùng `browser_navigate` + `browser_snapshot` + `browser_click` (Hermes built-in)

**Workaround cho multi-step flows:**
1. Dùng `browser_navigate` + `browser_snapshot` + `browser_click` (Hermes built-in)
2. Hoặc dùng Playwright `connect_over_cdp` — Playwright tự handle attach/detach
3. Hoặc chia nhỏ: navigate → 2-3 CDP commands → navigate lại nếu detach
