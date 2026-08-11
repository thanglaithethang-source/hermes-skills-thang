# YouTube InnerTube API — Endpoint catalog + Auth + Replay workflow

**Ngày capture:** 2026-07-26 | **Tab:** YouTube (youtube.com) | **Locale:** vi-VN, gl=US

YouTube dùng InnerTube API (`/youtubei/v1/*`) cho mọi chức năng: search, player, recommendations, creator analytics. Khác ChatGPT (Cloudflare anti-bot chặn Python requests 403), YouTube InnerTube API **replay được hoàn toàn bằng Python requests** — không có anti-bot layer.

## Auth — SAPISIDHASH

YouTube/Google services dùng SAPISIDHASH thay vì Bearer token. Cơ chế:

```
SAPISIDHASH = SHA1(timestamp + ' ' + SAPISID + ' ' + origin)
Authorization: SAPISIDHASH {timestamp}_{hash}
```

### Lấy SAPISID

SAPISID là **httpOnly cookie** → KHÔNG đọc được qua `document.cookie`. Phải dùng CDP `Network.getAllCookies`:

```python
r = send_command({
    'type': 'cdp_command',
    'method': 'Network.getAllCookies',
    'params': {},
    'tabId': tab_id
})
all_cookies = r.get('result', {}).get('result', {}).get('cookies', [])
if not all_cookies:
    all_cookies = r.get('result', {}).get('cookies', [])  # fallback nesting

yt_cookies = {}
for c in all_cookies:
    if 'youtube.com' in c.get('domain', ''):
        yt_cookies[c['name']] = c['value']

sapisid = yt_cookies.get('SAPISID', '')
```

### Tính SAPISIDHASH

```python
import hashlib, time

origin = 'https://www.youtube.com'
timestamp = int(time.time())
hash_input = f"{timestamp} {sapisid} {origin}"
sapisidhash = hashlib.sha1(hash_input.encode('utf-8')).hexdigest()
auth_header = f"SAPISIDHASH {timestamp}_{sapisidhash}"
```

### Auth cookies quan trọng

| Cookie | httpOnly | Mục đích |
|--------|----------|----------|
| SAPISID | Yes | SAPISIDHASH computation |
| __Secure-1PSID | Yes | Session auth |
| __Secure-3PSID | Yes | Session auth |
| SID | No | Session ID |
| HSID | No | Security token |
| APISID | Yes | API access |
| SSID | Yes | Session |
| LOGIN_INFO | Yes | Login state |
| VISITOR_INFO1_LIVE | No | Visitor tracking |

## INNERTUBE config — extract từ page

YouTube expose config qua `window.ytcfg`:

```python
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'JSON.stringify({api_key: window.ytcfg.get("INNERTUBE_API_KEY"), context: window.ytcfg.get("INNERTUBE_CONTEXT")})',
        'returnByValue': True
    },
    'tabId': tab_id
})
cfg = json.loads(r['result']['result']['value'])
api_key = cfg['api_key']        # AIzaSy...qcW8
context = cfg['context']        # Full INNERTUBE_CONTEXT
visitor_data = context['client']['visitorData']  # Long base64 string
```

### INNERTUBE_CONTEXT structure

```json
{
  "client": {
    "hl": "vi",
    "gl": "US",
    "remoteHost": "171.227.34.126",
    "userAgent": "Mozilla/5.0 ...",
    "clientName": "WEB",
    "clientVersion": "2.20260724.01.01",
    "osName": "Windows",
    "osVersion": "10.0",
    "platform": "DESKTOP",
    "visitorData": "Cgt6S0c2emZwbE5tay..."
  }
}
```

## Headers cần thiết cho replay

```python
headers = {
    'Content-Type': 'application/json',
    'Authorization': auth_header,  # SAPISIDHASH {timestamp}_{hash}
    'X-Goog-AuthUser': '0',
    'X-Goog-Visitor-Id': visitor_data,
    'X-Origin': 'https://www.youtube.com',
    'X-Youtube-Client-Name': '1',
    'X-Youtube-Client-Version': context['client']['clientVersion'],
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'Referer': f'https://www.youtube.com/watch?v={video_id}',
    'Origin': 'https://www.youtube.com',
}
```

## Endpoint catalog

### Core endpoints (replay được bằng Python requests)

| Endpoint | Method | Mô tả | Body keys |
|----------|--------|-------|-----------|
| `/youtubei/v1/player` | POST | Video details + streaming data | `videoId`, `context`, `playbackContext`, `cpn` |
| `/youtubei/v1/search` | POST | Tìm kiếm video | `context`, `query` |
| `/youtubei/v1/next` | POST | Recommendations + comments | `context`, `videoId` |
| `/youtubei/v1/guide` | POST | Sidebar/home feed | `context` |
| `/youtubei/v1/feedback` | POST | Like/dislike | `context`, `feedbackToken` |
| `/youtubei/v1/log_event` | POST | Telemetry (gzip compressed) | — |
| `/youtubei/v1/get_panel` | POST | Panel data | `panelId`, `params`, `context` |
| `/youtubei/v1/notification/get_unseen_count` | POST | Unread notifications | `context` |

### Creator endpoints (cần login session)

| Endpoint | Method | Mô tả | Body keys |
|----------|--------|-------|-----------|
| `/youtubei/v1/creator/get_creator_channels` | POST | Channel info | `channelIds`, `context`, `mask` |
| `/youtubei/v1/creator/get_creator_videos` | POST | Creator video list | `videoIds`, `context`, `mask` |
| `/youtubei/v1/creator/list_creator_playlists` | POST | Playlists | `channelId`, `context`, `mask` |
| `/youtubei/v1/yta_web/join` | POST | Analytics (hourly views) | `nodes`, `connectors`, `context` |

### Other API endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/jnn/v1/GenerateIT` | POST | Generate IT token |
| `/api/stats/qoe` | POST | Quality of experience stats |
| `/api/stats/playback` | POST | Playback stats |
| `/api/stats/atr` | POST | ATR stats |

## Replay workflow

### 1. Player API — video details + streaming data

```python
import requests, json, hashlib, time

video_id = '9bZkp7q19f0'
player_body = {
    "videoId": video_id,
    "context": context,
    "playbackContext": {
        "contentPlaybackContext": {
            "html5Preference": "HTML5_PREF_WANTS",
            "signatureTimestamp": 20195
        }
    }
}
url = f'https://www.youtube.com/youtubei/v1/player?key={api_key}&prettyPrint=false'
resp = requests.post(url, headers=headers, cookies=yt_cookies, json=player_body, timeout=15)
data = resp.json()

# Response structure:
# data.videoDetails: title, videoId, author, channelId, lengthSeconds, viewCount, keywords, shortDescription
# data.playabilityStatus: status (OK/ERROR), reason
# data.streamingData: formats (combined), adaptiveFormats (separate audio/video)
```

### 2. Search API

```python
search_body = {
    "context": context,
    "query": "AI automation 2026"
}
url = f'https://www.youtube.com/youtubei/v1/search?key={api_key}&prettyPrint=false'
resp = requests.post(url, headers=headers, cookies=yt_cookies, json=search_body, timeout=15)
data = resp.json()

# Parse: data.contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.contents[]
# → itemSectionRenderer.contents[] → videoRenderer: videoId, title, ownerText, viewCountText, lengthText, publishedTimeText
```

### 3. Next API (recommendations)

```python
next_body = {
    "context": context,
    "videoId": "9bZkp7q19f0"
}
url = f'https://www.youtube.com/youtubei/v1/next?key={api_key}&prettyPrint=false'
resp = requests.post(url, headers=headers, cookies=yt_cookies, json=next_body, timeout=15)
data = resp.json()

# Parse: data.contents.twoColumnWatchNextResults.results.results.contents[]
# → itemSectionRenderer.contents[] → videoRenderer (recommendations)
# → secondaryResults.secondaryResults.results[] → compactVideoRenderer (sidebar recommendations)
```

## Page-level data extraction (không cần API call)

Ngoài API replay, có thể extract data trực tiếp từ page JS objects:

```python
# ytInitialPlayerResponse — video details (available on watch page)
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {
        'expression': 'JSON.stringify(window.ytInitialPlayerResponse)',
        'returnByValue': True
    },
    'tabId': tab_id
})
player = json.loads(r['result']['result']['value'])
# player.videoDetails: title, videoId, author, channelId, lengthSeconds, viewCount
# player.streamingData: formats, adaptiveFormats
# player.playabilityStatus: status (OK/ERROR)

# ytInitialData — search results, recommendations, comments
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {
        'expression': 'JSON.stringify(window.ytInitialData)',
        'returnByValue': True
    },
    'tabId': tab_id
})
init_data = json.loads(r['result']['result']['value'])
```

## Key observations

1. **Không có anti-bot** — Python requests replay thành công 200 OK cho player, search, next. Khác ChatGPT (Cloudflare 403).
2. **SAPISIDHASH thay vì Bearer** — Google auth mechanism, tính từ SAPISID cookie (httpOnly).
3. **INNERTUBE_API_KEY public** — embedded trong page JS, không cần login để lấy. Login chỉ cần cho creator endpoints.
4. **visitorData** — long base64 string trong INNERTUBE_CONTEXT, dùng làm `X-Goog-Visitor-Id` header.
5. **Client version** — `WEB v2.20260724.01.01`, thay đổi theo ngày. Lấy từ `ytcfg` thay vì hardcode.
6. **Streaming URLs** — `streamingData.formats[].url` có thể `false` (cần signature decipher). Player API trả về format info nhưng URL có thể cần thêm processing.
7. **Region restriction** — một số video (VD: `jNQXGS9QH6c`) trả `playabilityStatus: ERROR` tùy region. Test với video phổ biến (VD: `9bZkp7q19f0` PSY Gangnam Style).
