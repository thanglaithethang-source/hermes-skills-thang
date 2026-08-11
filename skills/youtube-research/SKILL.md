---
name: youtube-research
description: Collect and analyze public YouTube search, channel, video, trending, browse, and suggested-video data with drift-aware InnerTube parsers. Use for YouTube competitor research, keyword research, public metric collection, snapshot-based growth or views-per-hour analysis, and explicitly labeled CTR, retention, or RPM availability checks.
---

# YouTube Research

Use the installable `youtube_research` package. Public, unauthenticated collection is the default.
Pass `authenticated=True` and a context file only when authenticated collection is explicitly
needed; authenticated mode is strict and does not silently downgrade unless the caller opts in.
Pass `db_path` only for snapshot history, growth, or VPH workflows.

## Prerequisites

- `requests` Python library
- `jsonschema` Python library (for calibration validation)
- Optional: InnerTube context file with SAPISID cookies for authenticated endpoints
- Optional: SQLite DB path for persistence (VPH, competitor tracking)

## Quick Start

```python
from scripts.youtube_research import YouTubeResearch

# Unauthenticated (public data only)
yt = YouTubeResearch()

# Authenticated (needs context file with SAPISID cookies)
ctx_path = "path/to/yt_context.json"
yt = YouTubeResearch(authenticated=True, context_path=ctx_path)

# With SQLite persistence (for VPH, competitor tracking)
yt = YouTubeResearch(authenticated=True, context_path=ctx_path, db_path='yt_research.db')

# Search keyword
result = yt.search("AI automation", limit=20)
if result.status in {"ok", "partial"}:
    for video in result.items:
        print(video["title"], video.get("views"))
if result.reason:
    print(result.status, result.reason)

# Channel info
ch = yt.channel_info("UCui4jxDaMb53Gdh-AZUTPAg")
if ch.ok:
    print(ch.items[0])

# Video metadata
vi = yt.video_info("dQw4w9WgXcQ")
if vi.ok:
    print(vi.items[0])

# Competitor report
report = yt.competitor_report("UCui4jxDaMb53Gdh-AZUTPAg", video_limit=5)
if report.items:
    md = yt.to_markdown(report.items[0])
    print(md)
```

## Result contract

Collection and report methods return `Result` with `status`, `items`, `reason`, `error_code`, and
`metadata`.

- `ok`: usable items and no known collection failure.
- `empty`: recognized response shape completed successfully with no matching items.
- `partial`: usable items remain, but an API, pagination, enrichment, parser, or dependency failure
  occurred. `reason` is always populated.
- `error`: no usable items because the request or operation failed.
- `unsupported`: HTTP 200 was received, but the response shape was not recognized.

Parser diagnostics in `metadata.parser_diagnostics` include `recognized_container`,
`candidate_nodes`, `parsed_nodes`, and `unknown_renderer_types`, plus the surface, response kind,
container path, continuation state, and a bounded shape fingerprint.

## Canonical video schema

Use these canonical keys: `video_id`, `channel_id`, `title`, `view_count`, `duration_seconds`,
`publish_date`, `published_raw`, `duration_raw`, `is_live`, and `is_upcoming`.

Temporary compatibility aliases are also emitted: `videoId`, `channelId`, `views`, `duration`, and
`published`. New integrations should use canonical keys.

`publish_date` is an ISO date obtained from `/player`. Localized relative text such as
`"3 days ago"` remains only in `published_raw` and is never converted into an exact date. Failed
date enrichment leaves `publish_date=None`, retains `published_raw`, and makes the batch `partial`.

## Data interpretation

- Exact public observations: identifiers, titles, public counters when exposed, duration, and
  `/player` publish date.
- Sampled observations: search positions, browse presence, suggested presence, and channel video
  samples. These are not exhaustive traffic-source measurements.
- Channel total views and join date are unavailable from the implemented browse contract.
- Subscriber, like, and comment counts may be hidden and therefore `None`.
- CTR and retention are owner-only. Their methods return `estimable=False` with public observable
  proxies, never a numeric estimate.
- RPM is owner-only and cannot be inferred reliably. It returns `estimable=False`; a range appears
  only when the caller explicitly selects a versioned scenario profile or provides an override.
- Keyword competition has no score unless a versioned calibration artifact passes JSON Schema,
  semantic, and provenance validation with at least 200 training queries.
- VPH prefers two stored snapshots. Metadata-aware snapshots use a 12–168 hour comparison
  window; young videos can fall back to lifetime-average VPH, while live streams are skipped.
- Channel performance curves persist views at 1h, 6h, 24h, 72h, 168h, and 672h buckets and
  expose perc30, perc70, and median baselines.
- The legacy `vidiq_score_client` formula is always labeled `client estimate`; it is not the
  production vidIQ score.
- Search volume (30-day demand) is NOT available from InnerTube API. Only YouTube Studio or
  Google Trends API expose demand data.

Read [InnerTube endpoints](references/innertube_endpoints.md) when changing collection/profile
behavior, [calibration](references/keyword_competition_calibration.md) when supplying a competition
artifact, and [RPM scenarios](references/niche_rpm_table.md) before selecting an RPM assumption.

## What This Skill Can Do

1. **Search** — keyword search with pagination, autocomplete suggestions, trending feed
2. **Channel** — name, subscriber count, video count, description, country, tags
3. **Video** — title, view count, like count, comment count, duration, publish date, tags
4. **Suggested/browse** — suggested videos, browse feed, presence detection
5. **VPH** — snapshot velocity plus the documented young-video lifetime fallback
6. **Outlier detection** — performance-curve midpoint when available, median cohort otherwise
7. **Keyword competition signals** — HHI, median views/day, relevance scoring (no fake score)
8. **Competitor tracking** — live snapshot, growth, multi-channel comparison
9. **Competitor/keyword reports** — markdown rendering, None-safe

## What This Skill CANNOT Do

1. **CTR/retention/RPM exact** — YouTube hides these. Only owner sees in YouTube Studio
2. **Search volume 30 days** — InnerTube API does not expose demand data
3. **Channel total views/join date** — not available from InnerTube browse

## Architecture (23 scripts, ~5000 lines)

```text
youtube-research/
├── SKILL.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── MANIFEST.in
├── .github/workflows/ci.yml
├── scripts/
│   ├── __init__.py
│   ├── youtube_research.py
│   ├── innertube.py
│   ├── client_profile.py
│   ├── parsers.py
│   ├── models.py
│   ├── result.py
│   ├── enrichment.py
│   ├── exceptions.py
│   ├── formatting.py
│   ├── validation.py
│   ├── pagination.py
│   ├── report_status.py
│   ├── calibration.py
│   ├── search.py
│   ├── channel.py
│   ├── video.py
│   ├── browse_suggested.py
│   ├── analytics_estimate.py
│   ├── tracking.py
│   ├── report.py
│   ├── storage.py
│   └── time_utils.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── contracts/
│   ├── integration/
│   └── live/
└── references/
    ├── innertube_endpoints.md
    ├── keyword_competition_calibration.schema.json
    ├── keyword_competition_calibration.md
    ├── niche_rpm_table.md
    └── rpm_scenarios.json
```

InnerTube is an undocumented interface and can drift. Do not return raw response JSON as a parser
fallback. Preserve typed errors, parser diagnostics, and partial data so callers can distinguish
network failure, legitimate emptiness, and unsupported response shapes.
