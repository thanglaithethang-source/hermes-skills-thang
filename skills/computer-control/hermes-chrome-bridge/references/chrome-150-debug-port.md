# Chrome 150 Debug Port Diagnosis (2026-07-22)

## Environment

- **Chrome**: 150.0.7871.129 (x64)
- **OS**: Windows 10 (x64)
- **Chrome path**: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **User Data**: `C:\Users\thang\AppData\Local\Google\Chrome\User Data`

## Symptoms

1. Chrome running normally (30+ `chrome.exe` processes) but `netstat` shows **nothing on port 9222**
2. Running `chrome --version` prints `"Opening in existing browser session."` — it detects an existing instance and attaches to it instead of printing the version
3. Killing all Chrome processes, deleting lock files, and restarting with `--remote-debugging-port=9222` **still fails**: Chrome process starts (PID alive) but port 9222 **never binds**

## Root Cause

Chrome 150's session management on Windows can **suppress`--remote-debugging-port`** even after a clean kill + lock-cleanup cycle. The hypothesis is:

- Chrome maintains session state beyond simple lock files (e.g., registry entries, named mutexes, or IPC state)
- When restarted with the main User Data directory, Chrome detects "session restoration" context and ignores certain CLI flags — including `--remote-debugging-port`
- This is NOT a lock-file issue (removing `lockfile`, `SingletonLock`, `SingletonSocket`, `SingletonCookie` changes nothing)
- This is NOT a stale process issue (confirmed zero `chrome.exe` before restart)

## Test Results

### Test 1: Kill + clean locks + main User Data → ❌ FAIL

```
[1/5] Kill 28 chrome.exe processes → done
[2/5] Remove lockfile, SingletonLock, SingletonSocket, SingletonCookie → done
[3/5] Start Chrome --remote-debugging-port=9222 --remote-allow-origins=* <main-User-Data>
[4/5] Wait 8s
Result: Chrome PID 19892 ALIVE, port 9222 NOT LISTENING
```

### Test 2: Kill + isolated temp User Data → ✅ PASS

```
[5/5] Kill failed instance → done
      Start Chrome --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-debug-9222
      Wait 8s
Result: Port 9222 LISTENING on 127.0.0.1:9222 (PID 10304)
       CDP endpoint http://127.0.0.1:9222/json/version responds
       Chrome 150.0.7871.129 confirmed
```

### CDP Verification

```bash
$ curl http://127.0.0.1:9222/json/version
{
   "Browser": "Chrome/150.0.7871.129",
   "Protocol-Version": "1.3",
   "V8-Version": "15.0.1240245",
   "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/<uuid>"
}
```

## Flags That Matter

| Flag | Required? | Why |
|---|---|---|
| `--remote-debugging-port=9222` | ✅ Yes | Core requirement |
| `--remote-allow-origins=*` | ✅ Yes (Chrome 140+) | Without this, CDP rejects cross-origin connections |
| `--user-data-dir=<temp>` | ✅ Yes (for Chrome 150) | Isolated profile bypasses session state that suppresses debug port |
| `--no-first-run` | Recommended | Avoids first-run wizard |
| `--disable-background-networking` | Recommended | Reduces noise, fewer subprocesses |
| `--disable-sync` | Recommended | Prevents sync prompts |
| `--disable-component-update` | Recommended | Prevents update checks |

## Key Insight

**`--user-data-dir` pointing to a fresh temp directory is the only reliable way to get Chrome 150 to honor `--remote-debugging-port` on Windows.** The main profile path (`%LOCALAPPDATA%\Google\Chrome\User Data`) carries persistent session state that overrides the flag — even after all processes are killed and lock files are cleaned.

## When To Use What

| Scenario | Approach |
|---|---|
| Need Chrome with debug port for automation | Use `--user-data-dir=%TEMP%\chrome-debug-9222` (isolated temp) |
| Need real profile (cookies, logins) with debug port | Use Extension Bridge (Method 2) — no `--remote-debugging-port` needed |
| Need real profile for interactive use | Accept no debug port; use computer_use for UI automation instead |
