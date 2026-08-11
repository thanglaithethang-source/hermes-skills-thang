---
name: innertube-api-reference
description: "YouTube InnerTube API reference — 2026 format changes, endpoint mapping, auth (SAPISIDHASH), response parsing paths for lockupViewModel + legacy videoRenderer. Load when building or debugging YouTube InnerTube integrations."
version: 2.1.0
created_by: agent
metadata:
  hermes:
    tags: [youtube, innertube, api, reference, parsing]
---

# YouTube InnerTube API Reference

## Activation
When task involves: building/debugging YouTube InnerTube API integrations, parsing YouTube API responses, fixing broken YouTube data extraction, reverse-engineering YouTube endpoints.

## Not for
General YouTube content research (use youtube-research skill instead).

## Context
YouTube changed its InnerTube API response structure significantly in 2026. The `videoRenderer` format was replaced with `lockupViewModel` across channel browse, search, and suggested video results. This skill documents the mapping and parsing strategies.

## Auth: SAPISIDHASH
- Header: `Authorization: SAPISIDHASH {timestamp}_{hash}`
- Hash: `SHA1({timestamp} {SAPISID} {origin})` — hex digest
- Origin: `https://www.youtube.com`
- Regenerate on EVERY request (timestamp-based, won't expire)
- SAPISID cookie can expire — re-capture via Chrome bridge if 401/403

## Endpoints
- POST `/youtubei/v1/search` — keyword search
- POST `/youtubei/v1/browse` — channel info, channel videos, trending, home feed
- POST `/youtubei/v1/next` — suggested/related videos, like/comment counts
- POST `/youtubei/v1/player` — video metadata (title, views, duration, tags)
- GET `suggestqueries.google.com/complete/search` — autocomplete (JSONP)

## 2026 Format Changes (see references/innertube_format_2026.md for full detail)

### Channel header
- OLD: `pageHeaderRenderer.content.pageHeaderMetaData.subscriberCountText`
- NEW: `pageHeaderRenderer.content.pageHeaderViewModel.metadata.contentMetadataViewModel.metadataRows[].metadataParts[].text.content`

### Channel videos tab params
- OLD: `Egh2aWRlb3PYBGAA`
- NEW: `EgZ2aWRlb3PyBgQKAjoA`
- Discovery: browse without params → read `tabs[].tabRenderer.endpoint.browseEndpoint.params`

### Video list items
- OLD: `richItemRenderer.content.videoRenderer`
- NEW: `richItemRenderer.content.lockupViewModel`
- videoId: extract from thumbnail URL (`/vi/{videoId}/`) or regex raw JSON
- Duration: `thumbnailBottomOverlayViewModel.badges[].thumbnailBadgeViewModel.text`
- Views/published: `lockupMetadataViewModel.metadata.contentMetadataViewModel.metadataRows[].metadataParts[].text.content`

### Suggested videos (/next)
- OLD: `secondaryResults.results[].compactVideoRenderer`
- NEW: `secondaryResults.results[].itemSectionRenderer.contents[].lockupViewModel`

### Like count
- OLD (regex): search raw JSON for "iconName": "LIKE", "title": "739" — title = like count string
- NEW (structured): Traverse response tree for likeCountEntity.likeCountIfIndifferentNumber — returns exact integer. Fallback: button title text.
- The regex approach is fragile — likeCountEntity is the canonical source.

### Comment count
- Structured: engagementPanels[].engagementPanelSectionListRenderer.header.engagementPanelTitleHeaderRenderer.contextualInfo.runs[0].text — digit string.
- Fallback: regex on raw JSON for contextualInfo runs text digit.
- May be None if comments disabled/not loaded — do NOT default to 0.

## Number Parsing (VN vs EN)
- VN: "825 N" = 825,000 (N=nghìn=thousand), "1,2 Tr" = 1,200,000 (Tr=triệu=million)
- EN: "1.2M" = 1,200,000, "45K" = 45,000
- CRITICAL BUG (FIXED in v2): parse float FIRST, THEN multiply by unit. Do NOT strip commas/dots before multiplying.
- CRITICAL: Must include `nghìn` and `triệu` (full Vietnamese words) in multipliers dict, not just `n` and `tr`. accessibilityLabel often contains full words: "89 nghìn lượt xem".
- Return `None` for missing/unparseable values, NOT `0`. Prevents false data in downstream analytics.

## Suggested lockupViewModel Structure (discovered during Codex review)
- Row 0, Part 0: channel name (e.g. "Liam Ottley")
- Row 1, Part 0: views — content="228 N" (compact), accessibilityLabel="228 nghìn lượt xem" (full)
- Row 1, Part 1: published — content="4 tháng trước"
- Channel ID: in avatar decoratedAvatarViewModel.rendererContext.commandContext.onTap.innertubeCommand.browseEndpoint.browseId
- Duration: in thumbnail overlay badge text (e.g. "3:05:04")
- videoId: in `contentId` field (direct), NOT regex on serialized JSON
- Parser must check BOTH `content` and `accessibilityLabel` for view text — accessibilityLabel has the full localized form.

## Pitfalls
- YouTube can change format anytime. Always have fallback paths.
- lockupViewModel: use `contentId` field for videoId (direct), NOT regex on serialized JSON. Fallback: `rendererContext.commandContext.onTap.innertubeCommand.watchEndpoint.videoId`.
- Suggested video lockupViewModel: views may be in `accessibilityLabel` (full text like "228 nghìn lượt xem"), not in `content` (compact "228 N"). Parser must check both.
- Missing/unparseable values: return `None`, NOT `0`. Collapsing unknown into zero corrupts downstream analytics. NEVER use `or 0` on count parser output.
- SAPISID cookie expiry → re-capture via Chrome bridge.
- Rate limiting: 0.3s delay between requests, retry on 429/5xx with exponential backoff + jitter.
- User-Agent: use realistic version (Chrome/122+), not fake versions.
- Circular import: `parsers.py` must NOT import from `search.py` — define own helper functions (`_parse_count`, `_parse_duration`, `_extract_text`).
- Auth opt-in: default `authenticated=False`. Only load cookies when `authenticated=True`. Public calls work without cookies.
- `to_markdown()` crash: report.py must handle `None` values before formatting (TypeError: unsupported format string passed to NoneType). Use `fmt_count()` helper returning 'unknown' for None.
- Codex review workflow: Codex needs a git repo. Run `git init && git add -A && git commit` before `codex exec --sandbox danger-full-access`. Review takes 5-9 minutes, ~130K tokens. Add `.gitignore` with `__pycache__/` before committing.
- Surface-aware parsing: Channel Videos tab has NO channel name row (channel is implicit). Suggested has channel name in row 0. Parser must classify parts by semantics, NOT by row position.
- Comment count compact VN: contextualInfo may contain "2,4 Tr". Must parse through `_parse_count()`, not just `text.isdigit()`. Validate `panelIdentifier == 'engagement-panel-comments-section'`.

## Surface-Aware Lockup Parsing (V3 Codex finding)
- Channel Videos tab: NO channel name row — row 0 contains views + published. Channel is implicit.
- Suggested: row 0 = channel name, row 1 = views + published.
- Parser must classify each part by SEMANTICS independently — a part can contain BOTH views and date (e.g. "34K views - 1 month ago"). Use separate `is_views` and `is_date` checks, NOT if/elif chain.
- Channel names can start with digits (e.g. "2CELLOS", "5-Minute Crafts"). Do NOT reject `label[0].isdigit()`.
- Pass `known_channel_id` from `channel_videos()` to lockup parser — channel ID is known from the browse request.
- Views and date must be parsed INDEPENDENTLY: check `is_views` and `is_date` separately, not if/elif. A part like "34K views - 1 month ago" contains both.

## Comment Count Extraction (V3 Codex finding)
- Comment contextualInfo may contain compact Vietnamese: "2,4 Tr" (= 2,400,000).
- Must parse through `_parse_count()`, not just `text.isdigit()`.
- Must validate `panelIdentifier == 'engagement-panel-comments-section'` before accepting count.
- REMOVED regex fallback entirely — it scanned entire /next response and could match unrelated engagement panels (e.g. transcript panel with numeric contextualInfo). Only structured path is used.

## None Handling (V3 Codex finding)
- Count parsers return `None` for missing/unparseable. NEVER use `or 0` — collapses unknown into false zero.
- Consumers must be None-safe: use `isinstance(value, int)` or `value is not None` checks.
- `video_info()` must initialize `view_count = None`, NOT `0`. Missing viewCount ≠ zero views.
- `to_markdown()` must handle None before formatting — use `fmt_count()` helper returning 'unknown'.
- `keyword_report()` aggregate must filter with `isinstance(v.get('view_count'), int)` before `> 0` comparison.
- `_get()` must catch `Timeout`, `ConnectionError`, `RequestException` and return `None`. `complete()` must check `resp is None`.

## Continuation Page Parsing (V6 Codex finding — CRITICAL)

YouTube InnerTube continuation responses use DIFFERENT top-level keys than initial responses:

- **Search continuation**: items arrive under `onResponseReceivedCommands[].appendContinuationItemsAction.continuationItems[]`
- **Channel videos continuation**: items arrive under `onResponseReceivedActions[].appendContinuationItemsAction.continuationItems[]`
- **Initial pages**: items are under `contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer.contents[]` (search) or `contents.twoColumnBrowseResultsRenderer.tabs[].tabRenderer.content.richGridRenderer.contents[]` (channel)

CRITICAL BUG (FIXED): `_parse_search_page()` and `_parse_channel_videos_page()` must check `continuation_items(data)` FIRST, then fall back to `initial_search_items(data)` / `initial_channel_video_items(data)`. If they only check the initial-page structure, continuation pages parse 0 videos.

CRITICAL BUG (FIXED): `continuation_token_from_items()` must receive FLATTENED nodes (after `iter_video_nodes()`), NOT raw items. Raw items contain `itemSectionRenderer` wrappers — the token is nested inside, not at the top level. Calling `continuation_token_from_items(raw_items)` returns None; calling it with `list(iter_video_nodes(raw_items))` finds the token.

### Pagination state machine
- Track `seen_tokens` set — stop on repeated token (`stop_reason="repeated_token"`)
- Track `seen_video_ids` set — dedup across pages
- Track `added` count per page — stop if 0 new videos (`stop_reason="no_progress"`)
- Impose `max_pages` cap (default 20) — stop at cap (`stop_reason="page_cap"`)
- Return `Result` envelope with `pages_requested`, `pages_succeeded`, `has_more`, `stop_reason`

## Result Envelope (V6 — replaces bare list returns)

All public collection methods return `Result` dataclass, NOT bare lists:
- `status`: 'ok' | 'empty' | 'partial' | 'error' | 'unsupported'
- `items`: list (may be non-empty even for 'partial')
- `reason`: explanation string
- `error_code`: HTTP status or error type
- `metadata`: dict with `requested`, `returned`, `pages_requested`, `pages_succeeded`, `has_more`, `truncated`, `stop_reason`

Factory methods:
- `Result.collection(items=, requested=, pages_requested=, ...)` — for paginated results
- `Result.error(reason, error_code=)` — for failures
- `Result.unsupported(reason)` — for unsupported endpoints
- `partial` status: items retained from successful pages + reason explaining why collection stopped

## V7 Codex Findings (final round)

### Autocomplete error handling
- `complete()` must return `None` on transport/parse failure, NOT `[]`. Returning `[]` makes `search_suggestions()` report `status="empty"` (valid response with zero results) when the request actually failed.
- `search_suggestions()` must check `if suggestions is None: return Result.error(...)` before treating as empty.

### Shorts classification (YouTube 2026)
- YouTube changed Shorts max duration to 3 minutes (180s) as of Oct 15 2024.
- OLD (wrong): `"short" if duration <= 60 else "long_form"` — misclassifies 61-180s Shorts as long_form.
- NEW (correct): `"short" if duration <= 180 else "long_form"`.
- This affects outlier cohort filtering (H4) and keyword competition median views/day by format (H5).
- Ideally, detect `is_short` from renderer/navigation endpoint. If unavailable, use duration threshold. If duration unknown, use `"unknown"` format — do NOT default to `long_form`.

### Report status propagation
- `competitor_report()` must check `suggested_result.status in {"partial", "error"}` (not just `.partial`) AND `growth.status in {"partial", "error"}`.
- If tracking/growth fails, report must be `partial` even if video collection succeeded.
- `compare_competitors()` must return `status="error"` (not `"partial"`) when ALL competitors fail and no rows were collected.

### Tracking as_of bug
- `channel_growth(as_of=...)` must use `get_channel_snapshot_at_or_before(channel_id, as_of)` for the "latest" snapshot, NOT just `get_channel_snapshots(limit=1)` which returns the newest in the entire DB (could be after `as_of`).

## Related Skills
- `youtube-research` — the skill that uses this API reference in practice (v2, Codex-reviewed)
- `browser-api-hijack` — how to capture InnerTube context/cookies from Chrome
- `chrome-cdp-control` — Chrome bridge for cookie refresh
- `codex` — Codex CLI review workflow: git init, commit, codex exec --sandbox danger-full-access
