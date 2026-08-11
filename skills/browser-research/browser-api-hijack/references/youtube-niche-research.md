# YouTube Niche Research — Batch Search + Channel Verification Workflow

**Ngày tạo:** 2026-07-26 | **Dùng cho:** tìm keyword/niche YouTube longform đang thắng cho faceless AI channels

## Tổng quan

Workflow dùng YouTube InnerTube API (search + next endpoints) để:
1. Search 30-40 niche queries → thu 500+ videos, 300+ channels
2. Filter major brands → giữ small/mid channels
3. Get subscriber count cho mỗi kênh (qua `next` endpoint)
4. Compute V/S ratio (views/subscriber) — strong signal khi >5x
5. Deep search mỗi kênh → 5-10 video mỗi kênh
6. Compute Win Rate — wins/total * 100

## Prerequisites

- Bridge server chạy + Chrome extension loaded
- YouTube tab mở + logged in
- Context + cookies + api_key extracted (xem `youtube-innertube-api.md`)

## Phase 1: Batch Discovery Search

```python
queries = [
    "stoicism life lessons", "dark psychology facts", "psychology manipulation",
    "dark history documentary", "space documentary faceless", "mystery unsolved",
    "mythology stories explained", "book summary animated", "movie ending explained",
    "money mindset psychology", "productivity systems", "discipline motivation",
    "AI tools tutorial", "future technology predictions", "conspiracy mysteries",
    "geography facts", "science mysteries explained", "survival facts",
    # ... 30-40 queries total
]

def yt_search(query, max_results=15):
    body = {"context": context, "query": query}
    url = f'https://www.youtube.com/youtubei/v1/search?key={api_key}'
    resp = requests.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
    data = resp.json()
    # Parse: data.contents.twoColumnSearchResultsRenderer.primaryContents
    #   .sectionListRenderer.contents[].itemSectionRenderer.contents[]
    #   .videoRenderer: { videoId, title, ownerText, viewCountText, lengthText, publishedTimeText }
    ...

# Rate limit: 0.3-0.5s between requests
for q in queries:
    results = yt_search(q, 15)
    time.sleep(0.3)
```

**Output:** ~500-600 videos, ~300-360 unique channels

## Phase 2: Filter + Get Subscriber Count

### Filter major brands

```python
major_brands = {'TED-Ed', 'BRIGHT SIDE', 'BBC Earth', 'Netflix', 'National Geographic',
    'Veritasium', 'Kurzgesagt', 'CrashCourse', 'The School of Life', 'HISTORY', ...}
```

### Get subscriber count via `next` endpoint

Browse API (`/youtubei/v1/browse`) không trả video list và subscriber count thường rỗng. Dùng `next` endpoint với 1 videoId của kênh:

```python
def get_channel_info_from_video(video_id):
    body = {"context": context, "videoId": video_id}
    url = f'https://www.youtube.com/youtubei/v1/next?key={api_key}'
    resp = requests.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
    data = resp.json()
    # Parse: data.contents.twoColumnWatchNextResults.results.results.contents[]
    #   .videoSecondaryInfoRenderer.owner.videoOwnerRenderer.subscriberCountText
```

### Parse Vietnamese locale subscriber count

YouTube trả sub count theo locale Chrome (vi-VN):
- `"230 N người đăng ký"` = 230,000 (N = nghìn)
- `"1,05 Tr người đăng ký"` = 1,050,000 (Tr = triệu)
- `"14,5 N người đăng ký"` = 14,500 (comma = decimal separator)

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

## Phase 3: Compute V/S Ratio + Win Rate

### V/S Ratio (Views/Subscriber)

```python
v_s_ratio = max_views / subscriber_count if subscriber_count > 0 else 0
# >5x = strong signal, >10x = very strong, >20x = exceptional
```

### Win Rate

```python
# Win = video views > median of channel's videos OR > subscriber count
wins = sum(1 for v in videos if v['views_num'] > median_views or v['views_num'] > subs)
win_rate = (wins / total_videos) * 100
# 70%+ = rất mạnh, 50-69% = đáng kiểm tra, <50% = không "cứ đăng là thắng", <35% = loại
```

## Phase 4: Deep Search per Channel

Search channel name + niche variants để thu 5-10 video mỗi kênh:

```python
results = yt_search(f'"{channel_name}"', 20)
ch_vids = [v for v in results if channel_name.lower() in v['channel'].lower()]
```

## Phase 5: Red-Team + Scoring

### Red-Team checklist

- [ ] Chỉ 1 kênh thắng? → KHÔNG đủ 3 kênh độc lập
- [ ] Phụ thuộc 1-2 viral outlier? → 1 video = 80%+ tổng views
- [ ] View đến từ Shorts?
- [ ] Kênh lớn đè? → top results toàn major brands
- [ ] Topic sắp bão hòa?
- [ ] RPM thấp?
- [ ] AI content dễ bị nhận diện rác?

### Scoring (100-point scale)

| Tiêu chí | Điểm tối đa |
|----------|-------------|
| Nhu cầu người xem hiện tại | 15 |
| Win Rate của các kênh đại diện | 15 |
| Khả năng kênh nhỏ chen vào | 12 |
| Mức độ cạnh tranh còn hở | 10 |
| Khả năng làm faceless AI | 12 |
| Chi phí và tốc độ sản xuất | 8 |
| Khả năng giữ chân người xem | 8 |
| Độ sâu ít nhất 100 video | 7 |
| Tiềm năng Browse/Suggested | 5 |
| Tiềm năng kiếm tiền | 4 |
| Độ evergreen | 2 |
| Mức an toàn chính sách | 2 |

Xếp loại: 90-100 đặc biệt mạnh, 85-89 triển khai ngay, 78-84 test nhỏ, 70-77 rủi ro, <70 loại.

## Data Files

Lưu JSON mỗi giai đoạn:
- `discovery_all.json` — tất cả search results
- `channel_infos.json` — subscriber count + channel ID mỗi kênh
- `channel_vids_deep.json` — video list mỗi kênh (từ deep search)
- `channel_stats.json` — Win Rate + V/S ratio + median views

## Key Findings (2026-07-26 session)

### Top niches by V/S ratio + Win Rate

| Niche | Top channel | Subs | Max Views | V/S | Win Rate |
|-------|-------------|------|-----------|-----|----------|
| Dark Psychology / Machiavelli | Dark Psychology Coded | 230K | 1.66M | 7.2x | 43% |
| Dark Psychology | How Talks | 63.6K | 1.64M | 25.9x | 40% |
| Dark Psychology | SleepWise | 243K | 1.67M | 6.9x | 50% |
| Discipline / Stoic | StickFigure Explains | 105K | 4.04M | 38.5x | 60% |
| Book Summary Animated | Pagely | 68K | 1.35M | 19.9x | 100% |
| Money Mindset | Becoming More | 70K | 1.66M | 23.7x | 67% |
| Language/General Facts | The Generalist Papers | 174K | 2.99M | 17.2x | 80% |
| Science Mysteries | Astrum Extra | 307K | 1.53M | 5.0x | 67% |
| Conspiracy/Mystery | Dantavius | 676K | 3.47M | 5.1x | 71% |

### RÁC channels (loại bỏ)

- **MindFold** — kênh nhạc electronic, 1 video viral science, rest = music tracks
- **Stoic Shift** — 1 video (8.8M views) = 80% tổng views. Viral outlier dependent
- **Extreme Mysteries** — tất cả video dưới 5K views
- **Maximum** — kênh gaming (WoW), không phải world records
- **Antidote** — kênh nhạc (Travis Scott), không phải book summary

### Winner: Dark Psychology / Machiavelli (82/100, TEST)

3 kênh verified, Win Rate 40-50%, kênh nhỏ (63K-70K subs) đạt 1.6M+ views. Nhưng Win Rate chưa đạt 60% → TEST, không GO.
