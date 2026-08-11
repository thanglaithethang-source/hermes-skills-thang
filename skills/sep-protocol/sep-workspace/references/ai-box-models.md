# AI-Box Model Reference

Provider: `https://api.ai-box.vn/v1` (OpenAI-compatible endpoint)
API key: in `config.yaml` under `model.api_key` + `custom_providers[0].api_key`
Last tested: 2026-07-23

## Available Models (12 total)

| # | Model | Type | Speed | Notes |
|---|-------|------|-------|-------|
| 1 | `deepseek-v4-pro[1m]` | Chat (1M ctx) | ★★★★ | **BEST OVERALL.** Fast, correct, concise. Daily driver. |
| 2 | `deepseek-v4-flash[1m]` | Reasoning (1M ctx) | ★★★★★ | Fastest. Reasoning model with `reasoning_tokens`. Good trace. |
| 3 | `deepseek-v4-pro` | Chat | ★★★★ | Same as [1m] without extended context. |
| 4 | `deepseek-v4-flash` | Chat | ★★★★★ | Budget + fast. |
| 5 | `glm-5.2` | Reasoning | ★★★★ | **WORKS.** Has `reasoning_content` — MUST capture it. Table-format trace. |
| 6 | `qwen3.7-max` | Chat | ★★★ | Solid, clean code. Slower than DeepSeek. |
| 7 | `qwen3.7-plus` | Chat | ★★★ | Mid-tier Qwen. |
| 8 | `qwen3.8-max-preview` | Reasoning | ★ | **TOO SLOW.** 103s for complex prompt (vs 34s DeepSeek). Avoid. |
| 9 | `kimi-k2.7-code` | Chat | ★★ | Correct but slow (59s). Decent code quality. |
| 10 | `kimi-k2.6` | Chat | ★★ | Previous-gen Kimi. |
| 11 | `wan2.7-image-pro` | Image gen | — | Image generation via `/v1/images/generations`. ~20s/ảnh 1024×1024. |
| 12 | `qwen-image-2.0` | Image gen | — | Alternative image model. |

## PITFALL: Reasoning Models (GLM-5.2, deepseek-v4-flash[1m], qwen3.8-max-preview)

These models return content in TWO fields:
- `message.content` — the visible response
- `message.reasoning_content` — internal chain-of-thought (may be large!)

If you only read `message.content`, you may see an empty response while the model used thousands of tokens on reasoning. Always check BOTH fields. The `usage` object will show `completion_tokens_details.reasoning_tokens`.

**GLM-5.2** was previously marked "DO NOT USE" because its `content` was empty — but it was generating 1300+ reasoning tokens. Works fine when `reasoning_content` is captured.

## Quality Ranking (tested 2026-07-23)

Benchmark: same hard prompt (max subarray ≤ k in O(n) — code + trace + verify), max_tokens=4096, temp=0.3. Measured: correctness, speed, code quality, trace quality.

### Tier 1 — Best Overall
- **deepseek-v4-pro[1m]**: 33.9s, correct, clean code, efficient token usage. Best balance.
- **glm-5.2**: 30.2s, correct, table-format trace (best visualization). Reasoning model.

### Tier 2 — Good Alternatives
- **deepseek-v4-flash[1m]**: 26.4s, correct, most detailed trace. Fastest.
- **qwen3.7-max**: 58.3s, correct, clean code.

### Tier 3 — Functional but Slow
- **kimi-k2.7-code**: 58.7s, correct, decent code.

### Tier 4 — Avoid
- **qwen3.8-max-preview**: 103.9s, correct but 3-4× slower than alternatives.

## Model Selection by Task

| Task | Primary | Fallback |
|---|---|---|
| Everything (daily driver) | deepseek-v4-pro[1m] | deepseek-v4-flash[1m] |
| Speed-critical | deepseek-v4-flash[1m] | deepseek-v4-pro[1m] |
| Deep reasoning / complex problems | glm-5.2 | deepseek-v4-pro[1m] |
| Image generation | wan2.7-image-pro | qwen-image-2.0 |

## Benchmark Methodology

To test models, use a single hard prompt requiring reasoning + code + verification:

```python
import json, urllib.request, time

API_KEY = "<from config.yaml>"
BASE_URL = "https://api.ai-box.vn/v1/chat/completions"

def test_model(model_name, prompt, max_tokens=4096, temp=0.3):
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    })
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - start
    msg = result["choices"][0]["message"]
    content = msg.get("content", "")
    reasoning = msg.get("reasoning_content", "")
    usage = result.get("usage", {})
    return {
        "time": round(elapsed, 1),
        "content": content,
        "reasoning": reasoning,
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
        "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
    }
```

Evaluate on: correctness, speed, code quality, explanation quality, token efficiency.

## Test Prompt Used (2026-07-23)

```
Solve this problem with concise reasoning then code:

PROBLEM: Given an array of n integers (1 <= n <= 10^5, elements between -10^9 and 10^9),
find the maximum sum of a contiguous subarray of length AT MOST k (1 <= k <= n).
The naive O(n*k) is too slow.

Requirements:
1. Explain your approach in 2-3 sentences
2. Write a Python function max_subarray_at_most_k(arr, k) that runs in O(n)
3. Trace step-by-step for: arr = [2, -1, 3, -4, 5, -2, 1, 4, -2, 3], k = 3
4. Give the final answer and verify it manually

Be concise.
```

All 6 chat models returned correct answer (5). Ranking was based on speed + code quality + trace quality.
