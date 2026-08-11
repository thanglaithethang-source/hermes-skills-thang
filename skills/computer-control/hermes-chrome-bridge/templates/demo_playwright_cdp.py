"""Demo: Playwright CDP — navigate + bắt API requests từ web bất kỳ."""
import json, time
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"  # NOT localhost (IPv6 bug)

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP, timeout=15000)
page = browser.contexts[0].pages[0]

# 1. Navigate
print(f"[1] Navigate to target...")
page.goto("https://example.com", wait_until="networkidle", timeout=15000)
print(f"    Title: {page.title()[:80]}")

# 2. Capture API requests
captured = []
def on_request(req):
    url = req.url
    if any(x in url for x in ['/api/', '/v1/', 'graphql']):  # Adjust filters
        try: pd = req.post_data
        except: pd = None
        captured.append({'method': req.method, 'url': url[:150], 'post_data': pd})
def on_response(resp):
    for c in captured:
        if c['url'][:80] == resp.url[:80] and 'status' not in c:
            c['status'] = resp.status
            try: c['body'] = resp.text()[:300]
            except: pass

page.on("request", on_request)
page.on("response", on_response)

# 3. Trigger action to generate API calls
print(f"[2] Trigger action...")
# page.click("button")  # or page.fill, page.press, etc.
time.sleep(3)

print(f"[3] Captured {len(captured)} API calls:")
for c in captured:
    print(f"    {c['method']} {c.get('status','?')} {c['url'][:120]}")

pw.stop()
print("\n[DONE]")
