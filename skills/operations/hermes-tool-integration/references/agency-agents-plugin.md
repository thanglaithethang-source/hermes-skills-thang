# Agency Agents — Hermes Plugin Reference

Installed from: `msitarzewski/agency-agents` (254 agents, MIT license)
Plugin name: `agency-agents-router`
Location: `$HERMES_HOME/plugins/agency-agents-router/`

## Plugin Structure

```
agency-agents-router/
  plugin.yaml       — metadata + declares 4 tools in toolset "agency_agents"
  __init__.py        — handler logic (search, inspect, load, delegate)
  data/
    agents.json      — full roster: 254 agents, ~3.7MB JSON
```

## Tools Exposed

All tools belong to toolset `agency_agents`:

| Tool | Params | Purpose |
|------|--------|---------|
| `agency_agents_search` | query, division?, limit? | Find agents by keyword/division |
| `agency_agents_inspect` | agent/slug, include_body? | Read one agent's metadata or full body |
| `agency_agents_load` | agent/slug, task? | Load agent as prompt block for current task |
| `agency_agents_delegate` | agent/slug, task, toolsets? | Delegate task to agent via `delegate_task` |

## Division Breakdown (17 divisions, 254 agents)

- engineering (49), specialized (54), marketing (36), game-development (20), gis (13)
- security (10), design (9), sales (9), testing (9), paid-media (7)
- project-management (7), academic (6), spatial-computing (6), support (6)
- finance (5), product (5), healthcare (3)

## Usage Pattern

The user does NOT call tools directly — the Hermes agent handles it:

1. User says "I need to optimize my database"
2. Agent calls `agency_agents_search(query="database optimization")`
3. Results include Database Optimizer, Backend Architect, SRE
4. Agent picks best match → `agency_agents_load(agent="database-optimizer", task="...")`
5. Agent persona is injected into context, specialist takes over

## Install Commands (Windows)

```bash
cd /tmp && git clone --depth 1 https://github.com/msitarzewski/agency-agents.git
cd agency-agents
# On Windows, use pwd -W for the build script (Python resolves /tmp differently than MSYS bash)
python scripts/build-hermes-plugin.py --repo-root "$(pwd -W)" --out "$(pwd -W)/integrations/hermes"
# Copy to $HERMES_HOME (NOT ~/.hermes — see pitfall below)
mkdir -p "$HERMES_HOME/plugins"
rm -rf "$HERMES_HOME/plugins/agency-agents-router"
cp -R integrations/hermes/agency-agents-router "$HERMES_HOME/plugins/"
```

Config (`$HERMES_HOME/config.yaml`):
```yaml
plugins:
  enabled:
    - agency-agents-router
```

Restart Hermes session after install.

## Debugging

If the plugin doesn't appear after `/new`, check with:

```bash
HERMES_PLUGINS_DEBUG=1 timeout 15 hermes chat -q "hello" --quiet 2>&1 | grep -i "agency-agents"
```

Expected output:
```
Parsed manifest: key=agency-agents-router ... source=user
Loading plugin 'agency-agents-router' ...
Plugin agency-agents-router registered tool: agency_agents_search
...
```

If you see `user: 0 manifest(s)`, the plugin is in the wrong directory. Check `echo $HERMES_HOME` vs `echo $HOME/.hermes`.

## Pitfalls

- **CRITICAL: `$HERMES_HOME` ≠ `~/.hermes` on Windows.** `HERMES_HOME` is often `%LOCALAPPDATA%\hermes` (e.g. `C:\Users\<user>\AppData\Local\hermes`), while `~/.hermes` resolves to `C:\Users\<user>\.hermes`. Install plugins and config to `$HERMES_HOME`, not `~/.hermes`.
- The repo's `install.sh` and `convert.sh` hardcode `python3` — fails on Windows. Run `build-hermes-plugin.py` directly with `python`.
- Plugin is lazy-loaded: agents are NOT preloaded into skill catalog. They appear only when searched/loaded via the tools.
- Agent slugs are auto-generated from names via `re.sub(r'[^a-z0-9]+', '-', name.lower())`. Search by slug or exact display name.
- `hermes config set` cannot write nested keys like `plugins.enabled`. Use Python/yaml to write the config file directly.
- The `hermes-agent` skill (bundled) is protected — cannot be edited. All plugin/tool integration knowledge lives in this skill instead.
