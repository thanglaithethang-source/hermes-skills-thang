# GitHub Repo Search — Technique Reference

## When to use

When Sếp asks to find "repo hay hay", "open source nào hợp", or wants to explore
GitHub for tools/frameworks that fit a goal.

## Core technique: GitHub Search API with star qualifier

The `stars:>N` qualifier is the single most effective filter for quality.

```
https://api.github.com/search/repositories?q=KEYWORD+stars:%3E10000&sort=stars&order=desc&per_page=15
```

- `%3E` = URL-encoded `>`
- `sort=stars&order=desc` = highest stars first
- `per_page=15` = good balance of coverage vs token cost

## Token extraction (Windows, no gh CLI)

```bash
GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
```

## Multi-category search pattern

When the goal is broad (e.g. "one-person AI company"), a single query is too
narrow. Run multiple queries across categories and merge:

```bash
GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')

for CATEGORY in "ai+agent+automation" "workflow+orchestration" "social+media+automation" "multi+agent+system"; do
  echo "=== $CATEGORY ==="
  curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/search/repositories?q=${CATEGORY}+stars:%3E5000&sort=stars&order=desc&per_page=10" \
    | python -c "
import sys, json
for r in json.load(sys.stdin)['items']:
    print(f\"  {r['full_name']} | ★{r['stargazers_count']} | {r.get('language','?')} | {(r['description'] or 'N/A')[:90]}\")
"
done
```

## Deep-dive a single repo

Before recommending a repo, read:

1. **Repo metadata** — stars, forks, language, license, topics, last updated
2. **README** — features, install instructions, usage
3. **package.json** (if JS/TS) — dependencies, scripts, version
4. **Repo structure** — list root contents, identify architecture
5. **Releases** — check for pre-built installers (.exe, .dmg, .AppImage)
6. **Source files** — read key files to understand tech stack

### API calls

```bash
# Repo metadata
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  | python -c "
import sys, json
r = json.load(sys.stdin)
print(f'Stars: {r[\"stargazers_count\"]} | Forks: {r[\"forks_count\"]} | Lang: {r.get(\"language\",\"?\")}')
print(f'Updated: {r[\"updated_at\"]} | License: {r.get(\"license\",{}).get(\"spdx_id\",\"None\") if r.get(\"license\") else \"None\"}')
print(f'Topics: {r.get(\"topics\",[])}')
"

# README
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/readme" \
  | python -c "
import sys, json, base64
print(base64.b64decode(json.load(sys.stdin)['content']).decode('utf-8'))
"

# Root contents
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/" \
  | python -c "
import sys, json
for f in json.load(sys.stdin):
    t = 'DIR ' if f['type'] == 'dir' else 'FILE'
    print(f'{t} {f[\"name\"]}')
"

# Releases + assets (installers)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/releases?per_page=3" \
  | python -c "
import sys, json
for r in json.load(sys.stdin):
    print(f'Tag: {r[\"tag_name\"]} | Date: {r[\"published_at\"]}')
    for a in r.get('assets', []):
        print(f'  -> {a[\"name\"]} ({a[\"size\"]//1024//1024}MB)')
"

# Language breakdown
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/languages

# Read a specific source file
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/path/to/file.ts" \
  | python -c "
import sys, json, base64
print(base64.b64decode(json.load(sys.stdin)['content']).decode('utf-8'))
"
```

## Star threshold guide

| Sếp's signal | Threshold |
|---|---|
| Default search | `stars:>5000` |
| "rác quá", "hàng chục ngàn sao" | `stars:>10000` |
| "hàng trăm ngàn sao" | `stars:>50000` |
| Niche/specific tool | `stars:>100` (lower is OK) |

## Scope matching

When Sếp asks for repos that "fit" them, identify the GOAL behind the request:

| Sếp says | Underlying goal | Search categories |
|---|---|---|
| "xây công ty AI 1 người" | Solo business automation | workflow, multi-agent, social media, CRM, analytics, content pipeline |
| "tìm tool video hay" | Video production | ffmpeg, video editing, ai video, subtitle, remotion |
| "tìm tool AI hay" | General AI tools | ai agent, llm, image gen, tts, automation |

Never search only the literal keywords. Decompose the goal into categories,
search each, merge results.

## Pitfalls

- **Single query too narrow**: "ai video" returns mostly content creation tools.
  To find business automation tools, search "workflow automation", "multi-agent",
  "social media" separately.
- **Small repos look interesting but are often abandoned**: always check
  `updated_at` — if > 6 months old with < 100 stars, likely unmaintained.
- **License matters**: AGPL-3.0 requires open-sourcing derivative works.
  Apache-2.0 and MIT are most permissive. Check before recommending for
  commercial use.
- **Stars ≠ quality**: a 200k-star repo might be a tutorial list. Read the
  description and README to understand what it actually is.
