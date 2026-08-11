# Tool Routing Guide

## Nguyên tắc chính

```
Công cụ chuyên biệt nhất + ít rủi ro nhất + đủ khả năng hoàn thành task
```

## Thứ tự ưu tiên tool

1. Official API → 2. CLI → 3. Script → 4. SDK/Automation → 5. Accessibility tree → 6. DOM/UI element → 7. Computer vision → 8. Fixed coordinates (last resort)

## Ma trận chọn tool

| Nhu cầu | Tool ưu tiên | Fallback | KHÔNG dùng |
|---------|-------------|----------|------------|
| Đọc/ghi file local | read_file, write_file, patch | terminal (cat/sed) | browser |
| Tìm file | search_files | terminal (find/rg) | browser |
| Chạy command | terminal | execute_code | browser |
| Script phức tạp | execute_code | terminal script | delegate_task |
| Web search | web_search | browser | computer_use |
| Web scraping | web_extract | browser | computer_use |
| Tương tác web app | browser tools | computer_use | — |
| Desktop automation | computer_use | browser (nếu web) | — |
| Tạo sub-agent | delegate_task | terminal (hermes chat -q) | — |
| Code repo | codex/claude-code/opencode | delegate_task | computer_use |
| Image analysis | vision_analyze | browser_vision | — |
| Image generation | image_gen tool | API call | browser |
| Persistent memory | memory tool | session_search | delegate_task |
| Lên lịch | cronjob | terminal (crontab) | — |

## Model routing

### Dùng model nhanh/rẻ cho:
- Phân loại (classification)
- Trích xuất (extraction)
- Tóm tắt (summarization)
- Research đơn giản
- Format conversion

### Dùng model mạnh cho:
- Kiến trúc hệ thống
- Debug khó
- Hợp nhất kết quả (integration)
- Audit phức tạp
- Quyết định quan trọng

### Trong Hermes
- Sub-agent inherit parent model (không chọn per-call)
- Để đổi model cho sub-agent: cấu hình delegation.model trong config.yaml
- Hoặc dùng delegate_task với context chỉ định "use model X" (không đảm bảo)

## Tool selection record

Trước khi giao task, ghi lại:
```yaml
required_capability: "Read and modify Python source code"
selected_tool: "codex"
selection_reason: "Coding agent chuyên biệt, có quyền truy cập repo, chạy test được"
fallback_tool: "delegate_task với role=leaf, toolsets=[terminal, file]"
permissions: "read+write repo directory"
side_effects: "modifies source files, runs tests"
verification_method: "git diff, pytest exit code"
```

## Quy tắc side-effect

Mọi tool có side effect phải có kiểm tra sau khi thực thi:
- `write_file` → `read_file` để verify content
- `terminal` command → check exit_code
- `delegate_task` → verify artifacts tồn tại
- `browser_click` → `browser_snapshot` để verify state change
- `patch` → auto syntax check (built-in)

## Khi nào dùng coding agent (Codex/Claude Code/OpenCode)

Nếu có sẵn:
- Dùng làm EXECUTOR chính cho: đọc repo, sửa code, chạy test, build, debug
- Hermes giữ vai trò orchestrator + auditor
- Không để Hermes tự sửa code lớn nếu coding agent đang khả dụng

Khi KHÔNG có:
- Dùng delegate_task với role=leaf, toolsets=[terminal, file]
- Hoặc tự làm nếu task nhỏ

## Pitfalls

1. **Dùng browser cho file local**: Chậm, không cần thiết, dễ lỗi. Dùng read_file/write_file.
2. **Dùng computer_use khi có API**: Overkill, chậm, không ổn định. Tìm API/CLI trước.
3. **Dùng model mạnh cho mọi task**: Tốn token, chậm. Phân loại task trước.
4. **Quên verify sau side-effect**: Tuyên bố PASS nhưng không kiểm tra. Luôn verify.
5. **delegate_task cho task đơn giản**: Overhead lớn hơn lợi ích. Tự làm.
