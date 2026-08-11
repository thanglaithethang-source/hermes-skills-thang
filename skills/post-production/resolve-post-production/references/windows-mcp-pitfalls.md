# Windows MCP Pitfalls — DaVinci Resolve

## Error 1: fusionscript DLL load failed

**Symptom (server.log):**
```
ERROR - Cannot import DaVinciResolveScript: DLL load failed while importing fusionscript: The specified module could not be found.
INFO - Starting DaVinci Resolve MCP Server (32 compound tools)
```
Server starts in degraded mode (32 tools instead of 34). `hermes mcp test` may still report 34 tools (schema listing vs actual connection differ).

**Root causes (either or both):**
1. Python 3.11+ — fusionscript binary compiled for Python 3.10
2. Wrong fusionscript.dll path — `get_resolve_paths()` hardcodes `C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`

**Fix A: MCP config env override (non-invasive)**
```yaml
# resolve/config.yaml
mcp_servers:
  davinci-resolve:
    command: C:/Users/thang/AppData/Local/Programs/Python/Python310/python.exe
    env:
      RESOLVE_SCRIPT_LIB: D:\davinci\fusionscript.dll
```

**Fix B: Patch platform.py (permanent)**
In `get_resolve_paths()`, after default `lib_path` assignment, add:
```python
# Fallback: try common alternative install paths
if not os.path.isfile(lib_path):
    for alt in [r'D:\davinci\fusionscript.dll', r'D:\DaVinci Resolve\fusionscript.dll']:
        if os.path.isfile(alt):
            lib_path = alt
            break
```

**Verification:**
```bash
"C:/Users/thang/AppData/Local/Programs/Python/Python310/python.exe" -c "
import os, sys
os.environ['RESOLVE_SCRIPT_LIB'] = r'D:\davinci\fusionscript.dll'
os.add_dll_directory(r'D:\davinci')
sys.path.insert(0, r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules')
import DaVinciResolveScript as dvr
r = dvr.scriptapp('Resolve')
print(f'OK: {r.GetVersionString()}' if r else 'FAIL: None')
"
```

## Error 2: Resolve not found at C:\Program Files\...\Resolve.exe

**Symptom (server.log):**
```
INFO - Resolve not running, attempting to launch automatically...
ERROR - DaVinci Resolve not found at C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe
```

**Cause:** `_launch_resolve()` in server.py hardcodes `C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe`. Resolve installed at non-standard path (e.g., `D:\davinci\Resolve.exe`).

**Fix:** Same as Error 1 Fix B — auto-detect from running process via `wmic`:
```python
import subprocess
result = subprocess.run(
    ['wmic', 'process', 'where', 'name="Resolve.exe"', 'get', 'ExecutablePath'],
    capture_output=True, text=True, timeout=5
)
for line in result.stdout.splitlines():
    if line.strip().lower().endswith('resolve.exe'):
        resolve_dir = os.path.dirname(line.strip())
        # Use this dir for both fusionscript.dll and Resolve.exe
```

## Error 3: MCP test passes but tools fail

**Symptom:** `hermes mcp test` → 34 tools, but actual tool calls return `NOT_CONNECTED`.

**Cause:** MCP server process starts, FastMCP registers 34 schema definitions, but the lazy Resolve connection (`get_resolve()`) fails on first tool call because fusionscript import failed silently.

**Check:** Always read `davinci-mcp/logs/server.log` for the real story. `hermes mcp test` is a server-startup check, NOT a Resolve API connectivity check.

**Real verification:**
```bash
hermes -p resolve chat -q "resolve_control action='get_version'"
# Must return actual version string, not error.
```
