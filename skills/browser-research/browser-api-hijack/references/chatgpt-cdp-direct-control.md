# ChatGPT CDP Direct Control — Review/Chat Workflow

Gửi task/code review tới ChatGPT qua CDP + bridge, đọc response từ DOM.
Không cần gateway API phức tạp — chỉ cần type/enter + DOM read.

## Prerequisites

- Bridge server chạy (WS:19978, TCP:19979)
- Chrome extension Hermes Bridge đã cài
- ChatGPT tab mở trong Chrome
- **KHÔNG dùng computer_use** — mọi thao tác qua `send_command()` (terminal/code)

## Quick Test (15s) — Gửi 1 msg + đọc response

Pattern nhanh nhất để giao tiếp với ChatGPT. Không cần WS interceptor, không cần reload.

```python
import json, time, sys, os
PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)
from chrome_send import send_command

# 1. Tìm ChatGPT tab
r = send_command({'type': 'list_tabs'})
tab_id = [t for t in r['tabs'] if 'chatgpt' in t.get('url','').lower()][0]['id']

# 2. Type message (ProseMirror — dùng execCommand)
msg = "What is 2+2? Answer in one word."
js = """
var el = document.querySelector('#prompt-textarea');
if (el) {
    el.focus(); el.innerHTML = '';
    document.execCommand('selectAll');
    document.execCommand('insertText', false, %s);
    'typed_ok';
} else { 'no_input'; }
""" % json.dumps(msg)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': js})

# 3. Send Enter
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': """
    var el = document.querySelector('#prompt-textarea');
    el.focus();
    ['keydown','keypress','keyup'].forEach(function(n) {
        el.dispatchEvent(new KeyboardEvent(n, {
            key:'Enter',code:'Enter',keyCode:13,which:13,
            bubbles:true,cancelable:true
        }));
    });
"""})

# 4. Wait + read response from DOM
time.sleep(25)
r = send_command({'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {'expression': '''
        var msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
        JSON.stringify(msgs.length > 0
            ? {source:'assistant', count:msgs.length, text:msgs[msgs.length-1].textContent.substring(0,5000)}
            : {source:'none', count:0, text:''})
    ''', 'returnByValue': True},
    'tabId': tab_id})
data = json.loads(r['result']['result']['value'])
print(data['text'])  # Response text
```

**Đã test 2026-07-29:** Gửi "What is 2+2?" → nhận "Four." trong 25s. 28 WS events + 29 fetch calls captured.

## Full Workflow (cần WS interceptor cho stream detection)

### 1. Tìm ChatGPT tab

```python
r = send_command({'type': 'list_tabs'})
tabs = r.get('tabs', [])
chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '').lower()]
tab_id = chatgpt_tabs[0]['id']
```

### 2. Inject WS interceptor (cần cho stream detection)

```python
WS_INTERCEPTOR_JS = r'''
(function() {
    window.__WS_RESPONSE__ = [];
    window.__WS_MSG_ID__ = 0;
    var OrigWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        var ws = protocols ? new OrigWebSocket(url, protocols) : new OrigWebSocket(url);
        var origAddListener = ws.addEventListener.bind(ws);
        ws.addEventListener = function(type, listener, options) {
            if (type === 'message') {
                var wrappedListener = function(event) {
                    if (event.data) {
                        window.__WS_RESPONSE__.push({
                            id: window.__WS_MSG_ID__,
                            data: String(event.data).substring(0, 8000),
                            ts: Date.now()
                        });
                    }
                    return listener.apply(this, arguments);
                };
                return origAddListener(type, wrappedListener, options);
            }
            return origAddListener(type, listener, options);
        };
        var origOnMessage = Object.getOwnPropertyDescriptor(OrigWebSocket.prototype, 'onmessage');
        if (origOnMessage && origOnMessage.set) {
            Object.defineProperty(ws, 'onmessage', {
                get: origOnMessage.get.bind(ws),
                set: function(listener) {
                    var wrappedListener = function(event) {
                        if (event.data) {
                            window.__WS_RESPONSE__.push({
                                id: window.__WS_MSG_ID__,
                                data: String(event.data).substring(0, 8000),
                                ts: Date.now()
                            });
                        }
                        return listener.apply(this, arguments);
                    };
                    return origOnMessage.set.call(ws, wrappedListener);
                },
                configurable: true
            });
        }
        return ws;
    };
    window.WebSocket.prototype = OrigWebSocket.prototype;
    window.WebSocket.CONNECTING = OrigWebSocket.CONNECTING;
    window.WebSocket.OPEN = OrigWebSocket.OPEN;
    window.WebSocket.CLOSING = OrigWebSocket.CLOSING;
    window.WebSocket.CLOSED = OrigWebSocket.CLOSED;
})();
'''

send_command({
    'type': 'cdp_command',
    'method': 'Page.addScriptToEvaluateOnNewDocument',
    'params': {'source': WS_INTERCEPTOR_JS},
    'tabId': tab_id
})
send_command({
    'type': 'cdp_command',
    'method': 'Page.reload',
    'params': {},
    'tabId': tab_id
})
time.sleep(12)  # Wait for page load
```

### 3. Type message + send

```python
# Clear previous responses
send_command({
    'type': 'execute_js', 'tabId': tab_id,
    'code': 'window.__WS_MSG_ID__ = (window.__WS_MSG_ID__ || 0) + 1; window.__WS_RESPONSE__ = [];'
})

# Type message using execCommand (ProseMirror-compatible, no escaping issues)
js = """
var el = document.querySelector('#prompt-textarea');
if (el) {
    el.focus();
    el.innerHTML = '';
    document.execCommand('selectAll');
    document.execCommand('insertText', false, %s);
    'typed_ok';
} else {
    'no_input_found';
}
""" % json.dumps(review_prompt)
send_command({'type': 'execute_js', 'tabId': tab_id, 'code': js})
time.sleep(1)

# Press Enter
send_command({
    'type': 'execute_js', 'tabId': tab_id,
    'code': """
    var el = document.querySelector('#prompt-textarea');
    if (el) {
        el.focus();
        ['keydown','keypress','keyup'].forEach(function(n) {
            el.dispatchEvent(new KeyboardEvent(n, {
                key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                bubbles: true, cancelable: true
            }));
        });
        'enter_sent';
    }
    """
})
```

### 4. Poll for completion + read response from DOM

```python
# Poll WS message count for stream completion
start = time.time()
last_count = 0
stable_count = 0

while time.time() - start < 60:
    time.sleep(3)
    r = send_command({
        'type': 'cdp_command', 'method': 'Runtime.evaluate',
        'params': {
            'expression': 'JSON.stringify({count: (window.__WS_RESPONSE__||[]).length})',
            'returnByValue': True
        },
        'tabId': tab_id
    })
    data = json.loads(r['result']['result']['value'])
    ws_count = data.get('count', 0)
    
    if ws_count == last_count and ws_count > 0:
        stable_count += 1
        if stable_count >= 3:  # 9s stable = done
            break
    else:
        stable_count = 0
    last_count = ws_count

# Read response from DOM (NOT from WS parsing)
r = send_command({
    'type': 'cdp_command', 'method': 'Runtime.evaluate',
    'params': {
        'expression': '''
        var msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
        if (msgs.length > 0) {
            JSON.stringify({source: 'assistant', count: msgs.length, text: msgs[msgs.length-1].textContent.substring(0, 5000)});
        } else {
            JSON.stringify({source: 'none', count: 0, text: ''});
        }
        ''',
        'returnByValue': True
    },
    'tabId': tab_id
})
data = json.loads(r['result']['result']['value'])
response_text = data['text']
```

## Performance (test 2026-07-24)

- Total time: ~30s from send to response
- WS messages captured: 107
- Response via DOM: 2670 chars (full)
- Response via WS parsing: 25 chars (97% lost to truncation + dedup issues)
- Verdict: DOM reading >> WS parsing for full response text

## When to use this vs gateway

| Scenario | Use |
|---|---|
| Need full response text after ChatGPT finishes | This workflow (DOM read) |
| Need streaming tokens real-time | WS delta patch parsing |
| Need OpenAI-compatible API endpoint for AGI | Gateway (templates/chatgpt_gateway.py) |
| Quick one-off review/chat | Quick Test pattern above — simplest, fastest |

## Pitfalls

1. **Bridge TCP instability on Windows** — `WinError 64` (network name no longer available) occurs intermittently. Each `send_command` call opens a fresh TCP connection, so transient errors don't kill the workflow. If a call fails, just retry.

2. **WS interceptor truncates at 8000 chars** — `String(event.data).substring(0, 8000)` in interceptor. Long WS messages lose tail. This is why DOM reading is more reliable than WS parsing for full response.

3. **`document.execCommand` deprecated but works** — ProseMirror editors don't respond to `innerHTML` reliably. `execCommand('insertText')` is deprecated in spec but still works in Chrome 150 and is the most reliable way to type into contenteditable.

4. **Enter key must dispatch 3 events** — `keydown`, `keypress`, `keyup` all needed. Single `keypress` alone doesn't trigger ChatGPT's send handler.

5. **KHÔNG dùng computer_use** — Sếp cấm. Mọi thao tác qua `send_command()` (terminal/code). Xem pitfall trong SKILL.md chính.
