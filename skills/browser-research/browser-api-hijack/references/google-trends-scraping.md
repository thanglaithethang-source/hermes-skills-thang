# Google Trends Scraping — Navigate + DOM Text Extract

## Vấn đề
- `pytrends` library: trả 404 (Google đổi endpoint)
- Google Trends RSS feed: trả 404
- Google Trends JSON API endpoints: tất cả 404

## Fix — Dùng Chrome bridge navigate + scrape text

Google Trends không có public API ổn định. Cách duy nhất hoạt động: navigate Chrome tới trang Trends, đợi page load, extract text content.

```python
import sys, json, time
sys.path.insert(0, r'C:\Users\thang\Downloads\_projects\hermes-chrome-extension')
from chrome_send import send_command

TAB_ID = <tab_id>  # bất kỳ tab nào

# 1. Navigate to Google Trends daily trending
send_command({'type': 'navigate', 'tabId': TAB_ID, 'url': 'https://trends.google.com/trends/trendingsearches/daily?geo=US&hl=en'})
time.sleep(8)

# 2. Extract text content
js = '''
(function() {
    var body = document.body ? document.body.innerText : '';
    return JSON.stringify({source: 'text', content: body.substring(0, 8000)});
})()
'''
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {'expression': js, 'returnByValue': True},
    'tabId': TAB_ID
})
val = r.get('result', {}).get('result', {}).get('value', '') if isinstance(r.get('result'), dict) else ''
data = json.loads(val)
print(data['content'])
```

## Output format
Page text chứa: keyword, search volume (200K+, 100K+, 50K+, 20K+, 10K+, 5K+), growth %, started time, status (Active), related keywords.

## Đã test thành công
- 2026-07-29: US daily trending, 25+ keywords với search volume + growth %
- pytrends + RSS + JSON API đều 404 → navigate + scrape là cách duy nhất
