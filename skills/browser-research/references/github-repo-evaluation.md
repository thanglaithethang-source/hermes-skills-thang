# GitHub Repo Evaluation for Agent Compatibility

## Problem

GitHub search results and README tags often claim compatibility with tools
(e.g., "supports Hermes Agent") but have zero actual integration code.
Marketing tags ≠ real support.

## Workflow

### 1. Search GitHub API

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/repositories?q=<keywords>&sort=stars&per_page=10"
```

Parse results: full_name, stars, description, html_url.

### 2. Clone promising repos

```bash
git clone https://github.com/<owner>/<repo>.git
```

### 3. Search codebase for actual integration evidence

```bash
# Search for the tool name in source code (not just README)
grep -r "hermes" --include="*.ts" --include="*.py" --include="*.js" --include="*.json" .
```

If zero results in source files → the "support" is marketing only.

### 4. Assess the architecture

- Is it a standalone tool? Plugin? MCP server?
- What's the install mechanism? (npm, pip, npx, curl pipe)
- What's the dependency on? (Claude Code hooks, custom runtime, etc.)
- Can Hermes actually integrate with it?

### 5. Give concise verdict

Format:
```
VERDICT: [COMPATIBLE / INCOMPATIBLE / PARTIAL]
WHY: [one sentence]
ACTION: [what to do next, if anything]
```

## Key Heuristics

| Signal | Means |
|--------|-------|
| Zero mentions in source code | Marketing tag only — NOT compatible |
| MCP server exposed | Can integrate via `hermes mcp add` |
| Depends on Claude Code hooks | Claude-only — NOT portable |
| Single binary / pip install | Likely portable |
| Plugin marketplace for specific tool | Locked to that tool |

## Real Example: claude-mem

- GitHub search said "Works with Hermes Agent"
- Cloned, searched `hermes` in entire codebase → 0 results
- Architecture: Claude Code plugin marketplace + Claude Agent SDK hooks
- Verdict: INCOMPATIBLE — Claude Code only, despite marketing claims
