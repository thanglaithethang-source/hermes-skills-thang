# Raw WebSocket Implementation for Chrome Bridge

## Why not `websockets` library

Python's `websockets` library (tested on Windows, Python 3.11) fails to communicate with Chrome extension WebSocket connections. Root cause: Chrome sends `Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits` in the upgrade request. The `websockets` library accepts this extension but the compressed frames are not decoded correctly, resulting in silent message loss — extension connects, hello is never received, commands never get responses.

## Solution: Raw asyncio TCP

Implement WebSocket protocol manually using Python's built-in `asyncio`:

### Handshake (server side)

```python
import asyncio, hashlib, base64, struct

MAGIC = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def accept_key(key: str) -> str:
    return base64.b64encode(
        hashlib.sha1((key + MAGIC.decode()).encode()).digest()
    ).decode()

# Read HTTP upgrade request
data = await reader.readuntil(b'\r\n\r\n')

# Extract Sec-WebSocket-Key
key = None
for line in data.decode('latin-1').split('\r\n'):
    if line.lower().startswith('sec-websocket-key:'):
        key = line.split(':', 1)[1].strip()
        break

# Send upgrade response WITHOUT permessage-deflate
response = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    f"Sec-WebSocket-Accept: {accept_key(key)}\r\n"
    "\r\n"  # NOTE: no Sec-WebSocket-Extensions
)
writer.write(response.encode())
await writer.drain()
```

### Read frame (with fragmentation reassembly)

Chrome MAY fragment large WebSocket messages (screenshots, big DOM payloads). `read_frame` MUST reassemble continuation frames (opcode 0x0). Without this, fragmented responses are silently dropped → TCP client timeout 30s.

```python
async def ws_read_frame(reader):
    """Returns (opcode, payload) — reassembles fragmented messages."""
    header = await reader.readexactly(2)
    opcode = header[0] & 0x0F
    fin = (header[0] & 0x80) != 0
    masked = (header[1] & 0x80) != 0
    length = header[1] & 0x7F
    
    if length == 126:
        length = struct.unpack('>H', await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack('>Q', await reader.readexactly(8))[0]
    
    mask_key = await reader.readexactly(4) if masked else None
    payload = await reader.readexactly(length)
    
    if mask_key:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    
    # Reassemble continuation frames (opcode 0x0)
    while not fin:
        ch = await reader.readexactly(2)
        cfin = (ch[0] & 0x80) != 0
        cmasked = (ch[1] & 0x80) != 0
        clen = ch[1] & 0x7F
        if clen == 126: clen = struct.unpack('>H', await reader.readexactly(2))[0]
        elif clen == 127: clen = struct.unpack('>Q', await reader.readexactly(8))[0]
        cmk = await reader.readexactly(4) if cmasked else None
        cp = await reader.readexactly(clen)
        if cmk: cp = bytes(b ^ cmk[i%4] for i,b in enumerate(cp))
        payload += cp
        fin = cfin
    
    return opcode, payload
```

### Send frame

```python
async def ws_send_frame(writer, payload: bytes, op: int = 0x1):
    """op=0x1 text, 0x9 ping, 0xA pong, 0x8 close"""
    frame = bytes([0x80 | op])
    length = len(payload)
    if length < 126:
        frame += bytes([length])
    elif length < 65536:
        frame += bytes([126]) + struct.pack('>H', length)
    else:
        frame += bytes([127]) + struct.pack('>Q', length)
    frame += payload
    writer.write(frame)
    await writer.drain()
```

## Chrome extension WebSocket handshake (for reference)

```
GET / HTTP/1.1
Host: 127.0.0.1:19978
Connection: Upgrade
Upgrade: websocket
Origin: chrome-extension://klghdnedebacaciemlnhchdghkoodgke
Sec-WebSocket-Version: 13
Sec-WebSocket-Key: <base64>
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
```

Key insight: the extension ID is in the `Origin` header. Do NOT accept `permessage-deflate` in the response.

## Concurrent write protection — DO NOT use asyncio.Lock

**PITFALL:** `asyncio.Lock()` causes DEADLOCK on Windows when used with `async with` pattern across multiple connection handlers (WS + TCP). Bridge server v2 failed completely due to this. asyncio is single-threaded cooperative multitasking — `writer.write()` + `await writer.drain()` is atomic in practice (no `await` between write and drain to yield).

**CORRECT:** No lock needed. If synchronization is truly required, use `asyncio.Queue` instead.

## Keepalive ping handling

Extension gửi text-level `{type: 'ping'}` mỗi 20s. **Không respond bằng text pong** — sẽ tạo noise cycle. Chrome's WebSocket protocol ping/pong (opcode 0x9/0xA) đã handle keepalive ở transport layer. Xử lý trong server:

```python
elif msg.get('type') == 'ping':
    pass  # Ignore — protocol-level ping/pong handles keepalive
```
