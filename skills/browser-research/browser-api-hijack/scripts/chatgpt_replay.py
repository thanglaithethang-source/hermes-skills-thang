#!/usr/bin/env python3
"""
ChatGPT Replay Script — gửi chat message và nhận response qua browser context.

KHÔNG thể dùng Python requests độc lập vì Cloudflare anti-bot (Turnstile token).
Cách duy nhất hoạt động: CDP + type/enter + WS intercept.

Cách dùng:
    python chatgpt_replay.py "What is 100 divided by 7?"

Yêu cầu:
    - Bridge server đang chạy (python -B hermes_bridge_server.py)
    - Chrome extension Hermes Bridge đã cài
    - ChatGPT tab đang mở và đã login

Workflow:
    1. Page.addScriptToEvaluateOnNewDocument inject WS interceptor
    2. Page.reload → interceptor chạy trước app scripts
    3. Type message vào #prompt-textarea (ProseMirror) + Enter
    4. ChatGPT tự xử lý anti-bot tokens (browser JS generate)
    5. WS stream bị intercept → parse delta patches → response text
"""
import json, sys, os, time

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)
from chrome_send import send_command

# WS interceptor script — patch WebSocket prototype BEFORE page scripts
INTERCEPTOR_JS = r'''
(function() {
    window.__WS_RESPONSE__ = [];
    
    var OrigWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        var ws = protocols ? new OrigWebSocket(url, protocols) : new OrigWebSocket(url);
        
        var origAddListener = ws.addEventListener.bind(ws);
        ws.addEventListener = function(type, listener, options) {
            if (type === 'message') {
                var wrappedListener = function(event) {
                    if (event.data) window.__WS_RESPONSE__.push(String(event.data).substring(0, 8000));
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
                        if (event.data) window.__WS_RESPONSE__.push(String(event.data).substring(0, 8000));
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


def send_chat(tab_id, message, wait_seconds=20):
    """Send a chat message to ChatGPT and return the response text.
    
    Args:
        tab_id: Chrome tab ID with ChatGPT open
        message: Text to send
        wait_seconds: Time to wait for response (default 20)
    
    Returns:
        Response text from ChatGPT
    """
    # Step 1: Inject WS interceptor via CDP pre-load
    send_command({
        'type': 'cdp_command',
        'method': 'Page.addScriptToEvaluateOnNewDocument',
        'params': {'source': INTERCEPTOR_JS},
        'tabId': tab_id
    })
    
    # Step 2: Reload page (interceptor runs before app scripts)
    send_command({
        'type': 'cdp_command',
        'method': 'Page.reload',
        'params': {},
        'tabId': tab_id
    })
    time.sleep(12)  # Wait for page to fully load
    
    # Step 3: Type message into ProseMirror editor
    send_command({
        'type': 'execute_js',
        'tabId': tab_id,
        'code': f'''
        var el = document.querySelector('#prompt-textarea');
        if (el) {{
            el.focus();
            el.innerHTML = '<p>{message}</p>';
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
        }}
        '''
    })
    time.sleep(1)
    
    # Step 4: Press Enter (dispatch KeyboardEvent)
    send_command({
        'type': 'execute_js',
        'tabId': tab_id,
        'code': '''
        var el = document.querySelector('#prompt-textarea');
        if (el) {
            el.focus();
            ['keydown', 'keypress', 'keyup'].forEach(function(n) {
                el.dispatchEvent(new KeyboardEvent(n, {
                    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                    bubbles: true, cancelable: true
                }));
            });
        }
        '''
    })
    
    # Step 5: Wait for response
    time.sleep(wait_seconds)
    
    # Step 6: Collect WS messages
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'JSON.stringify(window.__WS_RESPONSE__ || [])',
            'returnByValue': True
        },
        'tabId': tab_id
    })
    
    result = r.get('result', {})
    inner = result.get('result', {}) if isinstance(result, dict) else {}
    val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
    
    try:
        ws_msgs = json.loads(val)
    except:
        ws_msgs = []
    
    # Step 7: Parse WS messages to extract response text
    response_text = _parse_ws_messages(ws_msgs)
    return response_text


def _parse_ws_messages(ws_msgs):
    """Parse WebSocket messages to extract ChatGPT response text.
    
    WS messages contain stream items with encoded_item fields.
    Delta patches use JSON Patch format: p (path), o (operation), v (value).
    Text is assembled from append operations on /message/content/parts/0.
    """
    response_text = ""
    
    for msg_raw in ws_msgs:
        try:
            msg = json.loads(msg_raw)
        except:
            continue
        
        if isinstance(msg, list):
            for evt in msg:
                if not isinstance(evt, dict):
                    continue
                
                payload = evt.get('payload', {})
                if isinstance(payload, dict):
                    inner_payload = payload.get('payload', {})
                    if isinstance(inner_payload, dict):
                        encoded = inner_payload.get('encoded_item', '')
                        if encoded and 'data: ' in encoded:
                            for line in encoded.split('\n'):
                                if line.startswith('data: '):
                                    d_str = line[6:].strip()
                                    if d_str == '[DONE]' or not d_str:
                                        continue
                                    try:
                                        d = json.loads(d_str)
                                        # Append operation
                                        if d.get('p') == '/message/content/parts/0' and d.get('o') == 'append':
                                            v = d.get('v', '')
                                            if isinstance(v, str):
                                                response_text += v
                                        # Patch array
                                        elif d.get('p') == '' and d.get('o') == 'patch' and isinstance(d.get('v'), list):
                                            for p in d['v']:
                                                if p.get('p') == '/message/content/parts/0' and p.get('o') == 'append':
                                                    v = p.get('v', '')
                                                    if isinstance(v, str):
                                                        response_text += v
                                        # Full message (v.message.content.parts)
                                        if 'v' in d and isinstance(d['v'], dict):
                                            mc = d['v'].get('message', {}).get('content', {})
                                            if mc.get('content_type') == 'text':
                                                parts = mc.get('parts', [])
                                                if parts and isinstance(parts[0], str):
                                                    response_text = parts[0]
                                    except:
                                        pass
                    
                    # conversation-update (final message)
                    if evt.get('type') == 'conversation-update':
                        update = payload.get('update_content', {})
                        msg_obj = update.get('message', {})
                        content = msg_obj.get('content', {})
                        if content.get('content_type') == 'text':
                            parts = content.get('parts', [])
                            if parts and isinstance(parts[0], str):
                                response_text = parts[0]
    
    return response_text


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "What is 100 divided by 7?"
    
    # Get tab ID
    r = send_command({'type': 'list_tabs'})
    tabs = r.get('tabs', [])
    chatgpt_tab = None
    for t in tabs:
        if 'chatgpt' in t.get('url', '').lower():
            chatgpt_tab = t['id']
            break
    
    if not chatgpt_tab:
        print("ERROR: No ChatGPT tab found. Open chatgpt.com in Chrome first.")
        sys.exit(1)
    
    print(f"Sending: '{message}'")
    print(f"Tab ID: {chatgpt_tab}")
    print(f"{'='*60}")
    
    response = send_chat(chatgpt_tab, message)
    
    print(f"\n{'='*60}")
    print(f"RESPONSE: {response}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
