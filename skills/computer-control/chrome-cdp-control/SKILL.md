---
name: chrome-cdp-control
description: Kiểm soát Chrome toàn diện — Extension Bridge (session Sếp) + Playwright CDP (bắt API, replay). 2 mode trong 1 class. Đã audit + fix 3 CRITICAL bugs.
version: 3.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [chrome, cdp, playwright, extension, api-reverse-engineering]
---

# Chrome Control — Extension + CDP

**`ChromeController` trong `hermes_chrome.py`** — 1 class, 2 mode.

| Mode | Dùng khi | Yêu cầu |
|------|----------|---------|
| Extension Bridge | Cần session/login Sếp | Bridge server + extension loaded |
| Playwright CDP | Cần bắt API nặng, replay | Chrome với `--remote-debugging-port=9222` |

## Quick Start

```python
from hermes_chrome import ChromeController
ctrl = ChromeController()

# Extension mode — session Sếp
ctrl.ping()
tabs = ctrl.list_tabs()
ctrl.navigate('https://google.com')
ctrl.type_text('search', 'input[name="q"]')
cookies = ctrl.get_cookies(tab_id)  # → {name: value}

# Network monitoring
api_calls = ctrl.capture_api_requests(tab_id, 
    lambda: ctrl.click('button.submit'), duration=3)

# Replay API với cookies Sếp
import requests
resp = requests.post(api_url, cookies=cookies, data=post_data)
```

## Khởi động

**Extension mode:** `python hermes_bridge_server.py`

**CDP mode:** `start_chrome_cdp.bat`

## Audit v3.0 fixes

3 CRITICAL bugs đã fix sau 3-subagent audit:
1. **Frame DoS** — giới hạn 16MB, chống OOM kill bridge server
2. **Selector Injection (XSS)** — dùng `JSON.stringify` thay escape thủ công
3. **get_cookies()** — sửa double `.get('result')`, luôn trả empty

## Project files

| File | Vai trò |
|------|---------|
| `hermes_chrome.py` | Controller chính |
| `hermes_bridge_server.py` | Bridge server (WS:19978 + TCP:19979) |
| `background.js` | Chrome extension v3 (đã fix XSS) |
| `chrome_send.py` | TCP client |
| `hermes_chrome_controller.py` | Playwright CDP controller |
| `start_chrome_cdp.bat` | Launcher Chrome CDP |
