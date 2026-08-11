# YouTube InnerTube API Format Changes (2026)

YouTube changed its InnerTube API response structure significantly in 2026.
This document maps old → new format for all affected parsers.
Updated after Codex V1 review (828-line review, 12 HIGH issues found, 8 fixed).

## 1. Channel Header

### OLD (pre-2026)
header.pageHeaderRenderer.content.pageHeaderMetaData.subscriberCountText

### NEW (2026)
header.pageHeaderRenderer.content.pageHeaderViewModel
  .title.dynamicTextViewModel.text.content          = channel name
  .metadata.contentMetadataViewModel.metadataRows[]
    .metadataParts[].text.content                   = "825 N nguoi dang ky" / "251 video"
    .metadataParts[].text.accessibilityLabel        = "825 nghin nguoi dang ky"

### Parser fix
Search metadataRows for parts containing "nguoi dang ky" (VN) or "subscriber" (EN)
for subscriber count, and "video" for video count.

## 2. Channel Videos Tab

### OLD params: Egh2aWRlb3PYBGAA
### NEW params (2026): EgZ2aWRlb3PyBgQKAjoA

### How to discover current params
Browse channel without params, read tabs[].tabRenderer.endpoint.browseEndpoint.params
for the tab titled "Video" (or "Videos").

## 3. Video List Items (channel browse, search results, suggested)

### OLD format: videoRenderer
richItemRenderer.content.videoRenderer
  .videoId, .title.runs[0].text, .viewCountText.simpleText,
  .lengthText.simpleText, .publishedTimeText.simpleText, .ownerText.runs[0].text

### NEW format: lockupViewModel
richItemRenderer.content.lockupViewModel
  .contentId                                          = videoId (DIRECT FIELD)
  .contentType                                        = "LOCKUP_CONTENT_TYPE_VIDEO"
  .contentImage.thumbnailViewModel.image.sources[0].url  contains /vi/{videoId}/ (fallback)
  .contentImage.thumbnailViewModel.overlays[0]
    .thumbnailBottomOverlayViewModel.badges[0]
    .thumbnailBadgeViewModel.text                     = "37:17" (duration)
  .metadata.lockupMetadataViewModel.title.content      = title
  .metadata.lockupMetadataViewModel.metadata
    .contentMetadataViewModel.metadataRows[0]
    .metadataParts[0].text.content                     = "26 N luot xem" (views, compact)
    .metadataParts[0].text.accessibilityLabel          = "26 nghin luot xem" (views, full)
    .metadataParts[1].text.content                     = "1 thang truoc" (published)

### Key differences
- videoId: contentId is a DIRECT field. Use it. Do NOT regex on serialized JSON.
- Duration: In thumbnail overlay badge text, NOT in a lengthText field.
- Views/published: In metadataRows, NOT in viewCountText/publishedTimeText.
- Channel name: NOT in channel video lockups. IS in suggested video lockupViewModel Row 0 Part 0.

## 4. Suggested Videos (/next endpoint)

### OLD: secondaryResults.results[].compactVideoRenderer
### NEW: secondaryResults.results[].itemSectionRenderer.contents[].lockupViewModel

### Suggested lockupViewModel structure (verified 2026-07-26)
- Row 0, Part 0: channel name (e.g. "Liam Ottley")
- Row 1, Part 0: views — content="228 N" (compact), accessibilityLabel="228 nghin luot xem" (full)
- Row 1, Part 1: published — content="4 thang truoc"
- Channel ID: avatar decoratedAvatarViewModel.rendererContext.commandContext.onTap.innertubeCommand.browseEndpoint.browseId
- Duration: thumbnail overlay badge text (e.g. "3:05:04")
- videoId: contentId field (direct)

### Parser must check BOTH content and accessibilityLabel
content has compact form ("228 N"), accessibilityLabel has full localized form ("228 nghin luot xem").
accessibilityLabel is more reliable for count extraction.

## 5. Like Count (/next endpoint)

### OLD (regex, fragile): search raw JSON for iconName LIKE title digit
### NEW (structured, canonical): walk response tree for likeCountEntity.likeCountIfIndifferentNumber
Returns exact integer string. Fallback: button title text regex.

## 6. Comment Count (/next endpoint)

### Structured: engagementPanels[].engagementPanelSectionListRenderer.header.engagementPanelTitleHeaderRenderer.contextualInfo.runs[0].text
### Fallback: regex on raw JSON for contextualInfo runs text digit
### May be None if comments disabled. Do NOT default to 0.

## 7. Number Parsing (VN vs EN) — CRITICAL BUG FIXED

### Vietnamese format
- "825 N" = 825,000 (N = nghin = thousand)
- "7,1 N" = 7,100 (comma = decimal separator)
- "1,2 Tr" = 1,200,000 (Tr = trieu = million)
- "89 nghin luot xem" = 89,000 (FULL WORD)
- "524 trieu luot xem" = 524,000,000 (FULL WORD)
- "1,3 ty luot xem" = 1,300,000,000 (ty = billion)

### English format
- "1.2M" = 1,200,000
- "45.6K" = 45,600

### BUG (v1): stripping commas/dots BEFORE multiplying
"1.2M" strip dots "12M" 12 * 1,000,000 = 12,000,000 (WRONG)
This corrupted ALL abbreviated counts.

### FIX (v2): parse float first, then multiply
MULTIPLIERS must include full Vietnamese words: nghin, trieu, ty
Return None for missing/unparseable, NOT 0.

## 8. Centralized Parser Pattern
Single parsers.py with parse_lockup_video(), parse_video_renderer(), parse_compact_video(),
parse_any_video() dispatch. All modules import from parsers.py.
parsers.py must NOT import from search.py (circular import). Define own helpers.

## 9. Auth Opt-in
authenticated=False by default. Cookies only loaded when authenticated=True.
_build_headers() only adds SAPISIDHASH when authenticated. Public calls work without cookies.

## 10. Transport Error Handling
Catch requests.Timeout, requests.ConnectionError, requests.JSONDecodeError.
Retry on 429, 500, 502, 503, 504 with exponential backoff + jitter.
Use params= dict instead of manual URL construction.
Timeout tuple (5, 20) — connect 5s, read 20s.
