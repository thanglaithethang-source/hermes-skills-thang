---
name: complex_task_orchestrator
description: "Master Orchestrator cho mọi công việc phức tạp — phân tích yêu cầu, chia task, tạo sub-agent, chọn model và công cụ, chạy song song an toàn, hợp nhất kết quả, kiểm tra chất lượng và sửa lỗi cho đến khi đạt tiêu chí nghiệm thu."
version: 1.0.0
author: Sếp Thăng's Agent
license: MIT
metadata:
  hermes:
    tags: [orchestration, multi-agent, delegation, task-decomposition, parallel-execution, quality-gate, repair-loop]
    related_skills: [coding-engineering, hermes-agent, self-improving-agent]
---

# Complex Task Orchestrator

Master Orchestrator cho mọi công việc phức tạp. Khi người dùng giao một nhiệm vụ có nhiều đầu ra, nhiều giai đoạn phụ thuộc, cần nhiều công cụ hoặc chuyên môn khác nhau — skill này biến Hermes thành coordinator trung tâm: phân tích, chia task, tạo sub-agent, chạy song song an toàn, hợp nhất, kiểm tra và sửa lỗi cho đến khi đạt tiêu chí nghiệm thu.

## Activation

Tự kích hoạt khi nhiệm vụ có MỘT hoặc NHIỀU dấu hiệu sau:

- Có nhiều đầu ra (deliverables) khác nhau
- Có nhiều giai đoạn phụ thuộc nhau
- Cần sử dụng nhiều công cụ khác nhau
- Cần nghiên cứu rồi mới thực thi
- Cần sửa nhiều module hoặc file
- Cần nhiều chuyên môn khác nhau (backend, frontend, DevOps, v.v.)
- Có thể chia thành các nhánh độc lập
- Cần audit hoặc kiểm thử độc lập
- Có rủi ro cao nếu một agent tự làm toàn bộ
- Ước tính cần từ hai worker chuyên biệt trở lên

### KHÔNG kích hoạt orchestration nặng khi

- Task chỉ có một hành động nhỏ → thực hiện trực tiếp
- Task có thể hoàn thành bằng một tool call → gọi tool luôn
- Tạo sub-agent tốn nhiều chi phí hơn lợi ích → tự làm
- Các bước phụ thuộc hoàn toàn theo chuỗi, không thể song song → làm tuần tự

---

## Phân loại độ phức tạp

Trước khi chọn chiến lược, chấm nhiệm vụ theo ba mức.

### LEVEL 1 — SIMPLE

Đặc điểm:
- Một mục tiêu duy nhất
- Một công cụ hoặc một nhóm thao tác nhỏ
- Không cần chia sub-agent

Xử lý:
- Hermes thực hiện trực tiếp
- Vẫn phải kiểm tra kết quả trước khi báo hoàn thành
- Không tạo delegate_task

### LEVEL 2 — COMPOUND

Đặc điểm:
- Có từ 2–4 phần việc
- Có một số task độc lập
- Cần tối đa 3 sub-agent

Xử lý:
- Hermes tạo task graph đơn giản
- Chạy song song các task độc lập qua delegate_task batch
- Dùng một integrator duy nhất (có thể là Hermes tự làm)

### LEVEL 3 — COMPLEX

Đặc điểm:
- Nhiều giai đoạn
- Nhiều chuyên môn hoặc công cụ
- Có dependency, rủi ro hoặc shared state
- Cần nhiều vòng kiểm thử

Xử lý:
- Tạo execution manifest đầy đủ (xem templates/execution_manifest.yaml)
- Chia thành wave
- Chạy song song theo từng wave
- Có worker, integrator và auditor tách biệt
- Có repair loop và approval gate khi cần

---

## Quy trình chính

```
INTAKE → ANALYZE → PLAN → DECOMPOSE → ROUTE → EXECUTE → VERIFY → REPAIR → INTEGRATE → FINAL AUDIT → REPORT
```

### Bước 1 — INTAKE

Thu thập yêu cầu. Ghi lại:
- Mục tiêu tổng thể
- Deliverables kỳ vọng
- Constraints (thời gian, tài nguyên, quyền truy cập)
- Inputs có sẵn

### Bước 2 — ANALYZE

Tạo TASK CONTRACT (xem templates/task_contract.yaml). Quy tắc:
1. Chuyển mọi yêu cầu thành kết quả có thể kiểm chứng
2. KHÔNG dùng tiêu chí cảm tính: "tốt", "đẹp", "chuyên nghiệp", "hoàn hảo", "đầy đủ"
3. Nếu có tiêu chí cảm tính → chuyển thành checklist khách quan
4. Không tự tạo dữ liệu thực tế còn thiếu
5. Chỉ hỏi người dùng khi thiếu thông tin bắt buộc và không thể tiếp tục an toàn
6. Nếu dùng giả định an toàn → ghi rõ trong manifest

### Bước 3 — PLAN

Lập DEPENDENCY GRAPH. Mỗi task có schema (xem templates/execution_manifest.yaml):

```yaml
task_id: T01
title: ...
objective: ...
inputs: [...]
dependencies: [T00]
owned_resources:
  - path: server/**
    mode: write
allowed_tools: [terminal, file, web]
forbidden_actions: [rm -rf, git push --force]
acceptance_criteria:
  - "File X tồn tại và có nội dung Y"
output_schema:
  type: object
  properties: {...}
priority: HIGH
risk_level: MEDIUM
execution_mode: PARALLEL_SAFE  # SEQUENTIAL | PARALLEL_SAFE | APPROVAL_REQUIRED
assigned_role: EXECUTOR
```

Quy tắc execution_mode:
- `SEQUENTIAL`: chạy sau khi dependency hoàn thành
- `PARALLEL_SAFE`: chạy song song, KHÔNG xung đột resource
- `APPROVAL_REQUIRED`: dừng chờ người dùng duyệt trước khi thực thi

KHÔNG được đánh dấu `PARALLEL_SAFE` khi các task:
- Cùng sửa một file
- Cùng sửa database schema
- Cùng ghi vào một thư mục output
- Cùng điều khiển một ứng dụng GUI
- Cùng thay đổi shared state
- Cùng sử dụng tài nguyên không hỗ trợ concurrency
- Task sau cần output chưa hoàn thành của task trước

#### Circular dependency detection

Trước khi chạy, kiểm tra dependency graph có chu trình vòng không.
- Nếu phát hiện vòng (A → B → C → A) → báo lỗi, từ chối chạy
- Sắp xếp topological — nếu không sắp xếp được → có cycle
- Không tự ý cắt dependency để giải quyết vòng

### Bước 4 — DECOMPOSE

Chia thành WAVE. Ví dụ:
```
WAVE 0: Intake và kiểm tra môi trường
WAVE 1: Research, phân tích repository, thiết kế test
WAVE 2: Thực thi các module độc lập
WAVE 3: Hợp nhất
WAVE 4: Kiểm thử tích hợp
WAVE 5: Audit và repair
WAVE 6: Final verification
```

Chỉ bắt đầu wave tiếp theo khi tất cả dependency bắt buộc của wave đó đã PASS.

### Bước 5 — ROUTE

Chọn công cụ theo nguyên tắc: chuyên biệt nhất + ít rủi ro nhất + đủ khả năng hoàn thành.

Xem chi tiết: `references/tool_routing_guide.md`

Tóm tắt:
- Không dùng computer-use nếu có API, CLI, MCP hoặc tool trực tiếp ổn định hơn
- Không dùng browser để thao tác file local
- Dùng model nhanh/rẻ cho: phân loại, trích xuất, tóm tắt, research đơn giản
- Dùng model mạnh cho: kiến trúc, debug khó, hợp nhất, audit phức tạp
- Mọi tool có side effect phải có kiểm tra sau khi thực thi

Nếu Codex hoặc coding agent có sẵn:
- Dùng Codex làm executor chính cho task đọc repo, sửa code, chạy test, build, debug
- Hermes giữ vai trò orchestrator và auditor
- Không để Hermes tự sửa code lớn nếu coding agent chuyên biệt đang khả dụng

### Bước 6 — EXECUTE

Tạo sub-agent qua `delegate_task`. Xem chi tiết API: `references/delegate_task_api.md`

#### Cách gọi delegate_task

**Single task:**
```
delegate_task(
  goal="Xây dựng REST API cho user management",
  context="Project: FastAPI. Repo: /path/to/repo. Convention: pytest. Đọc README trước.",
  role="leaf"
)
```

**Batch (parallel, tối đa 3):**
```
delegate_task(
  tasks=[
    {goal: "Research tool A", context: "...", role: "leaf"},
    {goal: "Research tool B", context: "...", role: "leaf"},
    {goal: "Research tool C", context: "...", role: "leaf"}
  ]
)
```

#### Quy tắc tạo sub-agent

1. Mặc định tối đa 3 sub-agent chạy đồng thời (delegate_task batch cap)
2. Chỉ tăng concurrency khi: hệ thống đủ tài nguyên, task thực sự độc lập, không xung đột
3. Mặc định chỉ dùng một tầng sub-agent (max_spawn_depth=1)
4. KHÔNG để sub-agent tự tạo agent cháu trừ khi task cực lớn và cấu hình cho phép
5. Không tạo nhiều sub-agent làm cùng một việc (trừ khi: so sánh phương án, red-team, audit chéo)
6. Mỗi sub-agent phải có một nhiệm vụ chính duy nhất
7. Mỗi sub-agent chỉ nhận context cần thiết — không truyền toàn bộ lịch sử hội thoại
8. Không cho hai executor cùng quyền ghi vào một resource
9. Hermes cha giữ quyền: điều phối, phê duyệt, hợp nhất, công nhận hoàn thành

#### Vai trò sub-agent tiêu chuẩn

| Role | Trách nhiệm | Giới hạn |
|------|-------------|----------|
| PLANNER | Phân tích kiến trúc, dependency | Không thay đổi production state |
| RESEARCHER | Thu thập dữ liệu, tài liệu | Phải cung cấp nguồn và mức tin cậy |
| EXECUTOR | Tạo/sửa artifact | Chỉ tác động trong phạm vi ownership |
| TESTER | Viết/chạy kiểm thử | Không tự sửa production code |
| INTEGRATOR | Hợp nhất kết quả (duy nhất) | Xử lý conflict, kiểm thử tích hợp |
| AUDITOR | Kiểm tra độc lập | Không dựa vào tuyên bố của executor |
| REPAIRER | Sửa danh sách lỗi đã đóng băng | Không làm lại phần đã PASS |

#### Exclusive Ownership

Mỗi task ghi dữ liệu phải khai báo resource ownership:
```yaml
owned_resources:
  - path: server/**
    mode: write
  - path: database/schema.sql
    mode: read
```

Quy tắc:
1. Một resource chỉ có MỘT writer tại một thời điểm
2. Nhiều reader được phép
3. Thay đổi ngoài ownership → từ chối hoặc chuyển về Hermes
4. Phát hiện conflict → dừng task liên quan, giữ artifact gốc, giao integrator
5. Không merge trực tiếp vào production branch nếu chưa qua integration gate

### Bước 7 — VERIFY

Mỗi task chạy theo loop:
```
PLAN → EXECUTE → VERIFY → DIAGNOSE → REPAIR → VERIFY AGAIN
```

Quy tắc:
1. Sau mỗi thay đổi phải chạy kiểm tra phù hợp
2. Nếu FAIL: ghi lỗi, xác định nguyên nhân gốc, tạo repair task nhỏ nhất, chỉ sửa phạm vi liên quan
3. KHÔNG che giấu lỗi bằng: tắt test, xóa assertion, bỏ validation, dùng mock thay cho chức năng thật, hardcode kết quả
4. Không tuyên bố PASS nếu kiểm tra chưa chạy
5. Mọi kết luận PASS phải kèm bằng chứng

#### Build PASS ≠ Functional PASS

Build thành công (compile, syntax check) KHÔNG đồng nghĩa chức năng đúng.
- Sau build PASS, phải chạy functional test (luồng thực, không chỉ import check)
- Nếu không có functional test → tạo tối thiểu một luồng test
- Auditor không dừng ở build — phải kiểm tra functional behavior

#### Tool failure fallback

Khi tool chính không hoạt động:
1. Thử fallback tool (xem references/tool_routing_guide.md)
2. Nếu fallback cũng thất bại → báo BLOCKED, không bịa kết quả
3. Ghi lại tool nào fail, lỗi gì, đã thử fallback nào
4. Không tự thay thế bằng tool kém ổn định hơn nếu rủi ro cao

#### False PASS detection

Worker có thể tuyên bố PASS nhưng artifact không tồn tại hoặc sai.
- Integrator/Auditor phải kiểm tra artifact tồn tại thật (stat file, fetch URL, read content)
- Không tin tuyên bố PASS của worker nếu không có evidence tái kiểm chứng được
- Nếu phát hiện false PASS → đánh dấu FAIL, tạo repair task

### Bước 8 — REPAIR (Retry & Escalation)

Mặc định:
- Tối đa 3 repair attempt cho cùng một lỗi gốc
- Sau mỗi lần thất bại phải thay đổi chiến lược, không lặp nguyên xi

Sau 3 lần thất bại:
1. Thu nhỏ task
2. Đổi tool hoặc model
3. Giao cho agent chuyên môn khác
4. Kiểm tra lại giả định ban đầu
5. Nếu vẫn không thể tiếp tục → báo `BLOCKED` kèm bằng chứng

KHÔNG loop vô hạn.

### Bước 9 — INTEGRATE (Integration Gate)

Integration Gate — chỉ MỘT integrator được phép hợp nhất kết quả.

Integrator phải:
1. Kiểm tra artifact tồn tại
2. Kiểm tra format
3. Phát hiện conflict
4. Xác minh dependency
5. Hợp nhất theo thứ tự an toàn
6. Chạy test tích hợp
7. Kiểm tra regression
8. Ghi lại mọi thay đổi sau merge

KHÔNG tin rằng các module độc lập PASS đồng nghĩa toàn hệ thống PASS.

### Bước 10 — FINAL AUDIT

Auditor kiểm tra độc lập (xem templates/final_audit.yaml):
- Tất cả acceptance criteria
- Tất cả deliverable
- Tính đầy đủ, nhất quán
- Lỗi regression
- Security/privacy nếu liên quan
- Placeholder, TODO, mock không được phép
- File thừa, artifact thiếu
- Test và build
- Hướng dẫn sử dụng
- Khả năng hoàn tác

Khi audit FAIL:
1. Đóng băng fail_list
2. Tạo repair task chỉ cho lỗi trong danh sách
3. Không sửa lại phần đã PASS trừ khi bị ảnh hưởng bắt buộc
4. Chạy audit lại sau repair

### Bước 11 — REPORT

Báo cáo cuối (xem templates/final_report.md). Chỉ báo hoàn thành khi:
- Mọi deliverable tồn tại
- Mọi acceptance criterion bắt buộc PASS
- Không còn blocker nghiêm trọng
- Integration test PASS
- Final audit PASS
- Có bằng chứng kiểm tra
- Có báo cáo thay đổi
- Có hướng dẫn sử dụng nếu cần

KHÔNG dùng: "Có vẻ hoạt động", "Chắc là đã xong", "Mọi thứ ổn".

---

## Approval Gate

Phải yêu cầu người dùng duyệt trước khi:
- Xóa dữ liệu
- Ghi đè artifact quan trọng
- Thay đổi production
- Gửi email, đăng bài, xuất bản công khai
- Thực hiện thanh toán
- Thay đổi quyền truy cập
- Đổi kiến trúc lớn ngoài phạm vi
- Thực hiện hành động không thể hoàn tác
- Dùng secret hoặc tài khoản mà người dùng chưa cho phép

Các task chỉ đọc, phân tích, chạy test an toàn không cần approval riêng nếu người dùng đã giao nhiệm vụ.

Dùng `clarify` tool để yêu cầu phê duyệt khi cần.

---

## Context Management

1. Chỉ gửi context cần thiết cho từng sub-agent
2. Dùng file manifest hoặc artifact trung gian thay vì nhồi toàn bộ vào prompt
3. Tóm tắt kết quả worker theo schema cố định
4. Lưu: task graph, trạng thái từng task, artifact path, kết quả test, lỗi đang mở
5. Không đưa suy luận dài dòng của sub-agent về context chính
6. Chỉ đưa về: kết quả, bằng chứng, quyết định, rủi ro, blocker

### Context loss prevention

Khi context dài, acceptance criteria quan trọng có thể bị mất hoặc bỏ sót:
- Lặp acceptance criteria ở cuối context (bookend pattern)
- Đặt constraints quan trọng ở đầu VÀ cuối context truyền cho sub-agent
- Không dựa vào sub-agent tự suy đoán dữ liệu thiếu
- Nếu context quá dài → tóm tắt theo schema, giữ nguyên acceptance criteria nguyên bản
- Final audit phải kiểm tra đúng tiêu chí gốc, không phải tiêu chí sub-agent tự diễn giải

---

## Output Schema của sub-agent

Bắt buộc mọi sub-agent trả về:

```yaml
status: PASS | FAIL | BLOCKED
task_id: T01
summary: "Tóm tắt ngắn gọn kết quả"
artifacts_created:
  - path: /path/to/file
    type: source | config | test | doc
files_changed:
  - path: /path/to/file
    change: created | modified | deleted
tools_used:
  - terminal
  - write_file
checks_performed:
  - name: "pytest tests/"
    result: PASS
    evidence: "5 passed, 0 failed"
evidence:
  - "exit_code: 0"
  - "file exists: /path/to/output.txt"
open_issues: []
risks: []
recommended_next_action: "Proceed to integration"
```

Nếu agent không trả đúng schema → Hermes chuẩn hóa lại trước khi tiếp tục.

---

## Checkpoint báo cáo cho người dùng

Trong quá trình chạy, chỉ báo các checkpoint quan trọng:
- Đã hoàn thành phân tích
- Đã tạo task graph
- Wave nào đang chạy
- Blocker quan trọng
- Kết quả audit

Không spam log kỹ thuật.

---

## Pitfalls

1. **Over-delegation**: Tạo sub-agent cho task đơn giản tốn nhiều thời gian hơn tự làm. Luôn đánh giá cost/benefit trước khi delegate.
2. **Context bloat**: Truyền toàn bộ lịch sử hội thoại cho sub-agent → phình token, giảm chất lượng. Chỉ truyền context cần thiết.
3. **False PASS**: Sub-agent tuyên bố PASS nhưng không kèm bằng chứng → yêu cầu evidence, không tin lời nói.
4. **Silent conflict**: Hai executor cùng ghi một file → corruption. Luôn kiểm owned_resources trước khi chạy song song.
5. **Infinite retry**: Loop sửa lỗi vô tận → giới hạn 3 attempt, escalate sau đó.
6. **Skipping integration**: Module PASS độc lập ≠ hệ thống PASS. Luôn chạy integration test.
7. **delegate_task không bền vững**: Background child bị mất nếu parent process exit. Cho work cần bền vững → dùng cronjob hoặc terminal(background=true).
8. **Leaf agent không dùng được clarify/memory/execute_code**: Khi giao task cho leaf, không yêu cầu nó hỏi user hay dùng memory. Tự xử lý ở parent.

---

## Completion Criteria

- Skill được tạo đúng cấu trúc Hermes (YAML frontmatter + markdown body + linked files)
- Hermes phát hiện skill qua `hermes skills list`
- Phân biệt được task đơn giản và phức tạp
- Tạo được task graph
- Gọi được sub-agent qua delegate_task
- Giới hạn concurrency (mặc định 3)
- Ngăn xung đột shared resource (owned_resources)
- Hỗ trợ thực thi song song an toàn
- Có integration gate
- Có independent audit
- Có repair loop giới hạn (3 attempt)
- Có approval gate cho hành động nguy hiểm
