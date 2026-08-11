---
name: self-improving-agent
description: "AI tự cải thiện liên tục — ghi nhớ lỗi, học từ sửa sai của Sếp, không bao giờ lặp lại cùng một lỗi. Tự động沉淀 best practices thành tri thức dài hạn. Source: CocoLoop pskoett/Self-Improving Agent (419k stars)."
version: 1.0.0
---

# Self-Improving Agent

## Activation
Khi: Sếp sửa sai, em phát hiện mình làm sai, một workflow hoạt động đặc biệt tốt, Sếp yêu cầu tính năng mới, hoặc trước task phức tạp cần audit kinh nghiệm cũ.

## Not for
- Ghi task progress hàng ngày (dùng `session_search`)
- Log kỹ thuật chi tiết (dùng file log riêng)
- Thay thế `skill_manage` — learnings quan trọng mới promote lên skill

## Cách dùng

### 1. Ghi nhận lỗi (ERRORS)
Khi Sếp sửa em hoặc em phát hiện mình làm sai:
- Ghi vào memory với format: `[ERROR] <ngữ cảnh> | root: <nguyên nhân gốc> | fix: <cách sửa đúng>`
- Dùng `memory` tool, target="memory"
- Mỗi entry ≤200 chars

### 2. Ghi nhận best practice (LEARNINGS)
Khi một approach hoạt động tốt:
- Format: `[LEARNING] <trigger> | workflow: <các bước> | tools: <công cụ> | result: <kết quả>`
- Mỗi learning phải có evidence (file, exit code, screenshot path)

### 3. Feature Requests
Khi Sếp yêu cầu cải tiến:
- Format: `[FEATURE] <mô tả> | priority: low/med/high | status: requested`

### 4. Self-Audit (mỗi session)
Trước task phức tạp: `session_search(query="[ERROR] <từ khóa liên quan>")` để kiểm tra lỗi cũ, tránh lặp lại.

## Key Pitfalls

1. **Memory đầy (2,200 char limit)**: Mỗi ERROR/LEARNING ≤200 chars. Nếu đầy, consolidate entries cũ bằng `memory operations` batch.

2. **Không ghi task progress vào memory**: Memory là tri thức dài hạn, không phải TODO list. Task progress → `session_search` hoặc `todo` tool.

3. **LEARNINGS không có evidence thì vô giá trị**: Luôn kèm bằng chứng (exit code 0, file path, screenshot). "Có vẻ hoạt động" không phải learning.

4. **Spam memory với lỗi trivial**: Chỉ ghi lỗi lặp lại hoặc gây hậu quả. Lỗi một lần do typo → không cần ghi.

## Completion Criteria
- Sau mỗi lần Sếp sửa: ERROR đã được ghi vào memory (verify: memory có dòng `[ERROR]` mới)
- Trước task phức tạp: đã audit memory/session_search cho lỗi liên quan (verify: có output từ session_search)
- LEARNINGS có evidence rõ ràng (verify: kèm exit code/file path/screenshot)
- Memory ≤90% capacity sau mỗi lần ghi (verify: memory tool báo usage %)
