# GitHub Repo Deep Inspection via REST API

Pattern for evaluating an open-source GitHub repo remotely — before cloning, forking, or recommending to the user. Uses only the REST API + curl + python. No `gh` CLI needed.

## Prerequisites

```bash
GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
```

On Windows (git-bash/MSYS), use `python` not `python3` — `python3` is missing on this host.

## Inspection Order (least to most data)

1. **Repo metadata** — stars, forks, language, license, topics, last update
2. **README** — full project description, features, roadmap
3. **Directory structure** — top-level dirs/files to understand architecture
4. **package.json / equivalent** — dependencies, scripts, build system
5. **Key source files** — entry points, core logic (read via contents API)
6. **Releases** — version history, download assets (installer URLs + sizes)
7. **Open issues** — project health, known bugs, feature requests
8. **Languages** — language breakdown (bytes per language)

## Endpoints Used

| Step | Endpoint | Notes |
|------|----------|-------|
| Metadata | `GET /repos/{owner}/{repo}` | stars, forks, license, topics, updated_at |
| README | `GET /repos/{owner}/{repo}/readme` | returns base64-encoded content |
| Dir listing | `GET /repos/{owner}/{repo}/contents/{path}` | array of {name, type, size}; path optional (root) |
| File content | `GET /repos/{owner}/{repo}/contents/{path}` | single file → base64-encoded content |
| Releases | `GET /repos/{owner}/{repo}/releases?per_page=3` | tag_name, assets[{name, size, browser_download_url}] |
| Issues | `GET /repos/{owner}/{repo}/issues?state=open&per_page=5` | number, title, comments |
| Languages | `GET /repos/{owner}/{repo}/languages` | {lang: bytes} object |

## Base64 Decode Pattern

The README and file-content endpoints return `{"content": "<base64>", "encoding": "base64"}`.
Decode with python:

```bash
# README
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/readme" | \
  python -c "import json,sys,base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode('utf-8'))"

# Single file
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/electron/ffmpeg/index.ts" | \
  python -c "import json,sys,base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode('utf-8'))"
```

## Directory Listing Pattern

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/electron" | \
  python -c "
import json,sys
d=json.load(sys.stdin)
if isinstance(d, list):
    for f in d:
        t='DIR ' if f['type']=='dir' else 'FILE'
        print(f'{t} {f[\"name\"]}')
else:
    print(d)  # error message
"
```

## Multi-Query Batch Pattern

When researching multiple repos or categories, batch the curl calls in a single
terminal command. Each query is independent — no serialization needed.

```bash
GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')

echo "=== CATEGORY 1 ==="
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/repositories?q=ai+video+generation&sort=stars&order=desc&per_page=5" | \
  python -c "
import json,sys
d=json.load(sys.stdin)
for r in d.get('items',[]):
    print(f\"{r['full_name']} | ⭐{r['stargazers_count']} | {r.get('language','?')} | {r['description'][:80] if r['description'] else 'N/A'}\")
"

echo ""
echo "=== CATEGORY 2 ==="
# ... another search query
```

## Search API

```
GET /search/repositories?q={query}&sort=stars&order=desc&per_page=5
```

Query syntax: space-separated terms = AND. Use `+` for spaces in URL.
Can filter by language: `q=video+editing+language:python`.

## Output Format for User

When presenting repo evaluation results to Sếp, use this structure:
- Repo name + stars + license (one line)
- GitHub URL
- One-paragraph description (what it does)
- Tech stack (languages, frameworks, key dependencies)
- Architecture summary (key directories and their purpose)
- Features implemented vs planned
- Releases (version, date, download assets)
- Fit assessment: why it matches (or doesn't) the user's profile
- Limitations / gotchas (license restrictions, missing features, language barriers)

## Real Example: short-video-factory (2026-07-25)

Evaluated YILS-LIN/short-video-factory (4970⭐, AGPL-3.0) for Sếp.

Pipeline used:
1. Searched GitHub API across 5 categories (ai video, ai agents, video editing, money printer, trending this week)
2. Got repo metadata: stars, forks, language, license, topics, updated_at
3. Fetched README → decoded base64 → extracted features, roadmap, install instructions
4. Listed root dir → found Electron + Vue structure
5. Fetched package.json → identified key deps: ffmpeg-static, edge-tts, better-sqlite3, ws
6. Drilled into electron/ffmpeg/index.ts → found renderVideo() function (FFmpeg pipeline)
7. Drilled into electron/tts/index.ts → found EdgeTTS synthesize + SRT generation
8. Fetched releases → found Windows .exe installer (91MB)
9. Fetched open issues → found EdgeTTS network issues, TwelveLabs feature request
10. Got language breakdown: TypeScript 58%, Vue 41%

Verdict: PARTIAL fit — OpenAI-compatible API (works with api.ai-box.vn), FFmpeg stack matches, EdgeTTS is free, local-first. But no color grading, no Fusion effects, no AI video generation. AGPL-3.0 restricts derivative distribution.
