# InnerTube Continuation Page Parsing — Response Structure Reference

## Problem
YouTube InnerTube initial responses and continuation (paginated) responses use DIFFERENT top-level JSON structures. Parsers that only handle the initial structure will return 0 items for all subsequent pages.

## Initial vs Continuation Response Structure

### Search — Initial Page
```json
{
  "contents": {
    "twoColumnSearchResultsRenderer": {
      "primaryContents": {
        "sectionListRenderer": {
          "contents": [
            {
              "itemSectionRenderer": {
                "contents": [
                  {"videoRenderer": {"videoId": "vid1", ...}},
                  {"videoRenderer": {"videoId": "vid2", ...}},
                  {"continuationItemRenderer": {
                    "continuationEndpoint": {
                      "continuationCommand": {"token": "TOKEN_HERE"}
                    }
                  }}
                ]
              }
            }
          ]
        }
      }
    }
  }
}
```

### Search — Continuation Page
```json
{
  "onResponseReceivedCommands": [
    {
      "appendContinuationItemsAction": {
        "continuationItems": [
          {"videoRenderer": {"videoId": "vid3", ...}},
          {"videoRenderer": {"videoId": "vid4", ...}}
        ]
      }
    }
  ]
}
```

### Channel Videos — Initial Page
```json
{
  "contents": {
    "twoColumnBrowseResultsRenderer": {
      "tabs": [
        {
          "tabRenderer": {
            "selected": true,
            "content": {
              "richGridRenderer": {
                "contents": [
                  {"richItemRenderer": {"content": {"lockupViewModel": {...}}}},
                  {"continuationItemRenderer": {...}}
                ]
              }
            }
          }
        }
      ]
    }
  }
}
```

### Channel Videos — Continuation Page
```json
{
  "onResponseReceivedActions": [
    {
      "appendContinuationItemsAction": {
        "continuationItems": [
          {"richItemRenderer": {"content": {"lockupViewModel": {...}}}}
        ]
      }
    }
  ]
}
```

## Key Differences
| Aspect | Initial Page | Continuation Page |
|--------|-------------|-------------------|
| Top-level key | `contents.twoColumn...` | `onResponseReceivedCommands` or `onResponseReceivedActions` |
| Action container | N/A | `appendContinuationItemsAction` |
| Items location | Nested in sectionList/richGrid | `continuationItems[]` directly |
| Search uses | `onResponseReceivedCommands` | — |
| Channel uses | `onResponseReceivedActions` | — |

## Parser Strategy
1. Check `continuation_items(data)` first — scans both `onResponseReceivedCommands` and `onResponseReceivedActions`
2. If empty, fall back to `initial_search_items(data)` or `initial_channel_video_items(data)`
3. Flatten with `iter_video_nodes()` — handles `itemSectionRenderer`, `richItemRenderer`, and direct renderer variants
4. Extract continuation token from FLATTENED nodes, NOT raw items — `continuation_token_from_items(nodes)` not `continuation_token_from_items(raw_items)`

## Common Bug
`continuation_token_from_items(raw_items)` returns None because raw_items contains wrapper objects like `itemSectionRenderer` — the `continuationItemRenderer` is nested inside. Must flatten first with `iter_video_nodes()` then pass the flattened list.

## Live Verification (2026-07-27)
- Search "AI automation" limit=40: 4 pages, 40 items, 0 duplicates ✓
- Channel videos limit=40: 2 pages, 40 items, 0 duplicates ✓
- Continuation token correctly extracted from both `onResponseReceivedCommands` (search) and `onResponseReceivedActions` (channel)
