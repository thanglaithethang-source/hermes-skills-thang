# SFX/BGM Hunting Pattern

## Freesound API

Token: `r7EZFGAUP9iKxnPLLghnZ7WuWdUkjMGFAmbeh9Xs`

### Search
```
GET https://freesound.org/apiv2/search/text/?query={query}&token={token}&page_size=10&fields=id,name,duration,previews
```
- Query ngắn, broad: `whoosh`, `drum hit`, `campfire`, `cartoon pop`
- Query dài trả về 0 results
- Với BGM: KHÔNG dùng `&filter=duration:[10.0 TO *]` (giảm results về 0). Sort thủ công.

### Download preview — NO FFMPEG (Sếp cấm tuyệt đối 2026-07-31)
```
preview-hq-mp3 từ CDN: https://cdn.freesound.org/previews/XX/XXXXX_XXXXXX-hq.mp3
```
- Không cần auth cho CDN URL
- Dùng User-Agent header để tránh block
- **Lưu MP3 trực tiếp, KHÔNG convert sang WAV bằng ffmpeg.** Sếp cấm dùng ffmpeg cho âm thanh.
- Synthetic fallback dùng Python `wave` module (xem bên dưới).

## Parallel Download Pattern

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def hunt(dir, filename, query, min_bytes):
    fp = os.path.join(dir, filename)
    if os.path.exists(fp) and os.path.getsize(fp) >= min_bytes:
        return "SKIP"
    # search → get preview URL → download → save
    ...

tasks = [(dir, fn, query, min_bytes) for ...]
with ThreadPoolExecutor(max_workers=6) as ex:
    futures = {ex.submit(hunt, *t): t for t in tasks}
    for f in as_completed(futures):
        print(f.result())
```

- 5-8 workers là tối ưu (API rate limit Freesound không chặn ở mức này)
- `min_bytes` cho beat SFX: 500, ambience: 8000, BGM: 10000-50000
- Luôn skip file đã tồn tại + đủ size

## Synthetic Fallback

Khi Freesound không có kết quả, sinh bằng Python `wave`:

```python
import wave, struct, math

def gen_beat(filepath, freq, dur, sr=24000):
    n = int(sr * dur)
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 4)  # decay
            val = int(0.4 * env * 32767 * math.sin(2*math.pi*freq*t))
            wf.writeframesraw(struct.pack('<h', val))
```

- Beat SFX: sine wave với envelope decay (50-600Hz, 0.2-1.5s)
- Ambience: white/pink noise, dài 3-10s, amplitude thấp
- Dùng WAV 24kHz mono cho tương thích CapCut

## Known Quirks

- Pixabay API trả photos, không music (dù có param `category=music`)
- Pexels API: 403 (key hết hạn)
- Freesound: một số query trả 0 results dù category rộng → thử query siêu ngắn (1 từ)
- BGM từ Freesound: chất lượng preview MP3 thường ngắn (30-120s), đủ cho short loop
- **EXECUTE_CODE ENCODING PITFALL (2026-07-22):** Python `requests` library inside `execute_code` may fail ALL Freesound searches with `'latin-1' codec can't encode character` error. This is triggered when the HTTP request processing path encounters Unicode in the Python environment. When this happens, every query fails silently and ALL SFX/BGM fall back to synthetic. **Mitigation:** run Freesound downloads from `terminal` (subprocess via bash) instead of `execute_code`, or ensure PYTHONUTF8=1 is set before importing requests. If all queries fail identically, suspect this encoding issue before assuming no results.
