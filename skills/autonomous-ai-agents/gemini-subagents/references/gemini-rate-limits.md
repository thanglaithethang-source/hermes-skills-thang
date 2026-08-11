# Gemini API Rate Limits — Chi tiết

Nguồn: https://ai.google.dev/gemini-api/docs/rate-limits (2026-07-13)
Nguồn pricing: https://ai.google.dev/gemini-api/docs/pricing

## Nguyên tắc cốt lõi

> **"Rate limits are applied per project, not per API key."**

Đây là điểm quan trọng nhất: nhiều API key từ cùng 1 Google Cloud project
thì share chung 1 quota. Chỉ khi key thuộc project khác nhau mới có quota riêng.

## Cấu trúc 3 chiều

Rate limit được đo trên 3 chiều:
1. **RPM** (Requests per minute)
2. **TPM** (Tokens per minute — input)
3. **RPD** (Requests per day) — reset lúc midnight Pacific time

Vượt bất kỳ chiều nào cũng trigger 429.

## Usage Tiers

| Tier | Điều kiện | Billing cap/tháng | Spend rate/10ph |
|------|----------|-------------------|-----------------|
| Free | Active project hoặc free trial | N/A | N/A |
| Tier 1 | Gắn billing account | $250 | $10 |
| Tier 2 | Đã chi $100+ sau 3 ngày từ lần thanh toán đầu | $2,000 | $200 |
| Tier 3 | Đã chi $1,000+ sau 30 ngày | $20K-100K+ | $200 |

Tier tự động nâng cấp khi đủ điều kiện. Free→Tier 1 gần như ngay lập tức;
các tier sau mất ~10 phút.

## Gemini 3.5 Flash — Pricing (Paid Tier)

| Loại | Giá / 1M tokens |
|------|-----------------|
| Input | $1.50 |
| Output (gồm thinking tokens) | $9.00 |
| Context caching (storage) | $0.15 (+ $1.00/M tokens/giờ) |

**Free tier:** miễn phí nhưng data dùng để cải thiện sản phẩm của Google.

## Gemini 3.5 Flash — Rate Limits (Paid Tier)

Google không public bảng RPM/TPM/RPD chi tiết. Phải xem trong AI Studio:
https://aistudio.google.com → View your active rate limits

**Ước tính Tier 1:**
- RPM: ~2,000
- TPM: ~4,000,000
- RPD: Không giới hạn cứng (bị spend limit $10/10ph khống chế)

**Batch API (Gemini 3.5 Flash):**
- Concurrent batch requests: 100
- Input file size limit: 2GB
- File storage limit: 20GB
- Batch enqueued tokens: 3,000,000

## Tính toán token/ngày thực tế

### Tier 1 ($250/tháng, $10/10ph)

Giả định hỗn hợp input:output = 3:1:

- Input: $1.50/M → $250 mua được ~166M input tokens
- Output: $9.00/M → $250 mua được ~27.7M output tokens
- Hỗn hợp 3:1: ~100M input + ~11M output = ~111M tokens/ngày

### Tier 2 ($2,000/tháng)

Gấp ~8 lần Tier 1: ~888M tokens/ngày hỗn hợp.

## Cảnh báo

1. **Model quá tải:** Gemini 3.5 Flash từng trả 503 ngay cả với Paid key (2026-07-13).
   Không phải lúc nào cũng đạt max RPM.
2. **Spend limit đè RPM:** Với output $9/M, 1 request 10K output tokens = $0.09.
   Chỉ ~111 request/10ph là chạm spend limit $10, dù RPM có thể cao hơn nhiều.
3. **RPD không giới hạn cứng** trên Paid tier, nhưng bị spend limit khống chế gián tiếp.
