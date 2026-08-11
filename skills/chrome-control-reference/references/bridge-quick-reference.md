# Bridge Quick Reference — Verified 2026-07-29

## Project path

```
C:\Users\thang\Downloads\_projects\hermes-chrome-extension\
```

## Quick start (đã test PASS)

```bash
cd C:\Users\thang\Downloads\_projects\hermes-chrome-extension

# 1. Kill bridge cũ + free ports
for pid in $(netstat -ano | grep -E "19978|19979" | awk '{print $NF}' | sort -u); do
  [ "$pid" != "0" ] && taskkill //F //PID $pid 2>/dev/null
done
sleep 3

# 2. Start bridge server
python -B hermes_bridge_server.py &

# 3. Đợi "[WS] Extension connected" trong log

# 4. Verify
python -B chrome_send.py ping
python -B chrome_send.py list_tabs
python -B chrome_send.py get_current_tab
```

## Verified commands (PASS 2026-07-29)

| Command | Result |
|---------|--------|
| `ping` | `{"type": "pong", "timestamp": ...}` |
| `list_tabs` | 2 tabs: API AI BOX (142069444), ChatGPT (142069452) |
| `get_current_tab` | API AI BOX tab active |
| `get_text` with `selector: 'title'` | "API AI BOX" |

## Service worker lifecycle

Extension connect/disconnect pattern observed:
```
[WS] Extension connected
[WS] Hermes Bridge v1.0.0    ← connected OK
[WS] Extension disconnected   ← Chrome kills SW sau vài giây
Exception: [WinError 10054]   ← connection reset
[WS] Extension connected      ← auto-reconnect
```

**Command timeout khi:** extension đang disconnected → TCP chờ 30s → timeout. Giải pháp: đợi `[WS] Extension connected` rồi chạy ngay.

## Python one-shot pattern (không cần import module)

```python
import socket, json

def bridge_cmd(cmd_dict):
    """Gửi command, nhận response. Mở/đóng socket mỗi lần."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(35)
    sock.connect(('127.0.0.1', 19979))
    sock.sendall((json.dumps(cmd_dict) + '\n').encode())
    data = b''
    while True:
        try:
            chunk = sock.recv(65536)
            if not chunk: break
            data += chunk
            if b'\n' in data: break
        except socket.timeout: break
    sock.close()
    return json.loads(data.decode().strip())

# Dùng
r = bridge_cmd({'type': 'ping', 'requestId': 'p1'})
r = bridge_cmd({'type': 'list_tabs', 'requestId': 't1'})
r = bridge_cmd({'type': 'execute_js', 'tabId': 123, 'code': 'document.title', 'requestId': 'e1'})
```
