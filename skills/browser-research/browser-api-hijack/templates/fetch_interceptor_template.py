#!/usr/bin/env python3
"""Template: Inject fetch/XHR/WebSocket interceptor vào web app để bắt API traffic.
Dùng khi CDP Network monitoring không đủ (web app dùng WebSocket, Service Worker fetch, etc.).

Cách dùng:
1. cd C:\\Users\\thang\\Downloads\\_projects\\hermes-chrome-extension
2. python -B this_script.py
3. Script sẽ inject interceptor, trigger action, collect API log
"""
import json, time, sys, os

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)
from chrome_send import send_command

# ===== CONFIG =====
TAB_ID = None  # Điền tab ID, hoặc để None để tự chọn
TRIGGER_JS = "location.reload()"  # JS code trigger API calls
WAIT_SECONDS = 10  # Đợi bao lâu trước khi collect
OUTPUT_FILE = "/tmp/api_intercepted.json"

# ===== INTERCEPTOR JS =====
INTERCEPTOR_JS = r'''
(function() {
    window.__API_LOG__ = [];
    
    // 1. Intercept fetch
    var origFetch = window.fetch;
    window.fetch = function(input, init) {
        var url = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
        var method = (init && init.method) || 'GET';
        var body = (init && init.body) ? String(init.body).substring(0, 5000) : null;
        var entry = {type: 'fetch', method: method, url: url, body: body, timestamp: Date.now()};
        window.__API_LOG__.push(entry);
        return origFetch.apply(this, arguments).then(function(resp) {
            entry.status = resp.status;
            try { resp.clone().text().then(function(t) { entry.response = t.substring(0, 5000); }).catch(function(){}); } catch(e) {}
            return resp;
        });
    };
    
    // 2. Intercept sendBeacon
    if (navigator.sendBeacon) {
        var origBeacon = navigator.sendBeacon.bind(navigator);
        navigator.sendBeacon = function(url, data) {
            window.__API_LOG__.push({type: 'beacon', method: 'POST', url: url, body: data ? String(data).substring(0, 5000) : null, timestamp: Date.now()});
            return origBeacon(url, data);
        };
    }
    
    // 3. Intercept XHR
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__m = method; this.__u = url;
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body) {
        var self = this;
        var entry = {type: 'xhr', method: this.__m, url: this.__u, body: body ? String(body).substring(0, 5000) : null, timestamp: Date.now()};
        window.__API_LOG__.push(entry);
        this.addEventListener('load', function() {
            entry.status = self.status;
            entry.response = self.responseText ? self.responseText.substring(0, 5000) : null;
        });
        return origSend.apply(this, arguments);
    };
    
    // 4. Intercept WebSocket send
    var origWsSend = WebSocket.prototype.send;
    WebSocket.prototype.send = function(data) {
        window.__API_LOG__.push({
            type: 'ws_send', url: this.url,
            data: typeof data === 'string' ? data.substring(0, 5000) : '[binary]',
            timestamp: Date.now()
        });
        return origWsSend.apply(this, arguments);
    };
    
    // 5. Intercept WebSocket message events (cho listener mới)
    var origAddEventListener = WebSocket.prototype.addEventListener;
    WebSocket.prototype.addEventListener = function(type, listener, options) {
        if (type === 'message') {
            var self = this;
            var wrapped = function(event) {
                window.__API_LOG__.push({
                    type: 'ws_recv', url: self.url,
                    data: event.data ? String(event.data).substring(0, 5000) : null,
                    timestamp: Date.now()
                });
                return listener.apply(this, arguments);
            };
            return origAddEventListener.call(this, type, wrapped, options);
        }
        return origAddEventListener.apply(this, arguments);
    };
    
    "interceptor_installed";
})()
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
    
    # 1. Inject interceptor
    print("[1] Injecting interceptor...")
    r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': INTERCEPTOR_JS})
    val = r.get('result', {}).get('value', '') if isinstance(r.get('result'), dict) else str(r.get('result', ''))
    print(f"    -> {val}")
    
    # 2. Trigger action
    print(f"[2] Triggering: {TRIGGER_JS[:80]}")
    send_command({'type': 'execute_js', 'tabId': tab_id, 'code': TRIGGER_JS})
    
    # 3. Wait
    print(f"[3] Waiting {WAIT_SECONDS}s...")
    time.sleep(WAIT_SECONDS)
    
    # 4. Collect
    print("[4] Collecting API log...")
    r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'JSON.stringify(window.__API_LOG__ || [])'})
    raw = r.get('result', {}).get('value', '[]') if isinstance(r.get('result'), dict) else '[]'
    
    try:
        captured = json.loads(raw)
    except json.JSONDecodeError:
        # Control chars in response — try strict=False
        try:
            captured = json.loads(raw, strict=False)
        except:
            captured = []
    
    print(f"\nCaptured: {len(captured)} API calls")
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(captured, f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUTPUT_FILE}")
    
    # Display
    print("\n" + "=" * 80)
    for i, call in enumerate(captured):
        ctype = call.get('type', '?')
        method = call.get('method', '').upper()
        url = call.get('url', '?')
        status = call.get('status', '')
        body = call.get('body', '')
        resp = call.get('response', '')
        data = call.get('data', '')
        
        short_url = url[:120] + '...' if len(url) > 120 else url
        status_str = f'[{status}]' if status else ''
        print(f"\n[{i+1}] {ctype.upper()} {method} {status_str} {short_url}")
        
        if body and body != 'null' and body.strip():
            try:
                bj = json.loads(body)
                print(f"  REQ: {json.dumps(bj, indent=2, ensure_ascii=False)[:600]}")
            except:
                print(f"  REQ: {body[:600]}")
        
        if data and data != 'null' and data.strip():
            try:
                dj = json.loads(data)
                print(f"  WS:  {json.dumps(dj, indent=2, ensure_ascii=False)[:600]}")
            except:
                print(f"  WS:  {data[:600]}")
        
        if resp and resp != 'null' and resp.strip():
            try:
                rj = json.loads(resp)
                print(f"  RES: {json.dumps(rj, indent=2, ensure_ascii=False)[:600]}")
            except:
                print(f"  RES: {resp[:600]}")

if __name__ == '__main__':
    main()
