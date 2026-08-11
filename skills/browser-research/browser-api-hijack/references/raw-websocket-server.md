# WebSocket bug: `websockets` library vs Chrome Extension

## Problem

Python `websockets` library (pip install websockets) fails to communicate with Chrome extension WebSocket connections. Extension connects successfully but no messages are received by the Python server.

## Root Cause

Chrome sends `Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits` in the upgrade request. The `websockets` library may accept this extension but fails to properly handle the compression, causing message corruption or silent drops.

## Solution

Use raw TCP WebSocket implementation with `asyncio` — manual HTTP upgrade handshake + manual frame parsing. Do NOT accept `Sec-WebSocket-Extensions` in the upgrade response.

Key implementation details:

```python
# HTTP upgrade response WITHOUT extensions
response = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    f"Sec-WebSocket-Accept: {accept_key}\r\n"
    # NOTE: do NOT include Sec-WebSocket-Extensions
    "\r\n"
)

# Frame reading — handle masked frames (client → server)
async def ws_read_frame(reader):
    header = await reader.readexactly(2)
    opcode = header[0] & 0x0F
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
    
    return opcode, payload

# Frame writing — unmasked (server → client)
async def ws_send_frame(writer, payload: bytes, op: int = 0x1):
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

OpCodes: 0x1=text, 0x8=close, 0x9=ping, 0xA=pong.
