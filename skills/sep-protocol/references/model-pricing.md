# api.ai-box.vn Model Pricing

Provider: **custom** (https://api.ai-box.vn/v1) — 15 models.
Đơn giá: $/1M tokens. 1$ = 26,000₫. Quota mua qua gói (70K→1M quota).

## LLM Models (sorted by price)

| Model | Input | Output | Cache Hit | Notes |
|-------|-------|--------|-----------|-------|
| **qwen3.7-flash** | **$0.01** | **$0.043** | $0.001 | Rẻ nhất. Flash quality. |
| qwen3.6-flash | $0.047 | $0.094 | $0.00093 | Cũ hơn, rẻ. |
| **DeepSeek-V4 Flash** | **$0.047** | **$0.094** | **$0.00093** | **🟢 Best value. Gần bằng Pro.** |
| DeepSeek-V4 Pro | $0.145 | $0.29 | $0.0012 | Flagship thông minh nhất. |
| glm-5.2 | $0.145 | $0.29 | $0.0012 | Reasoning mạnh, chậm, no vision. |
| glm-5.2-fast-preview | $0.29 | $0.58 | $0.0024 | X2 giá glm-5.2. |
| qwen3.7-max | $0.145 | $0.29 | $0.0012 | Qwen flagship. |
| qwen3.7-plus | $0.145 | $0.29 | $0.0012 | Qwen mid-range. |
| qwen3.8-max | $0.145 | $0.29 | $0.0012 | Preview, chưa ổn định. |
| kimi-k2.7-code | $0.145 | $0.29 | $0.0012 | Chuyên code. |

## Benchmark Results (2026-08-04)

### Round 1: Basic Test — 5 bài × 12 models

Test: 5 bài (Logic, Math, Code, Vietnamese, Instruction) × 12 models. Temperature=0.

| Rank | Model | Score | Time | Notes |
|------|-------|-------|------|-------|
| 1 | deepseek-v4-flash[1m] | 3/5 | 8.5s | Nhanh nhất. [1m]=1M context. |
| 2 | deepseek-v4-flash | 3/5 | 11.5s | |
| 3 | qwen3.8-max | 3/5 | 17.5s | |
| 4 | deepseek-v4-pro[1m] | 3/5 | 19.8s | |
| 5 | deepseek-v4-pro | 3/5 | 24.6s | |
| 6 | kimi-k2.7-code | 3/5 | 24.8s | Code nhanh (3.3s) |
| 7 | qwen3.6-flash | 3/5 | 26.3s | |
| 8 | qwen3.7-flash | 3/5 | 29.2s | Rẻ nhất nhưng chậm hơn DS-flash |
| 9 | glm-5.2 | 3/5 | 31.5s | Model hiện tại của agent |
| 10 | qwen3.7-max | 3/5 | 58.3s | Chậm gấp 7x #1 |
| 11 | qwen3.7-plus | 3/5 | 61.2s | Chậm nhất |
| 12 | glm-5.2-fast-preview | 2/5 | 15.5s | Yếu nhất — fail Logic |

### Round 2: Deep Test — 8 bài × 12 models

Test: 8 bài (FuncCall, Reason, Math2, Code2, VN2, Puzzle, Format, ToolUse) × 12 models. Temperature=0, max_tokens=800.

| Rank | Model | Score | Time | Failed Tests |
|------|-------|-------|------|--------------|
| 1 | **kimi-k2.7-code** | **8/8** | **48.9s** | NONE — perfect score + fastest in 8/8 group |
| 2 | qwen3.7-flash | 8/8 | 51.2s | NONE |
| 3 | qwen3.6-flash | 8/8 | 58.9s | NONE |
| 4 | qwen3.8-max | 8/8 | 71.4s | NONE (but Puzzle took 54.8s alone) |
| 5 | qwen3.7-plus | 8/8 | 85.4s | NONE |
| 6 | qwen3.7-max | 8/8 | 91.9s | NONE — chậm nhất |
| 7 | glm-5.2 | 7/8 | 46.9s | Puzzle (logic ràng buộc 3 người) |
| 8 | deepseek-v4-flash[1m] | 6/8 | 27.3s | VN2 + Puzzle |
| 9 | glm-5.2-fast-preview | 6/8 | 29.5s | VN2 + Puzzle |
| 10 | deepseek-v4-flash | 6/8 | 35.0s | VN2 + Puzzle |
| 11 | deepseek-v4-pro | 6/8 | 35.9s | Puzzle + Format (thêm dấu phẩy) |
| 12 | deepseek-v4-pro[1m] | 6/8 | 38.0s | Puzzle + Format |

### Key Findings

- **kimi-k2.7-code là model mạnh nhất** — 8/8 perfect, nhanh nhất nhóm perfect (48.9s), code clean không markdown, VN dịch chuẩn
- **Qwen family (3.6/3.7/3.8) đều 8/8** — qwen3.7-flash là best value (8/8 + 51.2s + rẻ nhất $0.01/$0.043)
- **DeepSeek fail Puzzle + VN2/Format** — reasoning ràng buộc yếu, dịch nghĩa bóng kém
- **glm-5.2 (model agent đang dùng) chỉ 7/8** — fail Puzzle, nhanh thứ 2 overall nhưng reasoning yếu hơn Qwen
- **Puzzle (logic ràng buộc 3 người)** — chỉ Qwen + kimi giải được. GLM, DeepSeek đều fail
- **VN2 (dịch thành ngữ)** — DeepSeek-flash fail hoàn toàn (trả empty), glm-5.2 dịch sai ("Đừng đếm cua trong lỗ")
- **Format (3 từ, không dấu)** — DeepSeek-pro fail (thêm dấu phẩy "Vast, blue, endless")

### Updated Model Selection Strategy

```
Task phức tạp / reasoning / logic    → kimi-k2.7-code      (8/8, $0.145/$0.29)
Best value / task thường             → qwen3.7-flash       (8/8, $0.01/$0.043) ← RẺ NHẤT
Task khó + cần max reasoning          → qwen3.8-max         (8/8, $0.145/$0.29)
Code chuyên sâu                       → kimi-k2.7-code      (8/8, code clean)
Chat nhanh / task đơn giản            → deepseek-v4-flash[1m] (6/8, 27.3s, $0.047/$0.094)
Reasoning / toán (hiện tại)           → glm-5.2              (7/8, $0.145/$0.29) ← agent default
KHÔNG DÙNG                            → glm-5.2-fast-preview (6/8, fail VN2+Puzzle)
```

### Test Scripts

- Round 1: `C:\Users\thang\tmp_modeltest\test_models.py` — 5 basic tests
- Round 2: `C:\Users\thang\tmp_modeltest\test_deep.py` — 8 deep tests (FuncCall, Reason, Math2, Code2, VN2, Puzzle, Format, ToolUse)

Chạy lại:
```bash
python "C:\Users\thang\tmp_modeltest\test_models.py"   # Round 1
python "C:\Users\thang\tmp_modeltest\test_deep.py"     # Round 2
```

## Image Models

| Model | Price |
|-------|-------|
| wan2.7-image-pro | 52₫/req |
| qwen-image-2.0 | 52₫/req |

## Embedding

| Model | Price |
|-------|-------|
| text-embedding-v4 | $0.0007/M tokens |

## Chiến thuật chọn model

```
Task phức tạp / reasoning / logic    → kimi-k2.7-code      (8/8, $0.145/$0.29) ← MẠNH NHẤT
Best value / task thường             → qwen3.7-flash       (8/8, $0.01/$0.043) ← RẺ NHẤT + 8/8
Task khó + cần max reasoning          → qwen3.8-max         (8/8, $0.145/$0.29)
Code chuyên sâu                       → kimi-k2.7-code      (8/8, code clean)
Chat nhanh / task đơn giản            → deepseek-v4-flash[1m] (6/8, 27.3s, $0.047/$0.094)
Reasoning / toán (hiện tại)           → glm-5.2              (7/8, $0.145/$0.29) ← agent default
KHÔNG DÙNG                            → glm-5.2-fast-preview (6/8, fail VN2+Puzzle)
```

**Benchmark 2026-08-04**: kimi-k2.7-code 8/8 perfect + nhanh nhất nhóm perfect. Qwen family (3.6/3.7/3.8) đều 8/8. DeepSeek 6/8 (fail Puzzle + VN2). glm-5.2 7/8 (fail Puzzle). Chi tiết: xem bảng benchmark ở trên.

## Quota System

- Gói quota: 90K (70K₫) → 1M (520K₫)
- Gói reset hàng ngày: 45K (36K₫) +2K quota/ngày → 600K (364K₫) +20K/ngày
- Không giới hạn RPM/RPD
- Cache hit: giá chỉ ~2% so với cache miss (áp dụng cho repeated context)

## Lưu ý

- glm-5.2: reasoning model, có `reasoning_content`, ~30s cho bài phức tạp, KHÔNG vision
- qwen3.8-max-preview: rất chậm (~103s), không recommend cho production
- deepseek-v4-flash[1m] / deepseek-v4-pro[1m]: suffix `[1m]` = 1M context variant