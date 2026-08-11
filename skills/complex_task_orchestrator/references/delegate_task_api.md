# delegate_task API Reference

## Tổng quan

`delegate_task` là cơ chế tạo sub-agent trong Hermes. Mỗi sub-agent có:
- Conversation riêng (isolated context)
- Terminal session riêng (working directory và state riêng)
- Toolset có thể giới hạn

Chỉ kết quả tóm tắt (summary) được trả về parent. Intermediate tool results KHÔNG vào context parent.

## Hai chế độ

### 1. Single task
```
delegate_task(
  goal="Xây dựng REST API cho user management",
  context="Project: FastAPI. Repo: /path/to/repo. Convention: pytest.",
  role="leaf"
)
```

### 2. Batch (parallel, tối đa 3)
```
delegate_task(
  tasks=[
    {goal: "Research tool A", context: "...", role: "leaf"},
    {goal: "Research tool B", context: "...", role: "leaf"},
    {goal: "Research tool C", context: "...", role: "leaf"}
  ]
)
```
Batch trả về một handle, chạy N sub-agent đồng thời, trả kết quả sau khi TẤT CẢ hoàn thành.

## Background mode

Top-level single và batch delegation tự động chạy background. Parent tiếp tục làm việc khác. Kết quả re-enter conversation khi hoàn thành.

KHÔNG dùng `background=true` — đã deprecated, tự động background.

## Roles

| Role | Đặc điểm |
|------|----------|
| `leaf` (default) | Focused worker, KHÔNG delegate tiếp. Không dùng được: delegate_task, clarify, memory, send_message, execute_code |
| `orchestrator` | Có thể spawn workers riêng qua delegate_task. Bounded bởi max_spawn_depth=1. Vẫn không dùng được clarify, memory, send_message, execute_code |

## Giới hạn

- `max_concurrent_children`: mặc định 3 (cấu hình trong config.yaml: delegation.max_concurrent_children)
- `max_spawn_depth`: mặc định 1 (không cho nested delegation trừ khi cấu hình)
- Sub-agent inherit parent model + fallback chain (không chọn model per-call)
- Background delegation KHÔNG bền vững: nếu parent process exit → child bị mất

## Context truyền cho sub-agent

Sub-agent KHÔNG có memory của parent conversation. Truyền mọi thông tin cần thiết qua `context` field:
- File paths
- Error messages
- Project structure
- Constraints
- Output schema yêu cầu

Nếu user viết ngôn ngữ không phải tiếng Anh hoặc yêu cầu output ngôn ngữ/tone/style cụ thể → ghi trong context.

## Live transcripts

Mỗi sub-agent có live transcript log file (cache/delegation/live/<delegation_id>/). Có thể read hoặc `tail -f` để xem sub-agent đang làm gì.

## Verification sau khi nhận kết quả

Sub-agent summary là SELF-REPORT, không phải fact. Yêu cầu:
- Nếu sub-agent tuyên bố "uploaded successfully" hoặc "file written" → verify:
  - Fetch URL
  - Stat file
  - Read back content
- Cho operations có side-effects (HTTP POST/PUT, remote writes, file creation) → require verifiable handle

## Khi nào KHÔNG dùng delegate_task

- Mechanical multi-step work không cần reasoning → dùng execute_code
- Single tool call → gọi tool trực tiếp
- Task cần user interaction → sub-agent không dùng được clarify
- Durable long-running work → dùng cronjob hoặc terminal(background=true, notify_on_complete=true)

## Config

```yaml
# config.yaml
delegation:
  model: ""                    # override model cho sub-agents
  provider: ""                 # override provider
  max_iterations: 50           # max turns per sub-agent
  max_concurrent_children: 3   # max parallel sub-agents
  max_spawn_depth: 1           # nesting depth
  reasoning_effort: ""         # reasoning level
```
