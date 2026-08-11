# Computer Automation — Operating Rules

## Ưu tiên
1. API / CLI / Script
2. GUI (chỉ khi không có phương án ổn định hơn)

## GUI Automation Rules
- Phải có screenshot hoặc state verification sau mỗi thao tác.
- Không phụ thuộc hoàn toàn vào tọa độ màn hình.
- Ưu tiên UI element, accessibility tree, DOM, hoặc API.
- Có retry giới hạn và phương án phục hồi.
- Không lặp vô hạn.
- Sau mỗi nhóm thao tác phải chụp hoặc đọc lại trạng thái.
- Khi thao tác sai: dừng và khôi phục trước khi tiếp tục.

## Quan sát trước thao tác
- Nhận diện đúng cửa sổ, ứng dụng và trạng thái focus.
- Không click dựa hoàn toàn vào tọa độ cố định.
- Ghi log các hành động quan trọng.

## Windows Chrome_WidgetWin_1 (cua-driver)

Chrome/Chromium windows dùng class `Chrome_WidgetWin_1`, có các giới hạn với cua-driver background mode:

| Hành động | Background | Ghi chú |
|---|---|---|
| `type` (gõ text) | ✅ OK | Qua PostMessage, verified UIA read-back |
| `key` (phím đơn: return, pagedown, escape...) | ✅ OK | Single key press works |
| `key` (tổ hợp: ctrl+a, ctrl+v...) | ❌ | Cần foreground delivery |
| `click` / `scroll` | ❌ | Chrome_WidgetWin_1 không hỗ trợ mouse background |
| `scroll` foreground | ❌ | Có thể không được cua-driver build hỗ trợ |

**Chiến thuật khi cần tương tác Chrome:**
1. Navigate: dùng `type` vào address bar + `key=return` (works)
2. Scroll: dùng `key=pagedown` / `key=pageup` (works, nhưng cẩn thận focus tab)
3. Copy nội dung: không dùng được ctrl+a/ctrl+c trong background → dùng AX tree mode capture để trích xuất text từ accessibility tree
4. Hermes Bridge extension: cài trong Chrome, kết nối qua WebSocket đến Hermes Desktop app (port 19978). Desktop app phải đang chạy thì bridge mới hoạt động. Extension cho phép Navigate, Click, Screenshot, Get DOM, Run JS, List Tabs, Type, Download từ xa qua WebSocket.
