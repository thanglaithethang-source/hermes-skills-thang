---
name: hermes-tool-integration
description: Install and configure external tools for Hermes — MCP servers, scripts, plugins. Covers platform-specific pitfalls, config patterns, and verification.
version: 1.0.0
---

# Hermes Tool Integration

Integrating external MCP servers, scripts, and plugins into Hermes.
Load when installing or configuring any external tool for Hermes.

## MCP Server Setup

### Standard workflow

1. Clone/install the server (git, pip, npm, etc.)
2. Ensure prerequisites: Python/Node version, API keys, external apps running
3. Install MCP SDK: `pip install mcp`
4. Register in `~/.hermes/config.yaml` under `mcp_servers` (see config format below)
5. Test connection: `hermes mcp test <name>`
6. Restart Hermes (`/reset` in session, or new `hermes` invocation)

### Config format

```yaml
mcp_servers:
  server-name:
    command: "python"        # or npx, uvx, node, or absolute path to venv python
    args:                    # CRITICAL: must be YAML list, not string
      - "/path/to/server.py"
    timeout: 120             # per-tool-call timeout in seconds
```

For HTTP-based servers, use `url` instead of `command` + `args`.

## Plugin Installation

### CRITICAL: Determine the correct Hermes home FIRST

Before any plugin install, verify where Hermes actually reads its config and plugins:

```bash
echo $HERMES_HOME
# If unset or differs from ~/.hermes, use $HERMES_HOME for all paths below.
# On Windows, HERMES_HOME is often %LOCALAPPDATA%\hermes (e.g. C:\Users\<user>\AppData\Local\hermes)
# while ~/.hermes resolves to C:\Users\<user>\.hermes — these are DIFFERENT directories.
```

**All plugin files and config MUST go to `$HERMES_HOME`, not `~/.hermes`.** Hermes reads plugins from `$HERMES_HOME/plugins/` and config from `$HERMES_HOME/config.yaml`. Installing to `~/.hermes/` when `$HERMES_HOME` points elsewhere means Hermes never sees the plugin.

### Pattern: third-party plugin with build script

Many external projects (e.g. `msitarzewski/agency-agents`) ship a plugin for Hermes.
The standard workflow:

1. Clone the repo
2. Run the project's build/converter script to generate Hermes plugin files
3. Copy generated plugin directory to `$HERMES_HOME/plugins/<plugin-name>/`
4. Enable in `$HERMES_HOME/config.yaml` under `plugins.enabled`
5. Restart Hermes session

Example — agency-agents full install (see `references/agency-agents-plugin.md` for plugin details, division breakdown, and usage):

```bash
# On Windows, use pwd -W for the build script (Python resolves /tmp differently than MSYS)
cd /tmp && git clone --depth 1 https://github.com/msitarzewski/agency-agents.git
cd agency-agents
python scripts/build-hermes-plugin.py --repo-root "$(pwd -W)" --out "$(pwd -W)/integrations/hermes"
# Copy to the CORRECT Hermes plugins dir (use $HERMES_HOME, not ~/.hermes)
mkdir -p "$HERMES_HOME/plugins"
rm -rf "$HERMES_HOME/plugins/agency-agents-router"
cp -R integrations/hermes/agency-agents-router "$HERMES_HOME/plugins/"
```

Then write `$HERMES_HOME/config.yaml`:
```yaml
plugins:
  enabled:
    - agency-agents-router
```

A plugin directory contains: `plugin.yaml` (metadata + tool declarations), `__init__.py` (handler logic), and a `data/` dir for any bundled assets.

### Plugin enable config format

Minimal `config.yaml` for enabling plugins (Hermes auto-merges with existing config):
```yaml
plugins:
  enabled:
    - plugin-name
```

No nested `plugins.enabled` write via `hermes config set` — it treats values as scalars. Write the file directly.

## Windows-Specific Pitfalls

### HERMES_HOME ≠ ~/.hermes — the silent plugin killer

**Symptom:** Plugin files copied to `~/.hermes/plugins/`, config updated at `~/.hermes/config.yaml`, but `hermes plugins list` shows 0 user plugins. Restarting sessions doesn't help.

**Root cause:** On Windows, `HERMES_HOME` often points to `%LOCALAPPDATA%\hermes` (e.g. `C:\Users\<user>\AppData\Local\hermes`), while `~/.hermes` in bash resolves to `C:\Users\<user>\.hermes`. These are **different directories**. Hermes reads plugins from `$HERMES_HOME/plugins/` and config from `$HERMES_HOME/config.yaml` — NOT from `~/.hermes/`.

**Detect:** Run `echo $HERMES_HOME` and compare with `echo $HOME/.hermes`. If they differ, you have the dual-directory problem.

**Fix:** Always use `$HERMES_HOME` (not `~/.hermes`) for:
- Plugin files: `$HERMES_HOME/plugins/<name>/`
- Config: `$HERMES_HOME/config.yaml`
- Config writes via Python: `os.path.expandvars(r"%LOCALAPPDATA%\hermes\config.yaml")`

**Verify the fix** by running a one-shot debug session:
```bash
HERMES_PLUGINS_DEBUG=1 timeout 15 hermes chat -q "hello" --quiet 2>&1 | grep "user.*manifest"
```
Expected: `user: 1 manifest(s)` (or more). `user: 0 manifest(s)` means Hermes still can't find your plugin.

### python3 is a broken Windows Store stub

**Symptom:** Running `python3` returns exit code 49 with output "Python tìm thấy" (Vietnamese: "Python found") and then fails. No Python code executes.

**Root cause:** On Windows, `python3` resolves to `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\python3` — a Store redirect stub, not a real interpreter. The actual Python is at `python` (3.11.15 in the Hermes venv).

**Fix:** Always use `python` on Windows, never `python3`. When a third-party script hardcodes `python3`, bypass it — either run the underlying Python script directly with `python`, or patch the script's shebang.

### Git clone in MSYS terminal

**Symptom:** `terminal` tool runs `git clone`, reports exit code 0 with "Cloning into..." but the cloned directory is not visible to subsequent `cd`, `ls`, or file operations through the same terminal.

**Root cause:** MSYS/git-bash path handling mismatch between the git subprocess and the bash shell session.

**Fix:** Use `execute_code` with Python's `subprocess.run` for git operations on Windows:

```python
import subprocess, os
target = os.path.expanduser("~/repo-name")
subprocess.run(["git", "clone", url, target], capture_output=True, text=True, timeout=180)
```

Same pattern applies to `python install.py` and similar post-clone steps — run them inside the same `execute_code` block or a follow-up `execute_code` call with `cwd=target`.

### Config YAML lists via hermes config set

**Symptom:** `hermes config set mcp_servers.name.args "['path/to/server.py']"` stores the value as a literal string `"['path/to/server.py']"` instead of a YAML list. MCP test fails with: `args: Input should be a valid list [type=list_type]`.

**Root cause:** `hermes config set` treats every value as a scalar string. It cannot produce YAML lists.

**Fix:** Use `execute_code` with `yaml.safe_dump` to write proper YAML:

```python
import yaml, os

config_path = os.path.expandvars(r"%LOCALAPPDATA%\hermes\config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

config['mcp_servers']['server-name']['args'] = ['C:/absolute/path/to/server.py']

with open(config_path, 'w') as f:
    yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

Always use forward slashes in paths (`C:/Users/...`) — accepted by all Hermes tools and avoids shell-escaping backslashes.

### pip install may target wrong Python

On Windows with Hermes's bundled Python, `pip install mcp` may install to the system Python while Hermes runs on a different interpreter. Verify with `pip --version` that the path matches the active Hermes Python. If MCP discovery fails with "MCP SDK not available", verify the package is visible from the same Python that runs Hermes.

## Verification

After setup, always:

1. `hermes mcp test <name>` — validates transport, auth, and tool discovery count
2. Check that discovered tools appear with the prefix `mcp_<server>_*`
3. Restart Hermes and confirm tools appear in a new session

## Provider Model Authenticity

When Sếp asks to verify whether an API provider is serving the real model or a knockoff ("hàng đè tem"), use benchmark trap questions (9.9 vs 9.11, strawberry letter count, Sally logic), behavioral signature comparison, and consistency tests. See `references/model-authenticity-check.md` for full methodology.
