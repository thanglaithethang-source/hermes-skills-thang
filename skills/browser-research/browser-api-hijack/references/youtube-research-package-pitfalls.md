# YouTube Research Package — Pitfalls & Workarounds

Ghi chép các vấn đề gặp phải khi dùng `youtube_research` package (skill `youtube-research`).
Skill đó là manually authored — không patch được, nên ghi workarounds ở đây.

## 1. video_info trả "Video không có sẵn" dù video play được

**Triệu chứng:** `yt.video_info("VIDEO_ID")` trả `status=error, reason="Video không có sẵn"`.

**Root cause:** `video.py` check `playabilityStatus.status` quá strict. Known Issue #1 trong skill.

**Workaround:** Gọi `/youtubei/v1/player` trực tiếp:
```python
import json, time, hashlib, requests

with open(ctx_path, 'r') as f:
    ctx_data = json.load(f)
context = ctx_data['context']
api_key = ctx_data['api_key']
cookies = ctx_data['cookies']
sapisid = ctx_data.get('sapisid', '')

origin = "https://www.youtube.com"
ts = str(int(time.time()))
sapisidhash = hashlib.sha1((ts + ' ' + sapisid + ' ' + origin).encode()).hexdigest()
headers = {
    'Authorization': f"SAPISIDHASH {ts}_{sapisidhash}",
    'Content-Type': 'application/json',
    'Origin': origin,
    'Referer': 'https://www.youtube.com/',
}

url = f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
body = {"context": context, "videoId": VIDEO_ID,
        "playbackContext": {"contentPlaybackContext": {"html5Preference": "HTML5_PREF_WANTS"}}}
resp = requests.post(url, headers=headers, cookies=cookies, json=body, timeout=15)
vd = resp.json().get('videoDetails', {})
# vd has: title, author, channelId, viewCount, lengthSeconds, keywords, shortDescription
```

## 2. snapshot_video không lưu view_count vào DB

**Triệu chứng:** `yt.snapshot_video(VIDEO_ID)` trả `status=ok` nhưng `view_count=None`, `snapshot_epoch=None`.

**Root cause:** Facade `snapshot_video()` không truyền view_count vào `storage.snapshot_video()`. Storage method cần 3 args `(video_id, view_count, epoch)` nhưng facade chỉ truyền video_id.

**Workaround:** Gọi storage trực tiếp:
```python
from scripts.storage import Storage
storage = Storage(db_path)
storage.snapshot_video(VIDEO_ID, view_count, time.time())
```

## 3. calculate_vph trả dict thay vì Result

**Triệu chứng:** `yt.calculate_vph(VIDEO_ID)` trả `dict` (`{"status": "unavailable", ...}`) thay vì `Result` object.

**Root cause:** `calculate_vph` không có trong `YouTubeResearch` facade. Nằm trong `analytics_estimate.py`.

**Workaround — VPH thủ công:**
```python
from scripts.storage import Storage
storage = Storage(db_path)
snaps = storage.get_video_snapshots(VIDEO_ID)
if len(snaps) >= 2:
    s1, s2 = snaps[0], snaps[-1]
    views_delta = s2['view_count'] - s1['view_count']
    hours = (s2['snapshot_epoch'] - s1['snapshot_epoch']) / 3600
    vph = views_delta / hours if hours > 0 else 0
```

Cần 2 snapshots cách nhau ít nhất 15 phút.

## 4. Context file cũ — cần refresh từ Chrome tab

**Triệu chứng:** `video_info` trả error dù context file tồn tại — SAPISID hết hạn hoặc client version outdated.

**Fix:** Extract context mới từ YouTube tab đang mở:
```python
from chrome_send import send_command
import json

# Tab YouTube đang mở trong Chrome
r = send_command({'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': 'JSON.stringify(window.ytcfg.get("INNERTUBE_CONTEXT"))', 'returnByValue': True},
    'tabId': tab_id})
context = json.loads(r['result']['result']['value'])

r = send_command({'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': 'window.ytcfg.get("INNERTUBE_API_KEY")', 'returnByValue': True},
    'tabId': tab_id})
api_key = r['result']['result']['value']

# Cookies qua CDP (bao gồm httpOnly SAPISID)
r = send_command({'type': 'cdp_command', 'method': 'Network.getAllCookies', 'params': {}, 'tabId': tab_id})
all_cookies = r.get('result', {}).get('result', {}).get('cookies', []) or r.get('result', {}).get('cookies', [])
sapisid = next((c['value'] for c in all_cookies if c.get('name') == 'SAPISID'), None)

ctx_data = {'context': context, 'api_key': api_key,
            'cookies': {c['name']: c['value'] for c in all_cookies if 'google' in c.get('domain','') or 'youtube' in c.get('domain','')},
            'sapisid': sapisid}
with open(ctx_path, 'w') as f:
    json.dump(ctx_data, f, indent=2, ensure_ascii=False)
```

## 5. Network.getAllCookies response nesting — fallback chain

CDP `Network.getAllCookies` response có thể lồng 2 cấp:
- `r['result']['result']['cookies']` (qua cdp_command → Runtime.evaluate style)
- `r['result']['cookies']` (qua cdp_command trực tiếp)

Luôn dùng fallback:
```python
all_cookies = r.get('result', {}).get('result', {}).get('cookies', [])
if not all_cookies:
    all_cookies = r.get('result', {}).get('cookies', [])
```

Đã gặp 2026-07-26 với YouTube và 2026-07-29 với ChatGPT — response nesting khác nhau tùy version bridge/extension.
