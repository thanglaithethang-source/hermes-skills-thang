# Hermes Chrome Bridge — Code Audit Findings (2026-07-21)

3 subagents (Kimi K2.7, Codex, Qwen/GLM) analyzed entire codebase. 20 issues found.

## Critical/High — Fixed

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | WS fragmentation not handled → large response data loss | `hermes_bridge_server.py` read_frame | ✅ Added continuation frame reassembly |
| 2 | Network.enable double-call → deadlock 30s | `background.js` domains list | ✅ Removed Network.enable from auto-enable list |
| 3 | asyncio.Lock() deadlock → bridge server hang | `hermes_bridge_server.py` | ✅ Removed lock entirely (v3) |
| 4 | __pycache__ breaks extension loading | project directory | ✅ PYTHONDONTWRITEBYTECODE=1 + -B flag |

## Critical/High — Not Yet Fixed

| # | Issue | File |
|---|-------|------|
| 5 | CSS selector injection → arbitrary JS execution | `background.js` handleClick/Type/DOM |
| 6 | TCP response reader breaks on large/fragmented payloads | `chrome_send.py` recv loop |
| 7 | 2nd extension connection leaks old writer | `hermes_bridge_server.py` |

## Medium — Not Yet Fixed

| # | Issue | File |
|---|-------|------|
| 8 | pending memory leak on TCP disconnect | `hermes_bridge_server.py` |
| 9 | No timeout on WS read → zombie hang | `hermes_bridge_server.py` |
| 10 | set_result on already-done future | `hermes_bridge_server.py` |
| 11 | Race on debugger "already attached" recovery | `background.js` |
| 12 | MV3 worker restart loses activeDebuggerTabs | `background.js` |
| 13 | WS disconnect mid-request → response queued too late | `background.js` |
| 14 | windowsVirtualKeyCode wrong for special keys | `background.js` |

## Verification status (2026-07-21)

- ✅ ping/pong roundtrip
- ✅ list_tabs, get_current_tab
- ✅ execute_js, cdp_command
- ✅ network_start / network_stop (network monitoring)
- ✅ WebSocket fragmentation reassembly (unit tested)
- ❌ Chrome --remote-debugging-port=9222 (Chrome 150 blocks on Windows)
