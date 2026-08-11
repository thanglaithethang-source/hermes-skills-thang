---
name: stock-images
description: Search and download stock images from Pexels and Pixabay APIs
version: 1.0.0
platforms: [windows, linux, macos]
---

# Stock Images — Pexels + Pixabay

Search và download ảnh stock miễn phí từ 2 nguồn: Pexels và Pixabay.

## Setup

API keys lưu trong:
- `~/.hermes/pexels.key` — Pexels API key
- `~/.hermes/pixabay.key` — Pixabay API key

## Pexels API

```
curl -s "https://api.pexels.com/v1/search?query=QUERY&per_page=10" \
  -H "Authorization: $(cat ~/.hermes/pexels.key)"
```

Response có `photos[]` với `src.original`, `src.large`, `src.medium`, `photographer`.

## Pixabay API

```
curl -s "https://pixabay.com/api/?key=$(cat ~/.hermes/pixabay.key)&q=QUERY&per_page=10"
```

Response có `hits[]` với `webformatURL`, `largeImageURL`, `user`.

## Download ảnh

```bash
# Pexels: lấy URL từ search rồi curl
URL=$(curl -s "https://api.pexels.com/v1/search?query=nature&per_page=1" \
  -H "Authorization: $(cat ~/.hermes/pexels.key)" | \
  python -c "import sys,json; print(json.load(sys.stdin)['photos'][0]['src']['original'])")
curl -o image.jpg "$URL"

# Pixabay: tương tự
URL=$(curl -s "https://pixabay.com/api/?key=$(cat ~/.hermes/pixabay.key)&q=nature&per_page=1" | \
  python -c "import sys,json; print(json.load(sys.stdin)['hits'][0]['largeImageURL'])")
curl -o image.jpg "$URL"
```

## Pitfalls

- Pexels auth header: `Authorization: API_KEY` (không có Bearer)
- Pixabay dùng query param `?key=...` (khác Pexels)
- Cả 2 đều free, không cần OAuth
- Rate limit: Pexels 200 req/hour, Pixabay 100 req/min

## Rules

1. Luôn credit photographer khi dùng ảnh
2. Không tải hàng loạt — tôn trọng rate limit
3. Dùng size phù hợp (medium cho preview, original cho final)
