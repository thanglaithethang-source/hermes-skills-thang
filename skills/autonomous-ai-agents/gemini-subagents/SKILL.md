---
name: gemini-subagents
description: Gemini 3.5 Flash via Google AI API — 4-key pool, sub-agents + main model
version: 1.1.0
platforms: [windows]
---

# Gemini Sub-Agents

4 Gemini 3.5 Flash API keys (Google AI Studio), dùng cho cả sub-agents lẫn main model.
Hermes điều phối: giao task, chạy song song, gộp kết quả.

## Architecture

```
Sếp → Hermes → gemini-sub "task A" --key 1 --workdir /tmp/a
              → gemini-sub "task B" --key 2 --workdir /tmp/b  (parallel)
              → gemini-sub "task C" --key 3 --workdir /tmp/c
```

Mỗi sub-agent: Python script gọi Gemini API → function calling loop → task_done.

## Setup

- 4 API keys từ https://aistudio.google.com/apikey (mỗi Google account 1 key)
- Lưu keys vào `~/.hermes/gemini-pool.keys` (1 key/dòng)
- Scripts: `scripts/gemini-subagent.py` (Python agent loop), `scripts/gemini-sub` (bash wrapper)

## Usage

### Sub-Agent Mode

```bash
# Single sub-agent (random key)
bash scripts/gemini-sub "Create a FastAPI endpoint for /users" --workdir /path/to/project

# Specific key
bash scripts/gemini-sub "Fix the login bug" --key 2 --workdir /tmp/fix

# Parallel (3 sub-agents simultaneously)
bash scripts/gemini-sub "task A" --key 1 --workdir /tmp/a &
bash scripts/gemini-sub "task B" --key 2 --workdir /tmp/b &
bash scripts/gemini-sub "task C" --key 3 --workdir /tmp/c &
wait
```

### Main Hermes Model Mode

Dùng Gemini 3.5 Flash làm não chính của Hermes (thay DeepSeek):

```bash
# 1. Set API key vào .env (dùng key đầu tiên trong pool)
KEY=$(head -1 ~/.hermes/gemini-pool.keys)
echo "GOOGLE_API_KEY=$KEY" >> "$HERMES_HOME/.env"

# 2. Đổi model
hermes config set model.default "google/gemini-3.5-flash"
hermes config set model.provider "google"

# 3. Khởi động lại Hermes (cần session mới)
# /reset hoặc thoát + chạy lại hermes
```

**Quay lại DeepSeek:**
```bash
hermes config set model.default "deepseek-v4-pro"
hermes config set model.provider "custom"
```

## Cơ chế

- **Model:** Gemini 3.5 Flash (gemini-3.5-flash)
- **Max turns:** 15 per task
- **Tools:** read_file, write_file, run_command, list_dir, task_done
- **Auto fallback:** key bị 429 → tự động thử key khác trong pool
- **Path conversion:** tự động `cygpath -w` cho git-bash → Windows path

## Rate Limits

⚠️ **"Rate limits are applied per project, not per API key"** — Google AI Docs.
Nếu 4 key cùng 1 Google Cloud project → share chung quota, không nhân 4.
Nếu 4 key thuộc 4 project khác nhau → mỗi key có quota riêng.

### Paid Tier (Pro — đã gắn billing)

| Tier | Billing cap/tháng | Spend/10ph | Điều kiện |
|------|------------------|------------|-----------|
| Tier 1 | $250 | $10 | Gắn billing account |
| Tier 2 | $2,000 | $200 | Đã chi $100+ sau 3 ngày |
| Tier 3 | $20K-100K+ | $200 | Đã chi $1,000+ sau 30 ngày |

### Gemini 3.5 Flash — Paid Tier 1 (ước tính)

| Hạn mức | Con số |
|---------|--------|
| RPM (requests/phút) | ~2,000 |
| TPM (tokens/phút) | ~4,000,000 |
| RPD (requests/ngày) | Không giới hạn cứng (bị khống chế bởi spend limit) |

**Quy đổi token/ngày (Tier 1, giá $1.50/1M input, $9.00/1M output):**
- Input tối đa: ~166M tokens/ngày
- Output tối đa: ~27.7M tokens/ngày
- Hỗn hợp (3:1 input:output): ~100M input + ~11M output/ngày

**Tier 2:** gấp ~8 lần Tier 1.

### Free Tier (tham khảo)

~1,500 RPD, ~10-15 RPM, ~1M TPM per key. Không dùng cho production.

Xem thêm: `references/gemini-rate-limits.md` — chi tiết pricing, tier structure, và trích dẫn docs gốc.

## Pitfalls

1. **git-bash path mismatch:** `mktemp -d` trả về `/tmp/...` nhưng Python Windows cần `C:\...`.
   Wrapper tự convert qua `cygpath -w`. Khi gọi thẳng `gemini-subagent.py`, luôn truyền Windows path.
2. **`$HERMES_HOME` ≠ `~/.hermes` trên Windows:** HERMES_HOME trỏ đến `C:\Users\<user>\AppData\Local\hermes`, còn `~/.hermes` là `C:\Users\<user>\.hermes`. Key pool file nằm ở `~/.hermes/gemini-pool.keys`, không phải `$HERMES_HOME/gemini-pool.keys`. Khi tìm key, kiểm tra cả hai đường dẫn.
3. **429 Too Many Requests:** Có thể xảy ra ngay cả trên Paid tier khi model quá tải (503).
   Auto-fallback trong wrapper, đợi 1-2 phút. Paid Tier 1 có spend limit $10/10ph — nếu gọi quá nhiều model đắt (Gemini 3.5 Flash output $9/M) có thể bị chặn bởi spend limit chứ không phải RPM.
4. **Agent hallucinates completion:** Gemini đôi khi mô tả hành động thay vì gọi function.
   Script push lại "call task_done" để ép hoàn thành.
5. **Quota share nếu cùng project:** Nếu 4 key từ cùng 1 Google Cloud project, tổng quota không ×4. Kiểm tra trong AI Studio → "View your active rate limits".
6. **Model config cần session mới:** Sau khi `hermes config set model.default`, model cũ vẫn được dùng cho đến khi `/reset` hoặc khởi động lại Hermes. Không có hiệu lực mid-session.

## Rules

1. Luôn dùng `--workdir` cụ thể, không dùng `.`
2. Sub-agent chỉ làm task được giao, không tự ý mở rộng
3. Review output và file thay đổi trước báo cáo Sếp
4. Code của sub-agent luôn để Sếp duyệt trước commit
5. Không tự động chạy code của sub-agent — verify trước
