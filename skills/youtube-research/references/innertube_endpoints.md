# InnerTube endpoint and client profile reference

Runtime constants come from `scripts/client_profile.py`.

## Known-good profile

- Profile ID: `web-2026-07-24-v1`
- Client name: `WEB`
- Client version: `2.20260724.01.01`
- Default locale: `hl=en`, `gl=VN`
- Base URL: `https://www.youtube.com/youtubei/v1/{endpoint}`
- Search sort params, before request encoding:
  - views: `CAMSAhAB`
  - date: `CAISAhAB`
- Channel videos params, before request encoding: `EgZ2aWRlb3PyBgQKAjoA`
- Browse IDs: trending `FEtrending`; home `FEwhat_to_watch`

The API key is supplied as the `key` query parameter. `YT_INNERTUBE_KEY` may override the packaged
public web key. Request libraries perform URL encoding; do not pre-percent-encode these values.

## Authentication

Unauthenticated public mode is the default. Authenticated mode uses
`Authorization: SAPISIDHASH {timestamp}_{sha1}` where the digest input is
`"{timestamp} {SAPISID} https://www.youtube.com"`. Only allowlisted YouTube cookies are sent.
Authenticated mode is strict by default: missing or invalid auth material is an error rather than a
silent public-mode downgrade.

## Requests

### Search

Initial `POST /search`:

```json
{"context": {"client": {}}, "query": "keyword", "params": "CAMSAhAB"}
```

Continuation `POST /search`:

```json
{"context": {"client": {}}, "continuation": "token"}
```

Initial results may use `videoRenderer` or lockup/entity variants under a section list or rich grid.
Continuation results may appear under `onResponseReceivedCommands` or
`onResponseReceivedActions`.

### Browse

Initial `POST /browse` uses `browseId` and, for channel videos, the raw `params` value. Trending and
home use the profile browse IDs. Continuations use `{"context": ..., "continuation": "token"}`.
Channel and feed content may be nested in tabs, section lists, rich grids, or continuation actions.

### Next

`POST /next` uses `videoId` and returns sampled related/suggested entries. A successful `/player`
response combined with a failed `/next` response produces a partial video result.

### Player

`POST /player` uses `videoId`. `videoDetails` provides public metadata; exact `publishDate` is read
from microformat data. Playability failures are propagated. Batch publish-date enrichment calls
`/player` once per unique valid video ID, retains localized `published_raw`, and marks failures as
partial with `publish_date=None`.

### Autocomplete

`GET https://suggestqueries.google.com/complete/search` sends `client=youtube`, `ds=yt`, `q`, `hl`,
and `gl` as query parameters. The client accepts exact JSON and validates the JSONP wrapper when
present.

## Response drift contract

Every surface parser records `recognized_container`, `candidate_nodes`, `parsed_nodes`, and
`unknown_renderer_types`, along with response kind and a bounded shape fingerprint. A recognized
container with zero candidates is legitimate `empty`. An unrecognized HTTP-200 response is
`unsupported`. A later page that drifts retains prior items and returns `partial`.
