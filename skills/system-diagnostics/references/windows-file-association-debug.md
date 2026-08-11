# Windows File Association Debugging

## Symptom
Double-clicking a `.py` (or other extension) file flashes a cmd window then closes immediately. Script works fine from terminal. "Trước đây chạy vẫn ok."

## Root Cause: UserChoice Registry Hijack
Windows has two layers of file association:
1. **System-level**: `HKCR\.py` → `Python.File` → `HKCR\Python.File\shell\open\command`
2. **User-level override**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.py\UserChoice`

**UserChoice takes priority.** If a Microsoft Store app registers for the extension, it writes a `ProgId` pointing to an `AppX...` Store app ID, plus a cryptographic `Hash`. Windows then opens files with the Store app instead of `py.exe`.

## Diagnosis Steps

### 1. Check system association
```bash
cmd.exe /c "assoc .py && ftype Python.File"
```
Expected: `.py=Python.File` → `"C:\WINDOWS\py.exe" "%L" %*`

### 2. Check UserChoice (the hijacker)
```bash
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.py\UserChoice" /s
```
If `ProgId` is `AppX...` instead of `Python.File` → hijacked.

### 3. Check what Python versions py.exe sees
```bash
py -0p
```

## Fix

### Method A: Python winreg (works when reg.exe gets "Access is denied")

Windows locks `UserChoice` keys — `reg delete` and PowerShell `Remove-ItemProperty` both fail with "Access is denied". But Python's `winreg` can open the **parent** key with `KEY_ALL_ACCESS` and delete the UserChoice **subkey**:

```python
import winreg
parent = winreg.OpenKey(
    winreg.HKEY_CURRENT_USER,
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.py",
    0, winreg.KEY_ALL_ACCESS
)
winreg.DeleteKey(parent, "UserChoice")
winreg.CloseKey(parent)
```

After deletion, Windows falls back to system-level association.

### Method B: Manual (user action)
Right-click `.py` file → Open with → Choose another app → Python → "Always use this app".

### Method C: Reset via Settings
Settings → Apps → Default Apps → "Choose default apps by file type" → find `.py` → set to Python.

## Verification
```bash
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.py\UserChoice" 2>&1
```
Should return: `ERROR: The system was unable to find the specified registry key or value.`

Then double-click the file — should work normally.

## Root Cause #2: Mark of the Web (Zone.Identifier)

### Symptom
Same as above — double-click flashes cmd, but script works from terminal. UserChoice is clean, association is correct. But the `.py` file was downloaded from the internet (ChatGPT, browser, etc.).

### Diagnosis
```python
import os
zone_path = r"path\to\script.py:Zone.Identifier"
try:
    with open(zone_path, 'r') as f:
        print(f.read())
except FileNotFoundError:
    print("Clean")
```

If it prints `[ZoneTransfer]` with `ZoneId=3` → file is blocked by SmartScreen.

Zone IDs: `0`=local, `1`=intranet, `2`=trusted, `3`=internet, `4`=untrusted.

### Fix
```python
import os, subprocess

# Method 1: Remove ADS directly
os.remove(r"path\to\script.py:Zone.Identifier")

# Method 2: PowerShell Unblock-File
subprocess.run(["powershell", "-NoProfile", "-Command",
    "Unblock-File -Path 'path\\to\\script.py'"], capture_output=True)
```

### Bulk Clean
```python
import os
for root, dirs, files in os.walk(base_dir):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                os.remove(path + ":Zone.Identifier")
            except FileNotFoundError:
                pass
```

## Specific Store App: PythonSoftwareFoundation.PythonManager

This is the official Python Foundation Store app. When installed, it:
- Registers itself as the handler for `.py` files via UserChoice
- Even after uninstalling the app, the UserChoice may persist
- The Python runtime (3.14) may remain installed even after removing the manager

### Remove the Store app
```powershell
Remove-AppxPackage -Package 'PythonSoftwareFoundation.PythonManager_26.3.240.0_x64__3847v3x7pw1km'
```

Check for remaining Store stubs:
```python
appx = subprocess.run(["powershell", "-NoProfile", "-Command",
    "Get-AppxPackage -Name '*Python*' | Select Name, Version"],
    capture_output=True, text=True)
```

## Debug Logging Technique

When you can't see what happens during double-click execution, inject a logging block at the VERY TOP of the script (before imports that might fail):

```python
import sys, os
_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_run.log")
_f = open(_log, "w", encoding="utf-8")
_f.write(f"Python: {sys.version}\nExecutable: {sys.executable}\nCWD: {os.getcwd()}\n")
sys.stderr = _f  # capture all errors
```

Then check `debug_run.log` after the user double-clicks.

## Combined Pattern: Three Root Causes

When a Python script is downloaded from ChatGPT/Web and the system has a Store Python app:
1. **Store app hijacks** the `.py` association → wrong handler  
2. **Zone.Identifier blocks** execution even after fixing association  
3. **cp1252 encoding crash** — even after fixing #1 and #2, Vietnamese text in print() crashes silently

All three must be fixed. If any remains, double-click fails silently.

## Root Cause #3: cp1252 UnicodeEncodeError (Vietnamese in print)

### Symptom
After fixing Store app hijack and Zone.Identifier, double-click still flashes cmd. Add debug logging (see Debug Logging Technique above) — the log shows:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7'
```

### Why
When Python runs in a cmd.exe context (double-click from Explorer), `sys.stdout` defaults to the console's code page — `cp1252` on Western Windows. cp1252 cannot encode Vietnamese characters like `ệ`, `ạ`, `ố`, etc. Any `print()` containing these characters crashes immediately.

When run from git-bash or VS Code terminal, stdout is UTF-8 → no crash. This is why "chạy từ terminal được, double-click không được."

### Permanent Fix: System-wide PYTHONUTF8=1

**Do NOT modify scripts.** Set the environment variable once:

```powershell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

Then broadcast to running processes:
```python
import ctypes
ctypes.windll.user32.SendMessageTimeoutW(
    0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None
)
```

This tells Python (3.7+) to use UTF-8 for all text I/O regardless of console code page. Works for ALL Python versions, ALL scripts, no code changes needed.

### Side Effect: Garbled Vietnamese in cmd.exe

After setting PYTHONUTF8=1, Python outputs UTF-8 to stdout. But cmd.exe still uses the system code page (cp1252 or 437) to DISPLAY those bytes. Result: Vietnamese appears as garbled text like `"Nhß║Ñn Enter ─æß╗â..."`.

**Fix: cmd.exe AutoRun UTF-8**

Set cmd.exe to auto-switch to UTF-8 code page on every launch:

```bash
reg add "HKCU\Software\Microsoft\Command Processor" /v AutoRun /t REG_SZ /d "chcp 65001 >nul" /f
```

No admin required. This affects the current user only. Every new cmd.exe window (including those launched by double-clicking `.py` files) will run `chcp 65001` before executing anything.

**Combined fix:**
1. `PYTHONUTF8=1` — Python UTF-8 output ✓
2. `cmd AutoRun: chcp 65001` — cmd.exe UTF-8 display ✓

Both are per-user, no admin, revertible.

**To remove AutoRun later:**
```bash
reg delete "HKCU\Software\Microsoft\Command Processor" /v AutoRun /f
```

### In-Script Fix (only if system fix impossible)
```python
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
```

## Root Cause #4: Missing Python.File Progid (No Association At All)

### Symptom
Double-click `.py` does nothing — no cmd flash, no error. `assoc .py` returns nothing or wrong progid. `ftype Python.File` returns "File type 'Python.File' not found." From terminal, `python script.py` works fine. No UserChoice hijack, no Zone.Identifier.

### Why
The registry association is simply absent. This can happen after:
- Python installed via `pyenv` or manual unzip (no installer ran the association step)
- Windows feature update wiped user associations
- Multiple Python versions installed with conflicting installers
- Python uninstalled, then reinstalled to a different path

The progid chain `.py → Python.File → shell\open\command` simply doesn't exist.

### Diagnosis
```bash
cmd.exe /c "ftype Python.File 2>&1"
# Returns: "File type 'Python.File' not found or no open command associated with it."

reg query "HKCU\Software\Classes\.py" 2>&1
# (Default) is empty or missing

reg query "HKCU\Software\Classes\Python.File\shell\open\command" 2>&1
# ERROR: not found
```

### Fix: Create the progid via Python winreg

Find the right Python first, then create the HKCU keys:

```python
import winreg, os

# Use the user's main Python (not a venv)
python_exe = r"C:\Users\thang\AppData\Local\Python\bin\python.exe"
if not os.path.exists(python_exe):
    python_exe = r"C:\Users\thang\AppData\Local\Programs\Python\Python310\python.exe"

# Step 1: .py → Python.File
key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.py")
winreg.SetValue(key, "", winreg.REG_SZ, "Python.File")
winreg.CloseKey(key)

# Step 2: Python.File\shell\open\command
cmd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Python.File\shell\open\command")
winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'"{python_exe}" "%1" %*')
winreg.CloseKey(cmd_key)

# Step 3: DefaultIcon (optional, for Explorer display)
icon_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Python.File\DefaultIcon")
winreg.SetValue(icon_key, "", winreg.REG_SZ, f"{python_exe},0")
winreg.CloseKey(icon_key)
```

After creating keys, restart Explorer for changes to take effect:
```bash
taskkill /f /im explorer.exe && start explorer.exe
```

**Note:** `assoc` and `ftype` only read from HKLM (machine-wide, requires admin). HKCU keys work for the current user without admin. Explorer must be restarted to pick up new HKCU associations.

### Verification
```bash
reg query "HKCU\Software\Classes\Python.File\shell\open\command"
# Should show: (Default) REG_SZ "C:\Users\...\python.exe" "%1" %*
```

Then double-click the `.py` file — should open in Python.

## Workflow Principle: Fix Root Cause, Not the Script

When Sếp says a script "used to work but now doesn't":
1. **The script didn't change — the environment did.** Find what changed.
2. **Do NOT offer workarounds** (.bat files, modifying scripts) as the primary fix. Find and revert the environmental change.
3. **Restore the original conditions**, don't patch the script to survive the new broken environment.
4. Only modify the script as a last resort when the environment cannot be restored.
