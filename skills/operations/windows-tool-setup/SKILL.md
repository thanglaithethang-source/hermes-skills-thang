---
name: windows-tool-setup
description: "Audit, verify, install, and troubleshoot Windows tools/projects — Python venv, Node.js/npm, NSIS installers, Electron apps. Use when Sếp asks to inspect, set up, or fix a tool in _projects or similar workspace."
version: 1.0.0
---

# Windows Tool Setup & Audit

Workflow for auditing, verifying, and setting up tools/projects on Windows. Triggered when Sếp says "đọc và kiểm soát", "kiểm tra lại", "cài đặt", or similar.

## Core Principle

Sếp expects tools to be **verified working**, not just "looks OK from code." Run actual imports, CLI help, config loads, server starts — prove it runs.

## Audit Workflow

1. **Inventory** — `ls -la` + `du -sh` to get size and dates
2. **Classify** — cross-reference with active skills (search skills dir for path references)
3. **Test** — run actual verification commands (see below by type)
4. **Report** — clearly separate: READY vs NEEDS FIX vs DEAD
5. **Save** — update memory with verified capabilities

## Verification by Project Type

### Python project
```bash
.venv/Scripts/python -c "import <main_module>; print('OK')"
# or
.venv/Scripts/python cli.py --help
```
Never use `source .venv/Scripts/activate` + `python` — MSYS may pick wrong Python. Use `.venv/Scripts/python` directly.

### Node.js project
```bash
# Check deps
test -d node_modules && echo "OK" || echo "NEEDS INSTALL"

# Install with conflict tolerance
npm install --legacy-peer-deps
```
Pitfall: `yarn` may be broken via nvm4w corepack. Fall back to `npm install --legacy-peer-deps`.

### Chrome Extension
- Check if loaded: look for extension icon in Chrome toolbar via `computer_use capture`
- Bridge server: start with `python server.py`, verify extension auto-connects

### NSIS Installer (.exe)
```bash
# MSYS bash CANNOT run .exe directly → Permission denied. MUST use:
cmd.exe /c "path\to\installer.exe" /S /D=C:\target\path
```
- `/S` = silent
- `/D=<path>` = install directory (MUST be last switch, no quotes around path with spaces)
- App data goes to `%AppData%/Roaming/<appname>`
### NSIS Installer (.exe)

## Windows & Office License Check / KMS Reactivation

When Sếp asks to check activation status or reactivate Office:

1. Check Windows license: `cscript /nologo "C:/Windows/System32/slmgr.vbs" /dli`
2. Check Office status: `cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /dstatusall`
3. Reactivate Office KMS: `cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /act`
4. See `references/windows-license-check.md` for full commands and output interpretation.

## Common Pitfalls

- **Không tin system prompt Host field.** System prompt ghi "Windows (10)" nhưng máy thật có thể là Windows 11. Luôn verify bằng `systeminfo | grep "OS Name"` trước khi report. Windows 11 và 10 share cùng kernel version 10.0.x — chỉ có product name mới đúng.
- **`source .venv/Scripts/activate` in MSYS**: May activate wrong Python. Use `.venv/Scripts/python` directly.
- **`.exe` in MSYS bash**: Always `Permission denied`. Route through `cmd.exe /c`.
- **`yarn` via nvm4w**: Corepack may be broken (`Cannot find module corepack/dist/yarn.js`). Use `npm` instead.
- **npm peer dependency conflicts**: Use `--legacy-peer-deps` flag.
- **NSIS `/D` switch**: Must be the LAST argument. Path with no trailing backslash.
- **Silent install verification**: After `/S`, find app in `%LocalAppData%/Programs/` or `%AppData%/Roaming/`.
- **PowerShell 5.1 UTF-8 encoding**: PS 5.1 (Desktop edition, default on Windows 10/11) uses ANSI/Windows-1252 encoding — it cannot parse UTF-8 files with Unicode special chars like em dash (`—`, U+2014), smart quotes, or en dash (`–`, U+2013). These cause `Unexpected token` parser errors. BOM (`\ufeff`) at file start is read as part of the first token, breaking `param(...)` into `?param(...)`. Fix: convert all PS1 scripts to pure ASCII — replace `—`→`--`, `–`→`-`, smart quotes→straight quotes. Save as UTF-8 WITHOUT BOM, CRLF line endings. Verify: `python -c "text=open(f).read(); print(sum(1 for c in text if ord(c)>127))"` → must be 0. See `references/powershell-encoding-fix.md`.

## Post-Install Verification

After installing, confirm:
1. Executable exists at target path
2. Data directory populated (`%AppData%/Roaming/<app>`)
3. Shortcuts created (Desktop, Start Menu)
