---
name: ontology-knowledge-graph
description: "Knowledge graph có cấu trúc cho AI Agent — lưu trữ entities, quan hệ, constraints. Giúp Hermes duy trì tri thức dài hạn về dự án, công cụ, workflow mà không bị mất giữa các session. Source: CocoLoop ontology (174k stars)."
version: 1.0.0
---

# Ontology — Structured Knowledge Graph

## Activation
Khi: bắt đầu dự án mới (cần map tools/configs), cài công cụ mới (cần ghi nhớ config), hoàn thành workflow (cần cập nhật tri thức), hoặc trước task phức tạp (cần tra cứu entity liên quan).

## Not for
- Ghi task progress (dùng `todo` tool)
- Log hội thoại (dùng `session_search`)
- Thay thế `skill_manage` (entity đủ quan trọng → promote lên skill)
- Thay thế `memory` thông thường (ontology là structured, memory là flat notes)

## Cấu trúc Entity

Mỗi entity lưu trong memory với format:  
`[ENTITY] id:<slug> | type:<type> | label:<tên> | desc:<mô tả> | props:<json> | rels:<id1,id2,...> | updated:<ISO>`

Trường bắt buộc: `id`, `type`, `label`. Còn lại tùy chọn.

## Entity Types cho Sếp

| Type | Dùng cho | Ví dụ |
|---|---|---|
| `project` | Dự án đang làm | human-evolution, capcut-video |
| `tool` | Công cụ/config | davinci-resolve, capcut-cli, ffmpeg |
| `workflow` | Quy trình verified | resolve-sop-11-steps, disk-cleanup |
| `config` | Cấu hình hệ thống | hermes-home, paths, env-vars |
| `skill` | Skill đã cài | self-improving-agent, multi-search |
| `contact` | Người/platform | telegram-bot, discord-channel |

## Thao tác CRUD

### Create
```
memory(target="memory", action="add", 
  content="[ENTITY] id:resolve-api | type:tool | label:DaVinci Resolve API | desc:Python API tại D:/davinci | props:{python:3.10} | updated:2026-07-16")
```

### Read (tìm entity)
- Load toàn bộ memory → filter dòng bắt đầu bằng `[ENTITY]`
- Tìm theo type: grep `[ENTITY].*type:tool`
- Tìm theo id: grep `id:resolve-api`

### Update
```
memory(target="memory", action="replace",
  old_text="[ENTITY] id:resolve-api |",
  content="[ENTITY] id:resolve-api | type:tool | label:DaVinci Resolve API | props:{python:3.10,path:D:/davinci} | updated:2026-07-16")
```

### Delete
```
memory(target="memory", action="remove",
  old_text="[ENTITY] id:resolve-api")
```

## Quy tắc

- Mỗi entity ≤250 chars (ngắn hơn memory thường vì có cấu trúc)
- Luôn cập nhật `updated` khi thay đổi
- Entity dùng hàng ngày → promote lên `skill_manage`
- Trước task mới → load memory, filter `[ENTITY]` liên quan
- Sau task → cập nhật entity bị ảnh hưởng

## Key Pitfalls

1. **Memory 2,200 char limit**: Mỗi entity ≤250 chars. Khi đầy, consolidate entity cũ hoặc promote lên skill.

2. **session_search không tìm được entity**: `session_search` tìm trong SESSION DB (lịch sử hội thoại), không phải memory. Entity nằm trong `memory` tool.

3. **Entity quá chi tiết → phản tác dụng**: Chỉ lưu thông tin cần truy vấn lại. Không lưu code, log, output.

4. **Không duplicate với memory thường**: Memory flat notes cho facts ngắn. Entity cho structured data có quan hệ.

## Completion Criteria
- Entity mới được tạo sau khi cài tool/bắt đầu dự án (verify: memory có dòng `[ENTITY] id:<slug>` mới)
- Entity được cập nhật sau khi workflow thay đổi (verify: `updated` timestamp mới hơn)
- Entity cũ được cleanup khi không còn dùng (verify: không còn dòng `[ENTITY]` cho tool đã gỡ)
- Có thể tìm entity bằng id hoặc type: load memory → grep đúng entity
