# DaVinci Resolve — Operating Rules

## Scope
Resolve chỉ dùng cho hậu kỳ và dựng video. Raw video đã có sẵn. Không giả định Resolve tạo raw video.

## Phạm vi công việc
- Cut, assemble, transition
- Caption
- Sound design
- Color grading
- Fusion, effects
- QC và export

## Yêu cầu
- Blueprint phải đủ chi tiết để agent thực thi, không dùng chỉ dẫn mơ hồ.
- Mỗi thay đổi timeline phải được audit bằng:
  - Timeline state
  - Frame preview
  - Marker
  - Duration
  - Output render

## Tools ưu tiên
- Resolve API để tạo project và timeline
- GUI chỉ dùng cho Fusion node chưa được API hỗ trợ

## Bằng chứng bắt buộc
- Timeline tồn tại
- Clip đúng thứ tự và thời lượng
- Fusion/effect thực sự nằm trong composition
- Audio không clipping
- Caption không tràn khung
- File render mở và phát được

## Profile Isolation

MCP Resolve (34 tools) ngốn ~15-20k tokens — để riêng trong profile `resolve`, không để trong default.

- Default profile: không MCP → token thấp cho công việc hàng ngày
- Resolve profile: `hermes -p resolve` → đầy đủ tools khi làm hậu kỳ
- Agent tự spawn `hermes -p resolve chat -q "..."` khi Sếp yêu cầu hậu kỳ từ default

## Gate Bắt Buộc Trước Render

⛔ TUYỆT ĐỐI CẤM tự render khi chưa có duyệt của Sếp. Sau khi hoàn thành timeline và QC, agent phải dừng lại, báo cáo trạng thái, và hỏi Sếp duyệt timeline. Chỉ render sau khi Sếp xác nhận.
