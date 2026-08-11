#!/usr/bin/env python3
"""Template: Bắt và replay API từ 1 web app bất kỳ qua Hermes Bridge."""
import requests, json, time, sys, re
from chrome_send import send_command

# ===== CONFIG =====
TAB_ID = None  # Điền tab ID (lấy từ list_tabs)
WEB_NAME = "target-site"

def get_tab_id():
    """Lấy tab ID của web cần phân tích."""
    global TAB_ID
    if TAB_ID:
        return TAB_ID
    r = send_command({'type': 'list_tabs'})
    for t in r.get('tabs', []):
        print(f"  [{t['id']}] {t['title'][:60]}")
    TAB_ID = int(input("Tab ID: ").strip())
    return TAB_ID

def capture_apis(tab_id, action_js="location.reload()", wait=5):
    """Bắt tất cả API calls sau khi thực hiện 1 hành động."""
    print(f"[1] Bắt đầu theo dõi network trên tab {tab_id}...")
    send_command({'type': 'network_start', 'tabId': tab_id})
    
    print(f"[2] Thực hiện hành động...")
    send_command({'type': 'execute_js', 'tabId': tab_id, 'code': action_js})
    
    time.sleep(wait)
    
    print(f"[3] Dừng theo dõi...")
    r = send_command({'type': 'network_stop', 'tabId': tab_id})
    return r.get('requests', [])

def filter_apis(requests):
    """Lọc ra API calls (bỏ static resources)."""
    api_patterns = ['/api/', '/v1/', '/v2/', 'graphql', 'rpc', 'batch',
                    'backend-api', 'rest/', 'query']
    apis = []
    for req in requests:
        url = req.get('url', '')
        if any(p in url for p in api_patterns):
            apis.append(req)
    return apis

def extract_auth(tab_id, requests):
    """Extract cookies và auth headers từ browser + captured requests."""
    # Cookies từ browser
    r = send_command({'type': 'execute_js', 'tabId': tab_id, 'code': 'document.cookie'})
    cookies = {}
    for c in r.get('result', {}).get('value', '').split('; '):
        if '=' in c:
            k, v = c.split('=', 1)
            cookies[k] = v
    
    # Auth headers từ captured requests
    headers = {}
    auth_keys = {'authorization', 'x-api-key', 'x-csrf-token', 'cookie', 'x-xsrf-token'}
    for req in requests:
        for k, v in req.get('headers', {}).items():
            if k.lower() in auth_keys:
                headers[k] = v
    
    return cookies, headers

def replay_api(method, url, cookies, headers, body=None, content_type='application/json'):
    """Gọi lại API bằng Python requests."""
    req_headers = {
        'Content-Type': content_type,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        **headers
    }
    
    if method == 'GET':
        return requests.get(url, headers=req_headers, cookies=cookies, timeout=15)
    elif method == 'POST':
        if content_type == 'application/json' and isinstance(body, str):
            body = json.loads(body) if body else {}
        return requests.post(url, headers=req_headers, cookies=cookies, json=body, timeout=15)
    else:
        return requests.request(method, url, headers=req_headers, cookies=cookies, data=body, timeout=15)

# ===== MAIN =====
if __name__ == '__main__':
    tab_id = get_tab_id()
    
    # B1: Capture
    print(f"\n{'='*50}")
    print(f"BẮT API TỪ {WEB_NAME}")
    print(f"{'='*50}")
    
    requests = capture_apis(tab_id)
    print(f"\nTổng: {len(requests)} requests")
    
    apis = filter_apis(requests)
    print(f"API calls: {len(apis)}\n")
    
    # B2: Hiển thị APIs
    for i, req in enumerate(apis[:20]):
        print(f"[{i}] {req['method']} {req.get('status','?')} {req['url'][:130]}")
        if req.get('postData'):
            print(f"    Body: {req['postData'][:200]}")
    
    # B3: Extract auth
    cookies, auth_headers = extract_auth(tab_id, requests)
    print(f"\nCookies: {len(cookies)} items")
    print(f"Auth headers: {list(auth_headers.keys())}")
    
    # B4: Chọn API để replay
    if apis:
        choice = input("\nChọn API index để replay (Enter = skip): ").strip()
        if choice.isdigit() and int(choice) < len(apis):
            req = apis[int(choice)]
            print(f"\nReplaying: {req['method']} {req['url'][:100]}")
            resp = replay_api(
                req['method'],
                req['url'],
                cookies,
                auth_headers,
                req.get('postData'),
                req.get('responseHeaders', {}).get('content-type', 'application/json')
            )
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
