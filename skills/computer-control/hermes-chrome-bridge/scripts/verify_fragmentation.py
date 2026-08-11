"""Verify WS fragmentation reassembly in bridge server."""
import asyncio, struct, sys, os

BRIDGE = r'C:\Users\thang\Downloads\_projects\hermes-chrome-extension\hermes_bridge_server.py'

class FakeReader:
    def __init__(self, data): self._data, self._pos = data, 0
    async def readexactly(self, n):
        chunk = self._data[self._pos:self._pos+n]; self._pos += n
        if len(chunk) < n: raise asyncio.IncompleteReadError(chunk, n)
        return chunk

def build_frame(payload, fin=True):
    mask = os.urandom(4)
    return bytes([(0x80 if fin else 0x00)|0x01, 0x80|len(payload)]) + mask + bytes(b^mask[i%4] for i,b in enumerate(payload))

sys.path.insert(0, os.path.dirname(BRIDGE))
import hermes_bridge_server as b

async def tests():
    passed = total = 0
    # Single frame
    p = b'{"type":"pong"}'
    op, res = await b.read_frame(FakeReader(build_frame(p)))
    assert op == 1 and res == p, f"single: {res}"
    print("[PASS] single_frame"); total += 1; passed += 1

    # 2 fragments
    p1, p2 = b'{"a":', b'"b"}'
    data = build_frame(p1, False) + build_frame(p2)
    op, res = await b.read_frame(FakeReader(data))
    assert op == 1 and res == p1+p2, f"frag2: {res}"
    print("[PASS] fragmented_2"); total += 1; passed += 1

    # 3 fragments (large)
    parts = [b'{"x":"', b'y'*500, b'"}']
    data = b''.join(build_frame(p, i==len(parts)-1) for i,p in enumerate(parts))
    op, res = await b.read_frame(FakeReader(data))
    assert op == 1 and len(res)==sum(len(p) for p in parts), f"frag3: len={len(res)}"
    print(f"[PASS] fragmented_3 ({len(res)} bytes)"); total += 1; passed += 1

    print(f"\n{passed}/{total} passed")
    return passed == total

if not asyncio.run(tests()): sys.exit(1)
