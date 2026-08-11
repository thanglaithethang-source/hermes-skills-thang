#!/usr/bin/env python3
"""
ChatGPT Chat Replay — gửi message + đọc response qua CDP.

Cách dùng:
  from chatgpt_chat_replay import send_chat
  response = send_chat("What is 100 divided by 7?")
  print(response)

Yêu cầu:
  - Chrome đang mở ChatGPT tab
  - Bridge server đang chạy (hermes_bridge_server.py)
  - Tab ID đúng (lấy từ list_tabs)

Flow:
  1. Inject WS interceptor qua Page.addScriptToEvaluateOnNewDocument
  2. Reload page (interceptor chạy trước app scripts)
  3. Type message vào #prompt-textarea (ProseMirror)
  4. Dispatch Enter keyboard events
  5. Wait for response
  6. Collect WS messages → parse delta patches → response text

Giới hạn:
  - KHÔNG thể replay bằng Python requests (Cloudflare turnstile blocker)
  - Phải chạy qua browser context (CDP)
  - Mỗi lần gửi cần reload page (để interceptor chạy trước WS)
"""
import json
import os
import sys
import time

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)

from chrome_send import send_command

# ============================================================
# WS Interceptor — inject TRƯỚC khi page scripts chạy
# ============================================================
WS_INTERCEPTOR_JS = r'''
(function() {
    window.__WS_RESPONSE__ = [];
    
    var OrigWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        var ws = protocols ? new OrigWebSocket(url, protocols) : new OrigWebSocket(url);
        
        // Wrap addEventListener to intercept message events
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
        
        // Wrap onmessage setter
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

# ============================================================
# Type message + press Enter
# ============================================================
def type_and_send(tab_id, message):
    """Type message into ChatGPT ProseMirror input and press Enter."""
    # Type message
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
    
    # Press Enter
    send_command({
        'type': 'execute_js',
        'tabId': tab_id,
        'code': '''
        var el = document.querySelector('#prompt-textarea');
        if (el) {
            el.focus();
            ['keydown','keypress','keyup'].forEach(function(n) {
                el.dispatchEvent(new KeyboardEvent(n, {
                    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                    bubbles: true, cancelable: true
                }));
            });
        }
        '''
    })


# ============================================================
# Parse WS messages → response text
# ============================================================
def parse_ws_response(ws_messages):
    """Parse WebSocket messages to extract response text from delta patches."""
    response_text = ""
    
    for msg_raw in ws_messages:
        try:
            msg = json.loads(msg_raw)
        except:
            continue
        
        if not isinstance(msg, list):
            continue
        
        for evt in msg:
            if not isinstance(evt, dict):
                continue
            
            payload = evt.get('payload', {})
            if not isinstance(payload, dict):
                continue
            
            # Check for conversation-turn-stream with encoded_item
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
                                # Delta append
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


# ============================================================
# Main: send chat + get response
# ============================================================
def send_chat(message, tab_id=None, wait_seconds=20):
    """
    Send a chat message to ChatGPT and return the response text.
    
    Args:
        message: str — the message to send
        tab_id: int — Chrome tab ID (auto-detect if None)
        wait_seconds: int — seconds to wait for response
    
    Returns:
        str — ChatGPT response text, or empty string if failed
    """
    # Auto-detect tab if not specified
    if tab_id is None:
        r = send_command({'type': 'list_tabs'})
        tabs = r.get('tabs', [])
        chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '')]
        if not chatgpt_tabs:
            print("ERROR: No ChatGPT tab found")
            return ""
        tab_id = chatgpt_tabs[0]['id']
    
    # Step 1: Inject WS interceptor via CDP pre-load
    send_command({
        'type': 'cdp_command',
        'method': 'Page.addScriptToEvaluateOnNewDocument',
        'params': {'source': WS_INTERCEPTOR_JS},
        'tabId': tab_id
    })
    
    # Step 2: Reload page
    send_command({
        'type': 'cdp_command',
        'method': 'Page.reload',
        'params': {},
        'tabId': tab_id
    })
    time.sleep(12)  # Wait for page to fully load
    
    # Step 3: Type message + press Enter
    type_and_send(tab_id, message)
    
    # Step 4: Wait for response
    time.sleep(wait_seconds)
    
    # Step 5: Collect WS messages
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
        ws_messages = json.loads(val)
    except:
        ws_messages = []
    
    # Step 6: Parse response
    response_text = parse_ws_response(ws_messages)
    
    return response_text


# ============================================================
# Get auth token (for API calls that don't need turnstile)
# ============================================================
def get_auth_token(tab_id=None):
    """Get ChatGPT Bearer token via /api/auth/session."""
    if tab_id is None:
        r = send_command({'type': 'list_tabs'})
        tabs = r.get('tabs', [])
        chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '')]
        if not chatgpt_tabs:
            return None
        tab_id = chatgpt_tabs[0]['id']
    
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'fetch("/api/auth/session",{credentials:"include"}).then(r=>r.json()).then(d=>JSON.stringify(d))',
            'awaitPromise': True,
            'returnByValue': True
        },
        'tabId': tab_id
    })
    
    result = r.get('result', {})
    inner = result.get('result', {}) if isinstance(result, dict) else {}
    val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
    
    try:
        data = json.loads(val)
        return data.get('accessToken')
    except:
        return None


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "What is 100 divided by 7?"
    
    print(f"Sending: '{msg}'")
    print(f"{'='*60}")
    
    response = send_chat(msg)
    
    print(f"\n{'='*60}")
    if response:
        print(f"RESPONSE: {response}")
    else:
        print("No response received")
    print(f"{'='*60}")
