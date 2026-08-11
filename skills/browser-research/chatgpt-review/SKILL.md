---
name: chatgpt-review
description: "Gửi code/task cho ChatGPT review qua CDP — type vào input, đợi response, đọc từ DOM. Không cần gateway API, không cần WS parse. Đơn giản, nhanh, hoạt động thực tế."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [chatgpt, code-review, cdp, chrome, automation]
    related_skills: [browser-api-hijack, chrome-cdp-control, hermes-chrome-bridge]
---

# ChatGPT Review — Gửi task review qua CDP

Dùng ChatGPT như một tool review: gửi code/task → ChatGPT xử lý → đọc response. Không build gateway API phức tạp, không parse WS. Đọc response trực tiếp từ DOM.

## Kiến trúc

```
Hermes Agent → TCP:19979 → Bridge Server → WS:19978 → Chrome Extension → CDP
                                                                      ↓
                                              Type message vào #prompt-textarea
                                                                      ↓
                                              ChatGPT xử lý (browser tự xử lý anti-bot)
                                                                      ↓
                                              Response render vào DOM
                                                                      ↓
                                              Đọc [data-message-author-role="assistant"]
```

## Prerequisites

1. Chrome mở ChatGPT tab (đã login)
2. Bridge server chạy (port 19978/19979)
3. Hermes Bridge extension loaded

```bash
# Khởi động bridge server
cd "$HOME/Downloads/_projects/hermes-chrome-extension"
PYTHONDONTWRITEBYTECODE=1 python -B hermes_bridge_server.py &

# Verify
python -B chrome_send.py ping
python -B chrome_send.py list_tabs  # phải thấy chatgpt.com tab
```

## Quick Start

```python
from chatgpt_review import ChatGPTReviewer

reviewer = ChatGPTReviewer()
result = reviewer.review("Review this code for bugs:\n\ndef foo(x):\n    return x/0")
print(result)
```

## Flow 6 bước

### Bước 1: Tìm ChatGPT tab

```python
def find_chatgpt_tab():
    r = send_command({'type': 'list_tabs'})
    tabs = r.get('tabs', [])
    chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '').lower()]
    if chatgpt_tabs:
        return chatgpt_tabs[0]['id']
    return None
```

### Bước 2: Type message vào ChatGPT

ChatGPT dùng ProseMirror contenteditable editor (`#prompt-textarea`). KHÔNG dùng `chrome_send.py type` — không hoạt động với ProseMirror.

Dùng `document.execCommand('insertText')` — ProseMirror compatible:

```python
import json

def type_message(tab_id, message):
    # Escape message safely via JSON.stringify
    escaped = json.dumps(message)
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
    """ % escaped
    r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': js})
    return r.get('result', {}).get('value', '')
```

### Bước 3: Gửi message (Enter)

```python
def press_enter(tab_id):
    js = """
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
    } else {
        'no_input';
    }
    """
    r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': js})
    return r.get('result', {}).get('value', '')
```

### Bước 4: Đợi response

Poll DOM cho đến khi assistant message xuất hiện và ổn định:

```python
import time

def wait_for_response(tab_id, timeout=60, poll_interval=3, stable_checks=3):
    start = time.time()
    last_text = ""
    stable_count = 0

    while time.time() - start < timeout:
        time.sleep(poll_interval)
        text = read_response(tab_id)
        if text and text == last_text:
            stable_count += 1
            if stable_count >= stable_checks:
                break
        else:
            stable_count = 0
        last_text = text
    return last_text
```

### Bước 5: Đọc response từ DOM

**Phát hiện quan trọng:** Đọc response từ DOM đơn giản + chính xác hơn parse WS messages. ChatGPT render assistant response vào `[data-message-author-role="assistant"]`:

```python
def read_response(tab_id, max_chars=5000):
    js = """
    var msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
    if (msgs.length === 0) {
        JSON.stringify({source: 'none', count: 0, text: ''});
    } else {
        var last = msgs[msgs.length - 1];
        JSON.stringify({source: 'assistant', count: msgs.length, text: last.textContent.substring(0, %d)});
    }
    """ % max_chars
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {'expression': js, 'returnByValue': True},
        'tabId': tab_id
    })
    result = r.get('result', {})
    inner = result.get('result', {}) if isinstance(result, dict) else {}
    val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
    try:
        data = json.loads(val)
        return data.get('text', '')
    except:
        return ''
```

### Bước 6: Trả kết quả

Response text đã sẵn sàng. Trả về cho Sếp hoặc truyền cho agent.

## Class hoàn chỉnh

Xem template: `templates/chatgpt_review.py` — class `ChatGPTReviewer` hoàn chỉnh, sẵn sàng import.

## Tốc độ

- Type + Enter: ~1s
- ChatGPT response: ~15-30s (tùy độ phức tạp)
- Poll + detect done: ~9s (3 checks × 3s)
- **Tổng: ~25-40s/request**

## Giới hạn

- ~80 msg/3h (gói ChatGPT Plus)
- 1 request/lúc (1 tab = 1 conversation)
- Chrome phải mở, bridge phải chạy
- Conversation accumulation: mỗi request type vào cùng conversation đang mở → chat dài dần → context window đầy → response suy giảm. Cần "New Chat" định kỳ.

## Khi nào dùng

- Code review (Python, JS, etc.)
- Task review (kiểm tra logic, security, best practices)
- Hỏi ý kiến chuyên gia (khi cần góc nhìn thứ 2)
- Fallback khi api.ai-box.vn chậm/lỗi

## Pitfalls

### KHÔNG dùng `chrome_send.py type` với ProseMirror
ChatGPT dùng ProseMirror contenteditable editor. `type` command không hoạt động.
**Fix:** Dùng `document.execCommand('insertText')` qua `execute_js`.

### KHÔNG dùng `innerHTML = '<p>...</p>'` với code có dấu `{`
JS string escaping bị lỗi khi code chứa `{`, `}`, backticks, backslash.
**Fix:** Dùng `json.dumps(message)` để escape an toàn, rồi pass vào `document.execCommand('insertText', false, <escaped>)`.

### KHÔNG cần WS interceptor
WS interceptor (Phương pháp 3 trong browser-api-hijack) phức tạp, truncate ở 8000 chars, parser miss delta patches. Đọc từ DOM đơn giản + chính xác hơn.
**Chỉ dùng WS interceptor khi:** Cần streaming token real-time (không đợi response xong).

### `execute_js` không await được async
`execute_js` (qua `Runtime.evaluate` không có `awaitPromise`) không await được async function.
**Fix:** Dùng `cdp_command` với `Runtime.evaluate` + `awaitPromise: true` + `returnByValue: true` khi cần gọi `fetch()` hoặc async function.

### Bridge server TCP không ổn định
TCP connection có thể disconnect với `WinError 64`. Mỗi command nên mở connection mới, gửi, đóng — không giữ persistent connection.
**Fix:** Dùng pattern: `sock.connect()` → `sock.sendall()` → `sock.recv()` → `sock.close()` cho mỗi command.

### Conversation accumulation
Mỗi request type vào cùng conversation đang mở. Chat càng dài → context window đầy → response suy giảm.
**Fix:** Định kỳ tạo "New Chat" (click nút "New chat" hoặc navigate `chatgpt.com`).

### Response text mất formatting
`textContent` chỉ trả plain text, mất markdown formatting (bold, code blocks, lists).
**Fix:** Nếu cần markdown, dùng `innerText` thay `textContent`, hoặc parse DOM structure để reconstruct markdown. Cho code review, plain text thường đủ.

## File locations

```
C:\Users\thang\Downloads\_projects\hermes-chrome-extension\
├── hermes_bridge_server.py   # Bridge server
├── chrome_send.py             # Python client (send_command)
└── background.js              # Extension service worker

Skill templates:
C:\Users\thang\AppData\Local\hermes\skills\browser-research\chatgpt-review\
└── templates\chatgpt_review.py  # ChatGPTReviewer class
```
