---
name: browser-api-hijack
description: "Bắt API từ bất kỳ web app nào qua CDP Network monitoring, rồi gọi lại bằng Python requests — kế thừa session/login từ Chrome của Sếp. Thay vì click giao diện, giao tiếp thẳng với backend."
version: 2.1.0
platforms: [windows]
metadata:
  hermes:
    tags: [api, reverse-engineering, cdp, chrome-extension, network-monitoring]
    related_skills: [computer-use, browser-research]
---

# Browser API Hijack

Kỹ thuật: với bất kỳ web app nào, bắt API calls qua Chrome DevTools Protocol (CDP) Network domain, extract cookies/auth tokens, rồi gọi lại API bằng Python `requests` — kế thừa toàn bộ session/login của Sếp từ Chrome.

## Kiến trúc

```
Python (chrome_send.py) → TCP:19979 → Bridge Server → WS:19978 → Chrome Extension → CDP → Web page
                                                                                   → Network events
```

## Prerequisites

Extension Hermes Bridge đã cài trong Chrome, bridge server đang chạy. Xem `sep-workspace` → `references/hermes-bridge.md` để setup và troubleshooting.

**Quan trọng:** `network_start` / `network_stop` / `cdp_command` chỉ có trong bản background.js enhanced (có thêm `handleNetworkStart`, `handleNetworkStop`, `handleCDPCommand`, `captureNetworkEvent`). Bản clean background.js chỉ có các lệnh cơ bản (ping, execute_js, navigate, etc.). Nếu `network_start` trả về "Unknown command" → cần dùng bản enhanced.

```bash
cd C:\Users\thang\Downloads\_projects\hermes-chrome-extension
python -B hermes_bridge_server.py    # Khởi động bridge server
python -B chrome_send.py ping        # Test kết nối
```

## QUICK DECISION — Chọn phương pháp ĐÚNG NGAY (đọc trước khi hành động!)

| Web app | Phương pháp | Lý do |
|---|---|---|
| **ChatGPT** | **3** (CDP Pre-load Interceptor) | WebSocket streaming, KHÔNG dùng `network_start` |
| **Gemini** | **3** (CDP Pre-load Interceptor) | WebSocket + anti-abuse |
| **YouTube** | **1** (CDP Network) hoặc Python requests | HTTP only, replay được |
| Generic HTTP API | **1** (CDP Network) | Đơn giản nhất |
| Unknown app | Thử **1** trước, nếu thiếu endpoint chính → **3** | |

> **LỖI PHỔ BIẾN NHẤT:** Dùng `network_start` (Method 1) cho ChatGPT/Gemini → chỉ bắt được analytics/tracking, KHÔNG bắt được chat API (WebSocket). Nếu Sếp nói "bắt API ChatGPT" → dùng Method 3 NGAY, không dùng `network_start`.

## Pitfall: Bridge "No response" — restart bridge server, KHÔNG dùng computer_use

**Triệu chứng:** `ping` trả `{type: 'error', error: 'No response'}` hoặc `WinError 10053`. Bridge server đang LISTENING (port 19979) nhưng extension service worker đã chết.

**Root cause:** Service worker bị terminate sau 30s idle. Bridge server vẫn chạy nhưng không có WebSocket client (extension) kết nối.

**Fix ĐÃ VERIFIED (2026-07-29):**
```bash
# 1. Tìm bridge PID
BRIDGE_PID=$(netstat -ano | grep "19979.*LISTENING" | awk '{print $5}' | head -1)

# 2. Kill + restart (background)
taskkill /F /PID $BRIDGE_PID
cd "$HOME/Downloads/_projects/hermes-chrome-extension"
PYTHONDONTWRITEBYTECODE=1 python -B hermes_bridge_server.py &  # background

# 3. Đợi 2-3s extension auto-reconnect
sleep 3

# 4. Ping lại
python -B chrome_send.py ping
```

Extension tự động reconnect khi bridge server restart — KHÔNG cần click icon, KHÔNG cần computer_use. Sếp đã cấm dùng computer_use cho Chrome khi có bridge.

## Hai phương pháp bắt API

### Phương pháp 1: CDP Network monitoring (`network_start`/`network_stop`)

Dùng khi web app chỉ dùng HTTP/XHR/fetch thông thường. Bắt được mọi HTTP request/response.

**Hạn chế:** KHÔNG bắt được WebSocket messages (xem Pitfall bên dưới).

### Phương pháp 2: JS Interceptor injection (fetch/XHR/WS)

Dùng khi web app dùng WebSocket để stream (ChatGPT, Discord, Slack) hoặc khi CDP Network không bắt đủ. Inject JS patch `window.fetch`, `XMLHttpRequest`, `WebSocket.prototype.send` trực tiếp vào page context — bắt được TẤT CẢ API traffic kể cả WebSocket sends.

**Khi nào dùng:**
- Web app dùng WebSocket (wss://) cho real-time/streaming
- CDP Network monitoring thiếu endpoint chính (chỉ bắt được analytics/tracking)
- Cần bắt cả request body VÀ response body
- Service Worker fetch không hiện trong CDP Network

**Hạn chế quan trọng:** Interceptor inject SAU khi page đã load → WebSocket đã mở → `onmessage` listeners đã đăng ký → KHÔNG bắt được WS receive messages (chỉ bắt được WS send). Để bắt cả WS receive, dùng Phương pháp 3.

Xem template: `templates/fetch_interceptor_template.py`

### Phương pháp 3: CDP Pre-load Interceptor (STRONGEST — bắt TẤT CẢ traffic kể cả WS receive)

Dùng `Page.addScriptToEvaluateOnNewDocument` để inject interceptor TRƯỚC KHI page scripts chạy. Sau đó reload page → interceptor chạy đầu tiên → bắt được mọi fetch, XHR, WebSocket send VÀ receive từ lúc page khởi tạo.

**Khi nào dùng:**
- Cần bắt WebSocket receive messages (stream tokens từ server)
- Web app mở WebSocket connection ngay khi page load
- Phương pháp 2 chỉ bắt được ws_send nhưng thiếu ws_recv
- Cần full request headers + full response bodies

**Cách hoạt động:**
```
1. Page.addScriptToEvaluateOnNewDocument(source=INTERCEPTOR_JS)
   → Chrome đăng ký script chạy trước mọi script khác
2. Page.reload()
   → Page reload → interceptor chạy ĐẦU TIÊN → patch fetch/XHR/WS
3. Page scripts chạy → mở WebSocket → interceptor đã sẵn sàng → bắt ALL
```

```python
from chrome_send import send_command

# 1. Inject interceptor pre-load
send_command({
    'type': 'cdp_command',
    'method': 'Page.addScriptToEvaluateOnNewDocument',
    'params': {'source': INTERCEPTOR_JS},  # same JS as Phương pháp 2
    'tabId': tab_id
})

# 2. Reload page
send_command({
    'type': 'cdp_command',
    'method': 'Page.reload',
    'params': {},
    'tabId': tab_id
})

# 3. Wait for page to load + API calls
time.sleep(12)

# 4. Trigger action (type message, click button, etc.)
# ... same as Phương pháp 2 ...

# 5. Collect captured data
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'JSON.stringify(window.__CAPTURE__ || {fetch_calls:[], ws_events:[]})',
        'returnByValue': True
    },
    'tabId': tab_id
})
captured = json.loads(r['result']['result']['value'])
```

**Ưu điểm so với Phương pháp 2:**
- Bắt được WebSocket RECEIVE messages (stream tokens từ server)
- Interceptor chạy trước Service Worker → bắt được SW fetch
- Full response bodies (không bị truncate bởi timing)
- Đã test thành công: ChatGPT — bắt 112 fetch calls + 25 WS events (22 receive) so với Phương pháp 2 chỉ bắt 24 fetch + 2 WS events (0 receive)

Xem template: `templates/cdp_preload_interceptor.py`

## Workflow tổng quát (bất kỳ web nào)

### Bước 1: Bắt API calls

#### Cách 1a: CDP Network monitoring (HTTP only)

```python
from chrome_send import send_command
import time

tab_id = 142066066  # Lấy từ list_tabs

# Bắt đầu theo dõi network
send_command({'type': 'network_start', 'tabId': tab_id})

# Thực hiện hành động trigger API (click, reload, type...)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'location.reload()'})
# HOẶC click nút:
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': '''
  document.querySelector('button[aria-label="Send"]').click()
'''})

time.sleep(3)  # Đợi requests hoàn thành

# Dừng và lấy kết quả
result = send_command({'type': 'network_stop', 'tabId': tab_id})
requests = result.get('requests', [])
```

#### Cách 1b: JS Interceptor injection (HTTP + WebSocket)

```python
from chrome_send import send_command
import json, time

tab_id = 142067923

# Inject interceptor trước khi trigger action
interceptor_js = '''
(function() {
    window.__API_LOG__ = [];
    
    // 1. Intercept fetch
    var origFetch = window.fetch;
    window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
        var method = (init && init.method) || 'GET';
        var body = (init && init.body) ? String(init.body).substring(0, 5000) : null;
        var entry = {type: 'fetch', method: method, url: url, body: body, timestamp: Date.now()};
        window.__API_LOG__.push(entry);
        return origFetch.apply(this, arguments).then(function(resp) {
            entry.status = resp.status;
            try { resp.clone().text().then(function(t) { entry.response = t.substring(0, 5000); }).catch(function(){}); } catch(e) {}
            return resp;
        });
    };
    
    // 2. Intercept XHR
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__m = method; this.__u = url;
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body) {
        var self = this;
        var entry = {type: 'xhr', method: this.__m, url: this.__u, body: body ? String(body).substring(0, 5000) : null, timestamp: Date.now()};
        window.__API_LOG__.push(entry);
        this.addEventListener('load', function() {
            entry.status = self.status;
            entry.response = self.responseText ? self.responseText.substring(0, 5000) : null;
        });
        return origSend.apply(this, arguments);
    };
    
    // 3. Intercept WebSocket send
    var origWsSend = WebSocket.prototype.send;
    WebSocket.prototype.send = function(data) {
        window.__API_LOG__.push({
            type: 'ws_send', url: this.url,
            data: typeof data === 'string' ? data.substring(0, 5000) : '[binary]',
            timestamp: Date.now()
        });
        return origWsSend.apply(this, arguments);
    };
    
    // 4. Intercept WebSocket message events
    var origAddEventListener = WebSocket.prototype.addEventListener;
    WebSocket.prototype.addEventListener = function(type, listener, options) {
        if (type === 'message') {
            var self = this;
            var wrapped = function(event) {
                window.__API_LOG__.push({
                    type: 'ws_recv', url: self.url,
                    data: event.data ? String(event.data).substring(0, 5000) : null,
                    timestamp: Date.now()
                });
                return listener.apply(this, arguments);
            };
            return origAddEventListener.call(this, type, wrapped, options);
        }
        return origAddEventListener.apply(this, arguments);
    };
    
    "interceptor_installed";
})()
'''
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': interceptor_js})

# Trigger action (type message, click button, etc.)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'location.reload()'})
time.sleep(10)

# Collect captured API calls
r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'JSON.stringify(window.__API_LOG__ || [])'})
captured = json.loads(r.get('result', {}).get('value', '[]'))
```

**Lưu ý quan trọng về interceptor:**
- Interceptor phải được inject TRƯỚC khi action xảy ra
- WebSocket đã mở TRƯỚC khi inject: `send` interceptor vẫn bắt được future sends, nhưng `onmessage` interceptor chỉ bắt được nếu listener được thêm SAU khi inject (patch `addEventListener` bắt listener mới)
- Để bắt WS messages từ connection đã mở: patch `WebSocket.prototype.addEventListener` (như trên) — các listener mới sẽ được wrap
- Response body của fetch: đọc bất đồng bộ qua `resp.clone().text()`, có thể chưa sẵn sàng khi đọc `__API_LOG__` — đợi thêm 1-2s trước khi collect

### Bước 2: Phân tích API

Lọc ra API calls (bỏ qua static resources):

```python
apis = [r for r in requests if any(x in r.get('url','') 
    for x in ['/api/', '/v1/', '/v2/', 'graphql', 'rpc', 'batch', 'backend-api'])]

for req in apis:
    print(f"{req['method']} {req.get('status')} {req['url'][:120]}")
    if req.get('postData'):
        print(f"  Body: {req['postData'][:200]}")
    if req.get('responseHeaders'):
        ct = req['responseHeaders'].get('content-type','')
        print(f"  Content-Type: {ct}")
```

### Bước 3: Extract auth

```python
# Lấy cookies từ browser
r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'document.cookie'})
cookies = {}
for c in r['result']['value'].split('; '):
    if '=' in c:
        k, v = c.split('=', 1)
        cookies[k] = v

# Lấy token từ headers của captured request
auth_headers = {}
for req in requests:
    for k, v in req.get('headers', {}).items():
        if k.lower() in ('authorization', 'x-api-key', 'x-csrf-token'):
            auth_headers[k] = v
```

### Bước 4: Replay API bằng Python

```python
import requests

resp = requests.post(
    'https://api.example.com/v1/endpoint',
    headers={
        'Content-Type': 'application/json',
        'Authorization': auth_headers.get('Authorization', ''),
    },
    cookies=cookies,
    json={"key": "value"},
    timeout=10
)
print(f"Status: {resp.status_code}")
print(resp.json())
```

## Các command có sẵn

| Command | Mô tả |
|---------|-------|
| `ping` | Test kết nối |
| `list_tabs` | Liệt kê tất cả tabs |
| `get_current_tab` | Tab đang active |
| `navigate` | Mở tab mới (`newUrl`) hoặc chuyển tab (`url + tabId`) |
| `execute_js` | Chạy JS trong page context |
| `get_dom` | Đọc cấu trúc DOM (maxDepth) |
| `get_text` | Đọc text content |
| `screenshot` | Chụp màn hình (png/jpeg) |
| `click` | Click element (selector hoặc x,y) |
| `type` | Gõ text |
| `scroll` | Cuộn trang |
| `press_key` | Gửi phím |
| `network_start` | Bắt đầu theo dõi network requests |
| `network_stop` | Dừng + trả về captured requests |
| `cdp_command` | Gửi CDP command trực tiếp |

### Pitfall: `Network.getAllCookies` response nesting — fallback chain

CDP `Network.getAllCookies` response có thể lồng 2 cấp: `r['result']['result']['cookies']` hoặc `r['result']['cookies']` tùy version bridge/extension. Luôn dùng fallback chain:
```python
all_cookies = r.get('result', {}).get('result', {}).get('cookies', [])
if not all_cookies:
    all_cookies = r.get('result', {}).get('cookies', [])
```
Đã gặp 2026-07-26 với YouTube — response nesting khác ChatGPT session trước.

### Pitfall: INNERTUBE_CONTEXT rỗng sau khi navigate — phải extract từ YouTube page đang load

`window.ytcfg.get("INNERTUBE_CONTEXT")` trả `{}` khi page đã navigate away (VD: tab bị đóng, hoặc page hiện tại không phải YouTube). Context là page-specific — mất khi reload/navigate.

**Triệu chứng:** Search API trả `400 Precondition check failed` vì context rỗng.

**Fix:** Luôn navigate tới YouTube home trước khi extract context:
```python
# 1. Navigate to YouTube
send_command({'type': 'navigate', 'tabId': tab_id, 'url': 'https://www.youtube.com/'})
time.sleep(5)
# 2. Verify ytcfg exists
r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'typeof window.ytcfg !== "undefined" ? "exists" : "missing"'})
# 3. Extract context
r2 = send_command({'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': 'JSON.stringify(window.ytcfg.get("INNERTUBE_CONTEXT"))', 'returnByValue': True},
    'tabId': tab_id})
context = json.loads(r2['result']['result']['value'])
```

Lưu context + cookies + api_key vào file để reuse trong long-running sessions (search hàng loạt). Nếu tab bị đóng giữa chừng, mở tab mới → re-extract.

### Pitfall: Tab bị đóng trong long-running API session

Khi chạy 30+ search queries liên tục, tab YouTube có thể bị đóng (Sếp đóng, Chrome crash, hoặc tab ID đổi). `send_command` trả `{"error": "No tab with given id XXX"}`.

**Fix:** Luôn `list_tabs` để tìm tab mới, navigate lại YouTube, re-extract context. Lưu context/cookies/api_key vào file để restore nhanh.

### Pitfall: YouTube subscriber count — Vietnamese locale parsing

YouTube trả subscriber count theo locale Chrome của Sếp (vi-VN). Format: `"230 N người đăng ký"` (N = nghìn = thousand), `"1,05 Tr người đăng ký"` (Tr = triệu = million). **Comma là decimal separator**, không phải thousands separator. `"14,5 N"` = 14,500 (KHÔNG PHẢI 1,450,000).

**Fix:**
```python
import re
def parse_sub_count(s):
    if not s: return 0
    m = re.search(r'([\d.,]+)\s*(n|tr)', s.lower())
    if m:
        num = float(m.group(1).replace('.', '').replace(',', '.'))
        unit = m.group(2)
        if unit == 'n': return int(num * 1000)
        elif unit == 'tr': return int(num * 1000000)
    return 0
```

### Technique: Lấy subscriber count qua `/youtubei/v1/next` endpoint

Browse API (`/youtubei/v1/browse`) KHÔNG trả video list (params cho videos tab không hoạt động) và subscriber count thường rỗng. Cách tốt nhất: dùng `next` endpoint với 1 videoId của kênh đó:

```python
body = {"context": context, "videoId": video_id}
url = f'https://www.youtube.com/youtubei/v1/next?key={api_key}'
resp = requests.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
data = resp.json()
# Parse: data.contents.twoColumnWatchNextResults.results.results.contents[]
# → videoSecondaryInfoRenderer.owner.videoOwnerRenderer.subscriberCountText
```

Response chứa: channel_name, subscriber_count_raw, subscriber_count (number), channel_id.

### Pitfall: Browse API không trả video list

`/youtubei/v1/browse` với `browseId` + `params: "EgZ2aWRlb3PyBgQKAjoA"` (videos tab) trả 200 OK nhưng 0 videoRenderer trong response. Deep scan toàn bộ response cũng không tìm thấy. RSS feed (`/feeds/videos.xml?channel_id=`) trả 15 video nhưng views=0.

**Workaround:** Dùng search API với channel name làm query để tìm video của kênh đó. Hoặc navigate Chrome tới `/@channelhandle/videos` và extract `ytInitialData`.

### Pitfall: YouTube streaming URLs có thể `hasUrl=False`

Player API trả về `streamingData.formats[]` và `adaptiveFormats[]` nhưng `url` field có thể `false` — cần signature decipher (nCipher) để lấy direct download URL. Format metadata (itag, quality, mimeType) vẫn đầy đủ. Nếu cần direct URL, phải implement signature decipher riêng (ngoài scope của API hijack).

### Pitfall: Region-restricted videos trả `playabilityStatus: ERROR`

Một số video (VD: `jNQXGS9QH6c` — "Me at the zoo") trả `playabilityStatus: {status: "ERROR", reason: "Video không có sẵn"}` tùy region. Test replay với video phổ biến không bị region lock (VD: `9bZkp7q19f0` PSY Gangnam Style — 6B views, globally available).

### Technique: Batch search + channel verification workflow

Khi cần research nhiều kênh YouTube (VD: tìm niche đang thắng), workflow tối ưu:

1. **Batch search** — chạy 30-40 search queries qua InnerTube search API, thu 500+ videos, 300+ unique channels. Rate limit: 0.3-0.5s giữa mỗi request.
2. **Filter major brands** — loại TED-Ed, BBC, Netflix, Veritasium, etc. Giữ lại small/mid channels.
3. **Get subscriber count** — dùng `next` endpoint với 1 videoId của mỗi kênh (xem pitfall "Lấy subscriber count" ở trên). 0.3s giữa mỗi request.
4. **Compute V/S ratio** — `max_views / subscriber_count`. Ratio > 5x = strong signal (video views vượt xa subs).
5. **Deep search** — search thêm `"channel name"` + niche-specific queries để thu thập 5-10 video mỗi kênh.
6. **Win Rate** — `wins / total_videos * 100`. Win = video views > median OR > subscriber count.
7. **Save all data** — JSON files cho mỗi giai đoạn (discovery, channel_infos, channel_vids, channel_stats).

**Lưu ý:** Search API chỉ trả ~15-20 results mỗi query. Để có đủ video cho Win Rate, cần search nhiều query variants cho cùng niche + search channel name trực tiếp.

### Pitfall: Search API response structure — parse đúng path

Search response structure:
```
data.contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.contents[]
  → itemSectionRenderer.contents[]
    → videoRenderer: { videoId, title, ownerText, viewCountText, lengthText, publishedTimeText }
```

`ownerText.runs[0].text` = channel name. `ownerText.runs[0].navigationEndpoint.browseEndpoint.browseId` = channel ID. `viewCountText.simpleText` = view count string (cần parse locale).

Nếu `twoColumnSearchResultsRenderer` không có trong response → API trả error (thường `400 Precondition check failed` = context rỗng/hết hạn).

## Pitfalls

### 0. PORT CONFLICT — #1 silent failure khi extension "không kết nối"
Bridge server cũ (leftover process) chiếm port 19978 → server mới không bind được → extension kết nối tới server cũ (đã chết) → mọi lệnh trả về "Extension not connected" dù Sếp đã reload extension nhiều lần. **Đây là bug #1 — luôn kiểm tra đầu tiên.**
```bash
netstat -ano | grep 19978          # Chẩn đoán: PID nào đang LISTEN?
taskkill /F /PID <PID>             # Kill zombie
python -B hermes_bridge_server.py  # Restart sạch
```

### 0b. SW CHẾT — ping "No response" nhưng bridge đang LISTEN
Khác port conflict: bridge server đang chạy OK (port 19979 LISTENING) nhưng extension service worker bị terminate sau 30s idle → không có WebSocket client → mọi lệnh trả "No response" hoặc `WinError 10053`.

**Fix:** Kill bridge PID + restart `hermes_bridge_server.py` → extension tự reconnect sau 2-3s → ping lại. KHÔNG dùng computer_use. Xem chi tiết ở section "Bridge No response" ở trên.

Setup chuẩn + troubleshooting: xem `sep-workspace` → `references/hermes-bridge.md`

### 1. `__pycache__` phá extension
Python tạo `__pycache__/` khi chạy script trong thư mục extension. Chrome cấm thư mục bắt đầu bằng `_`.
**Fix:** Luôn dùng `python -B` hoặc set `PYTHONDONTWRITEBYTECODE=1`.

### `websockets` library không tương thích Chrome
Python `websockets` library bị lỗi với Chrome extension WebSocket (permessage-deflate compression).
**Fix:** Bridge server dùng raw TCP WebSocket (asyncio + manual frame parsing), KHÔNG dùng `websockets` library.

### Debugger detach sau extension reload
Sau `chrome.runtime.reload()`, debugger cũ vẫn attached → không attach được lại.
**Fix:** `ensureDebuggerAttached` đã được sửa để force-detach trước khi attach lại.

### Network events không về nếu tab chưa attach debugger
`network_start` yêu cầu debugger đã attach vào tab. Tab mới cần được attach lần đầu qua 1 lệnh CDP bất kỳ (vd: execute_js).

### AT token xoay vòng nhanh
Google services (NotebookLM) dùng `at=` token trong URL, token này đổi sau mỗi lần reload.
**Workflow:** Luôn bắt request MỚI NHẤT (network_start → reload → network_stop) để lấy token hiện tại.

### network_stop tiêu thụ buffer — gọi 2 lần = rỗng
`network_stop` trả về toàn bộ requests đã bắt VÀ xóa buffer. Gọi `network_stop` lần 2 (không có `network_start` mới ở giữa) → trả về `{"requests": []}`.
**Workflow đúng:** `network_start` → trigger action → `network_stop` (chỉ gọi 1 lần). Muốn bắt lại → `network_start` mới trước.

### KHÔNG parse JSON từ CLI output của chrome_send.py
Khi chạy `chrome_send.py network_stop` qua `terminal()` trong `execute_code`, JSON output chứa control characters (newlines, quotes trong CSP headers, etc.) làm `json.loads()` fail với `Invalid control character` hoặc `Expecting ',' delimiter`.
**Fix:** Gọi `send_command()` trực tiếp từ Python (import `chrome_send`) thay vì parse CLI output. `send_command` trả về dict đã parse sẵn, không cần JSON decode.
```python
# SAI — parse CLI output, dễ vỡ với control chars:
result = terminal('python -B chrome_send.py network_stop --tabId 123')
data = json.loads(result)  # FAIL: control chars trong CSP headers

# ĐÚNG — gọi trực tiếp:
from chrome_send import send_command
result = send_command({'type': 'network_stop', 'tabId': 123})
requests = result.get('requests', [])  # Đã là list, không cần parse
```

### Capture lớn cần lưu file
Một page load ChatGPT tạo ~241 requests, raw JSON ~38KB+. Khi cần phân tích sau, lưu thẳng vào file:
```python
import json
result = send_command({'type': 'network_stop', 'tabId': tab_id})
with open('/tmp/api_capture.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
```

### CDP Network KHÔNG bắt được WebSocket messages
CDP Network domain chỉ bắt HTTP requests/responses. WebSocket messages (wss://) KHÔNG xuất hiện trong `network_stop` results. Nếu web app dùng WS cho real-time/streaming (ChatGPT, Discord, Slack), CDP Network chỉ thấy các HTTP calls phụ (analytics, ping) nhưng thiếu endpoint chính.

**Triệu chứng:** `network_stop` trả về nhiều requests nhưng toàn analytics/tracking, thiếu endpoint conversation/chat chính.

**Fix:** Dùng JS Interceptor injection (Phương pháp 2) — patch `WebSocket.prototype.send` và `addEventListener('message')` để bắt WS traffic. Xem `templates/fetch_interceptor_template.py`.

### Interceptor inject sau khi WebSocket đã mở — chỉ bắt future sends
Khi inject interceptor (Phương pháp 2), nếu WebSocket đã mở sẵn (VD: ChatGPT giữ WS connection suốt session), `WebSocket.prototype.send` patch sẽ bắt được các send MỚI. Nhưng `onmessage`/`addEventListener('message')` patch chỉ wrap các listener ĐƯỢC THÊM SAU khi inject. Listener đã đăng ký trước đó không bị intercept.

**Triệu chứng:** `ws_recv` events = 0, chỉ có `ws_send` events.

**Fix:** Dùng Phương pháp 3 (CDP `Page.addScriptToEvaluateOnNewDocument`) — inject TRƯỚC khi page scripts chạy, interceptor patch WS prototype trước khi app đăng ký listeners → bắt được cả send VÀ receive.

Nếu không thể reload page (mất session state), Phương pháp 2 vẫn bắt được `ws_send` (client gửi) — đủ để hiểu API flow. Server response có thể đọc từ DOM.

### Bearer token trong httpOnly cookie — không đọc được qua execute_js
Web apps như ChatGPT lưu Bearer token trong httpOnly cookies hoặc Service Worker context. `execute_js` chạy trong page context → KHÔNG truy cập được httpOnly cookies hay SW internals.

**Triệu chứng:** `document.cookie` chỉ trả cookies non-httpOnly. `fetch('/api/auth/session')` từ `execute_js` trả về response nhưng không có Authorization header (browser tự thêm header khi fetch từ cùng origin).

**Fix — Cách 1 (tốt nhất):** Dùng CDP `Runtime.evaluate` với `awaitPromise: true` để gọi auth endpoint từ page context — browser tự đính kèm cookies:
```python
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'fetch("/api/auth/session",{credentials:"include"}).then(function(r){return r.json()}).then(function(d){return JSON.stringify(d)})',
        'awaitPromise': True,
        'returnByValue': True
    },
    'tabId': tab_id
})
# r['result']['result']['value'] = JSON string with accessToken
auth_data = json.loads(r['result']['result']['value'])
token = auth_data['accessToken']  # Full Bearer JWT
```

**Fix — Cách 2:** Dùng CDP `Network.getAllCookies` để lấy tất cả cookies (kể cả httpOnly):
```python
r = send_command({
    'type': 'cdp_command',
    'method': 'Network.getAllCookies',
    'params': {},
    'tabId': tab_id
})
cookies = r['result']['cookies']  # List of all cookies across all domains
```

**Fix — Cách 3:** Lấy từ captured request headers (interceptor bắt được `Authorization: Bearer ...` header trong fetch call).

### execute_js không await được async function
`execute_js` (qua `chrome.debugger.sendCommand` → `Runtime.evaluate`) không set `awaitPromise: true` → async function trả về `undefined` thay vì resolved value.

**Triệu chứng:** Gọi `fetch().then().then()` qua `execute_js` → result = `{type: 'undefined'}` hoặc rỗng.

**Fix:** Dùng `cdp_command` với `Runtime.evaluate` + `awaitPromise: true` + `returnByValue: true`:
```python
# SAI — execute_js không await:
r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'fetch("/api/auth/session").then(r=>r.json()).then(d=>JSON.stringify(d))'})
# r['result']['value'] = '' hoặc 'undefined'

# ĐÚNG — CDP Runtime.evaluate với awaitPromise:
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'fetch("/api/auth/session",{credentials:"include"}).then(r=>r.json()).then(d=>JSON.stringify(d))',
        'awaitPromise': True,
        'returnByValue': True
    },
    'tabId': tab_id
})
# r['result']['result']['value'] = JSON string
```

### Python requests KHÔNG replay được ChatGPT — Cloudflare anti-bot chặn 403

ChatGPT có 3 lớp anti-bot mà Python `requests` KHÔNG thể vượt qua, kể cả khi có đầy đủ Bearer token + cookies (kể cả httpOnly) + sentinel tokens:

1. **TLS fingerprint**: Python `requests` dùng TLS fingerprint khác Chrome → Cloudflare detect ngay
2. **`OpenAI-Sentinel-Turnstile-Token`** (3000+ chars): Generated by Cloudflare challenge JS chạy trong browser, KHÔNG phải standard Cloudflare Turnstile widget. Không có global variable hay function nào trả token này. Phải để browser JS tự generate.
3. **`OpenAI-Sentinel-Proof-Token`**: Từ `window.SentinelSDK.token()` (async function, trả JSON string `{"p":"gAAAAA..."}` 7903 chars). Có thể gọi qua CDP `Runtime.evaluate` + `awaitPromise`, nhưng Turnstile token vẫn thiếu.

**Triệu chứng:** `POST /backend-api/f/conversation` từ Python requests HOẶC từ CDP `fetch()` trong page context → `403 {"detail":"Unusual activity has been detected from your device"}`.

**Headers yêu cầu cho `/backend-api/f/conversation` (tất cả đều bắt buộc):**
```
Authorization: Bearer <jwt>
Content-Type: application/json
OpenAI-Sentinel-Chat-Requirements-Token: <finalize_token>
OpenAI-Sentinel-Turnstile-Token: <cloudflare_generated>
OpenAI-Sentinel-Proof-Token: <from SentinelSDK.token()>
x-conduit-token: <from /f/conversation/prepare>
chatgpt-account-id: <account_id>
x-oai-is-client-observation: v1.r.p.M61Sd_1cbaWvxV79
x-oai-turn-trace-id: <uuid>
x-openai-target-path: /backend-api/f/conversation
x-openai-target-route: /backend-api/f/conversation
OAI-Device-Id, OAI-Client-Version, OAI-Client-Build-Number, OAI-Session-Id
```

**Fix — Cách duy nhất hoạt động:** Dùng browser context (type/enter + WS intercept):
1. CDP `Page.addScriptToEvaluateOnNewDocument` inject WS interceptor
2. `Page.reload` → interceptor chạy trước app scripts
3. Type message vào `#prompt-textarea` (ProseMirror) + Enter
4. ChatGPT tự xử lý TẤT CẢ anti-bot tokens (browser JS generate)
5. WS stream bị intercept → parse delta patches → response text
6. Đã test thành công: 24 WS messages, response parse OK

### `/backend-api/f/conversation/prepare` trả 422 "body required" khi gọi từ Python

Endpoint `/backend-api/f/conversation/prepare` yêu cầu body nhưng interceptor bắt `body=None` vì body là `ReadableStream` (không phải JSON string). Gọi từ Python với `json={}` → `422 {"detail":"Invalid conversation body"}`.

**Fix:** Không thể gọi prepare từ Python. Phải để browser tự gọi (qua type/enter flow). Nếu cần conduit_token, bắt từ interceptor (Phương pháp 3).

### WS message duplication — catchups + live = duplicate delta patches

ChatGPT WebSocket gửi cả "catchups" (replay tất cả stream items từ đầu) VÀ live messages. Nếu accumulate delta appends từ TẤT CẢ WS messages, response text bị lặp N lần (N = số lần catchup).

**Triệu chứng:** Response text = "**Sếp**Sếp**Sếp + 5 = 10. + 5 = 10. + 5 = 10." thay vì "**Sếp + 5 = 10."

**Root cause:** Mỗi WS message chứa `payload.payload.stream_item_id` (UUID unique per stream item). Cùng stream_item_id xuất hiện trong cả catchup VÀ live message → accumulate 2 lần.

**Fix:** Deduplicate bằng `stream_item_id`:
```python
seen_ids = set()
for item in ws_messages:
    # ... parse to inner_payload ...
    sid = inner_payload.get('stream_item_id')
    if sid:
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
    # ... parse delta patches ...
```

Đã test: 189 WS messages → 16 unique stream_item_ids → response đúng: "**Sếp + 5 = 10."

### ProseMirror editor — dùng `document.execCommand('insertText')`
ChatGPT dùng ProseMirror contenteditable editor. `chrome_send.py type` command không hoạt động với ProseMirror.

**Cách tốt nhất (đã test 2026-07-24):** Dùng `document.execCommand('insertText')` — không cần escape JS, hoạt động với text dài + ký tự đặc biệt:
```python
# Text nhúng an toàn qua JSON.stringify
review_prompt = "Review this code for bugs..."
js = """
var el = document.querySelector('#prompt-textarea');
if (el) {
    el.focus();
    el.innerHTML = '';
    document.execCommand('selectAll');
    document.execCommand('insertText', false, %s);
    'typed_ok';
} else {
    'no_input_found';
}
""" % json.dumps(review_prompt)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': js})
```

**Cách cũ (vấn đề escaping):** `el.innerHTML = '<p>...</p>'` — dễ vỡ với text chứa `{`, `'`, `\n`. Nếu dùng, phải escape qua `json.dumps()` nhưng vẫn kém ổn định hơn `execCommand`.

Rồi gửi Enter bằng `KeyboardEvent` dispatch (không dùng `press_key`):
```javascript
var el = document.querySelector('#prompt-textarea');
el.focus();
['keydown', 'keypress', 'keyup'].forEach(function(evtName) {
    el.dispatchEvent(new KeyboardEvent(evtName, {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
    }));
});
```

### Đọc response từ DOM — đơn giản + chính xác hơn parse WS
Sau khi gửi message + đợi response, KHÔNG cần parse WS delta patches. Đọc trực tiếp từ DOM — đơn giản, chính xác, không bị truncate:

```python
js = '''
var msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
if (msgs.length === 0) {
    var msgs2 = document.querySelectorAll('.markdown');
    if (msgs2.length > 0) {
        JSON.stringify({source: 'markdown', count: msgs2.length, text: msgs2[msgs2.length-1].textContent.substring(0, 5000)});
    } else {
        JSON.stringify({source: 'none', count: 0, text: ''});
    }
} else {
    var last = msgs[msgs.length - 1];
    JSON.stringify({source: 'assistant', count: msgs.length, text: last.textContent.substring(0, 5000)});
}
'''
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': js, 'returnByValue': True},
    'tabId': tab_id
})
data = json.loads(r['result']['result']['value'])
response_text = data['text']  # Full response, up to 5000 chars
```

**So sánh (test thực tế 2026-07-24):**
- WS delta patch parsing: 25 chars / 2670 chars (97% mất do truncate 8000 chars/giới hạn stream_item_id dedup)
- DOM reading: 2670 chars / 2670 chars (100%)

**Khi nào dùng DOM reading:** Mọi trường hợp cần full response text sau khi ChatGPT đã trả lời xong.
**Khi nào dùng WS parsing:** Cần streaming (token real-time) hoặc cần response trước khi ChatGPT viết xong.

### Pitfall: Bridge execute_js trả empty `result.value` cho JS dài — vẫn chạy nhưng mất return

Khi inject JS interceptor (200+ chars) qua `execute_js` hoặc `cdp_command` + `Runtime.evaluate`, bridge có thể trả `result.value = ''` hoặc `undefined` dù JS ĐÃ thực thi thành công (side effects như `window.__API = []` vẫn có hiệu lực).

**Triệu chứng:** `r.get('result',{}).get('value','?')` trả `?` hoặc rỗng, nhưng kiểm tra `typeof window.__API` sau đó trả `"object"`.

**Root cause:** Có thể do service worker timeout, CDP response trễ, hoặc bridge TCP timeout ngắn hơn CDP eval time.

**Fix — verify riêng biệt:**
```python
# Inject (có thể trả empty, ignore)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': long_interceptor_js})

# Verify injection bằng 1 câu JS ngắn riêng:
r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'typeof window.__API'})
if r.get('result',{}).get('value') == 'object':
    print('Interceptor injected OK')
else:
    print('Injection failed, trying shorter JS...')
```

**Workaround — computer_use cho typing, CDP cho capture:**
Khi `execute_js` với JS dài gặp vấn đề, dùng hybrid: computer_use để click/type (ngắn, reliable), CDP interceptor vẫn inject qua execute_js (JS chạy dù trả empty). Đây là pattern đã test thành công cho Gemini (2026-07-29).

### Pitfall: KHÔNG dùng computer_use cho Chrome — DÙNG TERMINAL/CODE

Sếp đã cấm dùng `computer_use` cho mọi tương tác Chrome khi bridge server có sẵn. Lý do:
- computer_use chậm, steal focus, phụ thuộc GUI state
- Bridge + CDP + execute_js nhanh hơn, chính xác hơn, không cần focus
- Mọi thao tác (click, type, navigate, screenshot, API capture) đều làm được qua `send_command()`

**Workflow chuẩn (CODE-BASED, không computer_use):**
1. Bridge server chạy (`hermes_bridge_server.py`)
2. `send_command({'type': 'list_tabs'})` — tìm tab
3. `send_command({'type': 'cdp_command', ...})` — inject + control
4. `send_command({'type': 'execute_js', ...})` — type + interact
5. Đọc response từ DOM

Chỉ dùng `computer_use` khi KHÔNG có cách nào qua code (app native, không có CDP/bridge).

### Google Trends — pytrends/RSS/JSON API đều 404, dùng Chrome navigate

Google Trends không có public API hoạt động. Đã test 2026-07-29:
- `pytrends` library → 404
- Google Trends RSS endpoint → 404
- Google Trends JSON API endpoints → 404

**Fix:** Dùng Chrome bridge navigate tới `https://trends.google.com/trends/trendingsearches/daily?geo=US&hl=en` + extract DOM text:
```python
from chrome_send import send_command
import json, time

# Navigate
send_command({'type': 'navigate', 'tabId': tab_id, 'url': 'https://trends.google.com/trends/trendingsearches/daily?geo=US&hl=en'})
time.sleep(8)

# Extract text — page render trending keywords + search volume + growth %
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': 'document.body.innerText.substring(0, 8000)', 'returnByValue': True},
    'tabId': tab_id
})
text = r.get('result', {}).get('result', {}).get('value', '')
# Parse: keyword, search volume (200K+, 100K+, 50K+, etc.), growth %, started time
```

### youtube_research package — video_info quá strict, workaround gọi InnerTube player API trực tiếp

`youtube_research.video_info()` trả `error: "Video không có sẵn"` cho video play được bình thường (known issue #1). `snapshot_video()` lưu snapshot nhưng `view_count=None`.

**Workaround (đã test 2026-07-29):** Bypass `video_info`, gọi `/youtubei/v1/player` trực tiếp bằng Python requests:
```python
import requests, hashlib, time, json

# Load context from Chrome
with open(ctx_path) as f:
    ctx = json.load(f)
context = ctx['context']
api_key = ctx['api_key']
cookies = ctx['cookies']
sapisid = ctx['sapisid']

# SAPISIDHASH auth
ts = str(int(time.time()))
origin = "https://www.youtube.com"
sapisidhash = hashlib.sha1((ts + ' ' + sapisid + ' ' + origin).encode()).hexdigest()
headers = {'Authorization': f'SAPISIDHASH {ts}_{sapisidhash}', 'Content-Type': 'application/json', 'Origin': origin}

# Call player API
url = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
body = {"context": context, "videoId": video_id, "playbackContext": {"contentPlaybackContext": {"html5Preference": "HTML5_PREF_WANTS"}}}
resp = requests.post(url, headers=headers, cookies=cookies, json=body, timeout=15)
vd = resp.json().get('videoDetails', {})
view_count = int(vd.get('viewCount', 0))
title = vd.get('title')
channel = vd.get('author')
```

`calculate_vph()` trả dict (không phải Result object) — dùng `vph.get('status')`, `vph.get('vph')`, `vph.get('reason')`.

### Google Trends — pytrends/RSS/JSON API đều 404, dùng Chrome navigate

Google Trends không có public API hoạt động. Đã test 2026-07-29:
- `pytrends` library → 404
- Google Trends RSS endpoint → 404
- Google Trends JSON API endpoints → 404

**Fix:** Dùng Chrome bridge navigate tới `https://trends.google.com/trends/trendingsearches/daily?geo=US&hl=en` + extract DOM text:
```python
from chrome_send import send_command
import json, time

# Navigate
send_command({'type': 'navigate', 'tabId': tab_id, 'url': 'https://trends.google.com/trends/trendingsearches/daily?geo=US&hl=en'})
time.sleep(8)

# Extract text — page render trending keywords + search volume + growth %
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': 'document.body.innerText.substring(0, 8000)', 'returnByValue': True},
    'tabId': tab_id
})
text = r.get('result', {}).get('result', {}).get('value', '')
# Parse: keyword, search volume (200K+, 100K+, 50K+, etc.), growth %, started time
```

### youtube_research package — video_info quá strict, workaround gọi InnerTube player API trực tiếp

`youtube_research.video_info()` trả `error: "Video không có sẵn"` cho video play được bình thường (known issue #1). `snapshot_video()` lưu snapshot nhưng `view_count=None`.

**Workaround (đã test 2026-07-29):** Bypass `video_info`, gọi `/youtubei/v1/player` trực tiếp bằng Python requests:
```python
import requests, hashlib, time, json

# Load context from Chrome
with open(ctx_path) as f:
    ctx = json.load(f)
context = ctx['context']
api_key = ctx['api_key']
cookies = ctx['cookies']
sapisid = ctx['sapisid']

# SAPISIDHASH auth
ts = str(int(time.time()))
origin = "https://www.youtube.com"
sapisidhash = hashlib.sha1((ts + ' ' + sapisid + ' ' + origin).encode()).hexdigest()
headers = {'Authorization': f'SAPISIDHASH {ts}_{sapisidhash}', 'Content-Type': 'application/json', 'Origin': origin}

# Call player API
url = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
body = {"context": context, "videoId": video_id, "playbackContext": {"contentPlaybackContext": {"html5Preference": "HTML5_PREF_WANTS"}}}
resp = requests.post(url, headers=headers, cookies=cookies, json=body, timeout=15)
vd = resp.json().get('videoDetails', {})
view_count = int(vd.get('viewCount', 0))
title = vd.get('title')
channel = vd.get('author')
```

`calculate_vph()` trả dict (không phải Result object) — dùng `vph.get('status')`, `vph.get('vph')`, `vph.get('reason')`.

### Gemini không replay được bằng Python requests — giống ChatGPT

Gemini dùng anti-abuse tương tự ChatGPT. CDP Network monitoring chỉ bắt được CSP reports + analytics. Phải dùng JS interceptor (Phương pháp 2/3) để thấy API calls thật.

Các endpoint chính:
- `POST /_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate` — chat stream
- `POST /_/BardChatUi/data/batchexecute` — RPC (w7J4ee = send, aPya6c = poll)
- `wss://signaler-pa.clients6.google.com/punctual/multi-watch/channel` — real-time

Auth: SAPISIDHASH (giống YouTube) + `at=` token trong query string.

Xem `references/gemini-api.md` cho endpoint catalog + workflow chi tiết.
Xem `references/youtube-research-package-pitfalls.md` cho workarounds khi `youtube_research` package bị `video_info` strict, `snapshot_video` mất view_count, `calculate_vph` trả dict.
Xem `references/youtube-research-package-pitfalls.md` cho workarounds khi `youtube_research` package bị `video_info` strict, `snapshot_video` mất view_count, `calculate_vph` trả dict.

### Ưu tiên code-based control — KHÔNG dùng computer_use cho Chrome
Sếp yêu cầu: khi cần kiểm soát Chrome, dùng CODE (CDP qua bridge/Playwright), KHÔNG dùng `computer_use` (desktop automation). Code-based control nhanh hơn, chính xác hơn, không steal focus, không phụ thuộc GUI state.

**Workflow chuẩn (code-based):**
1. Bridge server chạy (`hermes_bridge_server.py`)
2. `send_command({'type': 'list_tabs'})` — tìm tab
3. `send_command({'type': 'cdp_command', ...})` — inject + control
4. `send_command({'type': 'execute_js', ...})` — type + interact
5. Đọc response từ DOM

Chỉ dùng `computer_use` khi KHÔNG có cách nào qua code (app native, không có CDP/bridge).

## ChatGPT API — Sentinel System & Replay Limitations

ChatGPT có 4-layer anti-bot system. Khi gửi chat message, browser thực hiện:

1. **Sentinel prepare** → POST /backend-api/sentinel/chat-requirements/prepare → `prepare_token`
2. **Sentinel finalize** → POST /backend-api/sentinel/chat-requirements/finalize → `token` (Chat-Requirements-Token)
3. **Conversation prepare** → POST /backend-api/f/conversation/prepare → `conduit_token`
4. **SentinelSDK.token()** → JS function trả về `OpenAI-Sentinel-Proof-Token` (7900+ chars)

Request POST /backend-api/f/conversation cần ĐỦ headers:
- `OpenAI-Sentinel-Chat-Requirements-Token` (từ finalize)
- `OpenAI-Sentinel-Turnstile-Token` (Cloudflare challenge, ~3000 chars, generate bởi browser JS)
- `OpenAI-Sentinel-Proof-Token` (từ SentinelSDK.token())
- `x-conduit-token` (từ conversation prepare)
- `chatgpt-account-id`
- `OAI-Device-Id`, `OAI-Session-Id`, `OAI-Client-Version`, `OAI-Client-Build-Number`
- `x-oai-is-client-observation`, `x-oai-turn-trace-id`
- `x-openai-target-path`, `x-openai-target-route`

### KHÔNG thể replay bằng Python requests

`OpenAI-Sentinel-Turnstile-Token` được generate bởi Cloudflare challenge JS chạy trong browser. Không thể replicate bằng Python. Gọi API từ Python requests (kể cả với Bearer token + cookies đầy đủ) → 403 "Unusual activity detected".

Gọi từ page context (CDP Runtime.evaluate + fetch) cũng 403 nếu thiếu Turnstile token.

### Cách duy nhất hoạt động: CDP type/enter + WS intercept

Phải để browser tự xử lý sentinel/turnstile (type vào input + Enter), rồi intercept WebSocket response:

```python
# 1. Inject WS interceptor qua Page.addScriptToEvaluateOnNewDocument
# 2. Page.reload() (interceptor chạy trước app scripts)
# 3. Type message vào #prompt-textarea (ProseMirror)
# 4. Dispatch Enter keyboard events
# 5. Wait 20s
# 6. Collect window.__WS_RESPONSE__ → parse delta patches → response text
```

Xem template: `templates/chatgpt_chat_replay.py` — script hoàn chỉnh gửi chat + đọc response qua CDP.

### Bearer token — lấy qua /api/auth/session

```python
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {
        'expression': 'fetch("/api/auth/session",{credentials:"include"}).then(r=>r.json()).then(d=>JSON.stringify(d))',
        'awaitPromise': True, 'returnByValue': True
    }, 'tabId': tab_id
})
auth = json.loads(r['result']['result']['value'])
token = auth['accessToken']  # Full Bearer JWT, ~1828 chars
```

### Cookies — lấy qua CDP Network.getAllCookies

```python
r = send_command({
    'type': 'cdp_command', 'method': 'Network.getAllCookies',
    'params': {}, 'tabId': tab_id
})
cookies = {c['name']: c['value'] for c in r['result']['cookies'] if 'chatgpt' in c.get('domain','')}
```

### ChatGPT WS stream format

Server gửi WS messages dạng JSON array. Mỗi message có `payload.encoded_item` chứa SSE-like data:

```
event: delta_encoding
data: "v1"

data: {"type": "resume_conversation_token", ...}

data: {"type": "input_message", ...}

event: delta
data: {"p": "/message/content/parts/0", "o": "append", "v": "**Sếp"}

event: delta
data: {"p": "", "o": "patch", "v": [
  {"p": "/message/content/parts/0", "o": "append", "v": ",** 45"},
  {"p": "/message/status", "o": "replace", "v": "finished_successfully"}
]}

data: {"type": "message_stream_complete"}
data: {"type": "conversation_detail_metadata", "limits_progress": [...]}
data: [DONE]
data: {"type": "done"}
```

Parse: tách `encoded_item` → split theo `data: ` → json.loads → check `p` + `o` + `v` cho delta patches.

### Conversation-update (final message)

WS message cuối cùng có `type: "conversation-update"` với `payload.update_content.message.content.parts[0]` = full response text.

NOTE: Trong thực tế, `conversation-update` KHÔNG phải lúc nào cũng xuất hiện. Có khi chỉ có `conversation-turn-complete` (thiếu full text). Phải accumulate delta appends làm fallback.

## Building API Gateways from Hijacked Web APIs

Khi đã hiểu API flow + có cách gửi/nhận message qua CDP, có thể build OpenAI-compatible gateway để AGI/subagent gọi như API bình thường.

### Kiến trúc

```
AGI/Agent → POST localhost:PORT/v1/chat/completions → FastAPI Gateway
                                                              ↓
                                                    CDP type/enter + WS intercept
                                                              ↓
                                                          Web app tab
                                                              ↓
                                                    Response → OpenAI format → AGI
```

### No-reload mode (inject 1 lần, gửi nhiều message)

Khác với Phương pháp 3 (reload mỗi lần gửi), gateway dùng no-reload mode:
1. Inject WS interceptor qua `Page.addScriptToEvaluateOnNewDocument` (1 lần)
2. `Page.reload()` (1 lần duy nhất)
3. Mỗi message: clear `__WS_RESPONSE__` → type + enter → poll → collect
4. Interceptor đã patch WS prototype → bắt được message mới cho mỗi turn

Ưu điểm: tiết kiệm 12s reload mỗi message. Chỉ reload khi mất kết nối.

### Stream completion detection

Cách biết ChatGPT đã response xong:
1. Tìm `[DONE]` hoặc `"type":"done"` trong `encoded_item`
2. Tìm `conversation-turn-complete` event
3. Count stability: WS message count không đổi trong 4 lần poll liên tiếp (12s)

### Thread safety

Gateway dùng `threading.Lock()` để serialize requests — chỉ 1 message gửi cùng lúc (Chrome tab = single-threaded).

Xem template: `templates/chatgpt_gateway.py` — FastAPI gateway hoàn chỉnh, OpenAI-compatible, ready cho AGI/subagent.

## YouTube InnerTube API — replay thành công bằng Python requests

Khác ChatGPT (Cloudflare anti-bot chặn 403), YouTube InnerTube API **replay được hoàn toàn bằng Python requests** — không có anti-bot layer. Đã test 2026-07-26: player, search, next API đều trả 200 OK.

### Auth — SAPISIDHASH (không phải Bearer)

YouTube/Google dùng SAPISIDHASH thay vì Bearer token:
```
SAPISIDHASH = SHA1(timestamp + ' ' + SAPISID + ' ' + origin)
Authorization: SAPISIDHASH {timestamp}_{hash}
```

SAPISID là **httpOnly cookie** → phải lấy qua CDP `Network.getAllCookies` (không đọc được qua `document.cookie`).

### Extract INNERTUBE config từ page

YouTube expose config qua `window.ytcfg`:
- `ytcfg.get("INNERTUBE_API_KEY")` — public client configuration value (retrieve at runtime)
- `ytcfg.get("INNERTUBE_CONTEXT")` — full context (clientName=WEB, clientVersion, hl, gl, visitorData)

### Endpoints chính (replay được)

| Endpoint | Body keys | Response |
|----------|-----------|----------|
| `/youtubei/v1/player` | `videoId`, `context`, `playbackContext` | videoDetails + streamingData (formats) |
| `/youtubei/v1/search` | `context`, `query` | search results (videoRenderer list) |
| `/youtubei/v1/next` | `context`, `videoId` | recommendations + comments |
| `/youtubei/v1/guide` | `context` | sidebar/home feed |
| `/youtubei/v1/creator/*` | `channelIds`, `context`, `mask` | creator analytics (cần login) |

### Page-level data (không cần API call)

- `window.ytInitialPlayerResponse` — video details + streaming data (available trên watch page)
- `window.ytInitialData` — search results, recommendations, comments (available trên mọi page)

Chi tiết endpoint catalog, auth workflow, code examples: xem `references/youtube-innertube-api.md`
Template replay script: xem `templates/youtube_innertube_replay.py`

### YouTube niche research workflow (batch search + channel verification)

Khi cần tìm niche/keyword YouTube đang thắng (VD: faceless AI channels), dùng workflow:

1. **Batch search** 30-40 queries qua InnerTube search API → 500+ videos, 300+ channels
2. **Filter major brands** — loại TED-Ed, BBC, Netflix, etc.
3. **Get subscriber count** qua `next` endpoint (1 videoId mỗi kênh)
4. **Compute V/S ratio** — max_views / subs. >5x = strong signal
5. **Deep search** — search channel name + niche variants → 5-10 video mỗi kênh
6. **Win Rate** — wins/total * 100. Win = views > median OR > subs
7. **Save JSON** mỗi giai đoạn

Xem `references/youtube-niche-research.md` cho workflow chi tiết + code examples.

## References

- `references/raw-websocket-server.md` — WebSocket bug: `websockets` library vs Chrome Extension
- `references/chatgpt-api-endpoints.md` — ChatGPT backend API endpoint catalog + chat message flow + WebSocket stream format (captured 2026-07-24)
- `references/chatgpt-ws-stream-format.md` — ChatGPT WebSocket stream protocol: subscribe/unsubscribe, delta patches, message markers, stream lifecycle
- `references/chatgpt-sentinel-system.md` — ChatGPT 4-layer anti-bot: sentinel prepare/finalize, turnstile, proof token, conduit token. Headers cần thiết. Tại sao Python requests không replay được.
- `references/chatgpt-cdp-direct-control.md` — Full workflow: gửi task/review tới ChatGPT qua CDP, đọc response từ DOM. Test 2026-07-24. So sánh DOM read vs WS parsing.
- `references/youtube-innertube-api.md` — YouTube InnerTube API endpoint catalog + SAPISIDHASH auth + replay workflow (captured 2026-07-26)
- `references/youtube-niche-research.md` — YouTube niche research workflow: batch search → channel verification → Win Rate → scoring (2026-07-26)
- `references/gemini-api.md` — Gemini API endpoints: StreamGenerate, batchexecute RPCs, Signal WS, auth (SAPISIDHASH + at=). Không replay được bằng Python requests (2026-07-29)
- `references/google-trends-scraping.md` — Google Trends scraping: pytrends/RSS/JSON API đều 404, dùng Chrome navigate + DOM text extract (2026-07-29)
- `references/youtube-research-package-pitfalls.md` — Workarounds khi `youtube_research` package bị `video_info` strict, `snapshot_video` mất view_count, `calculate_vph` trả dict
- `references/vidiq-reverse-engineering.md` — vidIQ metric formulas (VPH, Outlier, vidIQ Score) + backend endpoint catalog từ CRX v3.209.0 analysis (2026-07-29)
- `scripts/replay_template.py` — Generic API replay template (Python requests, cho web apps KHÔNG có Cloudflare anti-bot)
- `scripts/chatgpt_replay.py` — ChatGPT replay script (CDP + type/enter + WS intercept, KHÔNG dùng Python requests vì Cloudflare anti-bot chặn 403)
- `templates/fetch_interceptor_template.py` — JS interceptor injection template (fetch/XHR/WS) — Phương pháp 2
- `templates/cdp_preload_interceptor.py` — CDP pre-load interceptor template (Phương pháp 3 — strongest, catches WS receive)
- `templates/chatgpt_chat_replay.py` — ChatGPT chat replay script: gửi message qua CDP type/enter + WS intercept, parse delta patches thành response text
- `templates/chatgpt_gateway.py` — FastAPI OpenAI-compatible gateway: expose POST /v1/chat/completions, internal CDP type/enter + WS intercept. Thread-safe, no-reload mode, stream completion detection. Ready cho AGI/subagent.
- `templates/youtube_innertube_replay.py` — YouTube InnerTube API replay template: extract SAPISIDHASH auth + replay player/search/next API bằng Python requests

### Pitfalls của Web-API Gateway vs Real API — KHÔNG thể fix 100%

Khi build gateway từ web app (ChatGPT, Claude, etc.) thành OpenAI-compatible endpoint, có 6 flaws bản chất mà KHÔNG cách nào fix hoàn toàn:

1. **Conversation accumulation** — Mỗi request type vào cùng 1 conversation đang mở. Chat càng lúc càng dài → đầy context window → response suy giảm chất lượng. API thật stateless: request đến → response → quên. Gateway phải tạo "New Chat" mỗi request (hoặc định kỳ clear) để giảm vấn đề này, nhưng vẫn không stateless hoàn toàn.

2. **No structured messages** — API thật gửi `messages: [{role: "system", content: "..."}, {role: "user", content: "..."}]` với role rõ ràng. Gateway phải nối tất cả thành 1 đoạn text dài rồi type vào ô input. Web app không hiểu role structure → response bị lệch. Không thể fix — web UI chỉ nhận text, không nhận structured messages.

3. **No streaming** — API thật stream token về dần (SSE). Gateway đợi 25-30s rồi trả 1 cục. AGI/agent cần streaming để reasoning real-time. Có thể implement SSE proxy nhưng WS intercept có delay (~2-3s poll interval) → không true streaming.

4. **No parallelism** — 1 Chrome tab = 1 conversation = 1 request tại lúc. API thật xử lý parallel requests. Gateway dùng `threading.Lock()` để serialize. Không thể fix — Chrome tab là single-threaded.

5. **Browser dependency** — Chrome phải mở, tab phải active, bridge phải chạy. Vô tình tắt tab/Chrome → gateway chết. API thật không phụ thuộc gì.

6. **Rate limit theo gói web** — ChatGPT Plus: ~80 msg/3h. API thật: pay-per-use, không giới hạn. Server track theo account_id → không tránh được.

**Kết luận:** Web-API gateway có thể hoạt động (~80% giống API xịn về format) nhưng bản chất vẫn chậm + phụ thuộc browser + có rate limit. Phù hợp làm backup/fallback, KHÔNG phù hợp làm model chính cho AGI cần tốc độ + parallelism. Đã test thực tế: 19 requests gửi → conversation chất đống → response suy giảm.

### Hermes config integration — wire gateway làm model endpoint

Đã cấu hình ChatGPT Gateway làm custom provider + delegation endpoint trong Hermes config.yaml:

```yaml
# Thêm vào custom_providers:
custom_providers:
  - name: chatgpt-gateway
    base_url: http://127.0.0.1:5678/v1
    api_key: no-key
    model: gpt-5-6-thinking
    models:
      - gpt-5-6-thinking
      - gpt-5-3
      - gpt-5-5

# Delegation (subagent dùng gateway):
delegation:
  provider: custom
  base_url: http://127.0.0.1:5678/v1
  api_key: no-key
  model: gpt-5-6-thinking
```

Set qua CLI:
```bash
hermes config set delegation.provider custom
hermes config set delegation.base_url http://127.0.0.1:5678/v1
hermes config set delegation.api_key no-key
hermes config set delegation.model gpt-5-6-thinking
```

Cần restart Hermes (hoặc /reset) để config có hiệu lực. Main model không đổi — chỉ subagent (delegate_task) dùng ChatGPT Gateway.

### Đã test thực tế — kết quả

Session 20260724: Gateway chạy 19 requests. Sếp phát hiện vấn đề: response trả về từ phiên chat đang mở (conversation accumulation), không giống API thật. Phân tích ra 6 flaws bản chất (xem section "Pitfalls của Web-API Gateway vs Real API" bên trên). Kết luận: gateway phù hợp làm backup, không phù hợp làm model chính cho AGI.

## File locations

```
C:\Users\thang\Downloads\_projects\hermes-chrome-extension\
├── hermes_bridge_server.py   # Bridge server (raw WebSocket + TCP)
├── chrome_send.py             # Python client
├── start_bridge.bat           # Script khởi động nhanh
├── background.js              # Extension service worker
├── manifest.json              # Extension manifest
└── demo_api_call.py           # Demo script replay API
```

Extension ID: `klghdnedebacaciemlnhchdghkoodgke`
