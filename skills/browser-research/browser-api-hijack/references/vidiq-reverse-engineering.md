# vidIQ Reverse Engineering — Metric Formulas & Data Pipeline

Nguồn: Codex analysis vidIQ Chrome Extension v3.209.0 (CRX unpacked, 24 JS bundles).
Ngày: 2026-07-29. Báo cáo đầy đủ: ~/Downloads/_projects/vidiq-research/REPORT.md + DEEP_REPORT.md

## 1. VPH (Views Per Hour) — CONFIRMED từ source

### Backend call
```
POST https://api.vidiq.com/api/youtube/video/vph
Body: [{"id": "VIDEO_ID", "current_views": 12345, "published_at": "2026-07-20T12:00:00Z"}]
Returns: [{"vph": ...}]
```

### Client fallback (exact code)
```text
age_hours = (now - published_at) / 3,600,000
average_vph = current_views / age_hours
snapshot_vph = abs(current_views - snapshot.views) / ((now - snapshot.recorded_at) / 3,600,000)
```

### Rules
- Snapshot phải cũ 12-168 giờ
- Reject nếu vph > current_views
- Lifetime average CHỈ dùng khi video < 168 giờ (7 ngày)
- Skip live streams
- Ưu tiên server VPH → snapshot fallback → lifetime average fallback

### Python replica
```python
from datetime import datetime, timezone

def trailing_vph(samples, now=None, target_hours=24):
    """samples: sorted [(timestamp, cumulative_views), ...]"""
    now = now or datetime.now(timezone.utc)
    latest_t, latest_views = samples[-1]
    eligible = [x for x in samples[:-1]
                if (latest_t - x[0]).total_seconds() >= target_hours * 3600]
    if not eligible:
        return None
    old_t, old_views = eligible[-1]
    hours = (latest_t - old_t).total_seconds() / 3600
    return max(0, latest_views - old_views) / hours

def lifetime_vph(current_views, published_at, now=None):
    """Only valid for videos < 168 hours old"""
    now = now or datetime.now(timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    if age_hours >= 168:
        return None
    return current_views / age_hours if age_hours > 0 else None
```

## 2. Outlier/Breakout Score — CONFIRMED từ source

### Backend fields
- `breakout_median_score` from `/api/youtube/video-outliers`
- `breakout_score` from `/youtube/videos/metrics`

### Client fallback (exact code)
```text
expected_views(age) = (perc30(age) + perc70(age)) / 2
fallback_outlier = current_views / expected_views(age)
```

### Age bucket fallback order
1. exact rounded hour
2. rounded day × 24
3. 168 hours if age ≤ 7 days
4. greatest available age key

### Display/eligibility rules
- No score below 1,000 views
- Suppress ≤1x during first 24 hours
- Round scores ≥10x
- Cap >100x as ">100x"
- Segment Shorts và long-form riêng

### Performance curves source
```
GET /youtube/channels/video-performance-trends
Returns: minutesSincePublication + perc30/perc70 views
```

### Python replica
```python
from statistics import median

def outlier_score(target_views, target_age_hours, peer_videos):
    """
    peer_videos: each video's cumulative view curve: [(age_hours, views), ...]
    """
    comparable = []
    for curve in peer_videos:
        point = min(curve, key=lambda p: abs(p[0] - target_age_hours))
        comparable.append(point[1])
    baseline = median(v for v in comparable if v is not None)
    return target_views / baseline if baseline > 0 else None
```

## 3. vidIQ Score (client formula) — CONFIRMED

```text
vidiq_score_client = min(100, 3*log2(views) + 3*log2(facebook_likes))
```
Mỗi term = 0 nếu value < 1. Twitter tweets set = 0.

Production score: `POST /scraping/youtube/vidiq-score` với payload lớn (views, likes, comments, tags, SEO scores, channel stats...). Formula server-side, không public.

## 4. Keyword Metrics — ALL backend

### Endpoint
```
GET /xwords/hottersearch?q=<query>&group=v5&limit=...
```

### Returned fields (server-side, no client formula)
- `competition` (0-100)
- `overall` (0-100, combines volume + competition)
- `estimated_monthly_search` (monthly count)
- `calibrated_total_searches_30d` (for period change)
- `volume` (0-100 normalized)
- `related_score`

### Search Volume
- Server-side estimate, KHÔNG phải InnerTube field
- Model: `group=v5` selects model version
- Exact calibration source: UNKNOWN (could be Google Ads, clickstream, historical data)
- Autocomplete supplies candidates, NOT count

### Volume change formula (client-side, confirmed)
```text
if current >= previous: (current - previous) / previous * 100
if current < previous:  (current - previous) / current * 100
```
Asymmetric denominator.

## 5. YouTube Autocomplete (vidIQ uses)

```
GET https://suggestqueries.google.com/complete/search?q=<query>&client=firefox&ds=yt&hl=<lang>
```
`ds=yt` = YouTube-specific suggestions. Dùng cho keyword discovery, không phải volume.

## 6. Page-State Extraction (vidIQ reads from YouTube)

### ytInitialData parser
Regex: `/(?:window\["ytInitialData"\]|var ytInitialData) = ([^\n]+?);/`
Fields: videoPrimaryInfoRenderer (title, views, date), videoSecondaryInfoRenderer (description, channel, subs)

### ytInitialPlayerResponse parser
Regex: `/var ytInitialPlayerResponse = ({.+});var meta/`
Fields: videoDetails.viewCount, videoDetails.title, videoDetails.lengthSeconds, microformat.playerMicroformatRenderer.publishDate, isShortsEligible

### ytcfg.data_ keys extracted
CHANNEL_ID, INNERTUBE_CONTEXT_HL/GL/CLIENT_NAME/CLIENT_VERSION, XSRF_TOKEN, DELEGATED_SESSION_ID

### View count fallback order
1. ytInitialData videoViewCountRenderer
2. ytInitialPlayerResponse.videoDetails.viewCount
3. Regex over HTML
4. Legacy .watch-view-count DOM

## 7. vidIQ Backend Endpoint Catalog (key routes)

### YouTube data
| Endpoint | Purpose |
|---|---|
| POST /youtube/video/vph | VPH calculation |
| GET /youtube/video-outliers | Outlier scores |
| POST /youtube/videos/metrics | Batch metrics (vph, engagement, breakout) |
| GET /youtube/videos/{id}/history | Video history |
| GET /youtube/video/{id}/stats-history | Stats history |
| GET /youtube/videos/{id}/views | Views after publish |
| GET /youtube/channels/public/stats | Channel public time series |
| GET /youtube/channels/video-performance-trends | Age curves (perc30/perc70) |
| GET /youtube/video/trendy | Trending videos |
| GET /research/most-viewed | Most viewed |

### Keywords
| Endpoint | Purpose |
|---|---|
| GET /xwords/hottersearch | Keyword metrics + related terms |
| GET /xwords/keyword_trends/ | Rising keywords |
| GET /xwords/keyword_vph/ | Keyword VPH |

### Data API proxy
| Endpoint | Purpose |
|---|---|
| GET /proxy/youtube/v3/{resource} | YouTube Data API v3 proxy |
| GET /v1/proxy/youtube/data/{channelId}/v3/videos | Fixed projection videos |

## 8. Daily Ideas — NOT in extension CRX

- `/creators/ideas/{id}/recommended_v2` KHÔNG tồn tại trong CRX v3.209.0
- Extension chỉ mở link `app.vidiq.com/daily-video-ideas`
- Recommendation engine chạy trên web app, không thể reverse từ CRX
- `view_potential` = opaque string từ backend

## 9. Key Takeaways cho skill youtube-research

1. **VPH**: Thêm lifetime average fallback cho video < 168h + snapshot window 12-168h
2. **Outlier**: Chuyển sang (perc30+perc70)/2, thêm age buckets, min 1000 views, suppression rules
3. **Performance curves**: Store views tại 1h/6h/24h/3d/7d/28d cho age-matched comparison
4. **Autocomplete**: Đảm bảo dùng ds=yt cho YouTube-specific suggestions
5. **Page-state extraction**: Thêm ytInitialData/ytInitialPlayerResponse fallback
6. **vidIQ Score**: Client formula = min(100, 3*log2(views) + 3*log2(social_likes))
7. **Search Volume**: Server-side estimate — không thể replicate chính xác, chỉ có thể ước lượng bằng autocomplete + Google Trends + regression
8. **Competition**: Server-side 0-100 — không có client formula
