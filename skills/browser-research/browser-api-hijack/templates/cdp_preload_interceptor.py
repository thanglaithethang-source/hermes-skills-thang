#!/usr/bin/env python3
"""Template: CDP Pre-load Interceptor (Phương pháp 3 — STRONGEST)

Inject interceptor TRƯỚC KHI page scripts chạy qua CDP Page.addScriptToEvaluateOnNewDocument.
Bắt TẤT CẢ API traffic: fetch, XHR, WebSocket send VÀ receive.

Cách dùng:
1. cd C:\\Users\\thang\\Downloads\\_projects\\hermes-chrome-extension
2. python -B this_script.py
3. Script sẽ: inject pre-load → reload → wait → trigger action → collect

So sánh với Phương pháp 2 (fetch_interceptor_template.py):
- Phương pháp 2: inject sau khi page đã load → chỉ bắt WS send, KHÔNG bắt WS receive
- Phương pháp 3 (this): inject trước page load → bắt CẢ WS send VÀ receive
"""
import json, time, sys, os

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)
from chrome_send import send_command

# ===== CONFIG =====
TAB_ID = None  # Điền tab ID, hoặc None để tự chọn
WAIT_AFTER_RELOAD = 12  # Đợi page load sau reload
TRIGGER_JS = None  # JS code trigger action (VD: type + send chat). None = chỉ bắt page load
WAIT_AFTER_TRIGGER = 25  # Đợi sau khi trigger
OUTPUT_FILE = "/tmp/cdp_preload_capture.json"

# ===== INTERCEPTOR JS (same as Phương pháp 2, nhưng chạy pre-load) =====
INTERCEPTOR_JS = r'''
(function() {
    window.__CAPTURE__ = {
        fetch_calls: [],
        ws_events: []
    };
    
    // === 1. INTERCEPT FETCH - capture full request + response ===
    var origFetch = window.fetch;
    window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
        var method = (init && init.method) || (input && input.method) || 'GET';
        var body = null;
        var headers = {};
        
        if (init && init.body) {
            try { body = typeof init.body === 'string' ? init.body : JSON.stringify(init.body); }
            catch(e) { body = String(init.body); }
        }
        if (init && init.headers) {
            if (init.headers instanceof Headers) {
                init.headers.forEach(function(v, k) { headers[k] = v; });
            } else if (typeof init.headers === 'object') {
                for (var k in init.headers) { headers[k] = init.headers[k]; }
            }
        }
        if (input instanceof Request && input.headers) {
            input.headers.forEach(function(v, k) { headers[k] = v; });
        }
        
        var entry = {
            type: 'fetch', method: method, url: url,
            body: body, headers: headers, timestamp: Date.now()
        };
        window.__CAPTURE__.fetch_calls.push(entry);
        
        return origFetch.apply(this, arguments).then(function(resp) {
            entry.status = resp.status;
            entry.respHeaders = {};
            resp.headers.forEach(function(v, k) { entry.respHeaders[k] = v; });
            try {
                var clone = resp.clone();
                clone.text().then(function(text) { entry.response = text; }).catch(function(e) {});
            } catch(e) {}
            return resp;
        });
    };
    
    // === 2. INTERCEPT WebSocket - send AND receive ===
    var OrigWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        var ws = protocols ? new OrigWebSocket(url, protocols) : new OrigWebSocket(url);
        
        var origSend = ws.send.bind(ws);
        ws.send = function(data) {
            window.__CAPTURE__.ws_events.push({
                type: 'ws_send', url: url,
                data: typeof data === 'string' ? data : '[binary]',
                timestamp: Date.now()
            });
            return origSend(data);
        };
        
        var origAddListener = ws.addEventListener.bind(ws);
        ws.addEventListener = function(type, listener, options) {
            if (type === 'message') {
                var wrappedListener = function(event) {
                    window.__CAPTURE__.ws_events.push({
                        type: 'ws_recv', url: url,
                        data: event.data ? String(event.data) : null,
                        timestamp: Date.now()
                    });
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
                        window.__CAPTURE__.ws_events.push({
                            type: 'ws_recv', url: url,
                            data: event.data ? String(event.data) : null,
                            timestamp: Date.now()
                        });
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
    
    console.log('[INTERCEPTOR] pre-load interceptor installed');
})();
'''

def get_tab_id():
    global TAB_ID
    if TAB_ID:
        return TAB_ID
    r = send_command({'type': 'list_tabs'})
    for t in r.get('tabs', []):
        print(f"  [{t['id']}] {t['title'][:60]}")
    TAB_ID = int(input("Tab ID: ").strip())
    return TAB_ID

def main():
    tab_id = get_tab_id()
    
    # 1. Inject interceptor pre-load
    print("[1] Injecting pre-load interceptor via CDP...")
    r = send_command({
        'type': 'cdp_command',
        'method': 'Page.addScriptToEvaluateOnNewDocument',
        'params': {'source': INTERCEPTOR_JS},
        'tabId': tab_id
    })
    print(f"    -> {json.dumps(r.get('result', r), indent=2)[:200]}")
    
    # 2. Reload page
    print("[2] Reloading page...")
    send_command({
        'type': 'cdp_command',
        'method': 'Page.reload',
        'params': {},
        'tabId': tab_id
    })
    
    print(f"    Waiting {WAIT_AFTER_RELOAD}s for page load...")
    time.sleep(WAIT_AFTER_RELOAD)
    
    # Verify interceptor
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'JSON.stringify({capture: typeof window.__CAPTURE__, fetchCount: window.__CAPTURE__ ? window.__CAPTURE__.fetch_calls.length : 0, wsCount: window.__CAPTURE__ ? window.__CAPTURE__.ws_events.length : 0})',
            'returnByValue': True
        },
        'tabId': tab_id
    })
    val = r.get('result', {}).get('result', {}).get('value', '') if isinstance(r.get('result'), dict) else ''
    print(f"    Interceptor: {val}")
    
    # 3. Trigger action (if configured)
    if TRIGGER_JS:
        print(f"[3] Triggering: {TRIGGER_JS[:80]}")
        send_command({'type': 'execute_js', 'tabId': tab_id, 'code': TRIGGER_JS})
        print(f"    Waiting {WAIT_AFTER_TRIGGER}s...")
        time.sleep(WAIT_AFTER_TRIGGER)
    else:
        print("[3] No trigger configured, collecting page-load traffic only")
    
    # 4. Collect captured data
    print("[4] Collecting captured data...")
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'JSON.stringify(window.__CAPTURE__ || {fetch_calls:[], ws_events:[]})',
            'returnByValue': True
        },
        'tabId': tab_id
    })
    val = r.get('result', {}).get('result', {}).get('value', '') if isinstance(r.get('result'), dict) else ''
    
    try:
        captured = json.loads(val)
    except:
        captured = {'fetch_calls': [], 'ws_events': [], 'parse_error': str(val)[:500]}
    
    fetch_calls = captured.get('fetch_calls', [])
    ws_events = captured.get('ws_events', [])
    
    print(f"\n    Fetch calls: {len(fetch_calls)}")
    print(f"    WebSocket events: {len(ws_events)}")
    ws_sends = [e for e in ws_events if e.get('type') == 'ws_send']
    ws_recvs = [e for e in ws_events if e.get('type') == 'ws_recv']
    print(f"    WS sends: {len(ws_sends)}, WS receives: {len(ws_recvs)}")
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(captured, f, indent=2, ensure_ascii=False)
    print(f"    Saved to {OUTPUT_FILE}")
    
    # 5. Display summary
    print("\n" + "=" * 80)
    print("FETCH CALLS (API only):")
    for i, call in enumerate(fetch_calls):
        url = call.get('url', '')
        if any(x in url for x in ['/api/', '/backend-api/', '/v1/', '/v2/']):
            method = call.get('method', '?')
            status = call.get('status', '?')
            short = url[:100] + '...' if len(url) > 100 else url
            print(f"  [{i+1}] {method} [{status}] {short}")
    
    print(f"\nWEBSOCKET EVENTS ({len(ws_events)} total):")
    for i, evt in enumerate(ws_events):
        etype = evt.get('type', '?')
        data = evt.get('data', '')
        preview = data[:100] + '...' if len(data) > 100 else data
        print(f"  [{i+1}] {etype}: {preview}")

if __name__ == '__main__':
    main()
