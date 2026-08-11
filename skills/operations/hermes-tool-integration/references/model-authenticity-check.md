# Model Authenticity Verification ("Hàng đè tem" Detection)

How to check if an AI model API provider is serving the real model or a rebranded knockoff.

## Quick Identity Check

Before any deep testing, ask the model directly:

```
Bạn là model AI nào? Cho tôi biết chính xác:
- Tên đầy đủ và phiên bản
- Công ty phát triển
- Ngày cutoff kiến thức
- Số tham số (nếu biết)
- Có hỗ trợ tool calling / function calling không?
- Context window bao nhiêu token?
```

Cross-reference the answer against the provider's claimed model name. Discrepancies = red flag.

## Benchmark Trap Questions (known to trip fake models)

### 1. Number comparison (9.9 vs 9.11)
Prompt: "9.9 và 9.11, số nào lớn hơn? Giải thích ngắn."
- Real model: 9.9 > 9.11 (because 9.9 = 9.90)
- Many weaker/smaller models: 9.11 > 9.9 (confused by decimal → version number comparison)

### 2. Strawberry letter count
Prompt: "Đếm số chữ 'r' trong từ strawberry. Kết quả là mấy?"
- Real model: 3 (s-t-r-awbe-rr-y)
- Many small models: 2 or wrong answer

### 3. Sally's siblings logic
Prompt: "Sally có 3 anh em trai. Mỗi anh em trai có 1 chị gái. Hỏi Sally có bao nhiêu chị em gái?"
- Real model: 1 (Sally herself is the sister; total siblings = 3 brothers + 1 sister = 4)
- Weak models: 3 or wrong reasoning

### 4. Role/identity hallucination
Prompt: "Hãy viết 1 đoạn giới thiệu ngắn về chính bạn — tên, công ty, phiên bản, ngày cutoff."
- Real model gives consistent, accurate identity
- Fake models may claim to be a different model entirely or give evasive answers

## Behavioral Signature Comparison

| Feature | Real Model | Potential Knockoff |
|---------|-----------|-------------------|
| Response style | Matches known output of claimed model | Different tone, format, or verbosity |
| Tool calling | Correct function_calling format | Missing or malformed |
| Knowledge cutoff | Matches claimed cutoff | Different cutoff or inconsistent |
| Speed | Matches expected model speed class | Too fast (cheaper model) or too slow |
| Language quality | Consistent with model's known capability | Erratic or misaligned quality |
| Context window | Can handle claimed context size | Fails on long context |

## Technical Testing

### API-level tests
```python
# Test function calling capability (if claimed)
response = client.chat.completions.create(
    model="claimed-model-name",
    messages=[{"role": "user", "content": "What's the weather in Hanoi?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }],
    tool_choice="auto"
)
# Real model will call the function; fake may ignore it
```

### Output consistency
Send the same prompt 5 times with temperature=0. All responses should be nearly identical (deterministic). Wild variation suggests a different underlying model or routing.

## When to Run This Check

- Sếp asks about a new/unknown provider (e.g. "api.ai-box.vn")
- Model behavior seems off (too fast, too slow, wrong style)
- Provider claims a premium model at suspiciously low price
- Before relying on a model for production work

## Pitfalls

- **Model may refuse to self-identify** — that's not proof of fakery. Some models are trained not to reveal identity.
- **One wrong trap answer ≠ fake** — even real models make errors on specific prompts. Gather multiple signals.
- **API routing may vary** — some providers load-balance across multiple underlying models. Test at different times.
- **Distilled models are NOT fake** — a legit DeepSeek distilled from a larger model is still DeepSeek. "Hàng đè tem" = fraudulently relabeled, not distilled/smaller.
- **Provider-level pattern**: if ALL models on the same provider fail the same trap question (e.g., Sally logic wrong across every single model), that's a strong provider-level red flag — they may be routing through a single weak model or stripping capabilities at the proxy layer.
- **Function calling consistently absent across all models** is a massive red flag. Even if each model claims a different identity, none being able to call tools suggests the proxy layer strips tool-calling capability from all traffic.

## Real-World Case Study: api.ai-box.vn (2026-07-29)

Provider: `api.ai-box.vn`, 15 listed models including `deepseek-v4-flash`, `deepseek-v4-pro`, `glm-5.2`, `qwen3.7-max`, etc.

### Identity testing — model claims vs reality

| Claimed Model | Real Identity (self-reported) | Verdict |
|---|---|---|
| deepseek-v4-flash | DeepSeek (cutoff 05/2025) | Suspicious — no official "v4-flash" exists |
| deepseek-v4-pro | **Claude 3.5 Sonnet (Anthropic, cutoff 04/2024)** | **FLAGRANT FAKE** |
| glm-5.2 | GLM-4 by "Z.ai" | Suspicious — Zhipu AI not "Z.ai" |
| qwen3.7-max | Qwen by Alibaba Tongyi Lab (cutoff 2026) | Likely legit, cutoff unusually recent |
| deepseek-v4 | model_not_found | Non-existent |
| kimi-k2.7 | model_not_found | Non-existent |

### Trap test results (all models)

| Test | Correct Answer | deepseek-v4-flash | deepseek-v4-pro | glm-5.2 | qwen3.7-max | qwen3.7-flash |
|---|---|---|---|---|---|---|
| Strawberry "r" count | 3 | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 |
| 9.9 vs 9.11 | 9.9 | ✅ 9.9 | ✅ 9.9 | ❓ empty | ⏱ timeout | ❓ empty |
| Sally sisters | 1 | ❌ 0 | ❌ 0 | ❌ 0 | ❌ 0 | ❌ 0 |
| Function calling | should call tool | ❌ text reply | ❌ empty | ❌ empty | ❌ text reply | ❌ text reply |

### Key findings

1. **`deepseek-v4-pro` is unquestionably Claude 3.5 Sonnet** — it literally says so when asked for identity. This is the strongest "hàng đè tem" signal possible.

2. **ALL models fail Sally logic** (all say 0, correct is 1). This is a provider-level pattern suggesting either a single weak model behind a routing layer, or all models are distilled to the same performance level.

3. **Function calling is stripped across the entire provider** — no model calls tools even when explicitly given function definitions with `tool_choice: auto`. Hermes loses all tool capability through this provider.

4. **Security implication**: If `deepseek-v4-pro` runs Claude 3.5 Sonnet but charges DeepSeek prices, the provider may be reselling Anthropic's API without a license. This affects reliability, latency, and potential data privacy.

### Recommended action
- Do not rely on this provider for production work that needs function calling
- Verify function calling capability before using any new provider for Hermes
- Cross-check model identity claims with at least 3 test prompts
