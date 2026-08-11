# vidIQ Research Findings — How vidIQ Works with YouTube

Condensed findings from analyzing vidIQ Chrome Extension v3.209.0 (CRX ID: `pachckjkecffpdphbpmfolblodfkgbhl`).
Full reports: `~/Downloads/_projects/vidiq-research/REPORT.md` (818 lines) + `DEEP_REPORT.md` (1392 lines).

## Data Sources (Confirmed from Source Code)

1. **YouTube Data API v3** — via vidIQ proxy (`/api/proxy/youtube/v3/{resource}`). Batches up to 50 IDs, 100ms window.
2. **YouTube Analytics API** — owner-authorized (`/api/youtube/analytics`). Daily views, watch time, subs gained/lost, retention, revenue.
3. **YouTube Studio internals** — `/youtubei/v1/yta_web/join`, `/creator/get_channel_dashboard`, etc. Extension reuses page auth context.
4. **InnerTube** — `/youtubei/v1/browse`, `/player`, `/get_transcript`, `/comment/get_comments`.
5. **Page-state extraction** — `ytInitialData`, `ytInitialPlayerResponse`, `ytcfg.data_`, DOM. Uses `MutationObserver` for SPA navigation.
6. **Autocomplete** — `suggestqueries.google.com/complete/search?client=firefox&ds=yt` for YouTube-specific suggestions.
7. **Reddit** — `reddit.com/search.json?q=url:{videoId}` for engagement signals.
8. **vidIQ historical database** — 135M+ channels, 12B+ videos. Repeated snapshots → derived metrics.

## Metric Formulas (Confirmed from Client Source)

### VPH (Views Per Hour)
```
age_hours = (now - published_at) / 3,600,000
average_vph = current_views / age_hours
snapshot_vph = abs(current_views - snapshot.views) / ((now - snapshot.recorded_at) / 3,600,000)
```
Rules:
- Snapshot must be 12-168 hours old
- Reject if vph > current_views
- Lifetime average ONLY for videos < 168 hours (7 days)
- Skip live streams
- Backend `POST /api/youtube/video/vph` with `{id, current_views, published_at}` → returns `vph`

### Outlier / Breakout Score
```
expected_views = (perc30 + perc70) / 2  at age bucket
outlier = current_views / expected_views
```
Age bucket fallback: exact hour → day×24 → 168h (if ≤7d) → max available
Rules:
- Minimum 1,000 views (return None below)
- Suppress ≤1x during first 24 hours
- Round scores ≥10x to integer
- Cap >100x as ">100x"
- Backend fields: `breakout_median_score`, `breakout_score`

### vidIQ Score (Client Formula — Exact)
```
vidiq_score_client = min(100, 3*log2(views) + 3*log2(facebook_likes))
```
Each term is 0 if input < 1. Production score is backend `POST /scraping/youtube/vidiq-score` with large payload.

### Keyword Metrics (ALL Backend)
- `competition`, `overall`, `estimated_monthly_search`, `volume` → all from `/xwords/hottersearch`
- `group=v5` selects model version
- No client-side formula for any keyword metric
- Search Volume = server-side estimate, NOT InnerTube field

## Backend Endpoint Catalog (Key Routes)

| Route | Purpose |
|-------|---------|
| `GET /xwords/hottersearch` | Keyword metrics + related terms |
| `GET /xwords/keyword_trends/` | Rising keywords |
| `GET /xwords/keyword_vph/` | Keyword VPH |
| `POST /youtube/video/vph` | VPH calculation |
| `GET /youtube/video-outliers` | Outlier scores |
| `POST /youtube/videos/metrics` | Batch metrics (vph, engagement, breakout) |
| `GET /youtube/channels/video-performance-trends` | Performance curves (perc30/perc70) |
| `GET /youtube/videos/{id}/history` | Video stats history |
| `GET /youtube/video/{id}/stats-history` | Granular stats history |
| `GET /creators/ideas/{id}/recommended_v2` | Daily Ideas (NOT in CRX — web app only) |
| `GET/PUT /creators/competitors` | Competitor follow/unfollow |
| `POST /pyapi/auto_competitors/{channelId}` | Auto-competitor selection |
| `POST /scraping/youtube/vidiq-score` | Production vidIQ score |

## Daily Ideas Engine
- NOT in Chrome extension CRX — runs on `app.vidiq.com/daily-video-ideas`
- Extension only opens a link to the web app
- `view_potential` is an opaque string from backend
- Confirmed inputs: channel profile, similar channels/videos, keywords/trends, early-view curves, Save/Dismiss feedback
- Cannot be replicated from CRX source alone

## Performance Curves
- Endpoint: `GET /youtube/channels/video-performance-trends`
- Returns: `minutesSincePublication` + `views.perc30` + `views.perc70`
- Used for: age-matched outlier, view prediction, "typical first 24h/7d/28d"
- Standard buckets: 1h, 6h, 24h, 72h, 7d(168h), 28d(672h)

## Channel Growth Tracking
- Public: snapshot deltas — `views(t) - views(t-1)`, `subs(t) - subs(t-1)`
- Owner: Analytics API directly — `subscribersGained`, `subscribersLost`
- Public subscriber count is rounded to 3 significant figures (YouTube API limitation)

## Key Architecture Notes
- Extension does NOT use `chrome.webRequest` — uses content scripts + page-world helpers + `fetch`
- Page-world scripts injected via `document.createElement('script')` + `chrome.runtime.getURL()`
- `getWindowData.bundle.js` reads `ytcfg.data_` keys: CHANNEL_ID, INNERTUBE_CONTEXT_*, XSRF_TOKEN
- `pageRequest.bundle.js` performs authenticated same-origin POSTs using page-derived auth
- `fetchDOMContent.bundle.js` — DOM extraction bridge with origin check + handshake token
