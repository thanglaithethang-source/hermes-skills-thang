"""DEMO: Kiểm soát Chrome hoàn toàn qua Playwright CDP — 7 tests."""
import json, time, requests
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP, timeout=15000)
page = browser.contexts[0].pages[0]

results = {}

# 1. List tabs
results['list_tabs'] = len(browser.contexts[0].pages)

# 2. Navigate
page.goto("https://httpbin.org/get", wait_until="networkidle", timeout=10000)
results['navigate'] = "httpbin.org" in page.url

# 3. Execute JS
results['execute_js'] = page.evaluate("1 + 1") == 2

# 4. Click + Type
page.goto("https://www.google.com", wait_until="networkidle", timeout=10000)
page.fill('textarea[name="q"]', 'test')
page.press('textarea[name="q"]', 'Enter')
time.sleep(2)
results['click_type'] = 'test' in page.title()

# 5. Bắt API
page.goto("https://www.youtube.com", wait_until="networkidle", timeout=15000)
captured = []
page.on("request", lambda r: captured.append(r.url))
page.on("response", lambda r: None)
page.fill('input[name="search_query"]', 'test')
page.press('input[name="search_query"]', 'Enter')
time.sleep(3)
results['capture_api'] = any('youtubei/v1/search' in u for u in captured)

# 6. Screenshot
page.screenshot(path=r"C:\Users\thang\chrome_demo.png")
import os
results['screenshot'] = os.path.exists(r"C:\Users\thang\chrome_demo.png")

pw.stop()

print(json.dumps(results, indent=2))
passed = sum(1 for v in results.values() if v)
print(f"\n{passed}/{len(results)} PASSED")
