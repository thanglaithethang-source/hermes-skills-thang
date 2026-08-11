# Codex Review Findings — youtube-research skill

## Review History
- V1 (2026-07-26): 3/10 readiness. 12 HIGH + 12 MEDIUM issues. 828-line review.
- V2 (2026-07-26): 4/10 readiness. 6 new HIGH issues from V1 fixes. 285-line review.
- V3 (2026-07-26): 5/10 readiness. Fixed to_markdown None crash, surface-aware lockup, comment compact parse, removed total_views.
- V4 (2026-07-26): 6/10 readiness. Fixed independent views/date parse, known_channel_id pass, comment regex removed, view_count None, keyword None-safe, GET hardening.
- V5 (2026-07-26): 6/10 readiness. Fixed statistics.median, None aggregates, browse_feed parse_any_video, handle lookup hardened.
- V6 (2026-07-26): 6.5/10 readiness. Added pagination, SQLite storage, VPH, outlier, keyword score, competitor tracking. 6 HIGH remain.

## V1 Findings (all fixed)
- H1: Count parser `1.2M` → `12,000,000` (should be 1,200,000). Fixed: parse float first, then multiply.
- H2: lockupViewModel parser used regex on serialized JSON. Fixed: centralized parser using `contentId`, `accessibilityLabel`, avatar `browseEndpoint`.
- H3: Like/comment extraction used fragile regex. Fixed: structured traversal for `likeCountEntity.likeCountIfIndifferentNumber`.
- H4: Trending returned `[]` silently. Fixed: returns `{status, reason, videos}`.
- H5: Transport errors crashed report. Fixed: catch timeout/connection/JSON, retry 429/5xx with jitter.
- H6-H8: CTR/retention/RPM returned fake point estimates with fake confidence. Fixed: `estimable=False` + observable proxies + scenario ranges.
- H9: Full cookie jar auto-loaded. Fixed: auth opt-in (`authenticated=False` default).
- H11: `total_views`/`joined_date` promised but never populated. Fixed: removed from output.

## V2 Findings (all fixed)
- H-A: `to_markdown()` crashed with TypeError on None values. Fixed: `fmt_count()` helper, schema-aware rendering.
- H-B: lockup parser assumed fixed row positions (channel name in row 0). Broke on channel Videos tab. Fixed: classify parts by semantics, not row position.
- H-C: Comment count failed on compact VN "2,4 Tr". Fixed: parse through `_parse_count()`, validate `panelIdentifier`.
- H-D: `or 0` in parsers collapsed None into false zero. Fixed: removed `or 0`, use `isinstance` checks in consumers.
- H-E: `total_views=0` still in report output. Fixed: removed from report dict entirely.

## V6 Findings (6 HIGH remain — IMPLEMENTATION_PLAN.md being created by Codex)
- H1: Pagination continuation pages parse 0 videos. `_parse_search_page()` and `_parse_channel_videos_page()` only read initial page structure (`contents.twoColumnSearchResultsRenderer`). Continuation data arrives under `onResponseReceivedCommands[].appendContinuationItemsAction.continuationItems` (search) and `onResponseReceivedActions[].appendContinuationItemsAction.continuationItems` (channel). Parser must handle both shapes.
- H2: `result.py` defines Result envelope but NO module imports or uses it. All collection methods still return `[]` on error — indistinguishable from empty success.
- H3: VPH unsafe — `views_first = first.get('view_count') or 0` coerces None to 0. Storage uses `ASC LIMIT 100` (returns oldest, not newest). No minimum elapsed interval check.
- H4: Outlier baseline includes target video itself. No age/format normalization. Percentile ties all report 100%.
- H5: Keyword score saturates — 10 unique channels + 661K avg views = 97/100. Double-counts diversity/concentration. `keyword` argument unused.
- H6: Competitor tracking is raw `get_channel_snapshots()` — no auto-snapshot, no growth/delta calculation, no multi-channel comparison, no report integration.

## Key Workflow Lesson (V6)
- **When stuck on hard issues → ask Codex to create IMPLEMENTATION_PLAN.md first, then fix according to plan.** Do NOT cắm đầu cắm cổ fix trước rồi mới review. Sếp yêu cầu: Codex lập plan chi tiết → fix theo plan → Codex review lại → loop.

## Key Lessons
1. **Never collapse unknown into zero** — `None` means "not found", `0` means "found and it's zero". These are different.
2. **Surface-aware parsing** — YouTube lockupViewModel has different row layouts on different surfaces (channel videos vs suggested). Classify by semantics, not position.
3. **accessibilityLabel > content** — YouTube puts full localized text in accessibilityLabel, compact form in content. Always check both.
4. **Vietnamese full words** — `nghìn` and `triệu` must be in multipliers dict, not just `n` and `tr`.
5. **Codex review loop** — git init → commit → codex exec --sandbox danger-full-access → read review → fix → commit → re-review. Takes 5-9 min per round, ~130K tokens.
6. **Continuation response shape differs from initial** — search continuation arrives under `onResponseReceivedCommands`, channel under `onResponseReceivedActions`. Both use `appendContinuationItemsAction.continuationItems`. Parser must handle BOTH shapes.
7. **`_extract_text` name mangling** — function defined as `__extract_text` (double underscore) but called as `_extract_text` (single). Python name mangling bug. Always verify function names match exactly.
8. **Plan before fix** — when issues are complex (pagination, analytics calibration), ask Codex to create IMPLEMENTATION_PLAN.md with exact code snippets BEFORE fixing. Do not fix blindly.
