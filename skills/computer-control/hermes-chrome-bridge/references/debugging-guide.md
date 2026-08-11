# Bridge Server Debugging Guide

## Bridge Server Evolution

| Version | Approach | Result |
|---------|----------|--------|
| v1 | `websockets` library | **Broken** — `permessage-deflate` compression incompatible with Chrome |
| v2 | Raw WebSocket + `asyncio.Lock()` | **Broken** — Lock gây deadlock, ping/pong không roundtrip |
| v3 | Raw WebSocket, no lock, simplified | **Working** — ping, list_tabs, execute_js, cdp_command OK |

Key insight: **`asyncio.Lock()` gây deadlock trên Windows** khi dùng `async with` pattern với nhiều connection handler. Asyncio là single-threaded, `writer.write()` không yield nên không cần lock.

## Các lỗi đã gặp và fix

### 1. `__pycache__` blocks extension loading
```
Error: Cannot load extension with file or directory name __pycache__.
Filenames starting with "_" are reserved for use by the system.
```
**Fix**: `rm -rf __pycache__/` → `set PYTHONDONTWRITEBYTECODE=1` → `python -B`

### 2. Multiple bridge server instances (port conflict)
```
OSError: [Errno 10048] only one usage of each socket address
```
**Fix**: Kill all before start:
```bash
for pid in $(netstat -ano | grep -E "19978|19979" | awk '{print $NF}' | sort -u); do
  taskkill /F /PID $pid 2>/dev/null
done
```

### 3. Stale debugger after extension reload
```
Error: Another debugger is already attached
```
**Fix** in `background.js` `ensureDebuggerAttached`:
```javascript
try { await chrome.debugger.attach({ tabId }, '1.3'); }
catch(err) {
  if (err.message.includes('already attached')) {
    try { await chrome.debugger.detach({ tabId }); } catch(e) {}
    await chrome.debugger.attach({ tabId }, '1.3');
  } else { throw err; }
}
```

### 4. Extension service worker terminates after 30s idle
**Symptom**: Commands work then suddenly "Extension not connected"
**Fix**: Alarm keepalive wakes it every 30s. Manual wakeup: click extension icon on Chrome toolbar.

### 5. Missing requestId → TCP timeout
**Fix**: chrome_send.py auto-generates `requestId` via `str(uuid.uuid4())[:8]`

### 6. Bridge server needs `if __name__ == '__main__'` guard
Without guard, `import hermes_bridge_server` runs `asyncio.run(main())` and binds port.

### 7. `network_start` timeout — Network.enable double-enable deadlock
**Symptom**: `network_start` always times out after 30s. `cdp_command` (Runtime.evaluate), `ping`, `list_tabs` all work.
**Root cause**: `Network.enable` is called TWICE on the same tab — once in `ensureDebuggerAttached` (auto-enable domains list L85) and once in `handleNetworkStart` (L213). The second call on an already-enabled Network domain causes Chrome CDP to hang (Promise never settles).
**Fix**: Remove `'Network.enable'` from the domains array in `ensureDebuggerAttached`:
```javascript
// BEFORE (broken):
const domains = ['Page.enable', 'Runtime.enable', 'DOM.enable', 'Input.enable', 'Network.enable'];
// AFTER (fixed):
const domains = ['Page.enable', 'Runtime.enable', 'DOM.enable', 'Input.enable'];
```
**Why**: `Network.enable` should only be called from `handleNetworkStart`. Other commands don't need it. This avoids the double-enable deadlock in Chrome CDP.

## Testing without Chrome Extension

Use a simulated WebSocket client. See `references/test_ws_client.py`.

## Quick diagnostic commands

```bash
cd C:\Users\thang\Downloads\_projects\hermes-chrome-extension

# Check ports
netstat -ano | grep -E "19978|19979"

# Check extension connection
python -B chrome_send.py ping

# Check tabs
python -B chrome_send.py list_tabs

# Check CDP
python -B chrome_send.py execute_js --code "document.title"
```
