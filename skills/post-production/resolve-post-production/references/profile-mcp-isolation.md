# Profile-based MCP Isolation

Kỹ thuật giữ default profile gọn nhẹ (~20-25k token) trong khi vẫn có full MCP Resolve khi cần.

## Vấn đề

Davinci Resolve MCP server export 34-38 tools với schema rất dài, chiếm ~15-20k tokens. Nếu để trong default profile, mỗi phiên khởi động tốn 40-45k tokens — lãng phí khi không làm hậu kỳ.

## Giải pháp: Dual Profile

| Profile | MCP | Token | Dùng khi |
|---------|-----|-------|----------|
| `default` | Không | ~20-25k | Code, chat, việc hàng ngày |
| `resolve` | 34 tools | ~40-45k | Hậu kỳ video |

## Setup

```bash
# Tạo profile resolve clone từ default
hermes profile create resolve --clone-from default

# Quay về default, xóa MCP
hermes mcp remove davinci-resolve
```

## Cách dùng

```bash
# Hàng ngày
hermes

# Hậu kỳ
hermes -p resolve

# Hoặc alias (sau khi thêm ~/.local/bin vào PATH)
resolve
```

## Agent tự động chuyển profile

Khi Sếp yêu cầu hậu kỳ từ default profile, agent spawn subprocess:

```bash
hermes -p resolve chat -q "nhiệm vụ hậu kỳ..."
```

Không bắt Sếp tự thoát ra gõ `-p resolve`.
