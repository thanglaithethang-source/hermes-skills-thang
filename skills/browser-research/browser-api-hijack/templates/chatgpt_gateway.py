#!/usr/bin/env python3
"""
ChatGPT Gateway — OpenAI-compatible API proxy qua ChatGPT web.

Expose: POST /v1/chat/completions (OpenAI format)
Internal: CDP type/enter + WS intercept → ChatGPT tab

Usage:
  python chatgpt_gateway.py --port 5678

Test:
  curl http://localhost:5678/v1/chat/completions \\
    -H "Content-Type: application/json" \\
    -d '{"model":"gpt-5-6-thinking","messages":[{"role":"user","content":"What is 2+2?"}]}'

Requirements:
  - Chrome đang mở ChatGPT tab
  - Bridge server đang chạy (hermes_bridge_server.py)
  - fastapi + uvicorn installed

Flow:
  1. Inject WS interceptor qua Page.addScriptToEvaluateOnNewDocument (1 lần)
  2. Reload page (1 lần)
  3. Mỗi request: clear __WS_RESPONSE__ → type+enter → poll → collect → parse
  4. Return OpenAI-compatible JSON

Limitations:
  - ~80 msg/3h (gói Plus)
  - ~25-30s/message
  - Chrome phải mở ChatGPT tab
  - Thread-safe (lock serialize requests)
"""
import json
import os
import sys
import time
import uuid
import threading
import argparse

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)

from chrome_send import send_command

# ============================================================
# WS Interceptor — inject TRƯỚC khi page scripts chạy
# ============================================================
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

# ============================================================
# ChatGPT Gateway Core
# ============================================================
class ChatGPTGateway:
    def __init__(self):
        self.tab_id = None
        self.injected = False
        self.lock = threading.Lock()
        self.request_count = 0
        self.last_error = None

    def find_tab(self):
        r = send_command({'type': 'list_tabs'})
        tabs = r.get('tabs', [])
        chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '')]
        if chatgpt_tabs:
            self.tab_id = chatgpt_tabs[0]['id']
            return True
        return False

    def ensure_injected(self):
        if self.injected:
            return True
        if not self.tab_id:
            if not self.find_tab():
                return False
        send_command({
            'type': 'cdp_command',
            'method': 'Page.addScriptToEvaluateOnNewDocument',
            'params': {'source': WS_INTERCEPTOR_JS},
            'tabId': self.tab_id
        })
        send_command({
            'type': 'cdp_command',
            'method': 'Page.reload',
            'params': {},
            'tabId': self.tab_id
        })
        time.sleep(12)
        self.injected = True
        return True

    def type_and_send(self, message):
        send_command({
            'type': 'execute_js',
            'tabId': self.tab_id,
            'code': f'''
            window.__WS_MSG_ID__ = (window.__WS_MSG_ID__ || 0) + 1;
            window.__WS_RESPONSE__ = [];
            '''
        })
        send_command({
            'type': 'execute_js',
            'tabId': self.tab_id,
            'code': f'''
            var el = document.querySelector('#prompt-textarea');
            if (el) {{
                el.focus();
                el.innerHTML = '<p>{message}</p>';
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
            '''
        })
        time.sleep(0.5)
        send_command({
            'type': 'execute_js',
            'tabId': self.tab_id,
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

    def collect_response(self, timeout=60, poll_interval=3):
        start = time.time()
        response_text = ""
        ws_count = 0
        last_count = 0
        stable_count = 0
        stream_done = False

        while time.time() - start < timeout:
            time.sleep(poll_interval)
            r = send_command({
                'type': 'cdp_command',
                'method': 'Runtime.evaluate',
                'params': {
                    'expression': 'JSON.stringify({count: (window.__WS_RESPONSE__||[]).length, msgs: window.__WS_RESPONSE__||[]})',
                    'returnByValue': True
                },
                'tabId': self.tab_id
            })
            result = r.get('result', {})
            inner = result.get('result', {}) if isinstance(result, dict) else {}
            val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
            try:
                data = json.loads(val)
                ws_count = data.get('count', 0)
                msgs = data.get('msgs', [])
            except:
                msgs = []

            # Check for stream done signal
            if msgs:
                for item in msgs:
                    if isinstance(item, dict):
                        msg_raw = item.get('data', '')
                    else:
                        msg_raw = str(item)
                    try:
                        msg = json.loads(msg_raw)
                        if isinstance(msg, list):
                            for evt in msg:
                                if isinstance(evt, dict):
                                    t = evt.get('type', '')
                                    p = evt.get('payload', {})
                                    if isinstance(p, dict):
                                        ip = p.get('payload', {})
                                        if isinstance(ip, dict):
                                            enc = ip.get('encoded_item', '')
                                            if enc and ('[DONE]' in enc or '"type": "done"' in enc or '"type":"done"' in enc):
                                                stream_done = True
                                    if t == 'conversation-update' or t == 'conversation-turn-complete':
                                        stream_done = True
                    except:
                        pass
                response_text = self._parse_ws_messages(msgs)

            if stream_done:
                time.sleep(2)
                r = send_command({
                    'type': 'cdp_command',
                    'method': 'Runtime.evaluate',
                    'params': {
                        'expression': 'JSON.stringify({count: (window.__WS_RESPONSE__||[]).length, msgs: window.__WS_RESPONSE__||[]})',
                        'returnByValue': True
                    },
                    'tabId': self.tab_id
                })
                result = r.get('result', {})
                inner = result.get('result', {}) if isinstance(result, dict) else {}
                val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
                try:
                    data = json.loads(val)
                    msgs = data.get('msgs', [])
                    ws_count = data.get('count', ws_count)
                    response_text = self._parse_ws_messages(msgs)
                except:
                    pass
                break

            if ws_count == last_count and ws_count > 0:
                stable_count += 1
                if stable_count >= 4:
                    break
            else:
                stable_count = 0
            last_count = ws_count

        if msgs:
            response_text = self._parse_ws_messages(msgs)
        return response_text, ws_count

    def _parse_ws_messages(self, ws_messages):
        """Parse WS messages → response text.
        Deduplicate by stream_item_id (WS sends catchups + live = duplicates).
        Accumulate delta append patches for unique stream items.
        """
        full_text = ""
        seen_ids = set()

        for item in ws_messages:
            if isinstance(item, dict):
                msg_raw = item.get('data', '')
            else:
                msg_raw = str(item)
            try:
                msg = json.loads(msg_raw)
            except:
                continue
            if not isinstance(msg, list):
                continue

            for evt in msg:
                if not isinstance(evt, dict):
                    continue
                if evt.get('type') != 'message':
                    continue
                payload = evt.get('payload', {})
                if not isinstance(payload, dict):
                    continue
                inner_payload = payload.get('payload', {})
                if not isinstance(inner_payload, dict):
                    continue

                sid = inner_payload.get('stream_item_id')
                if sid:
                    if sid in seen_ids:
                        continue
                    seen_ids.add(sid)

                encoded = inner_payload.get('encoded_item', '')
                if not encoded or 'data: ' not in encoded:
                    continue

                for line in encoded.split('\n'):
                    if not line.startswith('data: '):
                        continue
                    d_str = line[6:].strip()
                    if d_str == '[DONE]' or not d_str:
                        continue
                    try:
                        d = json.loads(d_str)
                        if not isinstance(d, dict):
                            continue
                        if d.get('p') == '/message/content/parts/0' and d.get('o') == 'append':
                            v = d.get('v', '')
                            if isinstance(v, str):
                                full_text += v
                        if d.get('p') == '' and d.get('o') == 'patch' and isinstance(d.get('v'), list):
                            for p in d['v']:
                                if isinstance(p, dict) and p.get('p') == '/message/content/parts/0' and p.get('o') == 'append':
                                    v = p.get('v', '')
                                    if isinstance(v, str):
                                        full_text += v
                    except:
                        pass
        return full_text

    def send_chat(self, message, model="gpt-5-6-thinking"):
        with self.lock:
            self.request_count += 1
            req_id = self.request_count
            print(f"[Gateway] Request #{req_id}: '{message[:80]}'")

            if not self.ensure_injected():
                return {"error": "No ChatGPT tab found. Open ChatGPT in Chrome first."}

            self.type_and_send(message)
            response_text, ws_count = self.collect_response(timeout=45)

            print(f"[Gateway] Response #{req_id}: {response_text[:80]}... ({ws_count} WS msgs)")

            if not response_text:
                return {"error": "No response received", "ws_count": ws_count}
            return {"response": response_text, "ws_count": ws_count}


# ============================================================
# FastAPI Server (OpenAI-compatible)
# ============================================================
def create_app(gateway):
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI(title="ChatGPT Gateway", version="1.0.0")

    @app.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [
                {"id": "gpt-5-6-thinking", "object": "model", "owned_by": "chatgpt-plus"},
                {"id": "gpt-5-3", "object": "model", "owned_by": "chatgpt-plus"},
                {"id": "gpt-5-5", "object": "model", "owned_by": "chatgpt-plus"},
            ]
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        body = await request.json()
        messages = body.get("messages", [])
        model = body.get("model", "gpt-5-6-thinking")

        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"[System: {content}]")
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"[Previous response: {content}]")
        prompt = "\n\n".join(prompt_parts)

        result = gateway.send_chat(prompt, model=model)

        if "error" in result:
            return JSONResponse(status_code=429 if "limit" in result.get("error","").lower() else 500,
                              content={"error": {"message": result["error"], "type": "gateway_error"}})

        response_text = result["response"]
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": len(prompt) // 4,
                "completion_tokens": len(response_text) // 4,
                "total_tokens": (len(prompt) + len(response_text)) // 4,
            }
        }

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "tab_id": gateway.tab_id,
            "injected": gateway.injected,
            "requests": gateway.request_count,
            "last_error": gateway.last_error,
        }

    @app.get("/")
    async def root():
        return {
            "service": "ChatGPT Gateway",
            "version": "1.0.0",
            "endpoints": ["/v1/chat/completions", "/v1/models", "/health"],
        }

    return app


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Gateway API")
    parser.add_argument("--port", type=int, default=5678)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"ChatGPT Gateway — OpenAI-compatible API proxy")
    print(f"{'='*60}")
    print(f"Endpoint: http://{args.host}:{args.port}/v1/chat/completions")
    print(f"{'='*60}\n")

    gateway = ChatGPTGateway()
    if not gateway.find_tab():
        print("ERROR: No ChatGPT tab found. Open ChatGPT in Chrome first.")
        sys.exit(1)
    print(f"ChatGPT tab found: ID={gateway.tab_id}")

    app = create_app(gateway)
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
