---
name: image-generation
description: "Generate AI images via API (wan2.7-image-pro, qwen-image-2.0) on ai-box.vn. OpenAI-compatible /v1/images/generations endpoint. Use when Sếp asks to create, generate, or produce images from prompts."
version: 1.0.0
---

# Image Generation (API)

## Activation
Khi Sếp yêu cầu tạo ảnh từ prompt — "tạo ảnh", "generate image", "vẽ", gửi danh sách prompt.

## Models Available
| Model | Provider | Endpoint |
|---|---|---|
| `wan2.7-image-pro` | Alibaba DashScope (qua ai-box.vn) | `/v1/images/generations` |
| `qwen-image-2.0` | Qwen (qua ai-box.vn) | `/v1/images/generations` |

## Workflow

### 1. Single image
```python
POST {base_url}/images/generations
{
  "model": "wan2.7-image-pro",
  "prompt": "your prompt here",
  "n": 1,
  "size": "1024x1024"
}
→ Response: {"data": [{"url": "https://..."}]}
```

### 2. Download + save + verify
Sau khi có URL:
1. `requests.get(img_url)` → download bytes
2. Save to `C:\Users\thang\Downloads\New folder\`
3. Format filename: `YYYYMMDD_HHMMSS_{prompt_40chars_sanitized}.png`
4. Verify: `os.path.getsize()` + SHA256

### 3. Output directory
```
C:\Users\thang\Downloads\New folder\
```
Đây là thư mục Sếp chỉ định. LUÔN lưu ảnh vào đây.

## Benchmarks (tested 2026-07-23)

| Scenario | Time | Notes |
|---|---|---|
| 1 ảnh đơn | ~18-24s | 1024x1024 PNG ~2MB |
| 3 concurrent | ~20s | ThreadPool, không rate limit |
| 10 concurrent | ~21s | Tất cả OK, không fail |
| n=2 batch | ~21s | 2 ảnh trong 1 request |
| 200 ảnh (20w conc.) | ~3-5 phút | Ước tính |

## Bulk Generation (200+ prompts)

Dùng `scripts/bulk_generate.py` — nhận file prompts (mỗi dòng 1 prompt), chạy concurrent, lưu tất cả ảnh + manifest CSV.

Cấu hình trong script:
- `MAX_WORKERS = 20` (đã test OK)
- `BATCH_N = 4` (nếu API hỗ trợ n>2)

## Pitfalls

1. **URL hết hạn**: Ảnh trên Alibaba OSS có Expires. Phải download ngay sau khi generate, không lưu URL.
2. **Không phải chat model**: Gọi `/v1/chat/completions` với wan2.7-image-pro → 403 Access Denied. Chỉ dùng `/v1/images/generations`.
3. **Cost không tính token**: Image models tính per-image, không per-token. Không dùng `usage.prompt_tokens` để tính.
4. **size mặc định**: `1024x1024` được test OK. Các size khác chưa test.

## Completion Criteria
- Ảnh đã download + save vào `C:\Users\thang\Downloads\New folder\`
- File tồn tại, size > 0, SHA256 verified
- Trả về absolute path cho Sếp
