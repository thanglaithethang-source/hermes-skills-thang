# Complex Task Orchestrator

Master Orchestrator skill cho Hermes Agent. Biến Hermes thành coordinator trung tâm cho mọi công việc phức tạp: phân tích, chia task, tạo sub-agent, chạy song song an toàn, hợp nhất, kiểm tra và sửa lỗi.

## Kích hoạt

Skill tự kích hoạt khi nhiệm vụ có dấu hiệu phức tạp (nhiều đầu ra, nhiều giai đoạn, cần nhiều công cụ/chuyên môn). Tải thủ công:

```
/skill complex_task_orchestrator
```

Hoặc qua CLI:

```
hermes -s complex_task_orchestrator
```

## Cấu trúc skill

```
complex_task_orchestrator/
├── SKILL.md                              # File chính — toàn bộ logic orchestration
├── README.md                             # File này
├── templates/
│   ├── task_contract.yaml                # Template hợp đồng task
│   ├── execution_manifest.yaml            # Template manifest thực thi (task graph, waves, ownership)
│   ├── subagent_assignment.yaml           # Template giao việc cho sub-agent
│   ├── final_audit.yaml                  # Template audit cuối
│   └── final_report.md                   # Template báo cáo cuối
├── references/
│   ├── delegate_task_api.md              # Tham chiếu API delegate_task
│   └── tool_routing_guide.md            # Hướng dẫn chọn công cụ
└── scripts/
    ├── validate_orchestrator.py          # Script kiểm thử cấu trúc skill
    └── test_orchestrator.py              # 15 test scenarios
```

## Cách sử dụng

### Tự động

Khi Sếp giao nhiệm vụ phức tạp, Hermes tự đánh giá độ phức tạp (LEVEL 1/2/3) và áp dụng chiến lược tương ứng.

### Thủ công

Tải skill rồi giao việc:
```
/skill complex_task_orchestrator
```
Sau đó mô tả nhiệm vụ. Hermes sẽ:
1. Phân tích yêu cầu → tạo TASK CONTRACT
2. Lập DEPENDENCY GRAPH → chia WAVE
3. Chọn tool và model cho từng task
4. Tạo sub-agent qua delegate_task (batch tối đa 3)
5. Chạy song song theo wave
6. Verify từng task → repair nếu FAIL
7. Hợp nhất → integration test
8. Final audit độc lập
9. Báo cáo cuối

## Phân loại độ phức tạp

| Level | Đặc điểm | Chiến lược |
|-------|----------|------------|
| LEVEL 1 | Một mục tiêu, một tool | Hermes tự làm trực tiếp |
| LEVEL 2 | 2–4 phần việc, có task độc lập | Task graph đơn giản, tối đa 3 sub-agent |
| LEVEL 3 | Nhiều giai đoạn, dependency, rủi ro | Execution manifest đầy đủ, wave, integrator, auditor |

## Vai trò sub-agent

| Role | Trách nhiệm |
|------|-------------|
| PLANNER | Phân tích kiến trúc, dependency |
| RESEARCHER | Thu thập dữ liệu, tài liệu |
| EXECUTOR | Tạo/sửa artifact |
| TESTER | Viết/chạy kiểm thử |
| INTEGRATOR | Hợp nhất kết quả (duy nhất) |
| AUDITOR | Kiểm tra độc lập |
| REPAIRER | Sửa danh sách lỗi đã đóng băng |

## Kiểm thử

Chạy validator:
```bash
python "C:/Users/thang/AppData/Local/hermes/skills/complex_task_orchestrator/scripts/validate_orchestrator.py"
```

## Gỡ cài đặt / Rollback

1. Xóa thư mục skill:
```bash
rm -rf "C:/Users/thang/AppData/Local/hermes/skills/complex_task_orchestrator"
```

2. Reload skills:
```
/reload-skills
```

3. Backup cũ tại:
```
C:/Users/thang/AppData/Local/hermes/skills/.curator_backups/pre_orchestrator_20260723_223436/
```

## Giới hạn

- delegate_task batch tối đa 3 sub-agent đồng thời (cấu hình được trong config.yaml)
- max_spawn_depth=1: leaf agent không delegate tiếp
- Background delegation không bền vững: mất nếu parent process exit
- Leaf agent không dùng được: delegate_task, clarify, memory, send_message, execute_code
- Sub-agent inherit parent model (không chọn per-call)
