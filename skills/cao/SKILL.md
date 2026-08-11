---
name: cao
description: "Crawl4AI — cào web thành Markdown sạch cho LLM. pip install crawl4ai."
version: 1.0.0
---

# Crawl4AI

Cào web → Markdown sạch cho LLM/RAG. Local, free, Apache-2.0.

Repo: unclecode/crawl4ai | PyPI: `crawl4ai` | Python >=3.10

## Cài đặt

```bash
pip install lxml --only-binary=lxml   # Windows pitfall
pip install crawl4ai
crawl4ai-setup
crawl4ai-doctor
```

## CLI

```bash
# Cào cơ bản
crwl crawl https://example.com -o markdown

# LLM extraction (dùng -j, không phải -s)
crwl crawl https://example.com -j "Trích xuất tên, giá sản phẩm"

# Hỏi nội dung đã cào
crwl crawl https://example.com -q "Bài này nói về gì?"

# Deep crawl BFS
crwl crawl https://example.com --deep-crawl bfs -o markdown
```

## SDK cơ bản

```python
import asyncio
from crawl4ai import *

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")
        print(result.markdown)              # Markdown đầy đủ

asyncio.run(main())
```

## Cào hàng loạt

```python
async with AsyncWebCrawler() as crawler:
    results = await crawler.arun_many(
        urls=["https://a.com", "https://b.com"],
        config=CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
    )
    for r in results:
        print(r.url, len(r.markdown))
```

LLM extraction:
```python
result = await crawler.arun(
    url="...",
    extraction_strategy=LLMExtractionStrategy(
        provider="openai/gpt-4o",
        api_token="sk-...",          # hoặc để trong .env
        instruction="Extract name, price as JSON"
    )
)
print(result.extracted_content)      # JSON string
```

## Deep crawl

```python
async with AsyncWebCrawler() as crawler:
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_pages=20),
        cache_mode=CacheMode.ENABLED
    )
    async for result in crawler.arun_many(
        urls=["https://example.com"],
        config=config
    ):
        print(result.url, len(result.markdown))
```

## Không cần browser (nhẹ, nhanh)

```python
result = await crawler.arun(
    url="...",
    config=HTTPCrawlerConfig()  # HTTP-only, không Playwright
)
```

## Chiến lược extraction

| Strategy | Dùng khi |
|---|---|
| `LLMExtractionStrategy` | Cần hiểu ngữ nghĩa, output linh hoạt |
| `JsonCssExtractionStrategy` | Pattern lặp trong HTML, CSS selector |
| `JsonXPathExtractionStrategy` | XPath chính xác |
| `JsonLxmlExtractionStrategy` | lxml-based, nhanh hơn CSS/XPath |
| `RegexExtractionStrategy` | Pattern text đơn giản |
| `CosineStrategy` | Semantic search trong nội dung đã cào |

## Chiến lược deep crawl

| Strategy | Cách duyệt |
|---|---|
| `BFSDeepCrawlStrategy` | Duyệt theo chiều rộng |
| `DFSDeepCrawlStrategy` | Duyệt theo chiều sâu |
| `BestFirstCrawlingStrategy` | Ưu tiên URL "tốt nhất" |

## Cache modes

`CacheMode.ENABLED` (mặc định) | `DISABLED` | `BYPASS` | `WRITE_ONLY` | `READ_ONLY`

## Key output fields

- `result.markdown` — Markdown đầy đủ (là StringCompatibleMarkdown object)
- `result.markdown.fit_markdown` — Filtered markdown (BM25), dùng cho LLM
- `result.cleaned_html` — HTML sạch
- `result.extracted_content` — JSON string từ extraction strategy

## Pitfalls

1. Windows lxml → `pip install lxml --only-binary=lxml` trước
2. Thiếu browser → `crawl4ai-setup`
3. Timeout JS nặng → tăng `wait_for`
4. Bị block → proxy + user_agent rotate
