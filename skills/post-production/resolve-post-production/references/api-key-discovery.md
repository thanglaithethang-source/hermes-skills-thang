# API Key Discovery & Setup

## When Sếp says "tao đã cấp key" but env is empty

Sếp stores API keys in multiple locations. Search in THIS ORDER:

1. **Environment variables** — `echo $FREESOUND_API_KEY`, `echo $PIXABAY_API_KEY`, `echo $PEXELS_API_KEY`
2. **`~/.hermes/` key files** — `cat ~/.hermes/pexels.key`, `cat ~/.hermes/pixabay.key`, `ls ~/.hermes/*.key`
3. **`$HERMES_HOME/.env`** — `cat $HERMES_HOME/.env | grep -i key`
4. **`$HERMES_HOME/auth.json`** — credential pool, may contain API keys
5. **Session history** — `session_search(query="API key freesound pixabay pexels")` — Sếp often listed all keys in a session titled "Danh sách API đã cấp"
6. **Profile memories** — `cat $HERMES_HOME/profiles/resolve/memories/MEMORY.md` (or whichever profile was used for post-production) — keys are often saved as `FREESOUND [date] Token <value>`
7. **Shell profiles** — `~/.bashrc`, `~/.bash_profile`

## CRITICAL: Never give up after env check

If `$FREESOUND_API_KEY` is empty, that does NOT mean Sếp didn't provide it. It means it's stored elsewhere. Session history + profile memory are the most reliable secondary sources. Sếp stores keys once and expects you to find them.

## Key formats

| Service | Key location | Format |
|---------|-------------|--------|
| **Pexels** | `~/.hermes/pexels.key` | Long alphanumeric string (~55 chars) |
| **Pixabay** | `~/.hermes/pixabay.key` | `NNNNNNNN-XXXXXXXXXXXXXXXXXXXXXXXX` |
| **Freesound** | resolve profile `MEMORY.md` | `r7EZ...` (Client Secret = API token, NOT Client ID) |
| **GitHub** | `~/.hermes/.env` | `ghp_...` |

## Freesound: Client Secret = API Token (not Client ID)

When Sếp provides Freesound OAuth2 credentials:
- **Client ID** (`zrGZ...`) → NOT the API token. Using with `token=` → `"Invalid token"`.
- **Client Secret** (`r7EZ...`) → THIS IS THE API TOKEN. Use with `token=` → works.

## Verification

```bash
# Freesound
curl -s "https://freesound.org/apiv2/search/text/?query=pop&token=TOKEN&page_size=1"

# Pixabay (search OK, video download may 403)
curl -s "https://pixabay.com/api/?key=KEY&q=music&per_page=3"

# Pexels
curl -s -H "Authorization: KEY" "https://api.pexels.com/v1/search?query=nature&per_page=1"
```

## Known API limitations

| API | Status | Note |
|-----|--------|------|
| **Freesound** | Full access | Search + download, rate limit 0.3-0.5s between requests |
| **Pixabay** | Search only | Standard API returns photos/videos. Video download URLs return 403 on hotlink. Music-only endpoint (`/api/music/`) returns 404. |
| **Pexels** | Check key | Error 1010 = key expired/invalid. Error 403 otherwise = wrong auth format. |

## Freesound URL encoding (CRITICAL)

The `filter` parameter contains spaces and brackets that MUST be URL-encoded. Using `query.replace(' ', '+')` is NOT enough. Always use `urllib.parse.urlencode`:

```python
import urllib.parse
params = urllib.parse.urlencode({
    "query": "cartoon pop",
    "token": FREESOUND_KEY,
    "page_size": 3,
    "fields": "id,name,duration,previews,avg_rating",
    "sort": "rating_desc",
    "filter": "duration:[0.3 TO 5.0]"
})
url = f"https://freesound.org/apiv2/search/text/?{params}"
```

Without proper encoding, `urllib.request` throws `URL can't contain control characters` on the spaces in the filter parameter.

## Pixabay music workaround

Pixabay's standard API does NOT have a music/audio endpoint. The video endpoint returns some music-tagged hits but downloading the actual video files fails (403). For background music, prefer Freesound with `filter=duration:[15.0 TO 300.0]` or use local library.

## Per-page gotcha

Pixabay's `per_page` parameter has a limited range. Values like 1, 2, 10, 20 may return `[ERROR 400] "per_page" is out of valid range`. Use `per_page=3` or `per_page=5`.
